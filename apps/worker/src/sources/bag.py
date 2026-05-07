"""BAG client via PDOK OGC API (open, geen key vereist).

Endpoint: https://api.pdok.nl/kadaster/bag/ogc/v2/
Documentatie: https://api.pdok.nl/kadaster/bag/ogc/v2/

Pand-data (bouwjaar, gebruiksdoel) zit op de pand-collectie.
Oppervlakte zit op verblijfsobjecten (VBO's), gelinkt via pand.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import httpx

log = logging.getLogger(__name__)

_BASE = "https://api.pdok.nl/kadaster/bag/ogc/v2/collections"


@dataclass
class BagPand:
    pand_id: str
    bouwjaar: int | None
    status: str | None
    gebruiksdoelen: list[str] = field(default_factory=list)
    oppervlakte_min: int | None = None
    oppervlakte_max: int | None = None
    geometrie_geojson: dict | None = None   # GeoJSON polygon voor PostGIS


@dataclass
class BagVbo:
    vbo_id: str
    pand_id: str
    gebruiksdoel: str | None
    oppervlakte: int | None
    rd_x: float | None
    rd_y: float | None


def get_pand_from_vbo(vbo_id: str) -> BagPand | None:
    """
    Zoek pandgegevens op via een VBO-id (adresseerbaarobject_id van Locatieserver).
    Workflow: VBO ophalen → pand.href URL → pand ophalen.
    """
    url = f"{_BASE}/verblijfsobject/items"
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, params={"identificatie": vbo_id, "f": "json"})
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("BAG VBO lookup mislukt voor %s: %s", vbo_id, exc)
        return None

    features = resp.json().get("features", [])
    if not features:
        return None

    props = features[0].get("properties", {})
    pand_hrefs = props.get("pand.href", [])
    if not pand_hrefs:
        return None

    # Haal het eerste pand op via de UUID-URL
    pand_uuid_url = pand_hrefs[0]
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(pand_uuid_url, params={"f": "json"})
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("BAG pand UUID-lookup mislukt: %s", exc)
        return None

    pand_data = resp.json()
    pand_props = pand_data.get("properties", {})
    pand_id = pand_props.get("identificatie")
    if not pand_id:
        return None

    # Verzamel alle VBO-oppervlaktes voor min/max berekening
    all_opps = [props.get("oppervlakte")] if props.get("oppervlakte") else []
    gebruiksdoel_raw = pand_props.get("gebruiksdoel", "")
    gebruiksdoelen = (
        [g.strip() for g in gebruiksdoel_raw.split(",") if g.strip()]
        if isinstance(gebruiksdoel_raw, str) else gebruiksdoel_raw or []
    )

    pand = BagPand(
        pand_id=pand_id,
        bouwjaar=int(pand_props["bouwjaar"]) if pand_props.get("bouwjaar") else None,
        status=pand_props.get("status"),
        gebruiksdoelen=gebruiksdoelen,
        geometrie_geojson=pand_data.get("geometry"),
        oppervlakte_min=min(all_opps) if all_opps else None,
        oppervlakte_max=max(all_opps) if all_opps else None,
    )
    return pand


def get_pand(pand_id: str, *, retries: int = 3) -> BagPand | None:
    """Haal pandgegevens op voor het gegeven BAG pand_id (identificatie)."""
    url = f"{_BASE}/pand/items"
    params = {
        "identificatie": pand_id,
        "f": "json",
        "crs": "http://www.opengis.net/def/crs/EPSG/0/28992",  # RD New
    }

    for attempt in range(retries):
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(url, params=params)
        except httpx.HTTPError as exc:
            log.warning("BAG pand request mislukt (poging %d): %s", attempt + 1, exc)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            continue

        if resp.status_code == 404:
            return None

        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            log.warning("BAG pand HTTP-fout: %s", exc)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            continue

        features = resp.json().get("features", [])
        if not features:
            log.debug("BAG: geen features voor pand_id %s", pand_id)
            return None

        return _parse_pand_feature(features[0], pand_id)

    return None


def get_vbos_for_pand(pand_id: str) -> list[BagVbo]:
    """Haal verblijfsobjecten op voor een pand."""
    url = f"{_BASE}/verblijfsobject/items"
    params = {
        "pandIdentificatie": pand_id,
        "f": "json",
        "limit": 100,
        "crs": "http://www.opengis.net/def/crs/EPSG/0/28992",
    }

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("BAG VBO request mislukt voor pand %s: %s", pand_id, exc)
        return []

    results = []
    for feature in resp.json().get("features", []):
        vbo = _parse_vbo_feature(feature, pand_id)
        if vbo:
            results.append(vbo)
    return results


def _parse_pand_feature(feature: dict, pand_id: str) -> BagPand | None:
    try:
        props = feature.get("properties", {})
        geom = feature.get("geometry")

        bouwjaar_raw = props.get("bouwjaar") or props.get("oorspronkelijkBouwjaar")
        gebruiksdoel = props.get("gebruiksdoel") or props.get("gebruiksfunctie")

        # gebruiksdoel kan string of list zijn
        if isinstance(gebruiksdoel, str):
            gebruiksdoelen = [gebruiksdoel]
        elif isinstance(gebruiksdoel, list):
            gebruiksdoelen = gebruiksdoel
        else:
            gebruiksdoelen = []

        return BagPand(
            pand_id=pand_id,
            bouwjaar=int(bouwjaar_raw) if bouwjaar_raw else None,
            status=props.get("status"),
            gebruiksdoelen=gebruiksdoelen,
            geometrie_geojson=geom,
        )
    except (KeyError, TypeError, ValueError) as exc:
        log.warning("Kon BAG panddata niet parsen: %s", exc)
        return None


def _parse_vbo_feature(feature: dict, pand_id: str) -> BagVbo | None:
    try:
        props = feature.get("properties", {})
        vbo_id = props.get("identificatie") or feature.get("id", "")

        gebruiksdoel = props.get("gebruiksdoel") or props.get("gebruiksfunctie")
        if isinstance(gebruiksdoel, list):
            gebruiksdoel = gebruiksdoel[0] if gebruiksdoel else None

        oppervlakte = props.get("oppervlakte")

        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", []) if geom else []
        rd_x = float(coords[0]) if len(coords) >= 2 else None
        rd_y = float(coords[1]) if len(coords) >= 2 else None

        return BagVbo(
            vbo_id=str(vbo_id),
            pand_id=pand_id,
            gebruiksdoel=gebruiksdoel,
            oppervlakte=int(oppervlakte) if oppervlakte else None,
            rd_x=rd_x,
            rd_y=rd_y,
        )
    except (KeyError, TypeError, ValueError) as exc:
        log.warning("Kon BAG VBO niet parsen: %s", exc)
        return None
