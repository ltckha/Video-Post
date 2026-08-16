"""YouTube Resumable Video Uploader Module.

Implements Google API Client Resumable Upload protocol for YouTube Data API v3.
"""
import time
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional

from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from ..base import PostMetadata

logger = logging.getLogger(__name__)


class YouTubeUploader:
    def __init__(self, youtube_service, max_retries: int = 3):
        self.youtube = youtube_service
        self.max_retries = max_retries

    def upload(self, video_path: str, metadata: PostMetadata) -> Dict[str, Any]:
        """Resumable upload video to YouTube Data API v3."""
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found at: {video_path}")

        file_size = path.stat().st_size
        logger.info(f"Starting YouTube Resumable Upload for '{path.name}' ({file_size} bytes)...")

        # Ensure title is non-empty and strictly <= 95 chars (YouTube limit is 100)
        title_text = (metadata.title or "").strip()
        title_text = re.sub(r"[<>]", "", title_text)
        if not title_text:
            title_text = "Video"
        elif len(title_text) > 95:
            title_text = title_text[:92].strip() + "..."

        # Ensure #Shorts tag is present in description or title for YouTube Shorts indexing
        desc_text = metadata.description or ""
        if "#shorts" not in title_text.lower() and "#shorts" not in desc_text.lower():
            desc_text = f"{desc_text}\n\n#Shorts".strip()

        body = {
            "snippet": {
                "title": title_text,
                "description": desc_text,
                "tags": metadata.tags,
                "categoryId": "22",  # People & Blogs category default
            },
            "status": {
                "privacyStatus": metadata.privacy_status.lower(),
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            str(path.absolute()),
            mimetype="video/*",
            chunksize=4 * 1024 * 1024,
            resumable=True,
        )

        request = self.youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        error_count = 0

        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"YouTube Upload progress: {progress}%")
            except HttpError as e:
                if e.resp.status in [429, 500, 502, 503, 504]:
                    error_count += 1
                    if error_count > self.max_retries:
                        raise RuntimeError(f"YouTube upload failed after {self.max_retries} retries: {e}")
                    wait_time = 2 ** error_count
                    logger.warning(f"YouTube API HttpError {e.resp.status}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise e
            except Exception as e:
                error_count += 1
                if error_count > self.max_retries:
                    raise e
                wait_time = 2 ** error_count
                logger.warning(f"YouTube upload error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)

        video_id = response.get("id")
        logger.info(f"YouTube Video Upload SUCCESS! Video ID: {video_id}")

        return {
            "status": "success",
            "platform": "youtube",
            "post_id": video_id,
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "response": response,
        }
