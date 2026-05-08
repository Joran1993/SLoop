"""Herbereken materiaal_volume_estimate voor alle bestaande leads."""
from __future__ import annotations

import logging
import sys

from supabase import create_client

from ..config import settings
from ..scoring.scores import estimate_sloopindicatoren

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def run(start_offset: int = 0) -> None:
    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)

    offset = start_offset
    batch = 200  # kleiner batch om connection resets te voorkomen
    updated = 0

    while True:
        result = (
            supabase.table("sloop_leads")
            .select("id, gebruiksdoelen, oppervlakte_m2, bouwjaar")
            .range(offset, offset + batch - 1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            break

        for row in rows:
            indicatoren = estimate_sloopindicatoren(
                row.get("gebruiksdoelen") or [],
                row.get("oppervlakte_m2"),
                row.get("bouwjaar"),
            )
            if not indicatoren:
                continue
            supabase.table("sloop_leads").update(
                {"materiaal_volume_estimate": indicatoren}
            ).eq("id", row["id"]).execute()
            updated += 1

        log.info("Batch %d-%d verwerkt (%d bijgewerkt)", offset, offset + len(rows) - 1, updated)
        offset += batch
        if len(rows) < batch:
            break

    log.info("Klaar: %d leads bijgewerkt", updated)


if __name__ == "__main__":
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    run(start)
