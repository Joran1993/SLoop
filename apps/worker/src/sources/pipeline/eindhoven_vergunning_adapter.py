"""Bron: Gemeente Eindhoven — aangevraagde omgevingsvergunningen met sloopactiviteit.

Signaalwaarde: 2-12 maanden vóór sloop. Horizon: 2-12 maanden.

Bron: OpenDataSoft API van Gemeente Eindhoven.
Haalt vergunningsaanvragen op waarbij het zaaksubproduct 'Sloop' of 'Slopen' bevat.
Bevat adres, coördinaten (WGS84), datum indiening en status.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterator

import httpx

from .base import PipelineSourceAdapter, ParsedSignal, RawSignal

log = logging.getLogger(__name__)

_BASE_URL = (
    "https://data.eindhoven.nl/api/v2/catalog/datasets"
    "/aangevraagde-vergunningen/exports/json"
)
_FILTER = 'zaaksubproduct_oms like "Sloop" OR zaaksubproduct_oms like "Slopen"'
_PAGE_SIZE = 600  # meer dan genoeg voor alle ~566 records

# Statussen die een verleende vergunning aangeven
_VERLEEND_STATUSES = {"Beschikking vastgesteld", "Zaak afgerond"}


def _wgs84_to_rd(lon: float, lat: float) -> tuple[float, float]:
    """Approximated WGS84 → EPSG:28992 (RD New) polynomial transformation."""
    p = 0.36 * (lat - 52.15517440)
    q = 0.36 * (lon - 5.38720621)
    x = (
        155000.00
        + 190094.945 * q
        + -11832.228 * p * q
        + -114.221 * q ** 3
        + -32.391 * p ** 2
        + -0.705 * q
        + -2.340 * p ** 3 * q
        + -0.608 * p * q ** 3
        + -0.008 * q ** 5
        + 0.148 * p ** 2 * q ** 3
    )
    y = (
        463000.00
        + 309056.544 * p
        + 3638.893 * q ** 2
        + 73.077 * p ** 2
        + -157.984 * p * q ** 2
        + 59.788 * p ** 3
        + 0.433 * q ** 4
        + -6.439 * p ** 2 * q ** 2
        + -0.032 * p
        + 0.092 * p * q ** 4
        + -0.054 * p ** 3 * q ** 2
    )
    return x, y


class EindhovenVergunningAdapter(PipelineSourceAdapter):
    source_name = "eindhoven_vergunning"
    cron_schedule = "0 6 * * *"  # elke dag om 06:00

    def fetch_signals(self, since: datetime) -> Iterator[RawSignal]:
        since_date = since.strftime("%Y-%m-%d")
        where = f'({_FILTER}) AND ddindiening >= "{since_date}"'

        try:
            with httpx.Client(timeout=60, verify=False) as client:
                resp = client.get(_BASE_URL, params={
                    "limit": _PAGE_SIZE,
                    "where": where,
                })
                resp.raise_for_status()
                records = resp.json()
        except Exception as exc:
            log.warning("[%s] Fetch mislukt: %s", self.source_name, exc)
            return

        if not isinstance(records, list):
            log.warning("[%s] Onverwacht response-formaat", self.source_name)
            return

        log.info("[%s] %d vergunningen opgehaald", self.source_name, len(records))
        for rec in records:
            zaaknummer = rec.get("zaaknummer")
            if not zaaknummer:
                continue
            yield RawSignal(
                source_id=zaaknummer,
                raw_payload=rec,
                source_url=None,
            )

    def parse_signal(self, raw: RawSignal) -> ParsedSignal | None:
        rec = raw.raw_payload
        subprod = rec.get("zaaksubproduct_oms", "") or ""
        if "sloop" not in subprod.lower() and "slopen" not in subprod.lower():
            return None

        status = rec.get("status_oms", "") or ""
        is_verleend = status in _VERLEEND_STATUSES

        signal_type = "verleende_sloopvergunning" if is_verleend else "aangevraagde_sloopvergunning"
        signal_strength = "high" if is_verleend else "medium"

        # Datum: gebruik beschikking-datum als die er is, anders indiening
        datum_str = rec.get("ddbeschikking") or rec.get("ddindiening") or ""
        try:
            signal_time = datetime.fromisoformat(datum_str.rstrip("Z")).replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            signal_time = datetime.now(timezone.utc)

        # Adres
        adres = rec.get("adres") or ""
        postcode = rec.get("postcode") or None
        # Eindhoven addresses often miss city; add it
        address_text = f"{adres}, Eindhoven" if adres else None

        # Coördinaten WGS84 → RD New
        geometry_ewkt = None
        geo = rec.get("geo_point_2d")
        if geo and isinstance(geo, dict):
            lon = geo.get("lon")
            lat = geo.get("lat")
            if lon is not None and lat is not None:
                try:
                    x, y = _wgs84_to_rd(float(lon), float(lat))
                    geometry_ewkt = f"SRID=28992;POINT({x:.2f} {y:.2f})"
                except (ValueError, TypeError):
                    pass

        title = rec.get("omschrijving") or subprod
        title = title[:200] if title else None

        # Horizon: vergunning aangevraagd → sloop volgt typisch binnen 3-12 maanden
        horizon_min = 1 if is_verleend else 3
        horizon_max = 6 if is_verleend else 12

        return ParsedSignal(
            source=self.source_name,
            source_id=raw.source_id,
            signal_type=signal_type,
            signal_strength=signal_strength,
            signal_time=signal_time,
            title=title,
            description=subprod[:300] if subprod else None,
            address_text=address_text,
            postcode=postcode,
            gemeente="Eindhoven",
            bag_pand_id=None,
            geometry_ewkt=geometry_ewkt,
            source_url=None,
            raw_payload=rec,
            estimated_horizon_months_min=horizon_min,
            estimated_horizon_months_max=horizon_max,
            eigenaar_type="onbekend",
        )
