"""PDOK Locatieserver client — adres naar BAG pand_id + RD-coördinaten."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)

_FREE_ENDPOINT = "https://api.pdok.nl/bzk/locatieserver/search/v3_1"
_LOOKUP_ENDPOINT = f"{_FREE_ENDPOINT}/lookup"
_SUGGEST_ENDPOINT = f"{_FREE_ENDPOINT}/free"


@dataclass
class GeoResult:
    vbo_id: str | None        # adresseerbaarobject_id — VBO identificatie
    rd_x: float | None        # EPSG:28992
    rd_y: float | None
    wgs_lon: float | None
    wgs_lat: float | None
    address_full: str | None
    postcode: str | None
    gemeente: str | None
    provincie: str | None
    score: float = 0.0


def geocode_address(address: str, *, retries: int = 3) -> GeoResult | None:
    """
    Zoek een adres op via PDOK Locatieserver en geef het beste resultaat terug.
    Retourneert None als niets gevonden of bij een onherstelbare fout.
    """
    params = {
        "q": address,
        "fq": "type:(adres OR pand)",
        "fl": "id,identificatie,adresseerbaarobject_id,weergavenaam,postcode,"
              "woonplaatsnaam,gemeentenaam,provincienaam,centroide_rd,centroide_ll",
        "rows": 1,
    }

    for attempt in range(retries):
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(_SUGGEST_ENDPOINT, params=params)
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("PDOK free request mislukt (poging %d): %s", attempt + 1, exc)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            continue

        data = resp.json()
        docs = data.get("response", {}).get("docs", [])
        if not docs:
            return None

        doc = docs[0]
        return _parse_doc(doc)

    return None


def lookup_by_id(pdok_id: str) -> GeoResult | None:
    """Directe lookup op PDOK-object-ID voor gedetailleerdere data."""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(_LOOKUP_ENDPOINT, params={"id": pdok_id})
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("PDOK lookup mislukt voor %s: %s", pdok_id, exc)
        return None

    data = resp.json()
    docs = data.get("response", {}).get("docs", [])
    return _parse_doc(docs[0]) if docs else None


def _parse_doc(doc: dict) -> GeoResult:
    rd_x, rd_y = _parse_centroide(doc.get("centroide_rd"))
    lon, lat = _parse_centroide(doc.get("centroide_ll"))

    return GeoResult(
        vbo_id=doc.get("adresseerbaarobject_id"),
        rd_x=rd_x,
        rd_y=rd_y,
        wgs_lon=lon,
        wgs_lat=lat,
        address_full=doc.get("weergavenaam"),
        postcode=doc.get("postcode"),
        gemeente=doc.get("gemeentenaam"),
        provincie=doc.get("provincienaam"),
        score=float(doc.get("score", 0)),
    )


def _parse_centroide(value: str | None) -> tuple[float | None, float | None]:
    """Parse 'POINT(x y)' naar (x, y)."""
    if not value or not value.startswith("POINT("):
        return None, None
    try:
        coords = value[6:-1].split()
        return float(coords[0]), float(coords[1])
    except (IndexError, ValueError):
        return None, None
