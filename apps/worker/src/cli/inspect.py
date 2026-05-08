"""CLI inspect tool — bekijk pipeline-projecten per postcode.

Gebruik:
    python -m src.cli.inspect 1234AB
    python -m src.cli.inspect --gemeente Amsterdam
    python -m src.cli.inspect --top 30
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from supabase import create_client

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _get_supabase():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        print("ERROR: SUPABASE_URL en SUPABASE_SERVICE_ROLE_KEY vereist", file=sys.stderr)
        sys.exit(1)
    return create_client(url, key)


def _fmt_kans(k: float) -> str:
    pct = int(k * 100)
    bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
    return f"{bar} {pct:3d}%"


def cmd_inspect_postcode(postcode: str):
    sb = _get_supabase()
    raw = postcode.upper().replace(" ", "")
    # Normaliseer naar "1234 AB" formaat voor DB-vergelijking
    pc = f"{raw[:4]} {raw[4:]}" if len(raw) == 6 else raw

    signals_res = (
        sb.table("pipeline_signals")
        .select("source,signal_type,signal_strength,signal_time,title,gemeente")
        .eq("postcode", pc)
        .order("signal_time", desc=True)
        .execute()
    )
    signals = signals_res.data or []

    projects_res = (
        sb.table("pipeline_projects")
        .select("*")
        .eq("postcode", pc)
        .order("sloop_kans", desc=True)
        .execute()
    )
    projects = projects_res.data or []

    print(f"\n{'═'*60}")
    print(f"  Postcode: {pc}")
    print(f"  Signalen: {len(signals)}  |  Projecten: {len(projects)}")
    print(f"{'═'*60}\n")

    if not projects:
        print("  Geen projecten gevonden voor dit postcode.\n")
    else:
        for p in projects:
            kans = p.get("sloop_kans", 0)
            print(f"  Project: {p.get('address_text') or p.get('bag_pand_id') or p['id'][:8]}")
            print(f"  Kans:    {_fmt_kans(kans)}")
            print(f"  Horizon: {p.get('horizon_months_min')}–{p.get('horizon_months_max')} maanden")
            print(f"  Signalen: {p.get('signal_count')} ({p.get('signal_diversity')} types)")
            expl = p.get("prediction_explanation", {})
            if isinstance(expl, str):
                expl = json.loads(expl)
            contribs = expl.get("contributions", [])
            if contribs:
                print("  Bijdragen:")
                for c in contribs[:5]:
                    print(f"    · {c['type']:<35} {c['contrib']:.2f}")
            print()

    if signals:
        print(f"  Recente signalen ({min(len(signals), 10)} van {len(signals)}):")
        for s in signals[:10]:
            dt = s.get("signal_time", "")[:10]
            print(f"    [{dt}] {s['source']:<25} {s['signal_type']:<30} {s.get('title','')[:40]}")
    print()


def cmd_top(n: int, gemeente: str | None = None):
    sb = _get_supabase()
    q = (
        sb.table("pipeline_projects")
        .select("*")
        .eq("status", "actief")
        .order("sloop_kans", desc=True)
        .limit(n)
    )
    if gemeente:
        q = q.eq("gemeente", gemeente)

    projects = q.execute().data or []

    print(f"\n{'═'*70}")
    print(f"  Top {n} sloopprojecten{' in ' + gemeente if gemeente else ''}")
    print(f"{'═'*70}")
    print(f"  {'#':<3} {'Kans':>6}  {'Gemeente':<20} {'Adres':<30} {'Horizon'}")
    print(f"  {'─'*3} {'─'*6}  {'─'*20} {'─'*30} {'─'*12}")

    for i, p in enumerate(projects, 1):
        kans_pct = int(p.get("sloop_kans", 0) * 100)
        gemeente_str = (p.get("gemeente") or "—")[:20]
        adres = (p.get("address_text") or p.get("bag_pand_id") or p["id"][:8])[:30]
        horizon = f"{p.get('horizon_months_min')}–{p.get('horizon_months_max')}m"
        print(f"  {i:<3} {kans_pct:>5}%  {gemeente_str:<20} {adres:<30} {horizon}")

    print(f"\n  Totaal: {len(projects)} projecten\n")


def main():
    parser = argparse.ArgumentParser(description="Sloopradar pipeline inspector")
    sub = parser.add_subparsers(dest="cmd")

    p_pc = sub.add_parser("postcode", help="Inspecteer een postcode")
    p_pc.add_argument("postcode")

    p_top = sub.add_parser("top", help="Toon top-N projecten")
    p_top.add_argument("n", type=int, nargs="?", default=30)
    p_top.add_argument("--gemeente", "-g", default=None)

    # Backwards compat: positional arg zonder subcommand = postcode
    parser.add_argument("postcode_arg", nargs="?", default=None)

    args = parser.parse_args()

    if args.cmd == "postcode":
        cmd_inspect_postcode(args.postcode)
    elif args.cmd == "top":
        cmd_top(args.n, args.gemeente)
    elif args.postcode_arg:
        cmd_inspect_postcode(args.postcode_arg)
    else:
        cmd_top(30)


if __name__ == "__main__":
    main()
