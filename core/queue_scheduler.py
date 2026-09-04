"""Queue Priority Scheduler based on 'post_before' event deadline and golden window (3-15 days)."""

import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


def parse_post_before_date(date_str: Any) -> Optional[date]:
    """Parse various date formats for post_before field (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD)."""
    if not date_str:
        return None
    
    clean_str = str(date_str).strip()
    if not clean_str:
        return None

    # Handle full timestamp if present (e.g. DD/MM/YYYY HH:MM)
    if " " in clean_str:
        clean_str = clean_str.split(" ")[0]

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d/%m/%y",
        "%d.%m.%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(clean_str, fmt).date()
        except ValueError:
            pass

    return None


def calculate_days_remaining(post_before_str: Any, today: Optional[date] = None) -> Optional[int]:
    """Calculate remaining days until post_before deadline (delta = deadline - today)."""
    deadline = parse_post_before_date(post_before_str)
    if not deadline:
        return None
    
    curr_date = today or date.today()
    return (deadline - curr_date).days


def get_event_tier(post_before_str: Any, today: Optional[date] = None) -> Tuple[int, Optional[int], str]:
    """Classify a job into 5 priority tiers based on days remaining (delta):

    Tier 1: Urgent (0 <= delta < 3 days) -> Absolute top priority
    Tier 2: Golden Event Window (3 <= delta <= 15 days) -> High priority for pre-event wave
    Tier 3: Regular post (No post_before) -> Standard FIFO order
    Tier 4: Future event (delta > 15 days) -> Hold for later, too early for viral wave
    Tier 5: Expired (delta < 0) -> Past deadline, flagged with warning
    """
    days_left = calculate_days_remaining(post_before_str, today=today)

    if days_left is None:
        # Tier 3: Regular post without post_before
        return (3, None, "Bài thông thường")

    if days_left < 0:
        # Tier 5: Expired
        return (5, days_left, f"Đã quá hạn {abs(days_left)} ngày")
    elif days_left < 3:
        # Tier 1: Urgent rush
        return (1, days_left, f"Khẩn cấp (Còn {days_left} ngày)")
    elif days_left <= 15:
        # Tier 2: Golden window
        return (2, days_left, f"Khung giờ vàng sự kiện (Còn {days_left} ngày)")
    else:
        # Tier 4: Future event (> 15 days)
        return (4, days_left, f"Chưa đến thời điểm (Còn {days_left} ngày)")


CYCLE_ORDER = [
    "real_product",
    "tips_tricks",
    "real_accessory",
    "ai_product",
    "ai_accessory",
]


