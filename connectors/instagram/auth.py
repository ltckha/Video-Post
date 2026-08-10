"""Instagram Graph API Auth Module.

Handles Instagram Business Account credentials validation and token management.
"""
import json
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Optional

from config import settings
from ..base import BasePlatformConnector, PostMetadata

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v19.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class InstagramConnector(BasePlatformConnector):
    def __init__(self, token_path: Optional[str] = None):
        super().__init__("instagram")
        self.token_path = Path(token_path or "./config/tokens/instagram_token.json")
        self.instagram_account_id: Optional[str] = None
        self.access_token: Optional[str] = None

    def authenticate(self) -> bool:
        """Authenticate and validate Instagram Business Account token."""
        # 1. Load from token file
        if self.token_path.exists():
            try:
                with open(self.token_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.instagram_account_id = data.get("instagram_account_id")
                    self.access_token = data.get("access_token")
                logger.info(f"Loaded Instagram credentials from {self.token_path}")
            except Exception as e:
                logger.warning(f"Error loading Instagram token file: {e}")

        # 2. Fallback to settings (.env)
        if not self.access_token or not self.instagram_account_id:
            self.instagram_account_id = settings.INSTAGRAM_ACCOUNT_ID
            self.access_token = settings.INSTAGRAM_ACCESS_TOKEN

        if not self.access_token or not self.instagram_account_id:
            logger.warning(
                "Instagram Account ID or Access Token missing. "
                "Please configure config/tokens/instagram_token.json or .env"
            )
            return False

        # 3. Validate token with Graph API
        return self.validate_token()

    def validate_token(self) -> bool:
        """Verify token against Instagram Account endpoint."""
        if not self.access_token or not self.instagram_account_id:
            return False

        url = f"{GRAPH_API_BASE}/{self.instagram_account_id}"
        params = {
            "access_token": self.access_token,
            "fields": "id,username,name",
        }

        try:
            res = requests.get(url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                logger.info(
                    f"Instagram Account verified: @{data.get('username')} (ID: {data.get('id')})"
                )
                return True
            else:
                logger.error(
                    f"Instagram token validation failed (HTTP {res.status_code}): {res.text}"
                )
                return False
        except Exception as e:
            logger.error(f"Exception validating Instagram token: {e}")
            return False

    def refresh_access_token(self) -> str:
        """Refresh or validate Instagram access token."""
        if self.authenticate():
            return self.access_token
        raise RuntimeError(
            "Instagram token is invalid or expired. Please update config/tokens/instagram_token.json"
        )

    def save_token_file(self):
        """Save Instagram credentials to token JSON file."""
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "instagram_account_id": self.instagram_account_id,
                    "access_token": self.access_token,
                },
                f,
                indent=2,
            )
        logger.info(f"Saved Instagram token to {self.token_path}")

    def upload_video(self, video_path: str, metadata: PostMetadata, video_url: Optional[str] = None) -> Dict[str, Any]:
        """Publish Reels/Video to Instagram Business account."""
        if not self.access_token or not self.instagram_account_id:
            if not self.authenticate():
                raise RuntimeError("Instagram authentication failed. Cannot upload video.")

        from .uploader import InstagramUploader
        uploader = InstagramUploader(
            instagram_account_id=self.instagram_account_id,
            access_token=self.access_token,
        )
        return uploader.upload(video_path, metadata, video_url=video_url)

