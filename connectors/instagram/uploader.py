"""Instagram Reels Container Uploader Module.

Implements Instagram Graph API Reels publishing workflow:
1. Create Media Container (media_type=REELS)
2. Poll Container status until FINISHED
3. Publish Media Container
"""
import time
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Optional

from ..base import PostMetadata

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v19.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class InstagramUploader:
    def __init__(self, instagram_account_id: str, access_token: str, max_retries: int = 3):
        self.instagram_account_id = instagram_account_id
        self.access_token = access_token
        self.max_retries = max_retries

    def upload(self, video_path: str, metadata: PostMetadata, video_url: Optional[str] = None) -> Dict[str, Any]:
        """Publish Reels/Video to Instagram Business Account."""
        logger.info(f"Starting Instagram Reels Upload for '{metadata.title}'...")

        # If video_url is missing or local, generate a temporary public HTTP URL for Instagram API
        if not video_url or not str(video_url).startswith("http"):
            if video_path and Path(video_path).exists():
                video_url = self._upload_to_temp_host(video_path)
            else:
                raise ValueError(f"Valid video_url or local video_path is required for Instagram. Got: path={video_path}, url={video_url}")

        caption = f"{metadata.title}\n\n{metadata.description}"
        if metadata.tags:
            caption += "\n" + " ".join([f"#{t.strip('#')}" for t in metadata.tags])

        # Step 1: Create Media Container
        container_id = self._create_reels_container(caption=caption, video_url=video_url)
        logger.info(f"Created Instagram Reels Container ID: {container_id}")

        # Step 2: Poll Container Status
        self._wait_for_container_ready(container_id)

        # Step 3: Publish Container
        media_id = self._publish_container(container_id)
        logger.info(f"Instagram Reels Published SUCCESS! Media ID: {media_id}")

        return {
            "status": "success",
            "platform": "instagram",
            "post_id": media_id,
            "video_url": f"https://www.instagram.com/p/{media_id}",
        }

    def _create_reels_container(self, caption: str, video_url: Optional[str]) -> str:
        url = f"{GRAPH_API_BASE}/{self.instagram_account_id}/media"
        payload = {
            "media_type": "REELS",
            "caption": caption,
            "access_token": self.access_token,
        }
        if video_url:
            payload["video_url"] = video_url

        res = requests.post(url, data=payload, timeout=30)
        if res.status_code == 200:
            return res.json()["id"]
        else:
            logger.error(f"Failed to create Instagram Reels container: {res.text}")
            res.raise_for_status()

    def _upload_to_temp_host(self, local_path: str) -> str:
        """Upload local mp4 file to catbox.moe to obtain a direct public HTTP URL required by Instagram Graph API."""
        url = "https://catbox.moe/user/api.php"
        data = {"reqtype": "fileupload"}
        path = Path(local_path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found at: {local_path}")
        
        logger.info(f"Uploading local video '{path.name}' to temporary public host for Instagram Graph API...")
        with open(path, "rb") as f:
            files = {"fileToUpload": f}
            res = requests.post(url, data=data, files=files, timeout=120)
            if res.status_code == 200:
                direct_url = res.text.strip()
                logger.info(f"Temporary direct video URL generated: {direct_url}")
                return direct_url
            else:
                raise RuntimeError(f"Failed to generate temporary public video URL: {res.text}")

    def _wait_for_container_ready(self, container_id: str, timeout_seconds: int = 300):
        url = f"{GRAPH_API_BASE}/{container_id}"
        params = {
            "fields": "status_code,status",
            "access_token": self.access_token,
        }

        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            res = requests.get(url, params=params, timeout=15)
            if res.status_code == 200:
                data = res.json()
                status_code = data.get("status_code")
                logger.info(f"Instagram Container {container_id} status: {status_code}")

                if status_code == "FINISHED":
                    return True
                elif status_code == "ERROR":
                    raise RuntimeError(f"Instagram video processing failed: {data.get('status')}")
            time.sleep(5)

        raise TimeoutError(f"Instagram Container {container_id} processing timed out.")

    def _publish_container(self, container_id: str) -> str:
        url = f"{GRAPH_API_BASE}/{self.instagram_account_id}/media_publish"
        payload = {
            "creation_id": container_id,
            "access_token": self.access_token,
        }
        res = requests.post(url, data=payload, timeout=30)
        if res.status_code == 200:
            return res.json()["id"]
        else:
            logger.error(f"Failed to publish Instagram Reels: {res.text}")
            res.raise_for_status()
