"""CLI — historische backfill van KOOP sloopmeldingen in maandelijkse chunks.

Haalt records op per maand om rate-limiting te vermijden (KOOP throttelt bij >300 records).

Gebruik:
    python -m src.cli.historical_backfill --months 12
    python -m src.cli.historical_backfill --months 24 --delay 60
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _month_range(months_back: int):
    """Genereer (since, until) tuples per maand, nieuwste eerst."""
    now = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for i in range(months_back):
        until = now - timedelta(days=i * 30)
        since = until - timedelta(days=30)
        yield since.strftime("%Y-%m-%d"), until.strftime("%Y-%m-%d")


def main():
    parser = argparse.ArgumentParser(description="Historische KOOP backfill per maand")
    parser.add_argument("--months", type=int, default=12, help="Aantal maanden terug (default: 12)")
    parser.add_argument("--delay", type=int, default=30, help="Seconden wachten tussen maanden (default: 30)")
    args = parser.parse_args()

    if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        print("ERROR: SUPABASE_URL en SUPABASE_SERVICE_ROLE_KEY vereist", file=sys.stderr)
        sys.exit(1)

    from src.sources.koop import build_query, fetch_page, parse_response
    from src.pipelines.koop_pipeline import _upsert_meldingen, _get_unenriched, _enrich_and_score
    from src.config import settings
    from supabase import create_client
    import requests

    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)

    total_leads = 0
    for since_str, until_str in _month_range(args.months):
        log.info("Verwerken maand: %s tot %s", since_str, until_str)

        # Bouw query met datumrange
        kw_parts = ' OR '.join([
            'cql.textAndIndexes="sloopmelding"',
            'cql.textAndIndexes="sloopactiviteit"',
            'cql.textAndIndexes="asbest"',
            'cql.textAndIndexes="kennisgeving sloop"',
            'cql.textAndIndexes="omgevingsvergunning sloop"',
        ])
        query = (
            f"w.publicatienaam=Gemeenteblad"
            f" AND dt.modified>={since_str}"
            f" AND dt.modified<{until_str}"
            f" AND ({kw_parts})"
        )

        session = requests.Session()
        session.headers["User-Agent"] = "SloopradarWorker/1.0"

        all_records = []
        start = 1
        while True:
            try:
                xml_bytes = fetch_page(query, start, 100, session)
            except RuntimeError as exc:
                log.warning("Fetch mislukt bij start=%d: %s. Gebruik %d records.", start, exc, len(all_records))
                break
            total_count, next_pos, records = parse_response(xml_bytes)
            all_records.extend(records)
            log.info("  %s tot %s: %d records opgehaald (total=%s)", since_str, until_str, len(all_records), total_count)
            if not records or next_pos is None or (total_count and next_pos > total_count):
                break
            start = next_pos
            time.sleep(2)  # Voorkom rate-limiting

        if all_records:
            _upsert_meldingen(supabase, all_records)
            unenriched = _get_unenriched(supabase)
            stats = {"geocoded": 0, "bag_enriched": 0, "ep_enriched": 0, "leads_created": 0}
            for melding in unenriched:
                _enrich_and_score(supabase, melding, stats)
            total_leads += stats["leads_created"]
            log.info("  Maand klaar: %s (totaal tot nu: %d leads)", stats, total_leads)

        log.info("Wachten %ds voor volgende maand...", args.delay)
        time.sleep(args.delay)

    log.info("Backfill compleet. Totaal %d nieuwe leads.", total_leads)


if __name__ == "__main__":
    main()
