"""KOOP SRU → Supabase pipeline.

Stappen:
1. Haal nieuwe sloopmeldingen op via KOOP SRU API
2. Upsert naar sloopmeldingen_raw
3. Geocodeer adressen via PDOK Locatieserver
4. Haal BAG-panddata op (indien API-key beschikbaar)
5. Haal EP-Online energielabel op
6. Deriveer en score de lead → upsert sloop_leads
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from supabase import create_client, Client

from ..config import settings
from ..sources.koop import build_query, fetch_page, parse_response
from ..sources.pdok import geocode_address
from ..sources.bag import get_pand, get_pand_from_vbo, get_vbos_for_pand
from ..sources.eponline import get_label_for_address
from ..scoring.scores import calculate_total_score, estimate_materiaalvolumes

log = logging.getLogger(__name__)

_RE_POSTCODE = re.compile(r"\b(\d{4}\s?[A-Z]{2})\b")
_RE_HUISNUMMER = re.compile(r"\b(\d{1,5}[a-zA-Z]?)\b")

import requests


def run(lookback_days: int | None = None) -> dict:
    """Voer de volledige KOOP pipeline uit. Retourneert statistieken."""
    days = lookback_days or settings.koop_lookback_days
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    log.info("KOOP pipeline: ophalen meldingen vanaf %s", since)
    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)

    # 1. Haal meldingen op
    records = _fetch_all_records(since)
    log.info("KOOP: %d publicaties opgehaald", len(records))

    # 2. Upsert naar sloopmeldingen_raw
    new_ids = _upsert_meldingen(supabase, records)
    log.info("KOOP: %d nieuwe meldingen geüpsert", len(new_ids))

    # 3-6. Verwerk elke nieuwe melding
    stats = {"geocoded": 0, "bag_enriched": 0, "ep_enriched": 0, "leads_created": 0}
    for melding_id in new_ids:
        row = supabase.table("sloopmeldingen_raw").select("*").eq("id", melding_id).single().execute()
        if row.data:
            _enrich_and_score(supabase, row.data, stats)

    log.info("Pipeline klaar: %s", stats)
    return stats


def _fetch_all_records(since: str) -> list[dict]:
    query = build_query(since)
    session = requests.Session()
    session.headers["User-Agent"] = "SloopradarWorker/1.0"

    all_records: list[dict] = []
    start = 1
    while True:
        xml_bytes = fetch_page(query, start, 100, session)
        total, next_pos, records = parse_response(xml_bytes)
        all_records.extend(records)
        if not records or next_pos is None or (total and next_pos > total):
            break
        start = next_pos

    return all_records


def _upsert_meldingen(supabase: Client, records: list[dict]) -> list[str]:
    """Upsert records, retourneer IDs van nieuw ingevoegde rijen."""
    new_ids = []
    for rec in records:
        koop_id = rec.get("document_id") or rec.get("identifier", "")
        if not koop_id:
            continue

        row = {
            "koop_id": koop_id,
            "preferred_url": rec.get("identifier"),
            "gemeente": rec.get("gemeente"),
            "datum_publicatie": rec.get("publicatiedatum"),
            "publicatietype": rec.get("publicatietype"),
            "titel": rec.get("titel"),
            "parsed": rec,
            "address_text": rec.get("snippet"),
            "matched_keywords": rec.get("matched_keywords", []),
            "parse_status": "ok",
        }

        result = (
            supabase.table("sloopmeldingen_raw")
            .upsert(row, on_conflict="koop_id", ignore_duplicates=True)
            .execute()
        )
        if result.data:
            new_ids.extend([r["id"] for r in result.data])

    return new_ids


def _enrich_and_score(supabase: Client, melding: dict, stats: dict) -> None:
    """Geocodeer, verrijk met BAG/EP, maak lead aan."""
    address_text = melding.get("address_text") or melding.get("titel") or ""
    melding_id = melding["id"]

    # 3. Geocodeer
    geo = geocode_address(address_text)
    if not geo:
        log.debug("Geocoding mislukt voor melding %s", melding_id)
        supabase.table("sloopmeldingen_raw").update({
            "geocode_attempts": melding.get("geocode_attempts", 0) + 1,
            "geocode_status": "not_found",
        }).eq("id", melding_id).execute()
        return

    stats["geocoded"] += 1

    # Geometry als WKT voor PostGIS (RD New)
    geometry_wkt = None
    if geo.rd_x and geo.rd_y:
        geometry_wkt = f"SRID=28992;POINT({geo.rd_x} {geo.rd_y})"

    # 4. BAG: VBO-id → pand
    bag_pand = None
    if geo.vbo_id:
        bag_pand = get_pand_from_vbo(geo.vbo_id)
        if bag_pand:
            stats["bag_enriched"] += 1
            _upsert_bag_pand(supabase, bag_pand)
            vbos = get_vbos_for_pand(bag_pand.pand_id)
            for vbo in vbos:
                _upsert_bag_vbo(supabase, vbo)

    pand_id = bag_pand.pand_id if bag_pand else None

    supabase.table("sloopmeldingen_raw").update({
        "geocode_status": "ok",
        "geocode_attempts": melding.get("geocode_attempts", 0) + 1,
        "bag_pand_id": pand_id,
    }).eq("id", melding_id).execute()

    # 5. EP-Online
    ep_label = None
    if geo.postcode and geo.address_full:
        huisnummer = _extract_huisnummer(geo.address_full)
        if huisnummer:
            ep_label = get_label_for_address(geo.postcode, huisnummer)
            if ep_label:
                stats["ep_enriched"] += 1
                _upsert_ep_label(supabase, ep_label, pand_id)

    # 6. Lead aanmaken / updaten
    bouwjaar = bag_pand.bouwjaar if bag_pand else None
    oppervlakte = bag_pand.oppervlakte_max if bag_pand else None
    gebruiksdoelen = bag_pand.gebruiksdoelen if bag_pand else []
    energielabel = ep_label.energielabel if ep_label else None

    score = calculate_total_score(bouwjaar, oppervlakte, energielabel)
    volumes = estimate_materiaalvolumes(gebruiksdoelen, oppervlakte)

    provincie = geo.provincie or _provincie_from_gemeente(melding.get("gemeente", ""))

    lead_row = {
        "sloopmelding_id": melding_id,
        "pand_id": pand_id,
        "address_full": geo.address_full,
        "postcode": geo.postcode,
        "gemeente": geo.gemeente or melding.get("gemeente", ""),
        "provincie": provincie,
        "bouwjaar": bouwjaar,
        "oppervlakte_m2": oppervlakte,
        "gebruiksdoelen": gebruiksdoelen,
        "energielabel": energielabel,
        "asbest_risico_score": score.asbest_risico,
        "omvang_score": score.omvang,
        "bereikbaarheid_score": score.bereikbaarheid,
        "circulair_potentieel": score.circulair,
        "score_total": score.total,
        "score_breakdown": {
            "asbest_risico": score.asbest_risico,
            "omvang": score.omvang,
            "bereikbaarheid": score.bereikbaarheid,
            "circulair": score.circulair,
            "weights": score.weights_used,
        },
        "materiaal_volume_estimate": volumes,
        "koop_url": melding.get("preferred_url"),
        "datum_publicatie": melding.get("datum_publicatie"),
        "last_scored_at": datetime.now(timezone.utc).isoformat(),
    }

    supabase.table("sloop_leads").upsert(
        lead_row, on_conflict="sloopmelding_id"
    ).execute()
    stats["leads_created"] += 1


def _upsert_bag_pand(supabase: Client, pand) -> None:
    import json
    row = {
        "pand_id": pand.pand_id,
        "bouwjaar": pand.bouwjaar,
        "status": pand.status,
        "gebruiksdoelen": pand.gebruiksdoelen,
        "oppervlakte_min": pand.oppervlakte_min,
        "oppervlakte_max": pand.oppervlakte_max,
        "last_synced_at": datetime.now(timezone.utc).isoformat(),
    }
    if pand.geometrie_wkt:
        # GeoJSON string opslaan als PostGIS geometry via cast
        row["geometry"] = f"SRID=28992;{pand.geometrie_wkt}"
    supabase.table("bag_panden").upsert(row, on_conflict="pand_id").execute()


def _upsert_bag_vbo(supabase: Client, vbo) -> None:
    row = {
        "vbo_id": vbo.vbo_id,
        "pand_id": vbo.pand_id,
        "gebruiksdoel": vbo.gebruiksdoel,
        "oppervlakte": vbo.oppervlakte,
    }
    if vbo.rd_x and vbo.rd_y:
        row["geometry"] = f"SRID=28992;POINT({vbo.rd_x} {vbo.rd_y})"
    supabase.table("bag_verblijfsobjecten").upsert(row, on_conflict="vbo_id").execute()


def _upsert_ep_label(supabase: Client, ep, pand_id: str | None) -> None:
    row = {
        "postcode": ep.postcode,
        "huisnummer": ep.huisnummer,
        "huisnummertoevoeging": ep.huisnummertoevoeging,
        "energielabel": ep.energielabel,
        "energieklasse": ep.energieklasse,
        "registratiedatum": ep.registratiedatum,
        "geldig_tot": ep.geldig_tot,
        "pand_id": ep.pand_id or pand_id,
        "raw": ep.raw,
    }
    conflict_col = "pand_id" if (ep.pand_id or pand_id) else "vbo_id"
    supabase.table("ep_online_labels").upsert(row, on_conflict=conflict_col).execute()


def _extract_huisnummer(address: str) -> str | None:
    """Extraheer eerste huisnummer uit een adresstring."""
    parts = address.split()
    for part in parts:
        m = _RE_HUISNUMMER.fullmatch(part)
        if m and not part.isalpha():
            return m.group(1)
    return None


def _provincie_from_gemeente(_gemeente: str) -> str | None:
    """Placeholder: provincie-lookup uit gemeentenaam. Vervangen door BAG-data in productie."""
    return None