def interleave_by_content_type(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Interleave jobs round-robin across different content types to prevent content fatigue:
    real_product -> tips_tricks -> real_accessory -> ai_product -> ai_accessory -> ...
    """
    if not jobs or len(jobs) <= 1:
        return list(jobs)

    from collections import defaultdict
    buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for j in jobs:
        ct = j.get("content_type") or "real_product"
        buckets[ct].append(j)

    # Order cycle types with preferred priority, followed by any custom types
    active_cycle = [ct for ct in CYCLE_ORDER if ct in buckets]
    for ct in buckets:
        if ct not in active_cycle:
            active_cycle.append(ct)

    result = []
    total_jobs = len(jobs)
    while len(result) < total_jobs:
        added_in_round = False
        for ct in active_cycle:
            if buckets[ct]:
                result.append(buckets[ct].pop(0))
                added_in_round = True
        if not added_in_round:
            break

    return result


def sort_jobs_by_priority(jobs: List[Dict[str, Any]], today: Optional[date] = None) -> List[Dict[str, Any]]:
    """Sort a list of job records according to event deadline priority and content type interleaving:

    1. Urgent posts (0 <= delta < 3 days): sorted by delta ascending
    2. Golden window posts (3 <= delta <= 15 days): interleaved by content_type
    3. Regular posts (no deadline): interleaved by content_type to avoid repetitive formats
    4. Future posts (delta > 15 days): interleaved by content_type
    5. Expired posts (delta < 0): preserve order at the end with warning
    """
    curr_date = today or date.today()

    tier1: List[Tuple[int, int, Dict[str, Any]]] = []
    tier2: List[Tuple[int, int, Dict[str, Any]]] = []
    tier3: List[Tuple[int, Dict[str, Any]]] = []
    tier4: List[Tuple[int, int, Dict[str, Any]]] = []
    tier5: List[Tuple[int, int, Dict[str, Any]]] = []

    for idx, job in enumerate(jobs):
        post_before = job.get("post_before", "")
        tier, days_left, label = get_event_tier(post_before, today=curr_date)

        if tier == 1:
            tier1.append((days_left, idx, job))
        elif tier == 2:
            tier2.append((days_left, idx, job))
        elif tier == 3:
            tier3.append((idx, job))
        elif tier == 4:
            tier4.append((days_left, idx, job))
        elif tier == 5:
            tier5.append((days_left, idx, job))

    # Sort within tiers
    tier1.sort(key=lambda x: (x[0], x[1]))  # smallest days_left first, then original idx
    tier2.sort(key=lambda x: (x[0], x[1]))  # smallest days_left first
    tier3.sort(key=lambda x: x[0])          # original FIFO order
    tier4.sort(key=lambda x: (x[0], x[1]))  # closest future date first
    tier5.sort(key=lambda x: (x[0], x[1]))  # most recently expired first

    tier1_jobs = [item[2] for item in tier1]
    tier2_jobs = interleave_by_content_type([item[2] for item in tier2])
    tier3_jobs = interleave_by_content_type([item[1] for item in tier3])
    tier4_jobs = interleave_by_content_type([item[2] for item in tier4])
    tier5_jobs = [item[2] for item in tier5]

    return tier1_jobs + tier2_jobs + tier3_jobs + tier4_jobs + tier5_jobs


def format_content_type_badge(content_type: Any) -> str:
    """Format human-readable colored badge for content_type in Rich Console."""
    ct = str(content_type).strip() if content_type else "real_product"
    badges = {
        "real_product": "[bold green]🎥 [Sản phẩm thật][/bold green]",
        "ai_product": "[bold magenta]🤖 [Sản phẩm AI][/bold magenta]",
        "real_accessory": "[bold cyan]👜 [Phụ kiện thật][/bold cyan]",
        "ai_accessory": "[bold blue]✨ [Phụ kiện AI][/bold blue]",
        "tips_tricks": "[bold yellow]💡 [Mẹo vặt & Hướng dẫn][/bold yellow]",
    }
    return badges.get(ct, f"[dim]🏷️ [{ct}][/dim]")


def format_deadline_badge(post_before_str: Any, today: Optional[date] = None) -> str:
    """Format human-readable colored badge for Rich Console display."""
    if not post_before_str:
        return ""

    tier, days_left, label = get_event_tier(post_before_str, today=today)
    date_val = parse_post_before_date(post_before_str)
    date_display = date_val.strftime("%d/%m/%Y") if date_val else str(post_before_str)

    if tier == 1:
        day_str = "HÔM NAY" if days_left == 0 else f"{days_left} ngày"
        return f"[bold red blink]🚨 NƯỚC RÚT KHẨN CẤP: Hạn chót {date_display} (Còn {day_str})![/bold red blink]"
    elif tier == 2:
        return f"[bold yellow]🔥 KHUNG GIỜ VÀNG SỰ KIỆN: Hạn chót {date_display} (Còn {days_left} ngày)[/bold yellow]"
    elif tier == 4:
        return f"[dim]⏳ Sự kiện tương lai: Hạn chót {date_display} (Còn {days_left} ngày - chưa đến khung 15 ngày)[/dim]"
    elif tier == 5:
        return f"[bold red]⚠️ CẢNH BÁO: ĐÃ QUÁ HẠN {abs(days_left)} NGÀY (Hạn chót là {date_display})![/bold red]"

    return f"[cyan]📅 Hạn chót: {date_display}[/cyan]"
