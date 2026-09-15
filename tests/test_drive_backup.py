"""Unit tests for Google Drive video backup and Dual Video Source validation."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.drive_uploader import (
    GoogleDriveUploader,
    DRIVE_FOLDER_OMNI,
    DRIVE_FOLDER_HNC,
)
from core.sheet_client import GoogleSheetDirectClient, MASTER_HEADERS


def test_get_folder_id_for_source():
    """Verify source-to-folder-ID mapping."""
    assert GoogleDriveUploader.get_folder_id_for_source("Omni-Video") == DRIVE_FOLDER_OMNI
    assert GoogleDriveUploader.get_folder_id_for_source("omni") == DRIVE_FOLDER_OMNI
    assert GoogleDriveUploader.get_folder_id_for_source("SANPHAM") == DRIVE_FOLDER_HNC
    assert GoogleDriveUploader.get_folder_id_for_source("hnc_master") == DRIVE_FOLDER_HNC
    assert GoogleDriveUploader.get_folder_id_for_source("Auto-Video-Factory") is None
    assert GoogleDriveUploader.get_folder_id_for_source("Unknown") is None


def test_should_upload_video_filtering(tmp_path):
    """Verify strict filtering rules for Google Drive auto-backup."""
    dummy_video = tmp_path / "test.mp4"
    dummy_video.write_text("video content")

    # 1. Unsupported source should NOT upload
    assert not GoogleDriveUploader.should_upload_video(
        source_name="Auto-Video-Factory",
        local_path=str(dummy_video),
        existing_drive_url="",
        status_fb="pending",
    )

    # 2. Already has drive_url should NOT upload
    assert not GoogleDriveUploader.should_upload_video(
        source_name="Omni-Video",
        local_path=str(dummy_video),
        existing_drive_url="https://drive.google.com/file/d/123/view",
        status_fb="pending",
    )

    # 3. Non-existent local file should NOT upload
    assert not GoogleDriveUploader.should_upload_video(
        source_name="Omni-Video",
        local_path=str(tmp_path / "non_existent.mp4"),
        existing_drive_url="",
        status_fb="pending",
    )

    # 4. All channels published / not pending should NOT upload
    assert not GoogleDriveUploader.should_upload_video(
        source_name="SANPHAM",
        local_path=str(dummy_video),
        existing_drive_url="",
        status_fb="published",
        status_yt="published",
        status_ig="published",
    )

    # 5. Valid case: Omni/SANPHAM, file exists, drive_url empty, at least 1 pending
    assert GoogleDriveUploader.should_upload_video(
        source_name="Omni-Video",
        local_path=str(dummy_video),
        existing_drive_url="",
        status_fb="pending",
        status_yt="published",
        status_ig="published",
    )
    assert GoogleDriveUploader.should_upload_video(
        source_name="SANPHAM",
        local_path=str(dummy_video),
        existing_drive_url="",
        status_fb="needs_edit",
        status_yt="pending",
        status_ig="not_configured",
    )


def test_upload_file_new_and_existing(tmp_path):
    """Test upload_file handles both new file upload and existing file reuse."""
    dummy_video = tmp_path / "demo.mp4"
    dummy_video.write_text("content")

    with patch.object(GoogleDriveUploader, "_init_service", return_value=None):
        uploader = GoogleDriveUploader()
        uploader.service = MagicMock()

        # Case 1: File already exists in Google Drive
        uploader.service.files().list().execute.return_value = {
            "files": [{"id": "existing_id_123", "name": "demo.mp4", "webViewLink": "https://drive.google.com/file/d/existing_id_123/view"}]
        }
        res_url = uploader.upload_file(str(dummy_video), DRIVE_FOLDER_OMNI)
        assert res_url == "https://drive.google.com/file/d/existing_id_123/view"

        # Case 2: File does not exist yet -> Uploads new file
        uploader.service.files().list().execute.return_value = {"files": []}
        uploader.service.files().create().execute.return_value = {
            "id": "new_id_456",
            "name": "demo.mp4",
            "webViewLink": "https://drive.google.com/file/d/new_id_456/view",
        }
        with patch("core.drive_uploader.MediaFileUpload"):
            res_url2 = uploader.upload_file(str(dummy_video), DRIVE_FOLDER_OMNI)
            assert res_url2 == "https://drive.google.com/file/d/new_id_456/view"


def test_sync_input_tabs_integrates_drive_backup(tmp_path):
    """Test sync_input_tabs_to_master populates drive_url via GoogleDriveUploader."""
    video_file = tmp_path / "SP001.mp4"
    video_file.write_text("video binary")

    sanpham_headers = [
        "product_code", "product_name", "product_price", "product_color",
        "Tên Ngành Hàng", "product_description", "content_path", "content_files"
    ]
    sanpham_rows = [
        sanpham_headers,
        ["SP001", "Sản Phẩm Test Drive", "100.000đ", "Đen", "Giày", "Mô tả", str(video_file), "VIDEO"],
    ]

    with patch.object(GoogleSheetDirectClient, "_connect", return_value=None), \
         patch("core.sheet_client.GoogleDriveUploader") as mock_uploader_cls:

        mock_uploader_instance = MagicMock()
        mock_uploader_instance.upload_file.return_value = "https://drive.google.com/file/d/mock_drive_id/view"
        mock_uploader_cls.return_value = mock_uploader_instance
        mock_uploader_cls.should_upload_video.return_value = True
        mock_uploader_cls.get_folder_id_for_source.return_value = DRIVE_FOLDER_HNC

        client = GoogleSheetDirectClient(sheet_url="mock_url")
        client.sh = MagicMock()

        mock_master_ws = MagicMock()
        mock_master_ws.get_all_values.return_value = [MASTER_HEADERS]
        mock_sanpham_ws = MagicMock()
        mock_sanpham_ws.get_all_values.return_value = sanpham_rows

        def mock_worksheet(name):
            if name == "Master":
                return mock_master_ws
            elif name == "SANPHAM":
                return mock_sanpham_ws
            raise Exception("Tab not found")

        client.get_worksheet = mock_worksheet
        client.sh.worksheet = mock_worksheet

        res = client.sync_input_tabs_to_master(source_filter="SANPHAM")
        assert res["status"] == "success"

        update_calls = mock_master_ws.update.call_args_list
        written_matrix = update_calls[0].kwargs.get("values") or update_calls[0][0][0]

        row = dict(zip(MASTER_HEADERS, written_matrix[1]))
        assert row["job_id"] == "SP001"
        assert row["drive_url"] == "https://drive.google.com/file/d/mock_drive_id/view"


def test_dual_video_source_check(tmp_path):
    """Test validation handles both local file paths and Google Drive URLs."""
    local_file = tmp_path / "valid.mp4"
    local_file.write_text("dummy")

    non_existent = str(tmp_path / "ghost.mp4")
    drive_url = "https://drive.google.com/file/d/12345/view?usp=drivesdk"

    def is_valid_source(v_path: str) -> bool:
        v_path = (v_path or "").strip()
        is_cloud = v_path.startswith("http://") or v_path.startswith("https://")
        return bool(v_path and (is_cloud or Path(v_path).exists()))

    assert is_valid_source(str(local_file)) is True
    assert is_valid_source(drive_url) is True
    assert is_valid_source(non_existent) is False
    assert is_valid_source("") is False
