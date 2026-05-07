"""BAG Individuele Bevragingen client (Kadaster).

API-key is gratis aan te vragen:
  https://www.pdok.nl/restful-api/-/article/bag-individuele-bevragingen
  (verwerking duurt 1-2 werkdagen)

Zonder key werkt deze client niet. Stel BAG_API_KEY in .env in.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import httpx

from ..config import settings

log = logging.getLogger(__name__)

_BASE = "https://api.bag.kadaster.nl/lvbag/individuelebevragingen/v2"


@dataclass
class BagPand:
    pand_id: str
    bouwjaar: int | None
    status: str | None
    geometrie_wkt: str | None      # WKT van de pandvlak-geometrie
    gebruiksdoelen: list[str] = field(default_factory=list)
    oppervlakte_min: int | None = None
    oppervlakte_max: int | None = None


@dataclass
class BagVbo:
    vbo_id: str
    pand_id: str
    gebruiksdoel: str | None
    oppervlakte: int | None
    rd_x: float | None
    rd_y: float | None


def _headers() -> dict[str, str]:
    return {
        "X-Api-Key": settings.bag_api_key,
        "Accept": "application/hal+json",
        "Accept-Crs": "epsg:28992",
    }


def get_pand(pand_id: str, *, retries: int = 3) -> BagPand | None:
    """Haal pandgegevens op voor het gegeven BAG pand_id."""
    if not settings.bag_api_key:
        log.warning("BAG_API_KEY niet ingesteld — sla BAG-lookup over voor %s", pand_id)
        return None

    url = f"{_BASE}/panden/{pand_id}"
    for attempt in range(retries):
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(url, headers=_headers())
        except httpx.HTTPError as exc:
            log.warning("BAG pand request mislukt (poging %d): %s", attempt + 1, exc)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            continue

        if resp.status_code == 404:
            log.debug("BAG pand niet gevonden: %s", pand_id)
            return None

        if resp.status_code == 401:
            log.error("BAG API-key ongeldig of verlopen")
            return None

        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            log.warning("BAG pand HTTP-fout: %s", exc)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            continue

        return _parse_pand(resp.json())

    return None


def get_vbos_for_pand(pand_id: str) -> list[BagVbo]:
    """Haal verblijfsobjecten op voor een pand."""
    if not settings.bag_api_key:
        return []

    url = f"{_BASE}/verblijfsobjecten"
    params = {"pandIdentificatie": pand_id, "pageSize": 100}

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, headers=_headers(), params=params)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("BAG VBO request mislukt voor pand %s: %s", pand_id, exc)
        return []

    results = []
    for item in resp.json().get("_embedded", {}).get("verblijfsobjecten", []):
        vbo = _parse_vbo(item, pand_id)
        if vbo:
            results.append(vbo)
    return results


def _parse_pand(data: dict) -> BagPand | None:
    try:
        pand = data["pand"]
        pand_id = pand["identificatie"]
        bouwjaar = pand.get("oorspronkelijkBouwjaar")
        status = pand.get("status")

        # Geometrie als WKT (Kadaster retourneert GeoJSON, we slaan WKT op)
        geom = pand.get("geometrie", {})
        geom_wkt = _geojson_to_wkt_placeholder(geom)

        return BagPand(
            pand_id=pand_id,
            bouwjaar=int(bouwjaar) if bouwjaar else None,
            status=status,
            geometrie_wkt=geom_wkt,
        )
    except (KeyError, TypeError, ValueError) as exc:
        log.warning("Kon BAG panddata niet parsen: %s", exc)
        return None


def _parse_vbo(item: dict, pand_id: str) -> BagVbo | None:
    try:
        vbo_id = item["identificatie"]
        gebruiksdoel = (item.get("gebruiksdoelen") or [None])[0]
        oppervlakte = item.get("oppervlakte")

        geom = item.get("geometrie", {})
        coords = geom.get("punt", {}).get("coordinates", [])
        rd_x = coords[0] if len(coords) >= 2 else None
        rd_y = coords[1] if len(coords) >= 2 else None

        return BagVbo(
            vbo_id=vbo_id,
            pand_id=pand_id,
            gebruiksdoel=gebruiksdoel,
            oppervlakte=int(oppervlakte) if oppervlakte else None,
            rd_x=float(rd_x) if rd_x else None,
            rd_y=float(rd_y) if rd_y else None,
        )
    except (KeyError, TypeError, ValueError) as exc:
        log.warning("Kon BAG VBO niet parsen: %s", exc)
        return None


def _geojson_to_wkt_placeholder(geom: dict) -> str | None:
    """
    Tijdelijke WKT-conversie voor vlakgeometrie.
    PostGIS kan GeoJSON direct importeren via ST_GeomFromGeoJSON —
    we slaan de GeoJSON op als string en laten de pipeline converteren.
    """
    import json
    if not geom:
        return None
    return json.dumps(geom)
