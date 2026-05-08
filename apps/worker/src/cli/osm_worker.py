"""OSM lookup worker — verwerkt een subset van lead-IDs uit een JSON-bestand.

Gebruik:
    python -m src.cli.osm_worker /tmp/osm_chunk_1.json https://overpass.kumi.systems/api/interpreter
"""
from __future__ import annotations

import json
import logging
import sys
import time

import httpx
from supabase import create_client

from ..config import settings
from ..sources.osm_lookup import _best_match

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")

_TIMEOUT = 14
_SKIP_AMENITIES = {"parking", "bicycle_parking", "waste_basket", "bench",
                   "post_box", "telephone", "vending_machine",
                   "restaurant", "cafe", "pub", "bar", "fast_food", "food_court"}


def _lookup(lon: float, lat: float, overpass_url: str, radius: int = 50) -> dict:
    query = f"""[out:json][timeout:{_TIMEOUT}];
(
  node["name"](around:{radius},{lat},{lon})["shop"];
  node["name"](around:{radius},{lat},{lon})["office"];
  node["name"](around:{radius},{lat},{lon})["tourism"]["tourism"~"hotel|hostel|motel|guest_house"];
  node["name"](around:{radius},{lat},{lon})["amenity"]["amenity"!~"{'|'.join(_SKIP_AMENITIES)}"];
  node["name"](around:{radius},{lat},{lon})["craft"];
  way["name"](around:{radius},{lat},{lon})["shop"];
  way["name"](around:{radius},{lat},{lon})["office"];
  way["name"](around:{radius},{lat},{lon})["tourism"]["tourism"~"hotel|hostel|motel"];
  way["name"](around:{radius},{lat},{lon})["building"~"hotel|commercial|office|retail"]["building"!~"residential|house|detached|apartments"];
  way["name"](around:{radius},{lat},{lon})["craft"];
);
out tags;"""
    try:
        r = httpx.post(overpass_url, data={"data": query}, timeout=_TIMEOUT + 2,
                       headers={"User-Agent": "SloopradarWorker/1.0"})
        r.raise_for_status()
        return _best_match(r.json().get("elements", []))
    except Exception as exc:
        log.debug("OSM fout: %s", exc)
        return {}


def run(chunk_file: str, overpass_url: str) -> None:
    with open(chunk_file) as f:
        ids: list[str] = json.load(f)

    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)

    # Haal coördinaten op voor deze IDs in batches van 100
    coords: dict[str, tuple[float, float]] = {}
    for i in range(0, len(ids), 100):
        batch = ids[i:i + 100]
        rows = supabase.table("sloop_leads").select("id, longitude, latitude") \
            .in_("id", batch).execute().data or []
        for r in rows:
            if r.get("longitude") and r.get("latitude"):
                coords[r["id"]] = (r["longitude"], r["latitude"])

    found = skipped = 0
    for i, lead_id in enumerate(ids):
        if lead_id not in coords:
            skipped += 1
            continue

        lon, lat = coords[lead_id]
        contact = _lookup(lon, lat, overpass_url)
        if contact:
            supabase.table("sloop_leads").update(contact).eq("id", lead_id).execute()
            found += 1
            log.info("[%d/%d] %s → %s", i + 1, len(ids), lead_id[:8], contact.get("contact_naam"))
        elif (i + 1) % 200 == 0:
            log.info("[%d/%d] voortgang — %d gevonden", i + 1, len(ids), found)

        time.sleep(1.0)

    log.info("Klaar: %d gevonden, %d overgeslagen van %d", found, skipped, len(ids))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Gebruik: python -m src.cli.osm_worker <chunk.json> <overpass_url>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])
