"""Job Scheduler module using BackgroundScheduler (APScheduler)."""
import logging
from typing import Callable, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from core.runner import JobRunner

logger = logging.getLogger(__name__)


class VideoScheduler:
    """Schedules and executes background queue runner."""

    def __init__(self, interval_minutes: int = 1):
        self.scheduler = BackgroundScheduler()
        self.interval_minutes = interval_minutes
        self.runner = JobRunner()

    def _run_queue_job(self):
        logger.info("Scheduler pulse: Checking for pending due video jobs...")
        try:
            count = self.runner.process_due_jobs(max_jobs=5)
            logger.info(f"Scheduler pulse complete. Processed {count} jobs.")
        except Exception as e:
            logger.error(f"Error during scheduled queue processing: {e}")

    def start(self):
        """Start the background scheduler."""
        self.scheduler.add_job(
            self._run_queue_job,
            trigger="interval",
            minutes=self.interval_minutes,
            id="process_video_queue",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info(f"VideoScheduler started (polling every {self.interval_minutes} min).")

    def stop(self):
        """Stop background scheduler safely."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("VideoScheduler stopped.")
