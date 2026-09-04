"""Unit tests for cultural semantic event detection and post_before inference."""

import pytest
from core.event_detector import detect_event_deadline


def test_detect_lunar_mid_autumn():
    """Test detecting Mid-Autumn festival without explicit date."""
    # Test lantern
    res1 = detect_event_deadline(
        title="[HOT] Lồng đèn thỏ ngọc phát sáng rước đèn đêm rằm",
        description="Đồ chơi trung thu cho bé cực xinh",
        year=2026
    )
    assert res1 is not None
    name1, date1 = res1
    assert "Trung Thu" in name1
    assert date1 == "25/09/2026"

    # Test mooncake
    res2 = detect_event_deadline(
        title="Bánh trung thu thập cẩm gà quay 2 trứng muối",
        description="Hộp quà trăng rằm cao cấp",
        year=2026
    )
    assert res2 is not None
    name2, date2 = res2
    assert "Trung Thu" in name2
    assert date2 == "25/09/2026"


def test_detect_lunar_new_year():
    """Test detecting Tet Nguyen Dan from cultural symbols."""
    res = detect_event_deadline(
        title="Hộp quà tết đoàn viên kèm bao lì xì rồng vàng",
        description="Bánh chưng, mứt tết sum vầy",
        year=2026
    )
    assert res is not None
    name, date_str = res
    assert "Tết Nguyên Đán" in name
    assert date_str == "16/02/2026"


def test_detect_solar_holidays():
    """Test detecting fixed solar calendar events."""
    # Back to school (05/09)
    res_school = detect_event_deadline(
        title="Balo chống gù tựu trường cho bé lớp 1",
        description="Chuẩn bị năm học mới rực rỡ",
        year=2026
    )
    assert res_school is not None
    assert "Khai Giảng" in res_school[0]
    assert res_school[1] == "05/09/2026"

    # Vietnamese Women's Day (20/10)
    res_women = detect_event_deadline(
        title="BST Giày Cao Gót Món Quà Tri Ân 20/10 Cho Phái Đẹp",
        year=2026
    )
    assert res_women is not None
    assert "20/10" in res_women[0]
    assert res_women[1] == "20/10/2026"

    # Teachers' Day (20/11)
    res_teachers = detect_event_deadline(
        title="Ví da nam tri ân thầy cô kính yêu nhân ngày 20/11",
        year=2026
    )
    assert res_teachers is not None
    assert "20/11" in res_teachers[0]
    assert res_teachers[1] == "20/11/2026"

    # Christmas (25/12)
    res_xmas = detect_event_deadline(
        title="Cây thông noel để bàn mini trang trí phòng khách",
        year=2026
    )
    assert res_xmas is not None
    assert "Giáng Sinh" in res_xmas[0]
    assert res_xmas[1] == "25/12/2026"


def test_regular_product_returns_none():
    """Test that ordinary products with no occasion return None."""
    res = detect_event_deadline(
        title="Giày Tây Nam Công Sở Da Bò Thật Khâu Đế Bền Đẹp",
        description="Thiết kế mũi nhọn ôm chân lịch lãm",
        year=2026
    )
    assert res is None
