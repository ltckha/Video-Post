"""Unit test to verify that sync_input_tabs_to_master preserves custom columns (like audit scores and notes)
without clearing or losing user-defined headers on Tab Master.
"""

import pytest
from unittest.mock import MagicMock, patch
from core.sheet_client import GoogleSheetDirectClient


def test_sync_preserves_custom_headers_and_scores():
    sc = GoogleSheetDirectClient.__new__(GoogleSheetDirectClient)
    sc.sh = MagicMock()
    sc.gc = MagicMock()

    # Simulate existing Master tab with a custom 'Opening Hook Score' column and a 'Notes' column
    existing_headers = [
        "job_id", "title", "video_path", "drive_url", "Opening Hook Score", "post_before",
        "content_type", "shopee_link", "caption_fb", "caption_yt", "caption_ig",
        "caption_tt", "caption_shopee", "caption_zalo", "brand_fb", "brand_yt",
        "brand_ig", "brand_tt", "status_fb", "status_yt", "status_ig", "status_tt",
        "status_shopee", "status_zalo", "Notes"
    ]
    existing_rows = [
        existing_headers,
        [
            "VID_001", "Existing Title", "/path/to/vid1.mp4", "", "9.5/10", "30/09/2026",
            "real_product", "https://shopee.vn/link1", "Cap FB", "Cap YT", "Cap IG",
            "Cap TT", "Cap Shopee", "Cap Zalo", "Brand FB", "Brand YT",
            "Brand IG", "Brand TT", "published", "published", "published", "published",
            "published", "published", "VIP Product"
        ]
    ]

    master_ws_mock = MagicMock()
    master_ws_mock.get_all_values.return_value = existing_rows

    factory_ws_mock = MagicMock()
    factory_ws_mock.get_all_values.return_value = [
        ["job_id", "title", "video_path", "Opening Hook Score"],
        ["VID_002", "New Video from Factory", "/path/to/vid2.mp4", "8.8/10"]
    ]

    def mock_worksheet(name):
        if name == "Master":
            return master_ws_mock
        return factory_ws_mock

    sc.sh.worksheet.side_effect = mock_worksheet
    sc.get_worksheet = mock_worksheet

    with patch("core.drive_uploader.GoogleDriveUploader"):
        res = sc.sync_input_tabs_to_master(source_filter="Auto-Video-Factory")

    # Verify that master_ws.clear() was NEVER called
    master_ws_mock.clear.assert_not_called()

    # Verify update was called with preserved headers
    assert master_ws_mock.update.called
    call_args = master_ws_mock.update.call_args[1]
    matrix = call_args["values"]

    # Header check
    updated_headers = matrix[0]
    assert "Opening Hook Score" in updated_headers
    assert "Notes" in updated_headers

    # Row 1 check (Existing row preserved its score and note)
    row_1 = matrix[1]
    score_idx = updated_headers.index("Opening Hook Score")
    notes_idx = updated_headers.index("Notes")
    assert row_1[score_idx] == "9.5/10"
    assert row_1[notes_idx] == "VIP Product"

    # Row 2 check (New row mapped Opening Hook Score from Auto-Video-Factory)
    assert len(matrix) >= 3
    row_2 = matrix[2]
    assert row_2[score_idx] == "8.8/10"
