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


def main() -> None:
    log.info("Sloopradar worker gestart. Druk Ctrl+C om te stoppen.")
    scheduler.start()


if __name__ == "__main__":
    main()
