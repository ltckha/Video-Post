"""Market Intelligence Module.
Ingests weekly/daily market intelligence data (weather alerts, e-commerce campaigns, cultural events, recommended products),
matches them against products in Tab Master, and automatically updates 'post_before' and 'content_type'.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.sheet_client import GoogleSheetDirectClient, VALID_CONTENT_TYPES

logger = logging.getLogger(__name__)

DEFAULT_INTEL_PATH = "config/market_intelligence.json"


def load_market_intel(file_path: Optional[str] = None) -> Dict[str, Any]:
    """Load and validate market intelligence JSON file."""
    path = Path(file_path or DEFAULT_INTEL_PATH)
    if not path.exists():
        raise FileNotFoundError(f"Market intelligence file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Market intelligence file must contain a valid JSON object.")

    return data


def parse_date_safely(date_str: str) -> Optional[datetime]:
    """Safely parse DD/MM/YYYY string into datetime object."""
    if not date_str:
        return None
    s = str(date_str).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def match_intel_with_master(
    master_records: List[Dict[str, Any]],
    intel_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Match market intelligence data against master sheet records.

    Priority of matching:
    1. Direct item_id match in recommended_products (highest priority).
    2. Weather alerts boost_keywords matching title/caption.
    3. Upcoming events boost_keywords matching title/caption.

    Returns a list of records with updated fields: [{'job_id': ..., 'post_before': ..., ...}]
    """
    recommended_prods = intel_data.get("recommended_products", [])
    weather_alerts = intel_data.get("weather_alerts", [])
    upcoming_events = intel_data.get("upcoming_events", [])

    # Index recommended products by item_id (string normalized)
    rec_by_id: Dict[str, Dict[str, Any]] = {}
    for p in recommended_prods:
        item_id = str(p.get("item_id", "")).strip()
        if item_id:
            rec_by_id[item_id] = p

    updates_to_apply: List[Dict[str, Any]] = []

    for row in master_records:
        job_id = str(row.get("job_id", "")).strip()
        if not job_id:
            continue

        title = str(row.get("title", "")).lower()
        caption_fb = str(row.get("caption_fb", "")).lower()
        caption_tt = str(row.get("caption_tt", "")).lower()
        combined_text = f"{title} {caption_fb} {caption_tt}".strip()

        current_post_before = str(row.get("post_before", "")).strip()
        current_pb_dt = parse_date_safely(current_post_before)
        current_content_type = str(row.get("content_type", "")).strip()

        new_post_before = None
        new_content_type = None
        match_reason = None

        # 1. Direct item_id match (highest precision)
        if job_id in rec_by_id:
            rec = rec_by_id[job_id]
            target_pb = str(rec.get("post_before", "")).strip()
            if target_pb:
                new_post_before = target_pb
                match_reason = f"Khớp trực tiếp item_id (Lý do: {rec.get('reason', 'Đề xuất trong báo cáo')})"
            target_ct = str(rec.get("content_type", "")).strip()
            if target_ct and target_ct in VALID_CONTENT_TYPES:
                new_content_type = target_ct

        # 2. Weather alerts keyword match
        if not new_post_before and weather_alerts:
            for alert in weather_alerts:
                keywords = alert.get("boost_keywords", [])
                rec_pb = str(alert.get("recommended_post_before", "")).strip()
                if not rec_pb:
                    continue
                matched_kw = [kw for kw in keywords if kw.lower() in combined_text]
                if matched_kw:
                    new_post_before = rec_pb
                    match_reason = f"Khớp thời tiết: '{alert.get('condition', '')}' (Từ khóa: {', '.join(matched_kw)})"
                    break

        # 3. Upcoming events keyword match
        if not new_post_before and upcoming_events:
            for ev in upcoming_events:
                keywords = ev.get("boost_keywords", [])
                rec_pb = str(ev.get("recommended_post_before", "")).strip()
                if not rec_pb:
                    continue
                matched_kw = [kw for kw in keywords if kw.lower() in combined_text]
                if matched_kw:
                    new_post_before = rec_pb
                    match_reason = f"Khớp sự kiện: '{ev.get('event_name', '')}' (Từ khóa: {', '.join(matched_kw)})"
                    break

        # Decide if we need to update this row
        fields_to_update: Dict[str, Any] = {}

        if new_post_before:
            new_pb_dt = parse_date_safely(new_post_before)
            # Only update if current is empty or new date is more urgent (earlier)
            if not current_pb_dt or (new_pb_dt and new_pb_dt < current_pb_dt):
                fields_to_update["post_before"] = new_post_before

        if new_content_type and new_content_type != current_content_type:
            fields_to_update["content_type"] = new_content_type

        if fields_to_update:
            fields_to_update["job_id"] = job_id
            fields_to_update["_match_reason"] = match_reason or "Market Intel Update"
            fields_to_update["_title"] = row.get("title", "")
            updates_to_apply.append(fields_to_update)

    return updates_to_apply


def apply_market_intel(
    sheet_client: Optional[GoogleSheetDirectClient] = None,
    file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute end-to-end Market Intelligence update on Tab Master."""
    intel_data = load_market_intel(file_path)
    client = sheet_client or GoogleSheetDirectClient()

    logger.info("Fetching existing records from Tab Master...")
    master_records = client.fetch_all_records("Master")
    logger.info(f"Loaded {len(master_records)} records from Tab Master.")

    updates = match_intel_with_master(master_records, intel_data)

    if not updates:
        logger.info("No matching records found to update from Market Intelligence.")
        return {
            "status": "success",
            "report_date": intel_data.get("report_date", ""),
            "updated_count": 0,
            "details": [],
        }

    # Prepare pure fields for sheet update (strip internal metadata prefixed with '_')
    sheet_updates = []
    for u in updates:
        clean_row = {k: v for k, v in u.items() if not k.startswith("_")}
        sheet_updates.append(clean_row)

    updated_rows = client.update_master_rows(sheet_updates)
    logger.info(f"Successfully applied Market Intelligence updates to {updated_rows} rows on Tab Master.")

    return {
        "status": "success",
        "report_date": intel_data.get("report_date", ""),
        "updated_count": len(updates),
        "details": updates,
    }
