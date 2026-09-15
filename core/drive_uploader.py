"""Google Drive Uploader Module for Video-Post Cloud-First Backup.

Uploads local video files (Omni-Video and HNC SANPHAM) to dedicated Google Drive folders,
returning shareable drive URLs stored in Tab Master 'drive_url' column.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

DEFAULT_SA_PATH = "config/service_account.json"

# Google Drive Target Folder IDs
DRIVE_FOLDER_OMNI = "1j4cTLmaE963pqQ6lrrSN73reY9_zaLao"  # Spark/Omni-Video/Outputs/
DRIVE_FOLDER_HNC = "1rSrT8OWQPpkGgXiPFFhVnVUhCJC_zqe7"   # Spark/HNC_Master/Outputs/

SCOPES = [
    "https://www.googleapis.com/auth/drive",
]


class GoogleDriveUploader:
    """Handles uploading video files to Google Drive folders via Service Account."""

    def __init__(self, service_account_path: Optional[str] = None):
        self.sa_path = Path(service_account_path or DEFAULT_SA_PATH)
        self.service = None
        self._init_service()

    def _init_service(self):
        """Authenticate with Google Drive API v3."""
        if not self.sa_path.exists():
            alt_path = Path("video-post-bot.json")
            if alt_path.exists():
                self.sa_path = alt_path

        if not self.sa_path.exists():
            logger.warning(f"Service Account key not found at {self.sa_path}. Drive upload disabled.")
            return

        try:
            creds = Credentials.from_service_account_file(str(self.sa_path), scopes=SCOPES)
            self.service = build("drive", "v3", credentials=creds)
            logger.info("Connected to Google Drive API v3 via Service Account.")
        except Exception as e:
            logger.error(f"Failed to connect to Google Drive API: {e}")
            self.service = None

    @staticmethod
    def get_folder_id_for_source(source_name: str) -> Optional[str]:
        """Map source tab name to its target Google Drive folder ID."""
        clean = str(source_name).strip().lower()
        if "omni" in clean:
            return DRIVE_FOLDER_OMNI
        if "sanpham" in clean or "hnc" in clean:
            return DRIVE_FOLDER_HNC
        return None

    @staticmethod
    def should_upload_video(
        source_name: str,
        local_path: str,
        existing_drive_url: str = "",
        status_fb: str = "pending",
        status_yt: str = "pending",
        status_ig: str = "pending",
    ) -> bool:
        """Evaluate strict filtering rules:
        1. Only applies to Omni-Video and SANPHAM (HNC).
        2. Skip if already has a valid drive_url.
        3. Skip if local file does not exist.
        4. Skip if NONE of status_fb, status_yt, status_ig are 'pending' (already published/done).
        """
        folder_id = GoogleDriveUploader.get_folder_id_for_source(source_name)
        if not folder_id:
            return False

        # Rule 1: Skip if already backed up
        if existing_drive_url and str(existing_drive_url).strip().startswith("http"):
            return False

        # Rule 2: Skip if local video file doesn't exist
        if not local_path or not Path(local_path).exists():
            return False

        # Rule 3: Only upload if at least 1 automated channel is still pending
        statuses = [str(status_fb).strip().lower(), str(status_yt).strip().lower(), str(status_ig).strip().lower()]
        has_pending = any(s == "pending" for s in statuses)
        return has_pending

    def upload_file(
        self,
        local_path: str,
        folder_id: str,
        file_name: Optional[str] = None,
    ) -> Optional[str]:
        """Upload a local video file to target Google Drive folder, returning webViewLink."""
        if not self.service:
            logger.warning("Google Drive service not available.")
            return None

        p = Path(local_path)
        if not p.exists():
            logger.warning(f"File to upload not found: {local_path}")
            return None

        target_name = file_name or p.name
        mime_type = "video/mp4" if p.suffix.lower() == ".mp4" else "application/octet-stream"

        try:
            # Check if file with same name already exists in this folder to avoid duplicates
            query = f"'{folder_id}' in parents and name = '{target_name}' and trashed = false"
            existing = self.service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
            files = existing.get("files", [])
            if files:
                existing_file = files[0]
                file_id = existing_file["id"]
                drive_url = existing_file.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"
                logger.info(f"File '{target_name}' already exists in Drive folder (ID: {file_id}). Reusing URL.")
                return drive_url

            # Upload new file
            file_metadata = {
                "name": target_name,
                "parents": [folder_id],
            }
            media = MediaFileUpload(str(p), mimetype=mime_type, resumable=True)
            uploaded_file = (
                self.service.files()
                .create(body=file_metadata, media_body=media, fields="id, name, webViewLink")
                .execute()
            )

            file_id = uploaded_file.get("id")
            drive_url = uploaded_file.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"
            logger.info(f"Successfully uploaded '{target_name}' to Google Drive: {drive_url}")
            return drive_url

        except Exception as e:
            logger.error(f"Error uploading '{local_path}' to Google Drive: {e}")
            return None
