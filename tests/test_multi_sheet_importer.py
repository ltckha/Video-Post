"""Unit tests for Smart Multi-Format Google Sheet Importer & Platform Caption Formatter."""

import pytest
from unittest.mock import patch
from core.sheet_importer import SmartGoogleSheetImporter, format_caption_for_platform


def test_platform_caption_formatting():
    title = "Test Product Title"
    affiliate_link = "https://s.shopee.vn/sample"
    raw_caption = "Sample video description for unboxing"

    fb_caption = format_caption_for_platform("facebook", title, raw_caption, affiliate_link)
    assert "Test Product Title" in fb_caption
    assert "https://s.shopee.vn/sample" in fb_caption
    assert "#nesty" in fb_caption

    yt_caption = format_caption_for_platform("youtube", title, raw_caption, affiliate_link)
    assert "https://s.shopee.vn/sample" not in yt_caption
    assert "#shorts" in yt_caption

    ig_caption = format_caption_for_platform("instagram", title, raw_caption, affiliate_link)
    assert "Test Product Title" in ig_caption


def test_smart_importer_sheet_1_shopee():
    csv_sheet1 = (
        "Mã sản phẩm,Tên sản phẩm,Link ưu đãi,Output File\n"
        "24438735904,[NE01] Dép Sục NESTY,https://s.shopee.vn/aff1,/Volumes/Media/Omni-Video/24438735904.mp4\n"
    )

    importer = SmartGoogleSheetImporter(sheet_url="https://docs.google.com/spreadsheets/d/dummy1/")
    with patch.object(importer, "fetch_sheet_csv", return_value=csv_sheet1):
        jobs = importer.parse_jobs(target_platforms=["facebook", "youtube"])

        assert len(jobs) == 1
        assert jobs[0]["item_id"] == "24438735904"
        assert jobs[0]["title"] == "[NE01] Dép Sục NESTY"
        assert jobs[0]["video_path"] == "/Volumes/Media/Omni-Video/24438735904.mp4"
        assert "https://s.shopee.vn/aff1" in jobs[0]["platform_captions"]["facebook"]


def test_smart_importer_sheet_2_auto_factory():
    csv_sheet2 = (
        "Project ID,Video Title,Caption & Hashtags,Output File\n"
        "VID_20260621_173714,Unboxing Acrylic Marker,Khui hộp bộ màu vẽ #unboxing,/Volumes/Media/Auto-Video-Factory/VID_20260621_173714_final.mp4\n"
    )

    importer = SmartGoogleSheetImporter(sheet_url="https://docs.google.com/spreadsheets/d/dummy2/")
    with patch.object(importer, "fetch_sheet_csv", return_value=csv_sheet2):
        jobs = importer.parse_jobs(target_platforms=["facebook", "instagram"])

        assert len(jobs) == 1
        assert jobs[0]["item_id"] == "VID_20260621_173714"
        assert jobs[0]["title"] == "Unboxing Acrylic Marker"
        assert jobs[0]["video_path"] == "/Volumes/Media/Auto-Video-Factory/VID_20260621_173714_final.mp4"
        assert "Khui hộp bộ màu vẽ" in jobs[0]["platform_captions"]["facebook"]
