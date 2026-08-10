"""Unit tests for AI Caption Generator and 19 Concise English Columns Master Output Sheet Exporter."""

import json
import pytest
from core.ai_captioner import AICaptionGenerator
from core.sheet_exporter import MasterSheetExporter
from core.queue import JobQueue


def test_ai_caption_generator_rules():
    gen = AICaptionGenerator()
    title = "[NE01] Dép Sục Nam Nữ NESTY Kiểu Dáng Basic Đế Mềm"
    raw_desc = "Sắm ngay tại đây để nhận ưu đãi hấp dẫn"
    link = "https://s.shopee.vn/demo123"

    captions = gen.generate_all_captions(title=title, raw_caption=raw_desc, affiliate_link=link)

    # 1. Check all 6 platforms generated
    assert set(captions.keys()) == {"facebook", "youtube", "instagram", "tiktok", "shopee", "zalo"}

    # 2. Check CTA removed
    assert "Sắm ngay tại đây" not in captions["facebook"]

    # 3. Check Shopee strict length limit (< 150 chars total)
    shopee_cap = captions["shopee"]
    assert len(shopee_cap) <= 150
    assert "#shopeevideo" in shopee_cap
    assert "#luotvuimualien" in shopee_cap
    assert "#shopeecreator" in shopee_cap
    assert "#videohangthoitrang" in shopee_cap  # Detected category for dép sục

    # 4. Check YouTube Shorts hashtag
    assert "#shorts" in captions["youtube"]


def test_master_sheet_exporter_english_columns(tmp_path):
    db_file = tmp_path / "test_exporter.db"
    csv_file = tmp_path / "master_output_sheet.csv"

    queue = JobQueue(db_path=str(db_file))
    j_id = queue.add_job(
        video_path="/Volumes/Media/demo.mp4",
        target_platforms=["facebook"],
        title="Dép Sục NESTY",
        extra_options={
            "brand_map": {"facebook": "Mua Chuẩn Xài Lâu"},
            "platform_captions": {
                "facebook": "Bài viết Facebook",
                "shopee": "Bài viết Shopee #shopeevideo",
            },
            "affiliate_link": "https://s.shopee.vn/demo",
        },
    )

    exporter = MasterSheetExporter(db_path=str(db_file), output_csv=csv_file)
    exported_path = exporter.export_master_sheet()

    assert exported_path.exists()
    content = exported_path.read_text(encoding="utf-8-sig")
    assert "job_id" in content
    assert "caption_shopee" in content
    assert "status_fb" in content
    assert "Mua Chuẩn Xài Lâu" in content
