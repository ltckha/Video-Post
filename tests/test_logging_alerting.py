"""Unit tests for Phase 6 & 7 Logging, Alerting, and Reporting modules."""
import os
import pytest
from unittest.mock import patch, MagicMock

from core.logger import setup_logger, LOG_FILE_PATH
from core.alerter import AlertManager
from core.reporter import DailyReporter
from core.queue import JobQueue


def test_centralized_logger_file():
    test_logger = setup_logger("test_video_post")
    test_logger.info("Test centralized logger message")

    assert LOG_FILE_PATH.exists()
    content = LOG_FILE_PATH.read_text(encoding="utf-8")
    assert "Test centralized logger message" in content


def test_slack_alert_manager():
    alerter = AlertManager(slack_webhook_url="https://hooks.slack.com/services/test/mock/webhook")

    with patch("requests.post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_post.return_value = mock_res

        success = alerter.send_slack_alert(
            job_id=42,
            title="Failed Video Post",
            platform="facebook",
            error_message="HTTP 429 Rate Limit Exceeded",
            attempts=3,
        )

        assert success is True
        mock_post.assert_called_once()
        sent_json = mock_post.call_args[1]["json"]
        assert "Job #42" in sent_json["text"]


def test_daily_reporter_summary(tmp_path):
    db_file = tmp_path / "test_report.db"
    queue = JobQueue(db_path=str(db_file))

    # Add 2 completed jobs and 1 failed job
    j1 = queue.add_job("v1.mp4", ["facebook"], "Video 1")
    queue.update_job_status(j1, "completed", results={"facebook": {"post_id": "111"}})

    j2 = queue.add_job("v2.mp4", ["youtube"], "Video 2")
    queue.update_job_status(j2, "completed", results={"youtube": {"post_id": "222"}})

    j3 = queue.add_job("v3.mp4", ["instagram"], "Video 3")
    queue.update_job_status(j3, "failed", error_message="API Error")

    reporter = DailyReporter(db_path=str(db_file))
    summary = reporter.generate_daily_summary()

    assert summary["total_jobs"] == 3
    assert summary["completed"] == 2
    assert summary["failed"] == 1
    assert summary["success_rate_percent"] == 66.7
