"""Backfill contactinfo voor bestaande sloop_leads.

Stap 1: Corporaties — statisch, direct
Stap 2: OSM Overpass — voor bedrijf/overheid leads met coördinaten (throttled)

Gebruik:
    poetry run python -m src.cli.backfill_contact [--osm] [--corporaties]
"""
from __future__ import annotations

import argparse
import logging
import os
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

_ENV_PATH = os.path.join(os.path.dirname(__file__), "../../.env")
if os.path.exists(_ENV_PATH):
    with open(_ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

from supabase import create_client
from src.sources.corporaties import get_corporatie_contact
from src.sources.osm_lookup import lookup_contact_by_location

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])


def backfill_corporaties():
    log.info("Stap 1: corporatie contactinfo backfill…")
    result = (
        supabase.table("sloop_leads")
        .select("id, eigenaar_naam")
        .in_("eigenaar_type", ["corporatie_waarschijnlijk", "particulier_of_corporatie"])
        .not_.is_("eigenaar_naam", "null")
        .is_("contact_website", "null")
        .limit(5000)
        .execute()
    )
    leads = result.data or []
    log.info("  %d corporatie-leads zonder contactinfo", len(leads))

    updated = 0
    for lead in leads:
        contact = get_corporatie_contact(lead.get("eigenaar_naam"))
        if contact:
            supabase.table("sloop_leads").update(contact).eq("id", lead["id"]).execute()
            updated += 1

    log.info("  %d corporaties bijgewerkt", updated)


def backfill_osm(delay: float = 1.0):
    log.info("Stap 2: OSM Overpass backfill voor bedrijf/overheid leads…")

    # Haal alle IDs vooraf op (vermijdt sliding-window paginatie bij updates)
    all_leads: list[dict] = []
    page, page_size = 0, 1000
    while True:
        chunk = (
            supabase.table("sloop_leads")
            .select("id, longitude, latitude, eigenaar_type")
            .in_("eigenaar_type", ["bedrijf", "overheid_instelling"])
            .is_("contact_naam", "null")
            .not_.is_("longitude", "null")
            .range(page * page_size, (page + 1) * page_size - 1)
            .execute()
        ).data or []
        all_leads.extend(chunk)
        if len(chunk) < page_size:
            break
        page += 1

    log.info("  %d leads te verrijken via OSM", len(all_leads))

    found = 0
    for i, lead in enumerate(all_leads):
        lon = lead.get("longitude")
        lat = lead.get("latitude")
        if not lon or not lat:
            continue

        contact = lookup_contact_by_location(lon, lat)
        if contact:
            supabase.table("sloop_leads").update(contact).eq("id", lead["id"]).execute()
            found += 1
            log.info("  [%d/%d] gevonden: %s", i + 1, len(all_leads), contact.get("contact_naam"))
        elif (i + 1) % 100 == 0:
            log.info("  [%d/%d] voortgang, %d gevonden", i + 1, len(all_leads), found)

        time.sleep(delay)

    log.info("  %d van %d leads verrijkt via OSM", found, len(all_leads))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corporaties", action="store_true")
    parser.add_argument("--osm", action="store_true")
    args = parser.parse_args()

    run_all = not args.corporaties and not args.osm
    if args.corporaties or run_all:
        backfill_corporaties()
    if args.osm or run_all:
        backfill_osm()


if __name__ == "__main__":
    main()
