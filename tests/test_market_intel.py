"""Unit tests for core/market_intel.py (Market Intelligence Pipeline)."""

import json
import pytest
from unittest.mock import MagicMock
from core.market_intel import (
    load_market_intel,
    match_intel_with_master,
    apply_market_intel,
    parse_date_safely,
)


@pytest.fixture
def sample_intel_data():
    return {
        "report_date": "04/09/2026",
        "weather_alerts": [
            {
                "region": "Miền Bắc",
                "condition": "Mưa bão ngập úng",
                "boost_keywords": ["chống nước", "sấy giày", "nano"],
                "recommended_post_before": "08/09/2026",
            }
        ],
        "upcoming_events": [
            {
                "event_name": "Tết Trung Thu 2026",
                "event_date": "25/09/2026",
                "recommended_post_before": "15/09/2026",
                "boost_keywords": ["lồng đèn", "bánh trung thu"],
            }
        ],
        "recommended_products": [
            {
                "item_id": "SP_DIRECT_01",
                "title": "Giày Tây Công Sở Oxford Da Bò",
                "content_type": "real_product",
                "post_before": "07/09/2026",
                "reason": "Chiến dịch Payday sale",
            }
        ],
    }


def test_parse_date_safely():
    dt = parse_date_safely("25/09/2026")
    assert dt is not None
    assert dt.day == 25 and dt.month == 9 and dt.year == 2026

    dt2 = parse_date_safely("invalid-date")
    assert dt2 is None


def test_load_market_intel(tmp_path, sample_intel_data):
    file_path = tmp_path / "market_intel.json"
    file_path.write_text(json.dumps(sample_intel_data), encoding="utf-8")

    loaded = load_market_intel(str(file_path))
    assert loaded["report_date"] == "04/09/2026"
    assert len(loaded["weather_alerts"]) == 1

    with pytest.raises(FileNotFoundError):
        load_market_intel(str(tmp_path / "non_existent.json"))


def test_match_direct_item_id(sample_intel_data):
    records = [
        {
            "job_id": "SP_DIRECT_01",
            "title": "Giày Tây Oxford Nam",
            "post_before": "",
            "content_type": "",
        },
        {
            "job_id": "SP_OTHER",
            "title": "Sản phẩm bình thường",
            "post_before": "",
            "content_type": "real_product",
        },
    ]

    updates = match_intel_with_master(records, sample_intel_data)
    assert len(updates) == 1
    assert updates[0]["job_id"] == "SP_DIRECT_01"
    assert updates[0]["post_before"] == "07/09/2026"
    assert updates[0]["content_type"] == "real_product"
    assert "Khớp trực tiếp item_id" in updates[0]["_match_reason"]


def test_match_weather_keywords(sample_intel_data):
    records = [
        {
            "job_id": "SP_RAIN_01",
            "title": "Bình xịt phủ nano chống nước cho giày da",
            "post_before": "",
            "content_type": "real_accessory",
        }
    ]

    updates = match_intel_with_master(records, sample_intel_data)
    assert len(updates) == 1
    assert updates[0]["job_id"] == "SP_RAIN_01"
    assert updates[0]["post_before"] == "08/09/2026"
    assert "Khớp thời tiết" in updates[0]["_match_reason"]


def test_match_event_keywords(sample_intel_data):
    records = [
        {
            "job_id": "SP_EVENT_01",
            "title": "Lồng đèn thỏ ngọc phát sáng",
            "post_before": "",
            "content_type": "real_product",
        }
    ]

    updates = match_intel_with_master(records, sample_intel_data)
    assert len(updates) == 1
    assert updates[0]["job_id"] == "SP_EVENT_01"
    assert updates[0]["post_before"] == "15/09/2026"
    assert "Khớp sự kiện" in updates[0]["_match_reason"]


def test_does_not_overwrite_with_later_date(sample_intel_data):
    # Current post_before is 06/09/2026 (urgent), weather recommendation is 08/09/2026 (later)
    records = [
        {
            "job_id": "SP_RAIN_URGENT",
            "title": "Máy sấy giày khử mùi đi mưa",
            "post_before": "06/09/2026",
            "content_type": "real_accessory",
        }
    ]

    updates = match_intel_with_master(records, sample_intel_data)
    # Should not overwrite with a later date
    assert len(updates) == 0


def test_apply_market_intel_mock(tmp_path, sample_intel_data):
    file_path = tmp_path / "intel.json"
    file_path.write_text(json.dumps(sample_intel_data), encoding="utf-8")

    mock_client = MagicMock()
    mock_client.fetch_all_records.return_value = [
        {
            "job_id": "SP_DIRECT_01",
            "title": "Giày Tây Nam",
            "post_before": "",
            "content_type": "",
        }
    ]
    mock_client.update_master_rows.return_value = 1

    res = apply_market_intel(sheet_client=mock_client, file_path=str(file_path))
    assert res["status"] == "success"
    assert res["updated_count"] == 1
    assert mock_client.update_master_rows.called
