"""Google Drive Uploader Module for Video-Post Cloud-First Backup.

Uploads local video files (Omni-Video and HNC SANPHAM) to dedicated Google Drive folders,
returning shareable drive URLs stored in Tab Master 'drive_url' column.
"""

import os
import shutil
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

DEFAULT_SA_PATH = "config/service_account.json"

# Google Drive Target Folder IDs
DRIVE_FOLDER_OMNI = "1j4cTLmaE963pqQ6lrrSN73reY9_zaLao"  # Spark/Omni-Video/Outputs/
DRIVE_FOLDER_HNC = "1rSrT8OWQPpkGgXiPFFhVnVUhCJC_zqe7"   # Spark/HNC_Master/Outputs/

SCOPES = [
    "https://www.googleapis.com/auth/drive",
]


class GoogleDriveUploader:
    """Handles uploading video files to Google Drive folders via Service Account and Local Sync Bridge."""

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
    def get_local_drive_folder(source_name: str) -> Optional[Path]:
        """Get the local Google Drive for Desktop synced folder on macOS if available."""
        user_home = Path.home()
        cloud_storage = user_home / "Library/CloudStorage"
        if not cloud_storage.exists():
            return None

        clean = str(source_name).strip().lower()
        for drive_dir in cloud_storage.glob("GoogleDrive-*"):
            spark_dir = drive_dir / "My Drive" / "Spark"
            if spark_dir.exists():
                if "omni" in clean:
                    out_dir = spark_dir / "Omni-Video" / "Outputs"
                    out_dir.mkdir(parents=True, exist_ok=True)
                    return out_dir
                if "sanpham" in clean or "hnc" in clean:
                    out_dir = spark_dir / "HNC_Master" / "Outputs"
                    out_dir.mkdir(parents=True, exist_ok=True)
                    return out_dir
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
        source_name: Optional[str] = None,
    ) -> Optional[str]:
        """Upload a local video file to target Google Drive folder, returning webViewLink.
        
        Uses Hybrid Engine:
        1. Checks if file already exists in Google Drive folder.
        2. If local Google Drive Desktop folder is available, copies file to local mount (using user's personal quota).
        3. Retrieves webViewLink from Google Drive API v3.
        4. Fallbacks to direct API upload if local sync mount is not available.
        """
        p = Path(local_path)
        if not p.exists():
            logger.warning(f"File to upload not found: {local_path}")
            return None

        target_name = file_name or p.name

        # 1. Check if file already exists in Drive folder to avoid duplicate uploads
        if self.service:
            try:
                query = f"'{folder_id}' in parents and name = '{target_name}' and trashed = false"
                existing = self.service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
                files = existing.get("files", [])
                if files:
                    existing_file = files[0]
                    file_id = existing_file["id"]
                    drive_url = existing_file.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"
                    logger.info(f"File '{target_name}' already exists in Drive folder (ID: {file_id}). Reusing URL.")
                    return drive_url
            except Exception as e:
                logger.warning(f"Could not query Drive files: {e}")

        # 2. Check for local Google Drive desktop sync folder
        inferred_source = source_name or ("omni" if folder_id == DRIVE_FOLDER_OMNI else "sanpham")
        local_drive_dir = self.get_local_drive_folder(inferred_source)

        if local_drive_dir and local_drive_dir.exists():
            dest_file = local_drive_dir / target_name
            try:
                # Copy file into Google Drive for Desktop sync folder (uses user's personal quota)
                if not dest_file.exists() or dest_file.stat().st_size != p.stat().st_size:
                    shutil.copy2(str(p), str(dest_file))
                    logger.info(f"Synced '{target_name}' to local Google Drive folder: {dest_file}")

                # Poll Drive API for webViewLink if service is available
                if self.service:
                    for _ in range(4):
                        time.sleep(1)
                        query = f"'{folder_id}' in parents and name = '{target_name}' and trashed = false"
                        res = self.service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
                        files = res.get("files", [])
                        if files:
                            file_id = files[0]["id"]
                            drive_url = files[0].get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"
                            logger.info(f"Retrieved Google Drive URL for '{target_name}': {drive_url}")
                            return drive_url

                # Return local path representation if not yet indexed by API
                return str(dest_file)
            except Exception as e:
                logger.error(f"Error copying to local Google Drive folder: {e}")

        # 3. Direct API Upload Fallback (for Shared Drives / Headless environments)
        if not self.service:
            logger.warning("Google Drive service not available.")
            return None

        mime_type = "video/mp4" if p.suffix.lower() == ".mp4" else "application/octet-stream"
        try:
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
            logger.info(f"Successfully uploaded '{target_name}' to Google Drive via API: {drive_url}")
            return drive_url
        except HttpError as e:
            if "storageQuotaExceeded" in str(e):
                logger.error(
                    f"Service Account storage quota exceeded. Please ensure Google Drive for Desktop is running on macOS "
                    f"or use a Google Workspace Shared Drive for folder {folder_id}."
                )
            else:
                logger.error(f"Google Drive API HttpError for '{local_path}': {e}")
            return None
        except Exception as e:
            logger.error(f"Error uploading '{local_path}' to Google Drive: {e}")
            return None
