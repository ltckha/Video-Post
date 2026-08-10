"""Alerting & Notification Module for Video-Post framework."""
import logging
import requests
from typing import Dict, Any, Optional

from config import settings

logger = logging.getLogger("video_post.alerter")


class AlertManager:
    def __init__(self, slack_webhook_url: Optional[str] = None):
        self.slack_webhook_url = slack_webhook_url or settings.SLACK_WEBHOOK_URL

    def send_slack_alert(
        self,
        job_id: int,
        title: str,
        platform: str,
        error_message: str,
        attempts: int = 1,
    ) -> bool:
        """Send formatted failure alert to Slack Webhook."""
        if not self.slack_webhook_url:
            logger.warning("Slack webhook URL not configured. Skipping Slack alert.")
            return False

        payload = {
            "text": f"🚨 *Video Post Failure Alert (Job #{job_id})*",
            "attachments": [
                {
                    "color": "#FF0000",
                    "fields": [
                        {"title": "Job ID", "value": str(job_id), "short": True},
                        {"title": "Platform", "value": platform.upper(), "short": True},
                        {"title": "Video Title", "value": title, "short": False},
                        {"title": "Attempts", "value": f"{attempts}/3", "short": True},
                        {"title": "Error Details", "value": f"```{error_message}```", "short": False},
                    ],
                }
            ],
        }

        try:
            res = requests.post(self.slack_webhook_url, json=payload, timeout=10)
            if res.status_code == 200:
                logger.info(f"Slack alert sent successfully for Job #{job_id}.")
                return True
            else:
                logger.error(f"Failed to send Slack alert (HTTP {res.status_code}): {res.text}")
                return False
        except Exception as e:
            logger.error(f"Exception sending Slack alert: {e}")
            return False

    def notify_failure(
        self,
        job_id: int,
        title: str,
        platform: str,
        error_message: str,
        attempts: int = 1,
    ):
        """Trigger alerts across enabled channels."""
        logger.error(
            f"ALERT TRIGGERED: Job #{job_id} on {platform.upper()} failed (Attempts: {attempts}): {error_message}"
        )
        self.send_slack_alert(
            job_id=job_id,
            title=title,
            platform=platform,
            error_message=error_message,
            attempts=attempts,
        )
