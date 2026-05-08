"""CLI — voer een pipeline-adapter éénmalig uit.

Gebruik:
    python -m src.cli.run_adapter eindhoven --days 365
    python -m src.cli.run_adapter koop_voornemen --days 90
    python -m src.cli.run_adapter commissie_mer --days 180
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


_ADAPTERS = {
    "eindhoven": "src.sources.pipeline.eindhoven_vergunning_adapter.EindhovenVergunningAdapter",
    "koop_voornemen": "src.sources.pipeline.koop_voornemen_adapter.KoopVoornemenAdapter",
    "koop_sloopmelding": "src.sources.pipeline.koop_sloopmelding_adapter.KoopSloopMeldingAdapter",
    "commissie_mer": "src.sources.pipeline.commissie_mer_adapter.CommissieMerAdapter",
    "rvb": "src.sources.pipeline.rvb_adapter.RvbAdapter",
    "ruimtelijkeplannen": "src.sources.pipeline.ruimtelijkeplannen_adapter.RuimtelijkePlannenAdapter",
    "ontwerp_plan": "src.sources.pipeline.ontwerp_plan_adapter.OntwerpPlanAdapter",
}


def _load_adapter(name: str):
    module_path, class_name = _ADAPTERS[name].rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)()


def main():
    parser = argparse.ArgumentParser(description="Sloopradar pipeline adapter runner")
    parser.add_argument("adapter", choices=list(_ADAPTERS.keys()), help="Adapter om te draaien")
    parser.add_argument("--days", type=int, default=90, help="Lookback in dagen (default: 90)")
    args = parser.parse_args()

    # Validate env
    if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        print("ERROR: SUPABASE_URL en SUPABASE_SERVICE_ROLE_KEY vereist", file=sys.stderr)
        sys.exit(1)

    log.info("Adapter '%s' starten met lookback=%d dagen", args.adapter, args.days)

    try:
        adapter = _load_adapter(args.adapter)
    except Exception as exc:
        log.error("Adapter laden mislukt: %s", exc)
        sys.exit(1)

    from src.pipelines.pipeline_runner import run_pipeline
    result = run_pipeline(adapter, lookback_days=args.days)
    log.info("Klaar: %s", result)


if __name__ == "__main__":
    main()
