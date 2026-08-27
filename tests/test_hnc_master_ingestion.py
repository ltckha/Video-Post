"""Unit tests for HNC_Master SANPHAM tab ingestion and source filtering."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from core.sheet_client import GoogleSheetDirectClient


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
        mock_master_ws.get_all_values.return_value = [
            ["job_id", "title", "video_path", "shopee_link", "caption_fb", "caption_yt", "caption_ig", "caption_tt", "caption_shopee", "caption_zalo", "brand_fb", "brand_yt", "brand_ig", "brand_tt", "status_fb", "status_yt", "status_ig", "status_tt", "status_shopee", "status_zalo"]
        ]

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
        row_rv = written_matrix[1]
        assert row_rv[0] == "RV36330N"  # job_id
        assert row_rv[1] == "Giày Cao Gót Nữ Sang Trọng"  # title
        assert str(video_file.resolve()) in row_rv[2]  # video_path
        assert row_rv[10] == "Hiệu giày Hải Nancy"  # brand_fb
        assert row_rv[13] == "Hiệu giày Hải Nancy"  # brand_tt
        assert row_rv[14] == "needs_edit"  # status_fb
        assert row_rv[17] == "needs_edit"  # status_tt


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
        mock_master_ws.get_all_values.return_value = [
            ["job_id", "title", "video_path", "shopee_link", "caption_fb", "caption_yt", "caption_ig", "caption_tt", "caption_shopee", "caption_zalo", "brand_fb", "brand_yt", "brand_ig", "brand_tt", "status_fb", "status_yt", "status_ig", "status_tt", "status_shopee", "status_zalo"]
        ]
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
        row = written_matrix[1]
        assert row[0] == "MULTI99"
        assert "⚠️ Phát hiện 2 video" in row[2]
        assert row[14] == "not_configured"  # status_fb
        assert row[17] == "not_configured"  # status_tt


def test_sanpham_deduplication_preserves_existing_rows():
    """Test that syncing SANPHAM skips products already on Tab Master."""
    mock_master_rows = [
        ["job_id", "title", "video_path", "shopee_link", "caption_fb", "caption_yt", "caption_ig", "caption_tt", "caption_shopee", "caption_zalo", "brand_fb", "brand_yt", "brand_ig", "brand_tt", "status_fb", "status_yt", "status_ig", "status_tt", "status_shopee", "status_zalo"],
        # Existing published product
        ["RV36330N", "Giày Cao Gót Cũ", "/path/old.mp4", "", "Caption cũ", "", "", "", "", "", "Hiệu giày Hải Nancy", "Hiệu giày Hải Nancy", "Hiệu giày Hải Nancy", "Hiệu giày Hải Nancy", "published", "published", "published", "published", "published", "published"]
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
        
        # Must preserve original published status and captions
        assert len(written_matrix) == 2
        row_rv = written_matrix[1]
        assert row_rv[0] == "RV36330N"
        assert row_rv[4] == "Caption cũ"
        assert row_rv[14] == "published"
