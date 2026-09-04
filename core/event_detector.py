"""Event and holiday detection module to infer post_before deadlines from product titles and descriptions."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

CALENDAR_PATH = Path("config/events_calendar.json")


def load_events_calendar() -> Dict[str, Any]:
    """Load pre-configured solar and lunar events calendar."""
    if not CALENDAR_PATH.exists():
        logger.warning(f"Events calendar config not found at {CALENDAR_PATH}")
        return {}
    try:
        with open(CALENDAR_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading events calendar: {e}")
        return {}


def detect_event_deadline(
    title: str,
    description: str = "",
    year: Optional[int] = None,
) -> Optional[Tuple[str, str]]:
    """Infer occasion/holiday and return (event_name, deadline_date_str [DD/MM/YYYY]).

    Infers events without requiring explicit dates:
    - 'lồng đèn', 'bánh trung thu' -> Tết Trung Thu
    - 'hoa đào', 'bánh chưng', 'lì xì' -> Tết Nguyên Đán
    - 'cây thông', 'ông già noel' -> Giáng Sinh
    - 'tựu trường', 'cặp sách' -> Khai Giảng (05/09)
    - '20/10', 'quà tặng mẹ' -> Phụ Nữ VN (20/10)
    """
    cal = load_events_calendar()
    if not cal:
        return None

    target_year = str(year or datetime.now().year)
    full_text = f"{title} {description}".lower().strip()
    if not full_text:
        return None

    # 1. Check Lunar Events (with pre-calculated Solar dates for 2025-2030)
    lunar_events = cal.get("lunar_events", {})
    for event_key, data in lunar_events.items():
        keywords = data.get("keywords", [])
        if any(kw in full_text for kw in keywords):
            dates = data.get("dates", {})
            event_date = dates.get(target_year)
            if event_date:
                return data.get("name", event_key), event_date

    # 2. Check Fixed Solar Events
    solar_events = cal.get("solar_events", [])
    for event in solar_events:
        keywords = event.get("keywords", [])
        if any(kw in full_text for kw in keywords):
            day_month = event.get("day_month", "")
            if day_month:
                full_date_str = f"{day_month}/{target_year}"
                return event.get("name", "Sự kiện"), full_date_str

    return None
