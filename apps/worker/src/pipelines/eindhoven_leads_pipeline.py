"""Eindhoven vergunningen → sloop_leads pipeline.

Haalt sloopvergunningen op van Gemeente Eindhoven en voegt ze direct toe
als sloop_leads (source_type = 'eindhoven_vergunning').

BAG-lookup via PDOK voor pand_id en coördinaten.
Scoring: eenvoudige heuristiek op basis van status, omvang, bouwjaar.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from supabase import create_client, Client

from ..sources.pipeline.eindhoven_vergunning_adapter import (
    EindhovenVergunningAdapter,
    _wgs84_to_rd,
)
from ..sources.pdok import geocode_address
from ..sources.bag import get_pand_from_vbo
from ..scoring.scores import calculate_total_score

log = logging.getLogger(__name__)


def run(lookback_days: int = 90) -> dict:
    """Voert de Eindhoven vergunningen → sloop_leads pipeline uit."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    sb = create_client(url, key)

    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    adapter = EindhovenVergunningAdapter()

    # Haal alle sloop vergunningen op
    parsed = []
    for raw in adapter.fetch_signals(since):
        signal = adapter.parse_signal(raw)
        if signal:
            parsed.append((raw.source_id, signal))

    # Dedupliceer op zaaknummer
    seen: dict[str, Any] = {}
    for zaaknummer, signal in parsed:
        seen[zaaknummer] = signal
    unique_signals = list(seen.values())

    log.info("[eindhoven_leads] %d unieke vergunningen opgehaald", len(unique_signals))

    stats = {"upserted": 0, "geocoded": 0, "errors": 0}

    for signal in unique_signals:
        try:
            row = _build_lead_row(signal)
            _upsert_lead(sb, row, signal.source_id)
            stats["upserted"] += 1
        except Exception as exc:
            log.warning("[eindhoven_leads] Fout voor %s: %s", signal.source_id, exc)
            stats["errors"] += 1

    log.info("[eindhoven_leads] Klaar: %s", stats)
    return stats


def _build_lead_row(signal) -> dict:
    """Bouw een sloop_leads rij van een ParsedSignal (Eindhoven vergunning)."""
    address_full = None
    postcode = signal.postcode
    geometry_ewkt = signal.geometry_ewkt
    bag_pand_id = None

    # Geocoding via PDOK voor bag_pand_id
    if signal.address_text:
        try:
            geo = geocode_address(signal.address_text)
            if geo:
                postcode = postcode or geo.postcode
                if not geometry_ewkt and geo.rd_x and geo.rd_y:
                    geometry_ewkt = f"SRID=28992;POINT({geo.rd_x} {geo.rd_y})"
                if geo.vbo_id:
                    pand = get_pand_from_vbo(geo.vbo_id)
                    if pand:
                        bag_pand_id = pand.pand_id
        except Exception as exc:
            log.debug("Geocoding mislukt voor '%s': %s", signal.address_text, exc)

    # Score bepalen op basis van vergunningsstatus
    # verleende vergunning = hogere score dan aangevraagde
    if signal.signal_type == "verleende_sloopvergunning":
        score_total = 65  # Hoog: vergunning al verleend
        asbest_score = 30
    else:
        score_total = 45  # Matig: aanvraag ingediend
        asbest_score = 20

    # Extraheer adresgegevens
    adres = signal.address_text or ""
    if adres.endswith(", Eindhoven"):
        adres = adres[:-len(", Eindhoven")]

    return {
        "sloopmelding_id": None,
        "source_type": "eindhoven_vergunning",
        "address_full": adres,
        "gemeente": "Eindhoven",
        "provincie": "Noord-Brabant",
        "postcode": postcode,
        "geometry": geometry_ewkt,
        "pand_id": None,  # Geen FK-koppeling — Eindhoven panden staan niet in bag_panden
        "score_total": score_total,
        "asbest_risico_score": asbest_score,
        "omvang_score": 50,
        "bereikbaarheid_score": 60,  # Noord-Brabant: goed bereikbaar
        "circulair_potentieel": 30,
        "eigenaar_type": signal.eigenaar_type if signal.eigenaar_type != "onbekend" else "onbekend",
        "datum_publicatie": signal.signal_time.date().isoformat() if signal.signal_time else None,
        "koop_url": signal.source_url,
        "tender_window_estimate_weeks": 8 if signal.signal_type == "verleende_sloopvergunning" else 16,
    }


def _upsert_lead(sb: Client, row: dict, zaaknummer: str) -> None:
    """Upsert een lead op basis van source_type + adres (want geen sloopmelding_id)."""
    # Zoek op source_type + address_full als unieke sleutel
    existing = (
        sb.table("sloop_leads")
        .select("id")
        .eq("source_type", "eindhoven_vergunning")
        .eq("address_full", row.get("address_full", ""))
        .limit(1)
        .execute()
    )

    if existing.data:
        lead_id = existing.data[0]["id"]
        sb.table("sloop_leads").update(row).eq("id", lead_id).execute()
    else:
        sb.table("sloop_leads").insert(row).execute()
