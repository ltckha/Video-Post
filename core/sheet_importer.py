"""Smart Google Sheet Importer Module for Multi-Project Dynamic Columns.

Flexibly parses CSV exports from different Google Sheets (e.g. Shopee Nesty Affiliate Sheet,
Auto Video Factory Output Sheet) and automatically detects headers, video paths, IDs,
and per-platform brand assignments.
"""

import io
import csv
import json
import logging
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import settings
from core.queue import JobQueue
from core.ai_captioner import AICaptionGenerator

logger = logging.getLogger(__name__)

# Predefined dynamic mapping rules for different Google Sheet structures
DEFAULT_MAPPING_RULES = [
    {
        "name": "shopee_nesty_affiliate",
        "detect_headers": ["Mã sản phẩm", "Tên sản phẩm", "Link ưu đãi"],
        "field_map": {
            "id": ["Mã sản phẩm", "SKU"],
            "title": ["Tên sản phẩm", "Tên SP"],
            "caption": ["Mô tả bài đăng", "Chi tiết sản phẩm"],
            "affiliate_link": ["Link ưu đãi", "Link sản phẩm"],
            "video_path": ["Output File", "File ảnh lưu local"],
        },
    },
    {
        "name": "auto_video_factory",
        "detect_headers": ["Project ID", "Video Title", "Caption & Hashtags"],
        "field_map": {
            "id": ["job_id", "Project ID", "Video ID"],
            "title": ["title", "Video Title", "Title"],
            "caption": ["raw_caption", "Caption & Hashtags", "Hashtags"],
            "affiliate_link": ["shopee_link", "Affiliate Link", "Link ưu đãi"],
            "video_path": ["video_path", "Output File", "Video File Path"],
        },
    },
    {
        "name": "master_19_columns",
        "detect_headers": ["job_id", "video_path", "caption_fb"],
        "field_map": {
            "id": ["job_id"],
            "title": ["title"],
            "caption": ["raw_caption", "caption_fb"],
            "affiliate_link": ["shopee_link"],
            "video_path": ["video_path"],
        },
    },
]


