"""Backfill eigenaar_naam voor bestaande sloop_leads op basis van gemeente-corporatie mapping."""
from __future__ import annotations

import sys
import os

# Handmatig .env inlezen (multiline-safe)
_ENV_PATH = os.path.join(os.path.dirname(__file__), "../../.env")
if os.path.exists(_ENV_PATH):
    with open(_ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

from supabase import create_client
from src.sources.corporaties import get_primary_corporatie

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CORPORATIE_TYPES = {"corporatie_waarschijnlijk", "particulier_of_corporatie"}


def run():
    print("Ophalen leads met corporatie eigenaar_type...")
    result = (
        supabase.table("sloop_leads")
        .select("id, gemeente, eigenaar_type, eigenaar_naam")
        .in_("eigenaar_type", list(CORPORATIE_TYPES))
        .is_("eigenaar_naam", "null")
        .limit(5000)
        .execute()
    )
    leads = result.data or []
    print(f"Gevonden: {len(leads)} leads zonder eigenaar_naam")

    updated = 0
    skipped = 0
    for lead in leads:
        naam = get_primary_corporatie(lead.get("gemeente"))
        if naam:
            supabase.table("sloop_leads").update({"eigenaar_naam": naam}).eq("id", lead["id"]).execute()
            updated += 1
        else:
            skipped += 1

    print(f"Klaar: {updated} bijgewerkt, {skipped} overgeslagen (gemeente onbekend in mapping)")


if __name__ == "__main__":
    run()
