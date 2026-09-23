"""Master Output Sheet Exporter Module.

Exports all 19 concise English columns (Basic Info, AI Captions for 6 Platforms, 
Account Routing, and Per-Platform Posting Status) to local Master Output CSV.
"""

import csv
import json
import logging
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

from config import settings

logger = logging.getLogger(__name__)


MASTER_SHEET_CSV = Path("./master_output_sheet.csv")

MASTER_HEADERS = [
    "job_id",
    "title",
    "video_path",
    "drive_url",
    "post_before",
    "content_type",
    "shopee_link",
    "caption_fb",
    "caption_yt",
    "caption_ig",
    "caption_tt",
    "caption_shopee",
    "caption_zalo",
    "brand_fb",
    "brand_yt",
    "brand_ig",
    "brand_tt",
    "status_fb",
    "status_yt",
    "status_ig",
    "status_tt",
    "status_shopee",
    "status_zalo",
]


class MasterSheetExporter:
    """Exports SQLite Queue jobs and AI Captions to 19 Concise English Columns Master Sheet."""

    def __init__(self, db_path: str = "video_post.db", output_csv: Path = MASTER_SHEET_CSV):
        self.db_path = db_path
        self.output_csv = output_csv

    def _sync_two_way_statuses(self, ignore_job_ids=None, csv_text=None):
        """Đồng bộ ngược trạng thái từ Tab Master về SQLite (hoặc từ chuỗi csv_text được truyền vào)."""
        master_url = getattr(settings, "MASTER_SHEET_URL", "")
        if not master_url and not csv_text:
            return

        try:
            import requests
            import io
            if csv_text is not None:
                f = io.StringIO(csv_text)
            else:
                export_url = master_url
                if "/edit" in export_url:
                    base = export_url.split("/edit")[0]
                    export_url = f"{base}/gviz/tq?tqx=out:csv&sheet=Master"
                elif not export_url.endswith("/export?format=csv"):
                    export_url = export_url.rstrip("/") + "/gviz/tq?tqx=out:csv&sheet=Master"

                res = requests.get(export_url, timeout=15)
                if res.status_code != 200:
                    return

                res.encoding = "utf-8"
                f = io.StringIO(res.text)

            reader = csv.DictReader(f)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                valid_statuses = ["published", "failed", "not_configured", "manual_pending", "pending", "needs_edit"]
                
                for row in reader:
                    job_id = row.get("job_id")
                    if not job_id:
                        continue
                        
                    # Mở job ra từ DB để cập nhật
                    clean_id = job_id.replace("JOB_", "") if isinstance(job_id, str) and "JOB_" in job_id else job_id
                    cursor.execute(
                        "SELECT id, status, target_platforms, results_json FROM jobs WHERE title = ? OR id = ? OR json_extract(results_json, '$.item_id') = ?",
                        (job_id, clean_id, job_id)
                    )
                    db_job = cursor.fetchone()
                    if not db_job:
                        continue
                        
                    if ignore_job_ids and db_job["id"] in ignore_job_ids:
                        continue
                        
                    results_str = db_job["results_json"] or "{}"
                    try:
                        results_data = json.loads(results_str)
                    except:
                        results_data = {}
                        
                    changed = False
                    
                    # Quét các cột Đăng tay và đồng bộ ngược
                    for col, key in [("status_tt", "tiktok_status"), ("status_shopee", "shopee_status"), ("status_zalo", "zalo_status")]:
                        val = str(row.get(col, "")).strip().lower()
                        if val in valid_statuses:
                            if results_data.get(key) != val:
                                results_data[key] = val
                                changed = True
                                
                    # Quét các cột Đăng tự động & thủ công và đồng bộ ngược (hỗ trợ link video URL thật)
                    for col, plat_key in [("status_fb", "facebook"), ("status_yt", "youtube"), ("status_ig", "instagram"), ("status_tt", "tiktok")]:
                        raw_cell_val = str(row.get(col, "")).strip()
                        val = raw_cell_val.lower()

                        # Xử lý khi cell chứa link video URL (http/https) hoặc điểm số thẩm định (VD: 8.5/10)
                        if raw_cell_val.startswith("http") or "/10" in raw_cell_val:
                            plat_data = results_data.get(plat_key, {})
                            if not isinstance(plat_data, dict):
                                plat_data = {}
                            if plat_data.get("status") != "published":
                                plat_data["status"] = "published"
                                changed = True
                            if raw_cell_val.startswith("http") and plat_data.get("video_url") != raw_cell_val:
                                plat_data["video_url"] = raw_cell_val
                                changed = True
                            results_data[plat_key] = plat_data
                            if plat_key == "tiktok":
                                results_data["tiktok_status"] = raw_cell_val
                        elif val in valid_statuses:
                            plat_data = results_data.get(plat_key, {})
                            if isinstance(plat_data, dict):
                                if plat_data.get("status") != val:
                                    plat_data["status"] = val
                                    results_data[plat_key] = plat_data
                                    changed = True
                            else:
                                results_data[plat_key] = {"status": val}
                                changed = True
                            if plat_key == "tiktok":
                                results_data["tiktok_status"] = val
                                
                    # Quét nội dung bài đăng (Captions)
                    platform_captions = results_data.get("platform_captions", {})
                    for col, plat_key in [("caption_fb", "facebook"), ("caption_yt", "youtube"), 
                                          ("caption_ig", "instagram"), ("caption_tt", "tiktok"), 
                                          ("caption_shopee", "shopee"), ("caption_zalo", "zalo")]:
                        cap_val = row.get(col, "").strip()
                        if cap_val and platform_captions.get(plat_key) != cap_val:
                            platform_captions[plat_key] = cap_val
                            changed = True
                            
                    # Quét các cột Brand (Thương hiệu / Fanpage đích)
                    brand_map = results_data.get("brand_map", {})
                    for col, plat_key in [("brand_fb", "facebook"), ("brand_yt", "youtube"), ("brand_ig", "instagram")]:
                        if col in row:
                            brand_val = row.get(col, "").strip()
                            current_val = brand_map.get(plat_key, "")
                            if current_val != brand_val:
                                brand_map[plat_key] = brand_val
                                changed = True
                            
                    if changed:
                        results_data["platform_captions"] = platform_captions
                        results_data["brand_map"] = brand_map
                        new_results_str = json.dumps(results_data)
                        cursor.execute("UPDATE jobs SET results_json = ? WHERE id = ?", (new_results_str, db_job["id"]))
                        
                    # Đồng bộ lại danh sách target_platforms dựa trên trạng thái thực tế từ Sheet
                    active_targets = []
                    for col, plat in [("status_fb", "facebook"), ("status_yt", "youtube"), ("status_ig", "instagram")]:
                        st_val = str(row.get(col, "")).strip().lower()
                        if st_val and st_val != "not_configured":
                            active_targets.append(plat)
                    if active_targets:
                        new_target_str = ",".join(active_targets)
                        cursor.execute("UPDATE jobs SET target_platforms = ? WHERE id = ?", (new_target_str, db_job["id"]))
                        
                    # Cập nhật status chung của job dựa trên Sheet (nếu có yêu cầu needs_edit)
                    cursor.execute("SELECT status FROM jobs WHERE id = ?", (db_job["id"],))
                    current_db_status = cursor.fetchone()["status"]
                    
                    has_needs_edit = False
                    has_pending = False
                    
                    for c in ["status_fb", "status_yt", "status_ig", "status_tt", "status_shopee", "status_zalo"]:
                        val = str(row.get(c, "")).strip().lower()
                        if val == "needs_edit":
                            has_needs_edit = True
                        elif val == "pending":
                            has_pending = True
                            
                    if has_needs_edit and current_db_status != "needs_edit":
                        cursor.execute("UPDATE jobs SET status = 'needs_edit' WHERE id = ?", (db_job["id"],))
                    elif current_db_status == "needs_edit" and not has_needs_edit and has_pending:
                        # Gỡ needs_edit nếu user đổi lại thành pending
                        cursor.execute("UPDATE jobs SET status = 'pending' WHERE id = ?", (db_job["id"],))
                    else:
                        # Tự động dọn dẹp: Nếu tất cả các kênh target đã đăng thành công, chuyển job thành completed
                        targets = [t.strip() for t in db_job["target_platforms"].split(",") if t.strip()]
                        if targets and all(isinstance(results_data.get(t), dict) and results_data[t].get("status") == "published" for t in targets):
                            cursor.execute("UPDATE jobs SET status = 'completed' WHERE id = ?", (db_job["id"],))
                        
                conn.commit()
                logger.info("✅ Two-Way Sync: Đã đồng bộ trạng thái và nội dung (Captions) từ Master Sheet về local DB.")
        except Exception as e:
            logger.warning(f"Không thể đồng bộ 2 chiều từ Master Sheet: {e}")

    def export_master_sheet(self, skip_sync: bool = False, ignore_job_ids: List[int] = None, only_job_ids: List[int] = None) -> Path:
        """Fetch all jobs from SQLite DB and export 19 English columns to master_output_sheet.csv."""
        # 1. Sync Two-Way manual statuses first unless skipped
        if not skip_sync:
            self._sync_two_way_statuses(ignore_job_ids=ignore_job_ids)
        
        # 2. Fetch all jobs
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs ORDER BY id ASC")
            rows = cursor.fetchall()

        records = []
        for r in rows:
            results_str = r["results_json"] or "{}"
            results_data = {}
            try:
                results_data = json.loads(results_str)
            except Exception:
                pass

            # Primary Key (Column A): item_id (Product ID / Project ID)
            job_id = results_data.get("item_id") or r["title"] or f"JOB_{r['id']}"
            title = r["title"] or ""
            video_path = r["video_path"] or ""

            platform_captions = results_data.get("platform_captions", {})
            brand_map = results_data.get("brand_map", {})
            affiliate_link = results_data.get("affiliate_link", "")

            # Per-Platform Status Determination (Chuẩn 4 trạng thái)
            status = r["status"]
            
            # Hàm phụ trợ để lấy trạng thái hiển thị nền tảng (ưu tiên URL bài đăng thật)
            def get_platform_display_status(plat_key):
                plat_data = results_data.get(plat_key, {})
                if isinstance(plat_data, dict):
                    if plat_data.get("video_url") and plat_data.get("status") in ["published", "success", "completed"]:
                        return plat_data["video_url"]
                    if "status" in plat_data:
                        return plat_data["status"]
                
                # Fallback logic nếu chưa từng chạy
                if plat_key in r["target_platforms"]:
                    if status == "completed": return "published"
                    if status == "needs_edit": return "needs_edit"
                    return "pending"
                return "not_configured"

            fb_status = get_platform_display_status("facebook")
            yt_status = get_platform_display_status("youtube")
            ig_status = get_platform_display_status("instagram")
            
            # Hàm phụ trợ trạng thái nền tảng thủ công (được đồng bộ 2 chiều)
            def get_manual_status(plat_key, db_key):
                val = results_data.get(db_key)
                if str(val).startswith("http"):
                    return val
                if status == "needs_edit" or val == "needs_edit":
                    return "needs_edit"
                if val in ["published", "manual_done"]:
                    return val
                return "manual_pending"

            tt_data = results_data.get("tiktok", {})
            if isinstance(tt_data, dict) and tt_data.get("video_url") and tt_data.get("status") in ["published", "success", "completed"]:
                tt_status = tt_data["video_url"]
            elif results_data.get("tiktok_status", "").startswith("http"):
                tt_status = results_data["tiktok_status"]
            else:
                tt_status = get_manual_status("tiktok", "tiktok_status")

            sp_status = get_manual_status("shopee", "shopee_status")
            zl_status = get_manual_status("zalo", "zalo_status")

            record = {
                "job_id": job_id,
                "title": title,
                "video_path": video_path,
                "drive_url": results_data.get("drive_url", ""),
                "shopee_link": affiliate_link,
                "caption_fb": platform_captions.get("facebook", title),
                "caption_yt": platform_captions.get("youtube", title),
                "caption_ig": platform_captions.get("instagram", title),
                "caption_tt": platform_captions.get("tiktok", title),
                "caption_shopee": platform_captions.get("shopee", title),
                "caption_zalo": platform_captions.get("zalo", title),
                "brand_fb": brand_map.get("facebook", ""),
                "brand_yt": brand_map.get("youtube", ""),
                "brand_ig": brand_map.get("instagram", ""),
                "brand_tt": brand_map.get("tiktok", brand_map.get("facebook", "")),
                "status_fb": fb_status,
                "status_yt": yt_status,
                "status_ig": ig_status,
                "status_tt": tt_status,
                "status_shopee": sp_status,
                "status_zalo": zl_status,
            }
            records.append(record)


        # Write to Master CSV with UTF-8 BOM for Excel/Google Sheets compatibility
        with open(self.output_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=MASTER_HEADERS)
            writer.writeheader()
            writer.writerows(records)

        logger.info(f"Successfully exported {len(records)} jobs to Master Sheet CSV: {self.output_csv}")

        # Post directly to Google Sheet Online via Service Account API v4
        try:
            from core.sheet_client import GoogleSheetDirectClient
            client = GoogleSheetDirectClient()
            if only_job_ids:
                records_to_send = [r for idx, r in enumerate(records) if rows[idx]["id"] in only_job_ids]
                client.update_master_rows(records_to_send)
            else:
                client.sync_input_tabs_to_master()
            logger.info("Successfully synced records to Master Google Sheet Online via API v4! 🚀")
        except Exception as e:
            logger.warning(f"Could not sync to Google Sheet via Direct API: {e}")

        return self.output_csv
