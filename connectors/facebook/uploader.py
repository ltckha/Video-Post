"""Facebook Resumable Video & Reels Uploader Module.

Implements Graph API v19.0 3-phase resumable video upload protocol:
Phase 1: start - Initialize upload session
Phase 2: transfer - Stream video file in 4MB binary chunks
Phase 3: finish - Finalize upload and publish with metadata
"""
import os
import time
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Optional

from ..base import PostMetadata

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v19.0"
CHUNK_SIZE = 4 * 1024 * 1024  # 4MB chunks


class FacebookUploader:
    def __init__(self, page_id: str, access_token: str, max_retries: int = 3):
        self.page_id = page_id
        self.access_token = access_token
        self.max_retries = max_retries
        self.base_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{self.page_id}/videos"

    def upload(self, video_path: str, metadata: PostMetadata) -> Dict[str, Any]:
        """Perform 3-phase resumable video upload to Facebook Page."""
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found at: {video_path}")

        file_size = path.stat().st_size
        logger.info(f"Starting Facebook Resumable Upload for '{path.name}' ({file_size} bytes)...")

        # Phase 1: Start
        session_info = self._start_upload_session(file_size)
        upload_session_id = session_info["upload_session_id"]
        video_id = session_info.get("video_id")
        start_offset = int(session_info.get("start_offset", 0))
        end_offset = int(session_info.get("end_offset", min(CHUNK_SIZE, file_size)))

        logger.info(f"Initialized upload session {upload_session_id} for video_id {video_id}")

        # Phase 2: Transfer chunks
        with open(path, "rb") as f:
            while start_offset < file_size:
                f.seek(start_offset)
                chunk_len = end_offset - start_offset
                chunk_data = f.read(chunk_len)

                response_data = self._transfer_chunk(
                    upload_session_id=upload_session_id,
                    start_offset=start_offset,
                    chunk_data=chunk_data,
                )

                start_offset = int(response_data.get("start_offset", end_offset))
                end_offset = int(response_data.get("end_offset", min(start_offset + CHUNK_SIZE, file_size)))

                progress = min(100.0, (start_offset / file_size) * 100)
                logger.info(f"Upload progress: {progress:.1f}% ({start_offset}/{file_size} bytes)")

        # Phase 3: Finish
        finish_result = self._finish_upload_session(
            upload_session_id=upload_session_id,
            metadata=metadata,
        )

        published_video_id = finish_result.get("id", video_id)
        logger.info(f"Facebook Video Upload SUCCESS! Post/Video ID: {published_video_id}")

        return {
            "status": "success",
            "platform": "facebook",
            "post_id": published_video_id,
            "video_url": f"https://www.facebook.com/{published_video_id}",
            "response": finish_result,
        }

    def _execute_request_with_retry(self, method: str, params: Dict[str, Any], files: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute HTTP request with exponential backoff retry logic."""
        params["access_token"] = self.access_token

        for attempt in range(1, self.max_retries + 1):
            try:
                if method.upper() == "POST":
                    res = requests.post(self.base_url, data=params, files=files, timeout=30)
                else:
                    res = requests.get(self.base_url, params=params, timeout=30)

                if res.status_code == 200:
                    return res.json()
                elif res.status_code in [429, 500, 502, 503, 504]:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Facebook API transient error (HTTP {res.status_code}). Retrying in {wait_time}s (Attempt {attempt}/{self.max_retries})..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Facebook API error (HTTP {res.status_code}): {res.text}")
                    res.raise_for_status()
            except requests.RequestException as e:
                if attempt == self.max_retries:
                    raise RuntimeError(f"Facebook upload failed after {self.max_retries} attempts: {e}")
                wait_time = 2 ** attempt
                logger.warning(f"Connection error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)

        raise RuntimeError("Facebook API request failed max retry limit.")

    def _start_upload_session(self, file_size: int) -> Dict[str, Any]:
        params = {
            "upload_phase": "start",
            "file_size": str(file_size),
        }
        return self._execute_request_with_retry("POST", params)

    def _transfer_chunk(self, upload_session_id: str, start_offset: int, chunk_data: bytes) -> Dict[str, Any]:
        params = {
            "upload_phase": "transfer",
            "upload_session_id": upload_session_id,
            "start_offset": str(start_offset),
        }
        files = {"video_file_chunk": ("chunk.bin", chunk_data, "application/octet-stream")}
        return self._execute_request_with_retry("POST", params, files=files)

    def _finish_upload_session(self, upload_session_id: str, metadata: PostMetadata) -> Dict[str, Any]:
        params = {
            "upload_phase": "finish",
            "upload_session_id": upload_session_id,
            "title": metadata.title,
            "description": metadata.description,
            "published": "true" if metadata.privacy_status == "public" else "false",
        }
        return self._execute_request_with_retry("POST", params)