class SmartGoogleSheetImporter:
    """Smart importer supporting dynamic header mapping across multiple Google Sheets."""

    def __init__(self, sheet_url: str = "", db_path: str = "video_post.db", custom_mappings: Optional[List[Dict[str, Any]]] = None):
        self.sheet_url = sheet_url
        self.db_path = db_path
        self.mappings = custom_mappings or DEFAULT_MAPPING_RULES
        self.ai_generator = AICaptionGenerator()

    def fetch_sheet_csv(self, tab_name: str = "") -> str:
        """Fetch raw CSV content from a public or shared Google Sheet URL (supports specific tab name)."""
        if not self.sheet_url:
            from config import settings
            self.sheet_url = getattr(settings, "MASTER_SHEET_URL", "")

        if not self.sheet_url:
            raise ValueError("Google Sheet URL is empty.")

        export_url = self.sheet_url
        if "/edit" in export_url:
            base_url = export_url.split("/edit")[0]
        else:
            base_url = export_url.rstrip("/")

        if tab_name:
            import urllib.parse
            encoded_tab = urllib.parse.quote(tab_name)
            export_url = f"{base_url}/gviz/tq?tqx=out:csv&sheet={encoded_tab}"
        else:
            if not base_url.endswith("/export?format=csv"):
                export_url = f"{base_url}/export?format=csv"
            else:
                export_url = base_url

        logger.info(f"Fetching Google Sheet CSV from: {export_url} (Tab: '{tab_name or 'Default'}')")
        res = requests.get(export_url, timeout=15)
        res.raise_for_status()
        res.encoding = "utf-8"
        return res.text

    def parse_jobs(self, target_platforms: Optional[List[str]] = None, tab_name: str = "", generate_ai: bool = True) -> List[Dict[str, Any]]:
        """Fetch and dynamically parse jobs based on matching header mapping rules."""
        csv_data = self.fetch_sheet_csv(tab_name=tab_name)
        f = io.StringIO(csv_data)
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        active_mapping = self._detect_best_mapping(headers)
        logger.info(f"Using mapping rule: '{active_mapping['name']}' for sheet headers: {headers}")

        field_map = active_mapping.get("field_map", {})

        parsed_jobs = []
        for row in reader:
            primary_key_col = headers[0] if headers else "Mã sản phẩm"
            item_id = str(row.get(primary_key_col, "")).strip() or self._extract_field(row, field_map.get("id", []))

            title = self._extract_field(row, field_map.get("title", []))
            caption = self._extract_field(row, field_map.get("caption", []))
            affiliate_link = self._extract_field(row, field_map.get("affiliate_link", []))
            video_path = self._extract_field(row, field_map.get("video_path", []))

            if not video_path:
                continue

            target_set = {"facebook", "youtube", "instagram"}
            platform_brand_map = {}
            
            for col_name, val in row.items():
                if not col_name:
                    continue
                col_clean = str(col_name).strip().lower()
                val_clean = str(val).strip()

                for p in ["facebook", "youtube", "instagram"]:
                    if p in col_clean:
                        if val_clean.lower() == "không":
                            target_set.discard(p)
                        elif val_clean:
                            platform_brand_map[p] = val_clean

            target_list = list(target_set)

            # Read existing captions from sheet if available, or generate AI captions only if generate_ai=True
            ai_captions = {}
            if generate_ai:
                ai_captions = self.ai_generator.generate_all_captions(
                    title=title,
                    raw_caption=caption,
                    affiliate_link=affiliate_link,
                )
            else:
                for p in ["facebook", "youtube", "instagram", "tiktok", "shopee", "zalo"]:
                    col_p = f"caption_{p}"
                    if col_p in row and row[col_p]:
                        ai_captions[p] = str(row[col_p]).strip()
                    else:
                        ai_captions[p] = caption or title

            job_dict = {
                "item_id": item_id,
                "product_id": item_id,
                "title": title,
                "description": caption,
                "affiliate_link": affiliate_link,
                "video_path": video_path,
                "target_platforms": target_list,
                "brand_map": platform_brand_map,
                "platform_captions": ai_captions,
            }

            parsed_jobs.append(job_dict)

        logger.info(f"Successfully parsed {len(parsed_jobs)} jobs from Google Sheet.")
        return parsed_jobs

    def import_to_queue(self, target_platforms: Optional[List[str]] = None, tab_name: str = "", generate_ai: bool = True) -> int:
        """Parse sheet and enqueue valid jobs with brand routing into SQLite JobQueue."""
        jobs = self.parse_jobs(target_platforms=target_platforms, tab_name=tab_name, generate_ai=generate_ai)
        queue = JobQueue(db_path=self.db_path)
        imported_count = 0

        for job in jobs:
            brand_map = job.get("brand_map", {})
            captions = job.get("platform_captions", {})
            affiliate_link = job.get("affiliate_link", "")

            job_id = queue.add_job(
                video_path=job["video_path"],
                target_platforms=job["target_platforms"],
                title=job["title"],
                description=job["description"],
                extra_options={
                    "item_id": job["item_id"],
                    "brand_map": brand_map,
                    "platform_captions": captions,
                    "affiliate_link": affiliate_link,
                },
            )

            imported_count += 1
            logger.info(f"Enqueued Job #{job_id} for '{job['title']}' -> Brands: {brand_map}")

        return imported_count

    def _detect_best_mapping(self, headers: List[str]) -> Dict[str, Any]:
        """Detect which mapping rule best matches the CSV headers."""
        headers_set = set(headers)
        for rule in self.mappings:
            detect_headers = rule.get("detect_headers", [])
            if any(dh in headers_set for dh in detect_headers):
                return rule

        return {
            "name": "fallback_generic",
            "field_map": {
                "id": ["job_id", "Project ID", "Mã sản phẩm", "ID", "SKU"],
                "title": ["title", "Video Title", "Tên sản phẩm", "Title", "Tiêu đề"],
                "caption": ["raw_caption", "Caption & Hashtags", "Mô tả bài đăng", "Caption"],
                "affiliate_link": ["shopee_link", "Link ưu đãi", "Link sản phẩm", "Affiliate Link"],
                "video_path": ["video_path", "Output File", "File ảnh lưu local", "Video Path"],
            },
        }

    def parse_jobs_from_sheet(self, target_platforms: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Backward-compatible alias for parse_jobs."""
        return self.parse_jobs(target_platforms=target_platforms)

    def _extract_field(self, row: Dict[str, Any], possible_keys: List[str]) -> str:
        """Extract first matching value from possible CSV column header names."""
        for key in possible_keys:
            if key in row and row[key]:
                return str(row[key]).strip()
            for k, v in row.items():
                if k and v and str(k).strip().lower() == str(key).strip().lower():
                    return str(v).strip()
        return ""


def trigger_apps_script_sync() -> bool:
    """Trigger Google Apps Script Webhook action 'sync_input_tabs' to aggregate Input Tabs into Master_Post."""
    webhook_url = getattr(settings, "GOOGLE_SHEET_WEBHOOK_URL", None)
    if not webhook_url:
        print("⚠️ Chưa cấu hình GOOGLE_SHEET_WEBHOOK_URL trong .env")
        return False

    try:
        print("📡 Đang gửi tín hiệu sang Google Apps Script để gom Tab & xóa dòng thừa...")
        resp = requests.post(webhook_url, json={"action": "sync_input_tabs"}, timeout=30)
        if resp.status_code == 200 and "success" in resp.text:
            print(f"✅ Apps Script phản hồi thành công: {resp.text[:150]}")
            return True
        
        # Fallback to GET if POST returned HTML error
        sync_url = webhook_url if "?action=" in webhook_url else f"{webhook_url}?action=sync_input_tabs"
        resp_get = requests.get(sync_url, timeout=30)
        if resp_get.status_code == 200 and "success" in resp_get.text:
            print(f"✅ Apps Script phản hồi thành công (qua GET): {resp_get.text[:150]}")
            return True
        else:
            print(f"⚠️ Webhook Apps Script phản hồi: {resp.text[:150]}")
    except Exception as e:
        print(f"⚠️ Không thể kích hoạt Webhook Apps Script: {e}")
    return False


def sync_all_sources(db_path: str = "video_post.db") -> int:
    """Sync all connected input tabs into Master_Post via Apps Script and update local queue cache."""
    # 1. Trigger Apps Script to aggregate Input Tabs into Master_Post and delete removed rows
    trigger_apps_script_sync()

    # 2. Fetch Master_Post tab and sync to local queue cache
    master_url = getattr(settings, "MASTER_SHEET_URL", "")
    if not master_url:
        print("⚠️ Chưa cấu hình MASTER_SHEET_URL")
        return 0

    print("📥 Đang đọc dữ liệu mới nhất từ Tab Master...")
    importer = SmartGoogleSheetImporter(sheet_url=master_url, db_path=db_path)
    count = importer.import_to_queue(tab_name="Master", generate_ai=False)
    print(f"✅ Đồng bộ hoàn tất! Tổng số bài đang có trên Master: {count}")
    return count


def format_caption_for_platform(platform: str, title: str, caption: str = "", affiliate_link: str = "") -> str:
    """Backward-compatible helper to format caption for a specific platform."""
    gen = AICaptionGenerator()
    res = gen.generate_all_captions(title=title, raw_caption=caption, affiliate_link=affiliate_link)
    return res.get(platform, title)



GoogleSheetImporter = SmartGoogleSheetImporter

