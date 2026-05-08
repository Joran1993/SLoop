"""CLI om alert notificaties handmatig te versturen of te previewen."""
from __future__ import annotations

import argparse
import logging
import os
import webbrowser

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verstuur of preview alert notificaties")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simuleer alleen, verstuur geen emails")
    parser.add_argument("--preview", action="store_true",
                        help="Genereer email HTML voor deze week en open in browser")
    parser.add_argument("--test-email", metavar="EMAIL",
                        help="Stuur testmail naar dit adres (vereist RESEND_API_KEY)")
    parser.add_argument("--days", type=int, default=7,
                        help="Aantal terugkijkdagen voor --preview (default: 7)")
    args = parser.parse_args()

    if args.preview:
        _run_preview(args.days)
        return

    if args.test_email:
        _run_test_email(args.test_email, args.days)
        return

    if args.dry_run:
        logging.getLogger().setLevel(logging.DEBUG)
        log.info("DRY RUN — geen emails worden verstuurd")
        from ..config import settings
        settings.resend_api_key = "dry-run-key"

    from ..pipelines.alerts_pipeline import run
    result = run()
    print(result)


def _run_preview(days: int) -> None:
    """Genereer email HTML voor de afgelopen N dagen en open in browser."""
    from datetime import datetime, timedelta, timezone
    from supabase import create_client
    from ..config import settings
    from ..pipelines.alerts_pipeline import _query_matching_leads, _build_email_html

    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    log.info("Ophalen leads van afgelopen %d dagen...", days)
    leads = _query_matching_leads(supabase, {}, since)
    log.info("%d leads gevonden", len(leads))

    if not leads:
        print(f"Geen leads gevonden in de afgelopen {days} dagen.")
        return

    html = _build_email_html(f"Afgelopen {days} dagen", leads, since)

    out = "/tmp/sloopradar_alert_preview.html"
    with open(out, "w") as f:
        f.write(html)

    print(f"\n{len(leads)} leads in de email. Preview opgeslagen: {out}")
    webbrowser.open(f"file://{out}")


def _run_test_email(to_email: str, days: int) -> None:
    """Stuur een echte testmail naar het opgegeven adres."""
    from datetime import datetime, timedelta, timezone
    from supabase import create_client
    from ..config import settings
    from ..pipelines.alerts_pipeline import _query_matching_leads, _build_email_html, _send_email

    if not settings.resend_api_key:
        print("FOUT: RESEND_API_KEY is niet ingesteld in .env")
        print("Maak een gratis account aan op resend.com en stel de key in.")
        return

    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    leads = _query_matching_leads(supabase, {}, since)
    if not leads:
        print(f"Geen leads gevonden in de afgelopen {days} dagen.")
        return

    html = _build_email_html(f"Test — afgelopen {days} dagen", leads, since)
    subject = f"[TEST] Sloopradar: {len(leads)} leads van afgelopen {days} dagen"

    log.info("Versturen naar %s via Resend...", to_email)
    _send_email(to_email, subject, html)
    print(f"Verstuurd naar {to_email} ({len(leads)} leads)")


if __name__ == "__main__":
    main()
