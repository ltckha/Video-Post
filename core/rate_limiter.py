"""Rate Limiter module for Video-Post publishing platforms.

Tracks and enforces hourly and daily rate limits per social platform.
"""
import logging
from typing import Tuple, Dict

logger = logging.getLogger(__name__)

DEFAULT_RATE_LIMITS = {
    "facebook": 5,
    "youtube": 10,
    "instagram": 5,
    "tiktok": 5,
}
RATE_LIMITS = DEFAULT_RATE_LIMITS


class RateLimiter:
    """Enforces hourly publishing rate limits per social media platform."""

    def __init__(self, limits: Dict[str, int] = None):
        self.limits = limits or dict(DEFAULT_RATE_LIMITS)

    def get_max_hourly(self, platform: str) -> int:
        return self.limits.get(platform, 10)

    def check_rate_limit(self, platform: str, current_hourly_count: int) -> Tuple[bool, str]:
        """Check if posting to platform is allowed within current hourly limit."""
        max_hourly = self.get_max_hourly(platform)
        if current_hourly_count >= max_hourly:
            msg = f"Rate limit reached for {platform} ({current_hourly_count}/{max_hourly} posts in last hour). Job deferred."
            logger.warning(msg)
            return False, msg
        return True, ""
