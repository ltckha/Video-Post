"""Direct Google Sheets API v4 Client Module using Service Account.

Replaces Google Apps Script Webhooks with direct, ultra-fast Google Sheets API v4 calls.
Zero Apps Script redeployment friction. Works across Video-Post, Auto-Video-Factory, and Omni-Video.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import gspread
from google.oauth2.service_account import Credentials
from config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

MASTER_HEADERS = [
    "job_id", "title", "video_path", "shopee_link",
    "caption_fb", "caption_yt", "caption_ig", "caption_tt", "caption_shopee", "caption_zalo",
    "brand_fb", "brand_yt", "brand_ig", "brand_tt",
    "status_fb", "status_yt", "status_ig", "status_tt", "status_shopee", "status_zalo"
]


class GoogleSheetDirectClient:
    """Direct Google Sheets API v4 Controller for Master Sheet Operations."""

    def __init__(
        self,
        service_account_path: Optional[str] = None,
        sheet_url: Optional[str] = None,
    ):
        self.sa_path = Path(service_account_path or "config/service_account.json")
        self.sheet_url = sheet_url or getattr(settings, "MASTER_SHEET_URL", "")
        self.gc: Optional[gspread.Client] = None
        self.sh: Optional[gspread.Spreadsheet] = None
        self._connect()

    def _connect(self):
        """Authenticate using Service Account JSON key and open the Master Spreadsheet."""
        if not self.sa_path.exists():
            alt_path = Path("video-post-bot.json")
            if alt_path.exists():
                self.sa_path = alt_path

        if not self.sa_path.exists():
            raise FileNotFoundError(f"Service Account key not found at: {self.sa_path}")

        try:
            self.gc = gspread.service_account(filename=str(self.sa_path))
            if self.sheet_url:
                self.sh = self.gc.open_by_url(self.sheet_url)
                logger.info(f"Connected to Google Sheet: '{self.sh.title}' via Service Account.")
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets API: {e}")
            raise

    def get_worksheet(self, tab_name: str) -> gspread.Worksheet:
        """Get or create worksheet by tab name."""
        if not self.sh:
            self._connect()
        try:
            return self.sh.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            return self.sh.add_worksheet(title=tab_name, rows=100, cols=20)

    def fetch_all_records(self, tab_name: str) -> List[Dict[str, Any]]:
        """Fetch all rows from a worksheet as a list of dictionaries."""
        ws = self.get_worksheet(tab_name)
        return ws.get_all_records()

    def sync_input_tabs_to_master(self) -> Dict[str, Any]:
        """Collect all input tabs (Omni-Video, Auto-Video-Factory) and sync directly to Master tab.
        
        Automatically preserves existing AI captions, Brand routing, and statuses.
        Automatically cleans up deleted rows if an item was removed from its input tab.
        """
        if not self.sh:
            self._connect()

        # 1. Read existing Master Tab to preserve captions, brands, and statuses
        master_ws = self.get_worksheet("Master")
        master_data = master_ws.get_all_values()
        
        existing_master = {}
        if len(master_data) > 1:
            headers = [h.strip() for h in master_data[0]]
            for row in master_data[1:]:
                if not row or not row[0].strip():
                    continue
                row_dict = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
                job_id = str(row_dict.get("job_id", "")).strip()
                if job_id:
                    existing_master[job_id] = row_dict

        # 2. Determine input tabs from sheet_sources.json
        sources_cfg = Path("config/sheet_sources.json")
        input_tabs = ["Omni-Video", "Auto-Video-Factory"]
        if sources_cfg.exists():
            try:
                with open(sources_cfg, "r", encoding="utf-8") as f:
                    cfg_tabs = json.load(f).get("sources", [])
                    if cfg_tabs:
                        input_tabs = [t.get("tab_name", "") for t in cfg_tabs if t.get("tab_name")]
            except Exception:
                pass

        all_input_rows = []
        seen_job_ids = set()

        # 3. Read rows from each input tab
        for tab_name in input_tabs:
            try:
                ws = self.sh.worksheet(tab_name)
            except gspread.exceptions.WorksheetNotFound:
                continue

            tab_values = ws.get_all_values()
            if len(tab_values) < 2:
                continue

            headers = [h.strip() for h in tab_values[0]]
            
            def find_idx(possible_names):
                for p in possible_names:
                    for i, h in enumerate(headers):
                        if h.lower() == p.lower() or p.lower() in h.lower():
                            return i
                return -1

            id_idx = find_idx(["job_id", "Mã sản phẩm", "Project ID", "SKU", "Video ID"])
            title_idx = find_idx(["title", "Tên sản phẩm", "Video Title", "Tên SP"])
            video_idx = find_idx(["video_path", "Output File", "File ảnh lưu local", "Video File Path"])
            link_idx = find_idx(["shopee_link", "Link ưu đãi", "Affiliate Link", "Link sản phẩm"])
            fb_brand_idx = find_idx(["brand_fb", "Fanpage Facebook", "Brand FB"])
            yt_brand_idx = find_idx(["brand_yt", "Kênh YouTube", "Brand YT"])
            ig_brand_idx = find_idx(["brand_ig", "Kênh Instagram", "Brand IG"])
            tt_brand_idx = find_idx(["brand_tt", "Kênh TikTok", "Brand TT", "TikTok Brand"])

            for row in tab_values[1:]:
                if not row or not any(row):
                    continue
                
                raw_id = row[id_idx].strip() if id_idx != -1 and id_idx < len(row) else ""
                if not raw_id:
                    continue

                if raw_id in seen_job_ids:
                    continue
                seen_job_ids.add(raw_id)

                title_val = row[title_idx].strip() if title_idx != -1 and title_idx < len(row) else ""
                video_val = row[video_idx].strip() if video_idx != -1 and video_idx < len(row) else ""
                link_val = row[link_idx].strip() if link_idx != -1 and link_idx < len(row) else ""
                b_fb = row[fb_brand_idx].strip() if fb_brand_idx != -1 and fb_brand_idx < len(row) else ""
                b_yt = row[yt_brand_idx].strip() if yt_brand_idx != -1 and yt_brand_idx < len(row) else ""
                b_ig = row[ig_brand_idx].strip() if ig_brand_idx != -1 and ig_brand_idx < len(row) else ""
                b_tt = row[tt_brand_idx].strip() if tt_brand_idx != -1 and tt_brand_idx < len(row) else ""

                prev = existing_master.get(raw_id, {})

                # Automatic transition for TikTok: manual_pending -> pending
                prev_st_tt = prev.get("status_tt", "pending")
                if prev_st_tt in ["manual_pending", ""]:
                    prev_st_tt = "pending"

                master_row = {
                    "job_id": raw_id,
                    "title": title_val or prev.get("title", ""),
                    "video_path": video_val or prev.get("video_path", ""),
                    "shopee_link": link_val or prev.get("shopee_link", ""),
                    "caption_fb": prev.get("caption_fb", ""),
                    "caption_yt": prev.get("caption_yt", ""),
                    "caption_ig": prev.get("caption_ig", ""),
                    "caption_tt": prev.get("caption_tt", ""),
                    "caption_shopee": prev.get("caption_shopee", ""),
                    "caption_zalo": prev.get("caption_zalo", ""),
                    "brand_fb": b_fb or prev.get("brand_fb", "Default"),
                    "brand_yt": b_yt or prev.get("brand_yt", "Default"),
                    "brand_ig": b_ig or prev.get("brand_ig", "Default"),
                    "brand_tt": b_tt or prev.get("brand_tt", b_fb or "Default"),
                    "status_fb": prev.get("status_fb", "pending"),
                    "status_yt": prev.get("status_yt", "pending"),
                    "status_ig": prev.get("status_ig", "pending"),
                    "status_tt": prev_st_tt,
                    "status_shopee": prev.get("status_shopee", "manual_pending"),
                    "status_zalo": prev.get("status_zalo", "manual_pending"),
                }
                all_input_rows.append(master_row)

        # 4. Prepare 2D Matrix for Master Sheet Update
        final_matrix = [MASTER_HEADERS]
        for r in all_input_rows:
            final_matrix.append([r.get(h, "") for h in MASTER_HEADERS])

        # 5. Direct batch update to Master Tab (Clearing stale rows)
        master_ws.clear()
        master_ws.update(final_matrix, value_input_option="USER_ENTERED")
        logger.info(f"Directly synced {len(all_input_rows)} rows to Tab Master via Google Sheets API v4! 🚀")

        return {
            "status": "success",
            "total_synced": len(all_input_rows),
            "tabs_scanned": input_tabs,
        }

    def update_master_rows(self, records: List[Dict[str, Any]]) -> int:
        """Batch update specific rows on Tab Master matching job_id."""
        if not records:
            return 0

        master_ws = self.get_worksheet("Master")
        master_data = master_ws.get_all_values()
        if len(master_data) < 2:
            return 0

        headers = [h.strip() for h in master_data[0]]
        job_id_col = headers.index("job_id") if "job_id" in headers else 0

        row_map = {}
        for r_idx, row in enumerate(master_data[1:], start=2):
            if row and len(row) > job_id_col:
                j_id = str(row[job_id_col]).strip()
                if j_id:
                    row_map[j_id] = r_idx

        updates = []
        for rec in records:
            j_id = str(rec.get("job_id", "")).strip()
            if j_id in row_map:
                row_num = row_map[j_id]
                for col_name, val in rec.items():
                    if col_name in headers:
                        col_idx = headers.index(col_name) + 1
                        updates.append({
                            "range": gspread.utils.rowcol_to_a1(row_num, col_idx),
                            "values": [[val]]
                        })

        if updates:
            master_ws.batch_update(updates, value_input_option="USER_ENTERED")
            logger.info(f"Directly updated {len(records)} records on Tab Master.")

        return len(records)

    def update_brand_schedule(
        self,
        brand: str,
        times_fb: Optional[str] = None,
        times_yt: Optional[str] = None,
        times_ig: Optional[str] = None,
        times_tt: Optional[str] = None,
    ) -> bool:
        """Directly update posting schedule for a specific brand on Tab Status."""
        status_ws = self.get_worksheet("Status")
        status_data = status_ws.get_all_values()
        if len(status_data) < 2:
            return False

        import unicodedata
        
        def norm(s):
            return unicodedata.normalize("NFC", str(s)).strip().lower().replace("ờ", "ở")

        clean_brand = norm(brand)
        target_row = None
        for r_idx, row in enumerate(status_data[1:], start=2):
            if len(row) > 3:
                row_brand = norm(row[3])
                if row_brand == clean_brand or clean_brand in row_brand or row_brand in clean_brand:
                    target_row = r_idx
                    break

        if not target_row:
            return False

        updates = []
        if times_fb is not None:
            updates.append({"range": f"E{target_row}", "values": [[times_fb]]})
        if times_yt is not None:
            updates.append({"range": f"F{target_row}", "values": [[times_yt]]})
        if times_ig is not None:
            updates.append({"range": f"G{target_row}", "values": [[times_ig]]})
        if times_tt is not None:
            updates.append({"range": f"H{target_row}", "values": [[times_tt]]})

        if updates:
            status_ws.batch_update(updates, value_input_option="USER_ENTERED")
            logger.info(f"Directly updated schedule for Brand '{brand}' on Tab Status.")
            return True

        return False

    def apply_dropdown_validations(self):
        """Apply Data Validation Dropdowns for all Status columns on Tab Master."""
        master_ws = self.get_worksheet("Master")
        sheet_id = master_ws.id
        
        # Status columns: Column 15 (O) to Column 20 (T)
        req = {
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": 1000,
                    "startColumnIndex": 14,
                    "endColumnIndex": 20,
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": [
                            {"userEnteredValue": "pending"},
                            {"userEnteredValue": "published"},
                            {"userEnteredValue": "failed"},
                            {"userEnteredValue": "needs_edit"},
                            {"userEnteredValue": "manual_pending"},
                            {"userEnteredValue": "not_configured"},
                        ]
                    },
                    "showCustomUi": True,
                    "strict": False
                }
            }
        }
        try:
            self.sh.batch_update({"requests": [req]})
            logger.info("Applied dropdown validations to Status columns on Tab Master.")
        except Exception as e:
            logger.warning(f"Could not apply dropdown validations: {e}")
