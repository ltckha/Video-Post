"""YouTube OAuth 2.0 Auth Module.

Handles token loading from local JSON or .env, automatic refreshing of expired tokens,
and initial OAuth authorization flow.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import settings
from ..base import BasePlatformConnector, PostMetadata

logger = logging.getLogger(__name__)

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


class YouTubeConnector(BasePlatformConnector):
    def __init__(self, token_path: Optional[str] = None):
        super().__init__("youtube")
        self.token_path = Path(token_path or settings.YOUTUBE_TOKEN_PATH)
        self.credentials: Optional[Credentials] = None

    def authenticate(self) -> bool:
        """Authenticate with YouTube Data API using existing token or environment configs."""
        # 1. Try loading from token_path
        if self.token_path.exists():
            try:
                self.credentials = Credentials.from_authorized_user_file(
                    str(self.token_path), YOUTUBE_SCOPES
                )
                logger.info(f"Loaded YouTube credentials from {self.token_path}")
            except Exception as e:
                logger.warning(f"Failed to load YouTube token file: {e}")

        # 2. Check validity or refresh if expired
        if self.credentials:
            if self.credentials.expired and self.credentials.refresh_token:
                try:
                    logger.info("YouTube token expired. Refreshing token...")
                    self.credentials.refresh(Request())
                    self.save_credentials()
                    logger.info("Successfully refreshed YouTube token.")
                except Exception as e:
                    logger.error(f"Failed to refresh YouTube token: {e}")
                    return False
            return self.credentials.valid

        # 3. If no credentials file, try constructing from .env if variables exist
        if settings.YOUTUBE_CLIENT_ID and settings.YOUTUBE_CLIENT_SECRET:
            logger.info("Attempting YouTube authentication from environment settings.")
            # Note: For full initial browser OAuth flow, run_local_oauth_flow() can be called
            return False

        logger.warning(
            f"YouTube token not found at {self.token_path}. Please paste your token into config/tokens/youtube_token.json"
        )
        return False

    def refresh_access_token(self) -> str:
        """Force refresh YouTube OAuth token."""
        if self.credentials and self.credentials.refresh_token:
            self.credentials.refresh(Request())
            self.save_credentials()
            return self.credentials.token
        raise ValueError("Cannot refresh YouTube token: missing refresh_token.")

    def save_credentials(self) -> None:
        """Save current credentials to JSON token file."""
        if not self.credentials:
            return
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, "w", encoding="utf-8") as f:
            f.write(self.credentials.to_json())
        logger.info(f"Saved updated YouTube token to {self.token_path}")

    def get_service(self):
        """Get authenticated YouTube Data API service object."""
        if not self.credentials or not self.credentials.valid:
            if not self.authenticate():
                raise RuntimeError("YouTube API not authenticated. Token invalid or missing.")
        return build("youtube", "v3", credentials=self.credentials)

    def run_local_oauth_flow(self, client_secrets_file: str) -> bool:
        """Run interactive local browser OAuth flow to obtain initial tokens."""
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, YOUTUBE_SCOPES
        )
        self.credentials = flow.run_local_server(port=8080)
        self.save_credentials()
        return True

    def upload_video(self, video_path: str, metadata: PostMetadata) -> Dict[str, Any]:
        """Resumable upload video to YouTube."""
        service = self.get_service()
        from .uploader import YouTubeUploader
        uploader = YouTubeUploader(youtube_service=service)
        return uploader.upload(video_path, metadata)

