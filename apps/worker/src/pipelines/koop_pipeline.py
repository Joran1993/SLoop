"""KOOP SRU → Supabase pipeline."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

import requests
from supabase import create_client, Client

from ..config import settings
from ..sources.koop import build_query, fetch_page, parse_response
from ..sources.pdok import geocode_address
from ..sources.bag import get_pand_from_vbo, get_vbos_for_pand
from ..sources.eponline import get_label_for_address
from ..scoring.scores import calculate_total_score, estimate_sloopindicatoren
from ..sources.kvk_lookup import infer_eigenaar_type_from_bag, infer_eigenaar_type_from_title
from ..sources.corporaties import get_primary_corporatie, get_corporatie_contact
from ..sources.duo_lookup import lookup_school_by_postcode

log = logging.getLogger(__name__)

_RE_HUISNUMMER = re.compile(r"\b(\d{1,5}[a-zA-Z]?)\b")


def run(lookback_days: int | None = None) -> dict:
    days = lookback_days or settings.koop_lookback_days
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    log.info("KOOP pipeline: ophalen meldingen vanaf %s", since)
    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)

    records = _fetch_all_records(since)
    log.info("KOOP: %d publicaties opgehaald", len(records))

    _upsert_meldingen(supabase, records)

    # Bug #3 fix: query voor unenriched records in plaats van upsert-return vertrouwen
    unenriched = _get_unenriched(supabase)
    log.info("KOOP: %d meldingen nog te verrijken", len(unenriched))

    stats = {"geocoded": 0, "bag_enriched": 0, "ep_enriched": 0, "leads_created": 0}
    for melding in unenriched:
        _enrich_and_score(supabase, melding, stats)

    log.info("Pipeline klaar: %s", stats)
    return stats


def _fetch_all_records(since: str) -> list[dict]:
    import time as _time

    query = build_query(since)
    session = requests.Session()
    session.headers["User-Agent"] = "SloopradarWorker/1.0"

    all_records: list[dict] = []
    start = 1
    while True:
        try:
            xml_bytes = fetch_page(query, start, 100, session)
        except RuntimeError as exc:
            log.warning(
                "KOOP fetch mislukt bij startRecord=%d: %s. "
                "Gebruik %d reeds opgehaalde records.",
                start, exc, len(all_records),
            )
            break  # Verwerk wat we al hebben ipv helemaal stoppen

        total, next_pos, records = parse_response(xml_bytes)
        all_records.extend(records)
        if not records or next_pos is None or (total and next_pos > total):
            break
        start = next_pos
        _time.sleep(1)  # Voorkom rate-limiting door KOOP SRU

    return all_records


def _upsert_meldingen(supabase: Client, records: list[dict]) -> None:
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

        # ignore_duplicates=True: bestaande records worden overgeslagen
        supabase.table("sloopmeldingen_raw").upsert(
            row, on_conflict="koop_id", ignore_duplicates=True
        ).execute()


def _get_unenriched(supabase: Client) -> list[dict]:
    """Geef alle meldingen terug die nog niet geocodeerd zijn (geocode_status IS NULL)."""
    result = (
        supabase.table("sloopmeldingen_raw")
        .select("*")
        .is_("geocode_status", "null")
        .limit(500)
        .execute()
    )
    return result.data or []


def _enrich_and_score(supabase: Client, melding: dict, stats: dict) -> None:
    address_text = melding.get("address_text") or melding.get("titel") or ""
    melding_id = melding["id"]

    # Geocodeer
    geo = geocode_address(address_text)
    if not geo:
        log.debug("Geocoding mislukt voor melding %s", melding_id)
        supabase.table("sloopmeldingen_raw").update({
            "geocode_attempts": (melding.get("geocode_attempts") or 0) + 1,
            "geocode_status": "not_found",
        }).eq("id", melding_id).execute()
        return

    stats["geocoded"] += 1

    # Bug #2 + #4 fix: geometry WKT voor PostGIS (EWKT-formaat)
    geometry_wkt = None
    lon: float | None = None
    lat: float | None = None
    if geo.rd_x is not None and geo.rd_y is not None:
        geometry_wkt = f"SRID=28992;POINT({geo.rd_x} {geo.rd_y})"
        lon = geo.wgs_lon
        lat = geo.wgs_lat

    # BAG: VBO → pand
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
        "geocode_attempts": (melding.get("geocode_attempts") or 0) + 1,
        "bag_pand_id": pand_id,
        "provincie": geo.provincie,
        "geometry": geometry_wkt,   # Bug #4 fix
    }).eq("id", melding_id).execute()

    # EP-Online
    ep_label = None
    if geo.postcode and geo.address_full:
        huisnummer = _extract_huisnummer(geo.address_full)
        if huisnummer:
            ep_label = get_label_for_address(geo.postcode, huisnummer)
            if ep_label:
                stats["ep_enriched"] += 1
                _upsert_ep_label(supabase, ep_label, pand_id)

    bouwjaar = bag_pand.bouwjaar if bag_pand else None
    oppervlakte = bag_pand.oppervlakte_max if bag_pand else None
    gebruiksdoelen = bag_pand.gebruiksdoelen if bag_pand else []
    energielabel = ep_label.energielabel if ep_label else None

    provincie = geo.provincie
    gemeente_naam = geo.gemeente or melding.get("gemeente", "")
    score = calculate_total_score(bouwjaar, oppervlakte, energielabel, provincie=provincie, gemeente=gemeente_naam)
    volumes = estimate_sloopindicatoren(gebruiksdoelen, oppervlakte, bouwjaar)
    eigenaar_type = infer_eigenaar_type_from_bag(gebruiksdoelen, bouwjaar)
    if eigenaar_type == "onbekend":
        eigenaar_type = infer_eigenaar_type_from_title(melding.get("titel"))

    eigenaar_naam = None
    contact_info: dict = {}

    # Onderwijs: DUO open data (gratis, hoge trefkans voor PO/VO)
    is_onderwijs = any("onderwijs" in (d or "").lower() for d in gebruiksdoelen)
    if is_onderwijs and geo.postcode:
        duo_info = lookup_school_by_postcode(geo.postcode, _extract_huisnummer(geo.address_full or ""))
        if duo_info:
            eigenaar_naam = duo_info.get("eigenaar_naam")
            eigenaar_type = "overheid_instelling"
            contact_info = {k: v for k, v in duo_info.items() if k != "eigenaar_naam"}

    if not eigenaar_naam and eigenaar_type in ("corporatie_waarschijnlijk", "particulier_of_corporatie"):
        eigenaar_naam = get_primary_corporatie(gemeente_naam)
        contact_info = get_corporatie_contact(eigenaar_naam)

    # Sloopmelding = direct (4-12 weken), aanvraag/voornemen = langer (12-24 weken)
    pub_type = (melding.get("publicatietype") or "").lower()
    if "aanvraag" in pub_type or "voornemen" in pub_type:
        tender_weeks = 16
    else:
        tender_weeks = 8

    lead_row = {
        "sloopmelding_id": melding_id,
        "pand_id": pand_id,
        "address_full": geo.address_full,
        "postcode": geo.postcode,
        "gemeente": geo.gemeente or melding.get("gemeente", ""),
        "provincie": geo.provincie,
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
        "geometry": geometry_wkt,
        "longitude": lon,
        "latitude": lat,
        "titel": melding.get("titel"),
        "koop_publicatie_id": melding.get("document_id") or melding.get("identifier", "").split("/")[-1] or None,
        "eigenaar_type": eigenaar_type,
        "eigenaar_naam": eigenaar_naam,
        **contact_info,
        "tender_window_estimate_weeks": tender_weeks,
        "last_scored_at": datetime.now(timezone.utc).isoformat(),
    }

    supabase.table("sloop_leads").upsert(
        lead_row, on_conflict="sloopmelding_id"
    ).execute()
    stats["leads_created"] += 1


def _upsert_bag_pand(supabase: Client, pand) -> None:
    row = {
        "pand_id": pand.pand_id,
        "bouwjaar": pand.bouwjaar,
        "status": pand.status,
        "gebruiksdoelen": pand.gebruiksdoelen,
        "oppervlakte_min": pand.oppervlakte_min,
        "oppervlakte_max": pand.oppervlakte_max,
        "last_synced_at": datetime.now(timezone.utc).isoformat(),
        # Bug #1 fix: geometrie_wkt bestaat niet, geometrie_geojson is complex
        # om via PostgREST te sturen — voor nu weglaten.
    }
    supabase.table("bag_panden").upsert(row, on_conflict="pand_id").execute()


def _upsert_bag_vbo(supabase: Client, vbo) -> None:
    row = {
        "vbo_id": vbo.vbo_id,
        "pand_id": vbo.pand_id,
        "gebruiksdoel": vbo.gebruiksdoel,
        "oppervlakte": vbo.oppervlakte,
    }
    if vbo.rd_x is not None and vbo.rd_y is not None:
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
    parts = address.split()
    for part in parts:
        m = _RE_HUISNUMMER.fullmatch(part)
        if m and not part.isalpha():
            return m.group(1)
    return None
