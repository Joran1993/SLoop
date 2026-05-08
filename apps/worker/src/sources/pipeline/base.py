"""Base interface voor alle pipeline-signaalbronnen."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator

log = logging.getLogger(__name__)


@dataclass
class RawSignal:
    source_id: str
    raw_payload: dict
    source_url: str | None = None


@dataclass
class ParsedSignal:
    source: str
    source_id: str
    signal_type: str
    signal_strength: str          # 'high' | 'medium' | 'low'
    signal_time: datetime
    title: str | None
    description: str | None
    address_text: str | None
    postcode: str | None
    gemeente: str | None
    bag_pand_id: str | None
    geometry_ewkt: str | None     # SRID=28992;POINT(x y) of POLYGON(...)
    source_url: str | None
    raw_payload: dict
    estimated_horizon_months_min: int
    estimated_horizon_months_max: int
    eigenaar_type: str = "onbekend"
    eigenaar_naam: str | None = None


def geojson_to_ewkt(geojson: dict | None, srid: int = 28992) -> str | None:
    """Converteer GeoJSON geometry naar PostGIS EWKT string."""
    if not geojson:
        return None
    geom_type = geojson.get("type", "")
    coords = geojson.get("coordinates", [])

    try:
        if geom_type == "Point" and len(coords) >= 2:
            return f"SRID={srid};POINT({coords[0]} {coords[1]})"

        if geom_type == "Polygon" and coords:
            return f"SRID={srid};POINT({_polygon_centroid(coords)})"

        if geom_type == "MultiPolygon" and coords:
            # Centroid van eerste polygon
            return f"SRID={srid};POINT({_polygon_centroid(coords[0])})"
    except (IndexError, TypeError, ValueError):
        return None
    return None


def _polygon_centroid(rings: list) -> str:
    """Geef centroid van een polygon-ring als 'x y' string."""
    ring = rings[0] if rings and isinstance(rings[0][0], (int, float, list)) else rings
    # Als ring[0] zelf een list is, is het een polygon met outer ring
    if ring and isinstance(ring[0], list):
        ring = ring[0]
    xs = [c[0] for c in ring if isinstance(c, (list, tuple)) and len(c) >= 2]
    ys = [c[1] for c in ring if isinstance(c, (list, tuple)) and len(c) >= 2]
    if not xs:
        raise ValueError("Lege ring")
    return f"{sum(xs)/len(xs)} {sum(ys)/len(ys)}"


class PipelineSourceAdapter(ABC):
    source_name: str
    cron_schedule: str  # cron-expressie, bv "0 */6 * * *"

    @abstractmethod
    def fetch_signals(self, since: datetime) -> Iterator[RawSignal]:
        """Haalt nieuwe signalen op vanaf since. Sync iterator."""

    @abstractmethod
    def parse_signal(self, raw: RawSignal) -> ParsedSignal | None:
        """Normaliseert naar ParsedSignal. Geeft None terug als niet relevant."""

    def resolve_location(self, parsed: ParsedSignal) -> ParsedSignal:
        """
        Probeert adres → BAG pand_id te resolven via PDOK Locatieserver.
        Vult ook postcode, gemeente en geometry_ewkt in als die ontbreken.
        """
        if not parsed.address_text:
            return parsed
        if parsed.bag_pand_id and parsed.geometry_ewkt:
            return parsed

        try:
            from ..pdok import geocode_address
            from ..bag import get_pand_from_vbo

            geo = geocode_address(parsed.address_text)
            if not geo:
                return parsed

            if not parsed.postcode and geo.postcode:
                parsed.postcode = geo.postcode
            if not parsed.gemeente and geo.gemeente:
                parsed.gemeente = geo.gemeente

            if not parsed.geometry_ewkt and geo.rd_x and geo.rd_y:
                parsed.geometry_ewkt = f"SRID=28992;POINT({geo.rd_x} {geo.rd_y})"

            if not parsed.bag_pand_id and geo.vbo_id:
                pand = get_pand_from_vbo(geo.vbo_id)
                if pand:
                    parsed.bag_pand_id = pand.pand_id
        except Exception as exc:
            log.debug("Location-resolve mislukt voor '%s': %s", parsed.address_text, exc)

        return parsed
