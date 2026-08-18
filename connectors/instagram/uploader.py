"""Instagram Reels Container Uploader Module.

Implements official Meta Graph API Resumable Reels publishing workflow:
1. Create Media Container with upload_type=resumable
2. Stream binary video directly to Meta rupload server (rupload.facebook.com)
3. Poll Container status until FINISHED
4. Publish Media Container
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
        self.instagram_account_id = str(instagram_account_id).strip()
        self.access_token = str(access_token).strip()
        self.max_retries = max_retries

    def upload(self, video_path: str, metadata: PostMetadata, video_url: Optional[str] = None) -> Dict[str, Any]:
        """Publish Reels/Video to Instagram Business Account via Meta Graph API Resumable Upload."""
        path = Path(video_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Video file not found at: {video_path}")

        file_size = path.stat().st_size
        caption = metadata.description or metadata.title or ""
        logger.info(f"Starting Instagram Reels Upload for '{path.name}' ({file_size / (1024*1024):.2f} MB)...")

        # Step 1: Initialize Resumable Media Container
        url = f"{GRAPH_API_BASE}/{self.instagram_account_id}/media"
        init_payload = {
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": caption,
            "access_token": self.access_token,
        }

        logger.info("Initializing Instagram Resumable Reels Container...")
        res = requests.post(url, data=init_payload, timeout=30)
        if res.status_code != 200:
            logger.error(f"Failed to initialize Instagram container: {res.text}")
            res.raise_for_status()

        init_data = res.json()
        container_id = init_data["id"]
        upload_uri = init_data.get("uri") or f"https://rupload.facebook.com/ig-reels-upload/v19.0/{container_id}"
        logger.info(f"Created Instagram Reels Container ID: {container_id}")

        # Step 2: Stream Video Binary to Meta rupload Server
        logger.info(f"Streaming video bytes directly to Meta rupload server...")
        upload_headers = {
            "Authorization": f"OAuth {self.access_token}",
            "offset": "0",
            "file_size": str(file_size),
            "Content-Type": "application/octet-stream",
        }

        with open(path, "rb") as f:
            video_bytes = f.read()
            upload_res = requests.post(upload_uri, headers=upload_headers, data=video_bytes, timeout=300)
            if upload_res.status_code not in [200, 201]:
                logger.error(f"Meta rupload failed (HTTP {upload_res.status_code}): {upload_res.text}")
                upload_res.raise_for_status()

        logger.info("Video binary uploaded to Meta successfully! Waiting for Instagram video processing...")

        # Step 3: Poll Container Status until FINISHED
        self._wait_for_container_ready(container_id)

        # Step 4: Publish Container
        media_id = self._publish_container(container_id)
        logger.info(f"Instagram Reels Published SUCCESS! Media ID: {media_id}")

        return {
            "status": "success",
            "platform": "instagram",
            "post_id": media_id,
            "video_url": f"https://www.instagram.com/reel/{media_id}",
        }

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
