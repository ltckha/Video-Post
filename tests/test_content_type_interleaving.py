"""Unit tests for universal content_type classification and smart queue interleaving across all brands."""

import pytest
from core.sheet_client import detect_content_type, VALID_CONTENT_TYPES
from core.queue_scheduler import interleave_by_content_type, format_content_type_badge


def test_detect_content_type_across_brands():
    """Test universal content classification for shoes, macadamia, leather, and gadgets."""
    # 1. Hai Nancy (Shoes & Leather)
    # SANPHAM has real products but videos are AI-rendered!
    assert detect_content_type(source_name="SANPHAM", title="Giày Cao Gót Da Bò Nữ", category="Giày cao gót") == "ai_product"
    assert detect_content_type(source_name="SANPHAM", title="Thắt Lưng Nam Da Bò Khóa Tự Động", category="Dây nịt") == "ai_accessory"
    assert detect_content_type(source_name="SANPHAM", title="Ví Da Nam Cầm Tay", category="Ví da") == "ai_accessory"
    assert detect_content_type(source_name="SANPHAM", title="Mẹo làm sạch giày da trắng tại nhà") == "tips_tricks"

    # Real camera videos from Auto-Video-Factory
    assert detect_content_type(source_name="Auto-Video-Factory", title="Trải nghiệm mang thử giày tây công sở") == "real_product"
    assert detect_content_type(source_name="Auto-Video-Factory", title="Trên tay chiếc thắt lưng da bò thật") == "real_accessory"
    assert detect_content_type(source_name="Auto-Video-Factory", title="Hướng dẫn cách bảo quản giày da không bị mốc") == "tips_tricks"

    # 2. Macadamia & Agricultural products (Macadamia Hải Nancy / YenYen Farm)
    assert detect_content_type(source_name="Omni-Video", title="Hạt Macca Sấy Nứt Vỏ Hộp 500g") == "ai_product"
    assert detect_content_type(source_name="Auto-Video-Factory", title="Khui hộp ăn thử hạt macca giòn béo") == "real_product"
    assert detect_content_type(source_name="Auto-Video-Factory", title="Kìm tách vỏ macca cao cấp") == "real_accessory"
    assert detect_content_type(source_name="Auto-Video-Factory", title="Cách bảo quản hạt macca giòn lâu không bị hôi dầu") == "tips_tricks"

    # 3. Yen Handmade Leather
    assert detect_content_type(source_name="Auto-Video-Factory", title="Túi tote da bò sáp thủ công") == "real_accessory"
    assert detect_content_type(source_name="Auto-Video-Factory", title="Cách phân biệt da bò thật và da simili") == "tips_tricks"


def test_interleave_by_content_type_distribution():
    """Test that round-robin interleaving avoids consecutive identical content types."""
    jobs = [
        {"job_id": "P1", "content_type": "real_product"},
        {"job_id": "P2", "content_type": "real_product"},
        {"job_id": "P3", "content_type": "real_product"},
        {"job_id": "T1", "content_type": "tips_tricks"},
        {"job_id": "A1", "content_type": "real_accessory"},
        {"job_id": "AI1", "content_type": "ai_product"},
    ]

    interleaved = interleave_by_content_type(jobs)
    types_seq = [j["content_type"] for j in interleaved]

    # Order of cycle: real_product -> tips_tricks -> real_accessory -> ai_product -> (next round) real_product ...
    expected_seq = [
        "real_product",
        "tips_tricks",
        "real_accessory",
        "ai_product",
        "real_product",
        "real_product",
    ]
    assert types_seq == expected_seq


def test_format_content_type_badge():
    """Test console badge rendering for content_type."""
    assert "Sản phẩm thật" in format_content_type_badge("real_product")
    assert "Sản phẩm AI" in format_content_type_badge("ai_product")
    assert "Phụ kiện thật" in format_content_type_badge("real_accessory")
    assert "Phụ kiện AI" in format_content_type_badge("ai_accessory")
    assert "Mẹo vặt" in format_content_type_badge("tips_tricks")
