"""Unit tests for HNC_Master SANPHAM tab ingestion and source filtering."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from core.sheet_client import GoogleSheetDirectClient, MASTER_HEADERS


def test_sanpham_tab_filtering_and_mapping(tmp_path):
    """Test that SANPHAM tab extracts products with 'VIDEO', finds single mp4 file, defaults to 'Hiệu giày Hải Nancy' and 'needs_edit'."""
    # Create a mock video folder with exactly 1 video
    video_dir = tmp_path / "RV36330N"
    video_dir.mkdir(parents=True)
    video_file = video_dir / "RV36330N_final.mp4"
    video_file.write_text("dummy video")

    # Mock Worksheet data for SANPHAM
    sanpham_headers = [
        "product_code", "product_name", "product_price", "product_color",
        "Tên Ngành Hàng", "product_description", "content_path", "content_files"
    ]
    sanpham_rows = [
        sanpham_headers,
        # Row 1: Has VIDEO
        ["RV36330N", "Giày Cao Gót Nữ Sang Trọng", "590.000đ", "Đen", "Giày cao gót", "Chất liệu da cao cấp", str(video_dir), "VIDEO, IMG"],
        # Row 2: Only IMG (Should be ignored)
        ["959D", "Giày Lười Nam", "650.000đ", "Nâu", "Giày lười", "Da bò thật", str(tmp_path / "959D"), "IMG"],
    ]

    # Mock GoogleSheetDirectClient
    with patch.object(GoogleSheetDirectClient, "_connect", return_value=None):
        client = GoogleSheetDirectClient(sheet_url="mock_url")
        client.sh = MagicMock()

        # Mock worksheets
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
        # Check what was sent to master_ws.update
        update_calls = mock_master_ws.update.call_args_list
        assert len(update_calls) > 0
        written_matrix = update_calls[0].kwargs.get("values") or update_calls[0][0][0]
        
        # Row 0: Headers, Row 1: RV36330N (Only 1 product because 959D had no VIDEO)
        assert len(written_matrix) == 2
        row_rv = dict(zip(MASTER_HEADERS, written_matrix[1]))
        assert row_rv["job_id"] == "RV36330N"
        assert row_rv["title"] == "Giày Cao Gót Nữ Sang Trọng"
        assert str(video_file.resolve()) in row_rv["video_path"]
        assert row_rv["brand_fb"] == "Hiệu giày Hải Nancy"
        assert row_rv["brand_tt"] == "Hiệu giày Hải Nancy"
        assert row_rv["status_fb"] == "needs_edit"
        assert row_rv["status_tt"] == "needs_edit"


def test_sanpham_multiple_videos_marks_not_configured(tmp_path):
    """Test that when multiple video files are found, status is marked as 'not_configured'."""
    video_dir = tmp_path / "MULTI99"
    video_dir.mkdir(parents=True)
    (video_dir / "vid1.mp4").write_text("dummy 1")
    (video_dir / "vid2.mp4").write_text("dummy 2")

    sanpham_headers = [
        "product_code", "product_name", "product_price", "product_color",
        "Tên Ngành Hàng", "product_description", "content_path", "content_files"
    ]
    sanpham_rows = [
        sanpham_headers,
        ["MULTI99", "Giày Đa Video", "700.000đ", "Đen", "Giày tây", "Mô tả", str(video_dir), "VIDEO"],
    ]

    with patch.object(GoogleSheetDirectClient, "_connect", return_value=None):
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
        
        assert len(written_matrix) == 2
        row = dict(zip(MASTER_HEADERS, written_matrix[1]))
        assert row["job_id"] == "MULTI99"
        assert "⚠️ Phát hiện 2 video" in row["video_path"]
        assert row["status_fb"] == "not_configured"
        assert row["status_tt"] == "not_configured"


def test_sanpham_deduplication_preserves_existing_rows():
    """Test that syncing SANPHAM skips products already on Tab Master."""
    old_row_dict = {h: "" for h in MASTER_HEADERS}
    old_row_dict.update({
        "job_id": "RV36330N",
        "title": "Giày Cao Gót Cũ",
        "video_path": "/path/old.mp4",
        "post_before": "20/10/2026",
        "caption_fb": "Caption cũ",
        "brand_fb": "Hiệu giày Hải Nancy",
        "brand_tt": "Hiệu giày Hải Nancy",
        "status_fb": "published",
        "status_tt": "published",
    })
    mock_master_rows = [
        MASTER_HEADERS,
        [old_row_dict.get(h, "") for h in MASTER_HEADERS]
    ]

    sanpham_rows = [
        ["product_code", "product_name", "product_price", "product_color", "Tên Ngành Hàng", "product_description", "content_path", "content_files"],
        # Already exists in master
        ["RV36330N", "Giày Cao Gót Mới", "590.000đ", "Đen", "Giày cao gót", "Mô tả mới", "/path/new", "VIDEO"],
    ]

    with patch.object(GoogleSheetDirectClient, "_connect", return_value=None):
        client = GoogleSheetDirectClient(sheet_url="mock_url")
        client.sh = MagicMock()

        mock_master_ws = MagicMock()
        mock_master_ws.get_all_values.return_value = mock_master_rows
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
        
        # Must preserve original published status, post_before, and captions
        assert len(written_matrix) == 2
        row_rv = dict(zip(MASTER_HEADERS, written_matrix[1]))
        assert row_rv["job_id"] == "RV36330N"
        assert row_rv["caption_fb"] == "Caption cũ"
        assert row_rv["post_before"] == "20/10/2026"
        assert row_rv["status_fb"] == "published"
