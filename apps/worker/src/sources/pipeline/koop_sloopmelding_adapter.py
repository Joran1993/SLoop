"""Bron 1b: KOOP sloopmeldingen — omzetting van sloop_leads naar pipeline_signals.

Signaalwaarde: 1-6 maanden vóór sloop. Horizon: 1-6 maanden.

Leest uit de Supabase-tabel sloop_leads (reeds verrijkt en gescoord via koop_pipeline).
Sterkste signaaltype: directe sloopmelding met geometrie en score.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Iterator

from supabase import create_client

from .base import PipelineSourceAdapter, ParsedSignal, RawSignal
from ..kvk_lookup import infer_eigenaar_type_from_bag

log = logging.getLogger(__name__)


def _geojson_point_to_ewkt(geom: dict | None) -> str | None:
    """Converteer GeoJSON Point dict (EPSG:28992) naar PostGIS EWKT string."""
    if not geom or not isinstance(geom, dict):
        return None
    try:
        coords = geom["coordinates"]
        return f"SRID=28992;POINT({coords[0]} {coords[1]})"
    except (KeyError, IndexError, TypeError):
        return None


class KoopSloopMeldingAdapter(PipelineSourceAdapter):
    source_name = "koop_sloopmelding"
    cron_schedule = "0 */6 * * *"  # elke 6 uur

    def fetch_signals(self, since: datetime) -> Iterator[RawSignal]:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        sb = create_client(url, key)

        since_str = since.isoformat()

        # Haal leads op die na `since` aangemaakt zijn
        result = (
            sb.table("sloop_leads")
            .select("*")
            .gte("created_at", since_str)
            .limit(1000)
            .execute()
        )
        rows = result.data or []
        log.info("[%s] %d leads opgehaald", self.source_name, len(rows))

        for row in rows:
            # Gebruik sloopmelding_id als unieke identifier
            source_id = row.get("sloopmelding_id") or row["id"]
            yield RawSignal(
                source_id=source_id,
                raw_payload=row,
                source_url=row.get("koop_url"),
            )

    def parse_signal(self, raw: RawSignal) -> ParsedSignal | None:
        row = raw.raw_payload

        geom_ewkt = _geojson_point_to_ewkt(row.get("geometry"))

        datum_str = row.get("created_at", "")
        try:
            signal_time = datetime.fromisoformat(datum_str.rstrip("Z")).replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            signal_time = datetime.now(timezone.utc)

        postcode = row.get("postcode") or ""
        gemeente = row.get("gemeente") or ""
        adres = row.get("address_full") or None

        # Gebruik bestaand eigenaar_type of infereer via BAG-heuristiek
        eigenaar_type = row.get("eigenaar_type") or ""
        if not eigenaar_type or eigenaar_type == "onbekend":
            gebruiksdoelen = row.get("gebruiksdoelen") or []
            bouwjaar = row.get("bouwjaar")
            eigenaar_type = infer_eigenaar_type_from_bag(gebruiksdoelen, bouwjaar)

        return ParsedSignal(
            source=self.source_name,
            source_id=raw.source_id,
            signal_type="sloopmelding",
            signal_strength="high",
            signal_time=signal_time,
            title=adres or f"Sloopmelding {gemeente}",
            description=None,
            address_text=adres,
            postcode=postcode or None,
            gemeente=gemeente or None,
            bag_pand_id=row.get("pand_id") or None,
            geometry_ewkt=geom_ewkt,
            source_url=raw.source_url,
            raw_payload=row,
            estimated_horizon_months_min=1,
            estimated_horizon_months_max=6,
            eigenaar_type=eigenaar_type,
        )
