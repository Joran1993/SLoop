"""OpenStreetMap Overpass API — zoekt naam/telefoon/website op bij een pand-locatie.

Gratis, geen API key vereist. Goede dekking voor commerciële panden,
scholen, zorginstellingen en overheidsgebouwen in Nederland.

Gebruik:
    from src.sources.osm_lookup import lookup_contact_by_location
    info = lookup_contact_by_location(lon=5.1214, lat=52.0907, radius_m=40)
    # → {"naam": "Kantoor XYZ BV", "telefoon": "030-1234567", "website": "xyz.nl"}
"""
from __future__ import annotations

import logging
import time

import httpx

log = logging.getLogger(__name__)

_OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter"
_TIMEOUT = 15
_CACHE: dict[tuple, dict] = {}

# OSM-tags die we willen ophalen
_USEFUL_TAGS = {"name", "operator", "phone", "contact:phone", "website",
                "contact:website", "email", "contact:email", "brand"}

# Typen die we NIET willen (woonhuizen, parkeerplaatsen, etc.)
_SKIP_AMENITIES = {"parking", "bicycle_parking", "waste_basket", "bench",
                   "post_box", "telephone", "vending_machine"}

_SKIP_BUILDINGS = {"residential", "house", "detached", "semidetached_house",
                   "terrace", "apartments", "dormitory", "bungalow"}

# Suffixen die duiden op administratieve gebieden, niet op gebouwen/bedrijven
_ADMIN_SUFFIXES = (
    "-zuidoost", "-rijnmond", "-waterland", "-brabant", "-groningen",
    "-utrecht", "-friesland", "-limburg", "-zeeland", "veiligheidsregio",
    "ggd ", " regio", " gemeente", " provincie",
)


def lookup_contact_by_location(
    lon: float,
    lat: float,
    radius_m: int = 40,
) -> dict:
    """
    Zoekt het meest relevante OSM-object bij de opgegeven coördinaten.

    Returns dict met subset van: naam, telefoon, website, email
    of leeg dict als niets gevonden.
    """
    cache_key = (round(lon, 4), round(lat, 4), radius_m)
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    # around-only: geen is_in (geeft regiogrenzen terug die onbruikbaar zijn)
    # Uitsluitingen: horeca en consumentendiensten — die zijn geen eigenaar van het pand
    query = f"""
[out:json][timeout:{_TIMEOUT}];
(
  node["name"](around:{radius_m},{lat},{lon})["shop"];
  node["name"](around:{radius_m},{lat},{lon})["office"];
  node["name"](around:{radius_m},{lat},{lon})["tourism"]["tourism"~"hotel|hostel|motel|guest_house|chalet"];
  node["name"](around:{radius_m},{lat},{lon})["amenity"]["amenity"~"school|hospital|clinic|college|university|social_facility|theatre|cinema|place_of_worship"];
  node["name"](around:{radius_m},{lat},{lon})["craft"];
  way["name"](around:{radius_m},{lat},{lon})["shop"];
  way["name"](around:{radius_m},{lat},{lon})["office"];
  way["name"](around:{radius_m},{lat},{lon})["tourism"]["tourism"~"hotel|hostel|motel"];
  way["name"](around:{radius_m},{lat},{lon})["building"~"hotel|commercial|office|retail|industrial"]["building"!~"residential|house|detached|apartments"];
  way["name"](around:{radius_m},{lat},{lon})["craft"];
);
out tags;
"""
    try:
        resp = httpx.post(
            _OVERPASS_URL,
            data={"data": query},
            timeout=_TIMEOUT,
            headers={"User-Agent": "SloopradarWorker/1.0"},
        )
        resp.raise_for_status()
    except Exception as exc:
        log.debug("OSM Overpass lookup mislukt (%s, %s): %s", lon, lat, exc)
        _CACHE[cache_key] = {}
        return {}

    elements = resp.json().get("elements", [])
    result = _best_match(elements)
    _CACHE[cache_key] = result
    return result


def _best_match(elements: list[dict]) -> dict:
    """Kies het meest relevante element en extraheer contactvelden."""
    scored: list[tuple[int, dict]] = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name", "")
        if not name:
            continue

        # Skip woongebouwen en oninteressante objecten
        building = tags.get("building", "")
        amenity = tags.get("amenity", "")
        if building in _SKIP_BUILDINGS:
            continue
        if amenity in _SKIP_AMENITIES:
            continue

        # Skip administratieve gebieden (veiligheidsregio's, provincies, etc.)
        name_lower = name.lower()
        if any(suffix in name_lower for suffix in _ADMIN_SUFFIXES):
            continue

        has_contact = any(
            k in tags for k in ("phone", "contact:phone", "website", "contact:website", "email", "contact:email")
        )
        has_specific_type = any(
            k in tags for k in ("amenity", "office", "shop", "healthcare", "leisure")
        ) or building not in ("", "yes", "no")

        # Vereis óf contactinfo óf een specifiek gebouwtype — pure naam-only is niet bruikbaar
        if not has_contact and not has_specific_type:
            continue

        # Score: meer tags = relevanter
        score = sum(1 for k in _USEFUL_TAGS if k in tags)
        if has_contact:
            score += 5
        if tags.get("office") or tags.get("amenity") in (
            "school", "hospital", "clinic", "social_facility",
            "college", "university", "kindergarten",
        ):
            score += 3

        scored.append((score, tags))

    if not scored:
        return {}

    scored.sort(key=lambda x: -x[0])
    best = scored[0][1]

    return {
        k: v for k, v in {
            "contact_naam":     best.get("name") or best.get("operator") or best.get("brand"),
            "contact_telefoon": best.get("phone") or best.get("contact:phone"),
            "contact_website":  best.get("website") or best.get("contact:website"),
            "contact_email":    best.get("email") or best.get("contact:email"),
        }.items()
        if v
    }
