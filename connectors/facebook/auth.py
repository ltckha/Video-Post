"""Facebook Page Graph API Auth Module.

Handles Facebook Page Access Token validation and management strictly via
Multi-Brand Account Configuration (config/accounts.json).
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


class FacebookConnector(BasePlatformConnector):
    def __init__(self, brand_name: Optional[str] = None):
        super().__init__("facebook")
        self.brand_name = brand_name
        self.page_id: Optional[str] = None
        self.access_token: Optional[str] = None
        self.app_id: Optional[str] = None
        self.app_secret: Optional[str] = None

        if self.brand_name:
            self.load_brand_credentials(self.brand_name)

    def load_brand_credentials(self, brand_name: str) -> bool:
        """Load Facebook Page ID and Access Token for a specific brand from config/facebook_pages.json."""
        self.brand_name = brand_name
        from core.account_manager import AccountManager, is_token_expired
        account_mgr = AccountManager()
        creds = account_mgr.get_brand_credentials(brand_name, "facebook")

        if creds:
            self.page_id = creds.get("page_id")
            self.access_token = creds.get("access_token")
            self.app_id = creds.get("app_id")
            self.app_secret = creds.get("app_secret")
            self.expires_at = creds.get("expires_at")

            if is_token_expired(self.expires_at):
                logger.error(
                    f"Facebook Token for brand '{brand_name}' expired on {self.expires_at}. Please update config/facebook_pages.json"
                )

            logger.info(f"Loaded Facebook credentials for brand '{brand_name}' (Page ID: {self.page_id}, Expires: {self.expires_at or 'Never'})")
            return True
        else:
            logger.warning(
                f"Facebook credentials for brand '{brand_name}' not found in config/facebook_pages.json"
            )
            return False


    def authenticate(self) -> bool:
        """Authenticate and validate Facebook Page Access Token for current brand."""
        if not self.access_token or not self.page_id:
            logger.warning(
                f"Facebook Page ID or Access Token missing for brand '{self.brand_name or 'unspecified'}'. "
                "Please configure config/accounts.json"
            )
            return False

        return self.validate_token()

    def validate_token(self) -> bool:
        """Check token status against Graph API me endpoint."""
        if not self.access_token:
            return False

        url = f"{GRAPH_API_BASE}/me"
        params = {"access_token": self.access_token, "fields": "id,name"}
        try:
            res = requests.get(url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                logger.info(
                    f"Facebook authentication verified for Brand '{self.brand_name}' -> Page: {data.get('name')} (ID: {data.get('id')})"
                )
                return True
            else:
                logger.error(f"Facebook Token validation failed (HTTP {res.status_code}): {res.text}")
                return False
        except Exception as e:
            logger.error(f"Exception while validating Facebook token: {e}")
            return False

    def refresh_access_token(self) -> str:
        """Re-validate and return Facebook Page access token."""
        if self.authenticate():
            return self.access_token
        raise RuntimeError(
            f"Facebook token for brand '{self.brand_name}' is revoked or expired. Please update config/accounts.json"
        )

    def upload_video(self, video_path: str, metadata: PostMetadata) -> Dict[str, Any]:
        """Resumable upload video to Facebook Page / Reels."""
        if not self.access_token or not self.page_id:
            if not self.authenticate():
                raise RuntimeError(
                    f"Facebook authentication failed for brand '{self.brand_name}'. Cannot upload video."
                )

        from .uploader import FacebookUploader
        uploader = FacebookUploader(page_id=self.page_id, access_token=self.access_token)
        return uploader.upload(video_path, metadata)
