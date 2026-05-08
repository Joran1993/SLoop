"""Worker entry point — start de APScheduler cron-jobs."""
import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from .config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

scheduler = BlockingScheduler()


@scheduler.scheduled_job("interval", hours=settings.koop_poll_interval_hours, id="koop_pipeline")
def run_koop_pipeline() -> None:
    from .pipelines.koop_pipeline import run
    log.info("Starten KOOP pipeline...")
    run()
    log.info("KOOP pipeline klaar.")


@scheduler.scheduled_job("cron", hour=6, minute=30, id="eindhoven_vergunning")
def run_eindhoven_vergunning() -> None:
    from .pipelines.eindhoven_leads_pipeline import run
    log.info("Starten Eindhoven vergunning leads pipeline...")
    result = run(lookback_days=settings.pipeline_lookback_days)
    log.info("Eindhoven vergunning klaar: %s", result)


@scheduler.scheduled_job("cron", hour=7, minute=0, id="alert_notifications")
def run_alert_notifications() -> None:
    from .pipelines.alerts_pipeline import run
    log.info("Starten alert notificaties...")
    result = run()
    log.info("Alert notificaties klaar: %s", result)


@scheduler.scheduled_job("cron", hour=8, minute=0, id="koop_voornemen")
def run_koop_voornemen() -> None:
    from .sources.pipeline.koop_voornemen_adapter import KoopVoornemenAdapter
    from .pipelines.pipeline_runner import run_pipeline
    log.info("Starten koop_voornemen pipeline...")
    result = run_pipeline(KoopVoornemenAdapter(), lookback_days=settings.pipeline_lookback_days)
    log.info("koop_voornemen klaar: %s", result)


@scheduler.scheduled_job("cron", day_of_week="mon", hour=9, minute=0, id="ruimtelijkeplannen")
def run_ruimtelijkeplannen() -> None:
    from .sources.pipeline.ruimtelijkeplannen_adapter import RuimtelijkePlannenAdapter
    from .pipelines.pipeline_runner import run_pipeline
    log.info("Starten ruimtelijkeplannen pipeline...")
    result = run_pipeline(RuimtelijkePlannenAdapter(), lookback_days=settings.pipeline_lookback_days)
    log.info("ruimtelijkeplannen klaar: %s", result)


@scheduler.scheduled_job("cron", day_of_week="tue", hour=9, minute=0, id="commissie_mer")
def run_commissie_mer() -> None:
    from .sources.pipeline.commissie_mer_adapter import CommissieMerAdapter
    from .pipelines.pipeline_runner import run_pipeline
    log.info("Starten commissie_mer pipeline...")
    result = run_pipeline(CommissieMerAdapter(), lookback_days=settings.pipeline_lookback_days)
    log.info("commissie_mer klaar: %s", result)


@scheduler.scheduled_job("cron", day_of_week="tue", hour=9, minute=30, id="rvb")
def run_rvb() -> None:
    from .sources.pipeline.rvb_adapter import RvbAdapter
    from .pipelines.pipeline_runner import run_pipeline
    log.info("Starten RVB pipeline...")
    result = run_pipeline(RvbAdapter(), lookback_days=settings.pipeline_lookback_days)
    log.info("RVB klaar: %s", result)


@scheduler.scheduled_job("cron", hour=6, minute=0, id="bag_status")
def run_bag_status() -> None:
    from .sources.pipeline.bag_status_adapter import BagStatusAdapter
    from .pipelines.pipeline_runner import run_pipeline
    log.info("Starten BAG status pipeline...")
    result = run_pipeline(BagStatusAdapter(), lookback_days=settings.pipeline_lookback_days)
    log.info("BAG status klaar: %s", result)


def main() -> None:
    log.info("Sloopradar worker gestart. Druk Ctrl+C om te stoppen.")
    scheduler.start()


if __name__ == "__main__":
    main()
