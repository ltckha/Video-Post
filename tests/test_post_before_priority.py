"""Unit tests for 'post_before' deadline parsing, event window classification, and queue prioritization."""

import pytest
from datetime import date, timedelta
from core.queue_scheduler import (
    parse_post_before_date,
    calculate_days_remaining,
    get_event_tier,
    sort_jobs_by_priority,
    format_deadline_badge,
)


def test_parse_post_before_date():
    """Test date parsing for various standard formats."""
    assert parse_post_before_date("20/10/2026") == date(2026, 10, 20)
    assert parse_post_before_date("02-09-2026") == date(2026, 9, 2)
    assert parse_post_before_date("2026-12-25") == date(2026, 12, 25)
    assert parse_post_before_date("05/10/26") == date(2026, 10, 5)
    assert parse_post_before_date("20/10/2026 14:30") == date(2026, 10, 20)
    assert parse_post_before_date("") is None
    assert parse_post_before_date(None) is None
    assert parse_post_before_date("invalid-date") is None


def test_calculate_days_remaining():
    """Test calculating days remaining with a fixed reference date."""
    ref_date = date(2026, 9, 4)

    assert calculate_days_remaining("04/09/2026", today=ref_date) == 0
    assert calculate_days_remaining("05/09/2026", today=ref_date) == 1
    assert calculate_days_remaining("09/09/2026", today=ref_date) == 5
    assert calculate_days_remaining("02/09/2026", today=ref_date) == -2
    assert calculate_days_remaining("", today=ref_date) is None


def test_get_event_tier_classification():
    """Test the 5-tier classification logic based on golden window (3-15 days)."""
    ref_date = date(2026, 9, 4)

    # Tier 1: Urgent (0 <= delta < 3)
    tier, delta, label = get_event_tier("04/09/2026", today=ref_date)
    assert tier == 1
    assert delta == 0
    assert "Khẩn cấp" in label

    tier, delta, label = get_event_tier("06/09/2026", today=ref_date)
    assert tier == 1
    assert delta == 2

    # Tier 2: Golden window (3 <= delta <= 15)
    tier, delta, label = get_event_tier("07/09/2026", today=ref_date)
    assert tier == 2
    assert delta == 3
    assert "Khung giờ vàng" in label

    tier, delta, label = get_event_tier("19/09/2026", today=ref_date)
    assert tier == 2
    assert delta == 15

    # Tier 3: Regular post (No post_before)
    tier, delta, label = get_event_tier("", today=ref_date)
    assert tier == 3
    assert delta is None
    assert "thông thường" in label

    # Tier 4: Future event (delta > 15)
    tier, delta, label = get_event_tier("20/10/2026", today=ref_date)
    assert tier == 4
    assert delta == 46
    assert "Chưa đến thời điểm" in label

    # Tier 5: Expired (delta < 0)
    tier, delta, label = get_event_tier("02/09/2026", today=ref_date)
    assert tier == 5
    assert delta == -2
    assert "Đã quá hạn" in label


def test_sort_jobs_by_priority():
    """Test sorting candidates strictly by priority: Urgent -> Golden Window -> Regular -> Future -> Expired."""
    ref_date = date(2026, 9, 4)

    jobs = [
        {"job_id": "REG_1", "title": "Bài thường 1", "post_before": ""},
        {"job_id": "FUTURE_1", "title": "Sự kiện 20/10 xa", "post_before": "20/10/2026"},  # delta = 46 (Tier 4)
        {"job_id": "GOLDEN_2", "title": "Sự kiện 14/9", "post_before": "14/09/2026"},       # delta = 10 (Tier 2)
        {"job_id": "EXPIRED_1", "title": "Bài 2/9 lố", "post_before": "02/09/2026"},        # delta = -2 (Tier 5)
        {"job_id": "URGENT_1", "title": "Bài ngày mai 5/9", "post_before": "05/09/2026"},   # delta = 1 (Tier 1)
        {"job_id": "GOLDEN_1", "title": "Sự kiện 09/9", "post_before": "09/09/2026"},       # delta = 5 (Tier 2)
        {"job_id": "URGENT_0", "title": "Bài hôm nay 4/9", "post_before": "04/09/2026"},    # delta = 0 (Tier 1)
        {"job_id": "REG_2", "title": "Bài thường 2", "post_before": ""},
    ]

    sorted_jobs = sort_jobs_by_priority(jobs, today=ref_date)
    sorted_ids = [j["job_id"] for j in sorted_jobs]

    expected_ids = [
        "URGENT_0",   # Tier 1 (delta 0)
        "URGENT_1",   # Tier 1 (delta 1)
        "GOLDEN_1",   # Tier 2 (delta 5)
        "GOLDEN_2",   # Tier 2 (delta 10)
        "REG_1",      # Tier 3 (regular FIFO 1)
        "REG_2",      # Tier 3 (regular FIFO 2)
        "FUTURE_1",   # Tier 4 (future delta 46)
        "EXPIRED_1",  # Tier 5 (expired delta -2)
    ]

    assert sorted_ids == expected_ids


def test_format_deadline_badge():
    """Test console badge rendering for each tier."""
    ref_date = date(2026, 9, 4)

    # Urgent badge
    badge_urgent = format_deadline_badge("04/09/2026", today=ref_date)
    assert "NƯỚC RÚT KHẨN CẤP" in badge_urgent

    # Golden window badge
    badge_golden = format_deadline_badge("09/09/2026", today=ref_date)
    assert "KHUNG GIỜ VÀNG SỰ KIỆN" in badge_golden

    # Future badge
    badge_future = format_deadline_badge("20/10/2026", today=ref_date)
    assert "Sự kiện tương lai" in badge_future

    # Expired badge
    badge_expired = format_deadline_badge("02/09/2026", today=ref_date)
    assert "ĐÃ QUÁ HẠN" in badge_expired

    # Empty badge
    assert format_deadline_badge("") == ""
