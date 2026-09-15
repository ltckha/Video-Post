"""Direct Google Sheets API v4 Client Module using Service Account.
100% DYNAMIC HEADER-BASED READ / WRITE ENGINE (Zero fixed-column assumptions).
Zero Apps Script redeployment friction. Works across Video-Post, Auto-Video-Factory, and Omni-Video.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import gspread
from google.oauth2.service_account import Credentials
from config import settings
from core.drive_uploader import GoogleDriveUploader

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

MASTER_HEADERS = [
    "job_id", "title", "video_path", "drive_url", "post_before", "content_type", "shopee_link",
    "caption_fb", "caption_yt", "caption_ig", "caption_tt", "caption_shopee", "caption_zalo",
    "brand_fb", "brand_yt", "brand_ig", "brand_tt",
    "status_fb", "status_yt", "status_ig", "status_tt", "status_shopee", "status_zalo"
]

VALID_CONTENT_TYPES = [
    "real_product",
    "ai_product",
    "real_accessory",
    "ai_accessory",
    "tips_tricks",
]


def detect_content_type(source_name: str, title: str = "", description: str = "", category: str = "") -> str:
    """Classify video into 5 universal content pillars across all brands:
    - real_product: Real camera video of main product (e.g. shoes, macadamia nuts, leather bags)
    - ai_product: AI-rendered video of main product (e.g. from SANPHAM or Omni-Video)
    - real_accessory: Real camera video of accessories/add-ons (e.g. belts, wallets, shell crackers)
    - ai_accessory: AI-rendered video of accessories/add-ons
    - tips_tricks: Tips, hacks, care guide, size guide, recipes, maintenance
    """
    full_text = f"{title} {description} {category}".lower()

    # 1. Check for tips/tricks/guides
    tips_keywords = [
        "mẹo", "meo", "hướng dẫn", "huong dan", "cách ", "cach ",
        "vệ sinh", "ve sinh", "bảo quản", "bao quan", "khử mùi", "khu mui",
        "tips", "hacks", "chọn size", "chon size", "phân biệt", "phan biet",
        "công dụng", "cong dung", "bí quyết", "bi quyet"
    ]
    if any(kw in full_text for kw in tips_keywords):
        return "tips_tricks"

    # 2. Determine AI vs Real production method
    # SANPHAM (from HNC_Control_Center) has real products but videos are AI-rendered!
    # Omni-Video is also AI-generated.
    # Auto-Video-Factory or real camera folders are Real.
    src_lower = str(source_name).lower()
    is_ai = ("sanpham" in src_lower) or ("omni" in src_lower) or ("ai" in src_lower)

    # 3. Check for accessory/secondary products
    accessory_keywords = [
        "ví", "vi da", "thắt lưng", "that lung", "dây nịt", "day nit",
        "túi", "balo", "vớ", "tất", "xi ", "đón gót", "don got", "lót giày", "lot giay",
        "kìm tách", "dụng cụ", "phụ kiện", "phu kien", "clutch", "wallet", "belt",
        "móc khóa", "moc khoa", "dây đồng hồ", "card holder"
    ]
    if any(kw in full_text for kw in accessory_keywords):
        return "ai_accessory" if is_ai else "real_accessory"

    # 4. Main product
    return "ai_product" if is_ai else "real_product"


def normalize_header(s: Any) -> str:
    return "".join(c for c in str(s).lower() if c.isalnum())


class GoogleSheetDirectClient:
    """Direct Google Sheets API v4 Controller for Master Sheet Operations with Dynamic Header Mapping."""

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
        """Fetch all rows from a worksheet as a list of dictionaries keyed by Column Header."""
        ws = self.get_worksheet(tab_name)
        all_vals = ws.get_all_values()
        if not all_vals or len(all_vals) < 2:
            return []

        headers = [str(h).strip() for h in all_vals[0]]
        records = []
        for row in all_vals[1:]:
            if not row or not any(row):
                continue
            rec = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers)) if headers[i]}
            records.append(rec)
        return records

    def sync_input_tabs_to_master(self, source_filter: Optional[str] = None) -> Dict[str, Any]:
        """Collect all input tabs (SANPHAM, Omni-Video, Auto-Video-Factory) and sync directly to Master tab.
        
        Dynamically reads headers from Row 1, preserves existing captions, brands, and statuses.
        Supports filtering by specific source/tab (e.g. 'SANPHAM', 'Omni-Video', 'Auto-Video-Factory', or 'all').
        """
        if not self.sh:
            self._connect()

        # 1. Read existing Master Tab dynamically
        master_ws = self.get_worksheet("Master")
        master_data = master_ws.get_all_values()
        
        existing_master = {}
        existing_master_order = []
        if len(master_data) > 1:
            headers = [h.strip() for h in master_data[0]]
            for row in master_data[1:]:
                if not row or not any(row):
                    continue
                row_dict = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers)) if headers[i]}
                job_id = str(row_dict.get("job_id", "")).strip()
                if job_id:
                    existing_master[job_id] = row_dict
                    if job_id not in existing_master_order:
                        existing_master_order.append(job_id)

        # 2. Determine input sources from sheet_sources.json
        sources_cfg = Path("config/sheet_sources.json")
        sources_list = [
            {"name": "SANPHAM", "tab_name": "SANPHAM", "sheet_url": "https://docs.google.com/spreadsheets/d/1U0b6_aVJJ93i5-V1RV1jUsQ9dhLYCY9BcJMI7R6J2C0/"},
            {"name": "Omni-Video", "tab_name": "Omni-Video"},
            {"name": "Auto-Video-Factory", "tab_name": "Auto-Video-Factory"},
        ]
        if sources_cfg.exists():
            try:
                with open(sources_cfg, "r", encoding="utf-8") as f:
                    cfg_sources = json.load(f).get("sources", [])
                    if cfg_sources:
                        sources_list = cfg_sources
            except Exception:
                pass

        if source_filter and source_filter.lower() != "all":
            clean_filter = source_filter.strip().lower()
            filtered_sources = [
                s for s in sources_list
                if s.get("tab_name", "").lower() == clean_filter
                or s.get("name", "").lower() == clean_filter
                or clean_filter in s.get("tab_name", "").lower()
                or clean_filter in s.get("name", "").lower()
            ]
            if filtered_sources:
                sources_list = filtered_sources

        input_data_map = {}
        new_items_order = []
        tabs_scanned = []

        # 3. Read rows dynamically from each input source
        for src in sources_list:
            tab_name = src.get("tab_name") or src.get("name", "")
            if not tab_name:
                continue

            target_sh = self.sh
            custom_url = src.get("sheet_url")
            if custom_url and self.gc:
                try:
                    target_sh = self.gc.open_by_url(custom_url)
                except Exception as e:
                    logger.warning(f"Could not open custom sheet_url '{custom_url}': {e}")
                    target_sh = self.sh

            try:
                ws = target_sh.worksheet(tab_name)
            except Exception:
                continue

            tab_values = ws.get_all_values()
            if len(tab_values) < 2:
                continue

            tabs_scanned.append(f"{target_sh.title} -> {tab_name}")

            # Check whether Row 1 or Row 2 contains technical headers (e.g. SANPHAM has grouped headers in Row 1)
            header_row_idx = 0
            if len(tab_values) > 1:
                row1_str = " ".join(tab_values[0]).lower()
                row2_str = " ".join(tab_values[1]).lower()
                if ("product_code" in row2_str or "content_files" in row2_str) and "product_code" not in row1_str:
                    header_row_idx = 1

            headers = [h.strip() for h in tab_values[header_row_idx]]
            data_rows = tab_values[header_row_idx + 1:]
            
            def find_idx(possible_names):
                header_norms = {normalize_header(h): i for i, h in enumerate(headers) if h}
                for p in possible_names:
                    norm_p = normalize_header(p)
                    if norm_p in header_norms:
                        return header_norms[norm_p]
                return -1

            is_sanpham_tab = ("sanpham" in tab_name.lower()) or ("san_pham" in tab_name.lower())

            if is_sanpham_tab:
                code_idx = find_idx(["product_code", "Mã SP", "Mã sản phẩm", "code", "job_id", "SKU"])
                name_idx = find_idx(["product_name", "Tên sản phẩm", "Tên SP", "name", "title"])
                files_idx = find_idx(["content_files", "Tư liệu", "Files", "Media", "Tư liệu Media"])
                path_idx = find_idx(["content_path", "Đường dẫn", "Path", "Folder", "Thư mục Media"])
                cat_idx = find_idx(["Tên Ngành Hàng", "Ngành hàng", "Category", "Tên ngành hàng"])
                desc_idx = find_idx(["product_description", "Mô tả", "Chi tiết", "Description"])
                price_idx = find_idx(["product_price", "Giá", "Price", "Giá bán"])
                color_idx = find_idx(["product_color", "Màu sắc", "Color"])
                link_idx = find_idx(["shopee_link", "Link Shopee", "Affiliate Link", "Link"])
                post_before_idx = find_idx(["post_before", "hạn chót", "deadline", "han_chot", "postbefore"])

                for row in data_rows:
                    if not row or not any(row):
                        continue
                    
                    raw_id = row[code_idx].strip() if code_idx != -1 and code_idx < len(row) else ""
                    if not raw_id or raw_id in input_data_map:
                        continue

                    # Filter: Only process rows where content_files contains "VIDEO"
                    files_val = row[files_idx].strip() if files_idx != -1 and files_idx < len(row) else ""
                    if "video" not in files_val.lower():
                        continue

                    title_val = row[name_idx].strip() if name_idx != -1 and name_idx < len(row) else raw_id
                    folder_path = row[path_idx].strip() if path_idx != -1 and path_idx < len(row) else ""
                    cat_val = row[cat_idx].strip() if cat_idx != -1 and cat_idx < len(row) else ""
                    desc_val = row[desc_idx].strip() if desc_idx != -1 and desc_idx < len(row) else ""
                    price_val = row[price_idx].strip() if price_idx != -1 and price_idx < len(row) else ""
                    color_val = row[color_idx].strip() if color_idx != -1 and color_idx < len(row) else ""
                    link_val = row[link_idx].strip() if link_idx != -1 and link_idx < len(row) else ""
                    post_before_val = row[post_before_idx].strip() if post_before_idx != -1 and post_before_idx < len(row) else ""

                    # Resolve video files in content_path
                    video_val = ""
                    initial_status = "needs_edit"

                    if folder_path:
                        f_p = Path(folder_path)
                        if f_p.exists() and f_p.is_dir():
                            video_exts = ("*.mp4", "*.MP4", "*.mov", "*.MOV", "*.mkv", "*.avi")
                            found_videos = []
                            for ext in video_exts:
                                found_videos.extend(list(f_p.glob(ext)))
                            found_videos = sorted(list(set([v for v in found_videos if not v.name.startswith(".")])))

                            if len(found_videos) == 1:
                                video_val = str(found_videos[0].resolve())
                                initial_status = "needs_edit"
                            elif len(found_videos) > 1:
                                video_val = f"⚠️ Phát hiện {len(found_videos)} video: " + ", ".join([v.name for v in found_videos])
                                initial_status = "not_configured"
                            else:
                                video_val = ""
                                initial_status = "not_configured"
                        elif f_p.is_file() and str(f_p).lower().endswith((".mp4", ".mov")):
                            video_val = str(f_p.resolve())
                            initial_status = "needs_edit"
                        else:
                            video_val = ""
                            initial_status = "not_configured"
                    else:
                        initial_status = "not_configured"

                    # Skip products that don't have video files yet
                    if not video_val:
                        continue

                    context_caption = f"{title_val}\n✔ Mã SP: {raw_id}"
                    if cat_val:
                        context_caption += f"\n✔ Ngành hàng: {cat_val}"
                    if price_val:
                        context_caption += f"\n✔ Giá: {price_val}"
                    if color_val:
                        context_caption += f"\n✔ Màu sắc: {color_val}"
                    if desc_val:
                        context_caption += f"\n\n{desc_val}"

                    c_type = detect_content_type(source_name=tab_name, title=title_val, description=desc_val, category=cat_val)
                    input_data_map[raw_id] = {
                        "raw_id": raw_id,
                        "source_tab": tab_name,
                        "title_val": title_val,
                        "raw_cap_val": context_caption,
                        "video_val": video_val,
                        "link_val": link_val,
                        "post_before_val": post_before_val,
                        "content_type": c_type,
                        "b_fb": "Hiệu giày Hải Nancy",
                        "b_yt": "Hiệu giày Hải Nancy",
                        "b_ig": "Hiệu giày Hải Nancy",
                        "b_tt": "Hiệu giày Hải Nancy",
                        "initial_status": initial_status,
                    }
                    if raw_id not in existing_master and raw_id not in new_items_order:
                        new_items_order.append(raw_id)

            else:
                id_idx = find_idx(["job_id", "Mã sản phẩm", "Project ID", "SKU", "Video ID", "itemId"])
                title_idx = find_idx(["title", "Tên sản phẩm", "Video Title", "Tên SP", "productName"])
                caption_idx = find_idx(["raw_caption", "Caption & Hashtags", "caption", "Mô tả bài đăng", "Chi tiết sản phẩm", "Hashtags", "Mô tả", "description"])
                video_idx = find_idx(["video_path", "Output File", "Video File Path", "output_path", "video_url"])
                link_idx = find_idx(["shopee_link", "Link ưu đãi", "Affiliate Link", "Link sản phẩm", "shopeeLink"])
                post_before_idx = find_idx(["post_before", "hạn chót", "deadline", "han_chot", "postbefore"])
                fb_brand_idx = find_idx(["brand_fb", "Fanpage Facebook", "Brand FB"])
                yt_brand_idx = find_idx(["brand_yt", "Kênh YouTube", "Brand YT"])
                ig_brand_idx = find_idx(["brand_ig", "Kênh Instagram", "Brand IG"])
                tt_brand_idx = find_idx(["brand_tt", "Kênh TikTok", "Brand TT", "TikTok Brand"])

                for row in tab_values[1:]:
                    if not row or not any(row):
                        continue
                    
                    raw_id = row[id_idx].strip() if id_idx != -1 and id_idx < len(row) else ""
                    if not raw_id or raw_id in input_data_map:
                        continue

                    title_val = row[title_idx].strip() if title_idx != -1 and title_idx < len(row) else ""
                    raw_cap_val = row[caption_idx].strip() if caption_idx != -1 and caption_idx < len(row) else ""
                    video_val = row[video_idx].strip() if video_idx != -1 and video_idx < len(row) else ""
                    # Skip items that don't have video path yet
                    if not video_val:
                        continue

                    link_val = row[link_idx].strip() if link_idx != -1 and link_idx < len(row) else ""
                    post_before_val = row[post_before_idx].strip() if post_before_idx != -1 and post_before_idx < len(row) else ""
                    b_fb = row[fb_brand_idx].strip() if fb_brand_idx != -1 and fb_brand_idx < len(row) else ""
                    b_yt = row[yt_brand_idx].strip() if yt_brand_idx != -1 and yt_brand_idx < len(row) else ""
                    b_ig = row[ig_brand_idx].strip() if ig_brand_idx != -1 and ig_brand_idx < len(row) else ""
                    b_tt = row[tt_brand_idx].strip() if tt_brand_idx != -1 and tt_brand_idx < len(row) else ""

                    c_type = detect_content_type(source_name=tab_name, title=title_val, description=raw_cap_val, category="")
                    input_data_map[raw_id] = {
                        "raw_id": raw_id,
                        "source_tab": tab_name,
                        "title_val": title_val,
                        "raw_cap_val": raw_cap_val,
                        "video_val": video_val,
                        "link_val": link_val,
                        "post_before_val": post_before_val,
                        "content_type": c_type,
                        "b_fb": b_fb,
                        "b_yt": b_yt,
                        "b_ig": b_ig,
                        "b_tt": b_tt,
                    }
                    if raw_id not in existing_master and raw_id not in new_items_order:
                        new_items_order.append(raw_id)

        # 4. Build combined list: Preserve existing Master rows order, then append brand new rows at the bottom
        all_ordered_ids = []
        for j_id in existing_master_order:
            if j_id not in all_ordered_ids:
                all_ordered_ids.append(j_id)
        for j_id in new_items_order:
            if j_id not in all_ordered_ids:
                all_ordered_ids.append(j_id)

        # Initialize Google Drive Uploader for automatic video backup
        try:
            drive_uploader = GoogleDriveUploader()
        except Exception as e:
            logger.warning(f"Could not initialize GoogleDriveUploader: {e}")
            drive_uploader = None

        all_input_rows = []
        for raw_id in all_ordered_ids:
            if raw_id in input_data_map:
                inp = input_data_map[raw_id]
                source_tab = inp.get("source_tab", "")
                title_val = inp["title_val"]
                raw_cap_val = inp["raw_cap_val"]
                video_val = inp["video_val"]
                link_val = inp["link_val"]
                post_before_val = inp.get("post_before_val", "")
                c_type = inp.get("content_type", "")
                b_fb = inp["b_fb"]
                b_yt = inp["b_yt"]
                b_ig = inp["b_ig"]
                b_tt = inp["b_tt"]
            else:
                prev = existing_master.get(raw_id, {})
                source_tab = ""
                title_val = prev.get("title", "")
                raw_cap_val = prev.get("caption_fb", "")
                video_val = prev.get("video_path", "")
                link_val = prev.get("shopee_link", "")
                post_before_val = prev.get("post_before", "")
                c_type = prev.get("content_type", "")
                b_fb = prev.get("brand_fb", "Default")
                b_yt = prev.get("brand_yt", "Default")
                b_ig = prev.get("brand_ig", "Default")
                b_tt = prev.get("brand_tt", "Default")

            if not c_type:
                c_type = detect_content_type(source_name="", title=title_val, description=raw_cap_val)

            base_text = raw_cap_val or title_val
            is_existing = raw_id in existing_master
            prev = existing_master.get(raw_id, {})

            if is_existing:
                # Preserve existing AI captions (or fill with base_text if empty)
                cap_fb = prev.get("caption_fb") or base_text
                cap_yt = prev.get("caption_yt") or base_text
                cap_ig = prev.get("caption_ig") or base_text
                cap_tt = prev.get("caption_tt") or base_text
                cap_shopee = prev.get("caption_shopee") or base_text
                cap_zalo = prev.get("caption_zalo") or base_text

                # Preserve existing status unless multiple videos warning detected
                if str(video_val).startswith("⚠️"):
                    st_fb = "not_configured"
                    st_yt = "not_configured"
                    st_ig = "not_configured"
                    st_tt = "not_configured"
                    st_shopee = "not_configured"
                    st_zalo = "not_configured"
                else:
                    st_fb = prev.get("status_fb") or "needs_edit"
                    st_yt = prev.get("status_yt") or "needs_edit"
                    st_ig = prev.get("status_ig") or "needs_edit"
                    st_tt = prev.get("status_tt") or "needs_edit"
                    st_shopee = prev.get("status_shopee") or "needs_edit"
                    st_zalo = prev.get("status_zalo") or "needs_edit"
            else:
                # Brand new row: default all captions to raw_caption/title and all statuses to initial_status
                cap_fb = base_text
                cap_yt = base_text
                cap_ig = base_text
                cap_tt = base_text
                cap_shopee = base_text
                cap_zalo = base_text

                init_st = inp.get("initial_status", "needs_edit") if raw_id in input_data_map else "needs_edit"
                st_fb = init_st
                st_yt = init_st
                st_ig = init_st
                st_tt = init_st
                st_shopee = init_st
                st_zalo = init_st

            clean_video_path = video_val or prev.get("video_path", "")

            # Exclude items that do NOT have a video path yet
            if not str(clean_video_path).strip():
                continue

            # Check Google Drive video backup upload (Omni-Video & SANPHAM)
            drive_url_val = prev.get("drive_url", "")
            if not source_tab:
                clean_vp_lower = clean_video_path.lower()
                raw_id_lower = raw_id.lower()
                if "omni" in clean_vp_lower or "omni" in raw_id_lower:
                    source_tab = "Omni-Video"
                elif "sanpham" in clean_vp_lower or "hnc" in clean_vp_lower or "hải nancy" in str(b_fb).lower():
                    source_tab = "SANPHAM"

            if drive_uploader and GoogleDriveUploader.should_upload_video(
                source_name=source_tab,
                local_path=clean_video_path,
                existing_drive_url=drive_url_val,
                status_fb=st_fb,
                status_yt=st_yt,
                status_ig=st_ig,
            ):
                folder_id = GoogleDriveUploader.get_folder_id_for_source(source_tab)
                if folder_id:
                    logger.info(f"Auto-uploading video to Google Drive for {raw_id} ({source_tab})...")
                    try:
                        uploaded_url = drive_uploader.upload_file(clean_video_path, folder_id)
                        if uploaded_url:
                            drive_url_val = uploaded_url
                    except Exception as e:
                        logger.warning(f"Failed to upload video for {raw_id} to Google Drive: {e}")

            master_row = {
                "job_id": raw_id,
                "title": title_val or prev.get("title", ""),
                "video_path": clean_video_path,
                "drive_url": drive_url_val,
                "post_before": post_before_val or prev.get("post_before", ""),
                "content_type": c_type or "real_product",
                "shopee_link": link_val or prev.get("shopee_link", ""),
                "caption_fb": cap_fb,
                "caption_yt": cap_yt,
                "caption_ig": cap_ig,
                "caption_tt": cap_tt,
                "caption_shopee": cap_shopee,
                "caption_zalo": cap_zalo,
                "brand_fb": b_fb or prev.get("brand_fb", "Default"),
                "brand_yt": b_yt or prev.get("brand_yt", "Default"),
                "brand_ig": b_ig or prev.get("brand_ig", "Default"),
                "brand_tt": b_tt or prev.get("brand_tt", b_fb or "Default"),
                "status_fb": st_fb,
                "status_yt": st_yt,
                "status_ig": st_ig,
                "status_tt": st_tt,
                "status_shopee": st_shopee,
                "status_zalo": st_zalo,
            }
            all_input_rows.append(master_row)

        # 5. Prepare 2D Matrix strictly mapped by MASTER_HEADERS
        final_matrix = [MASTER_HEADERS]
        for r in all_input_rows:
            final_matrix.append([r.get(h, "") for h in MASTER_HEADERS])

        # 5. Direct batch update to Master Tab
        master_ws.clear()
        master_ws.update(values=final_matrix, range_name="A1", value_input_option="USER_ENTERED")
        logger.info(f"Directly synced {len(all_input_rows)} rows to Tab Master via Google Sheets API v4! 🚀")

        return {
            "status": "success",
            "total_synced": len(all_input_rows),
            "tabs_scanned": tabs_scanned,
        }

    def update_master_rows(self, records: List[Dict[str, Any]]) -> int:
        """Batch update specific rows on Tab Master matching job_id using dynamic header mapping."""
        if not records:
            return 0

        master_ws = self.get_worksheet("Master")
        master_data = master_ws.get_all_values()
        if len(master_data) < 2:
            return 0

        headers = [h.strip() for h in master_data[0]]
        header_map = {normalize_header(h): idx + 1 for idx, h in enumerate(headers) if h}
        
        job_id_norm = normalize_header("job_id")
        job_id_col = header_map.get(job_id_norm, 1) - 1

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
                for field_name, val in rec.items():
                    norm_k = normalize_header(field_name)
                    if norm_k in header_map:
                        col_idx = header_map[norm_k]
                        cell_a1 = gspread.utils.rowcol_to_a1(row_num, col_idx)
                        updates.append({
                            "range": cell_a1,
                            "values": [[val]]
                        })

        if updates:
            master_ws.batch_update(updates, value_input_option="USER_ENTERED")
            logger.info(f"Directly updated {len(records)} records on Tab Master via dynamic header mapping.")

        return len(records)

    def record_post_timestamp(
        self,
        brand: str,
        platform: str,
        timestamp_str: Optional[str] = None,
    ) -> bool:
        """Record actual posting timestamp on Tab Status using dynamic header and brand mapping."""
        from datetime import datetime
        import unicodedata
        
        ts = timestamp_str or datetime.now().strftime("%H:%M %d/%m/%Y")

        status_ws = self.get_worksheet("Status")
        status_data = status_ws.get_all_values()
        if len(status_data) < 2:
            return False

        headers = [h.strip() for h in status_data[0]]
        header_map = {normalize_header(h): idx + 1 for idx, h in enumerate(headers) if h}

        # Find brand column index
        brand_col_idx = header_map.get("brand", 4) - 1

        def norm(s):
            return unicodedata.normalize("NFC", str(s)).strip().lower().replace("ờ", "ở")

        clean_brand = norm(brand)
        target_row = None
        for r_idx, row in enumerate(status_data[1:], start=2):
            if len(row) > brand_col_idx:
                row_brand = norm(row[brand_col_idx])
                if row_brand == clean_brand or clean_brand in row_brand or row_brand in clean_brand:
                    target_row = r_idx
                    break

        if not target_row:
            return False

        plat_lower = platform.lower().strip()
        short_p = "fb" if plat_lower in ["facebook", "fb"] else ("yt" if plat_lower in ["youtube", "yt"] else ("ig" if plat_lower in ["instagram", "ig"] else ("tt" if plat_lower in ["tiktok", "tt"] else plat_lower)))
        plat_key = f"times_{short_p}"
        col_idx = header_map.get(normalize_header(plat_key))
        if not col_idx:
            # Fallback alias search
            col_idx = header_map.get(normalize_header(f"times_{plat_lower}")) or header_map.get(normalize_header(plat_lower)) or header_map.get(normalize_header(short_p))

        if not col_idx:
            return False

        cell_a1 = gspread.utils.rowcol_to_a1(target_row, col_idx)
        try:
            status_ws.update(range_name=cell_a1, values=[[ts]], value_input_option="USER_ENTERED")
            logger.info(f"Recorded timestamp '{ts}' for Brand '{brand}' [{platform.upper()}] on Tab Status ({cell_a1}).")
            return True
        except Exception as e:
            logger.warning(f"Could not record timestamp on Tab Status: {e}")
            return False

    def update_brand_schedule(
        self,
        brand: str,
        times_fb: Optional[str] = None,
        times_yt: Optional[str] = None,
        times_ig: Optional[str] = None,
        times_tt: Optional[str] = None,
    ) -> bool:
        """Directly update posting schedule for a specific brand on Tab Status with dynamic header mapping."""
        import unicodedata

        status_ws = self.get_worksheet("Status")
        status_data = status_ws.get_all_values()
        if len(status_data) < 2:
            return False

        headers = [h.strip() for h in status_data[0]]
        header_map = {normalize_header(h): idx + 1 for idx, h in enumerate(headers) if h}

        brand_col_idx = header_map.get("brand", 4) - 1

        def norm(s):
            return unicodedata.normalize("NFC", str(s)).strip().lower().replace("ờ", "ở")

        clean_brand = norm(brand)
        target_row = None
        for r_idx, row in enumerate(status_data[1:], start=2):
            if len(row) > brand_col_idx:
                row_brand = norm(row[brand_col_idx])
                if row_brand == clean_brand or clean_brand in row_brand or row_brand in clean_brand:
                    target_row = r_idx
                    break

        if not target_row:
            return False

        updates = []
        schedule_fields = {
            "times_fb": times_fb,
            "times_yt": times_yt,
            "times_ig": times_ig,
            "times_tt": times_tt,
        }

        for f_name, f_val in schedule_fields.items():
            if f_val is not None:
                col_idx = header_map.get(normalize_header(f_name))
                if col_idx:
                    cell_a1 = gspread.utils.rowcol_to_a1(target_row, col_idx)
                    updates.append({"range": cell_a1, "values": [[f_val]]})

        if updates:
            status_ws.batch_update(updates, value_input_option="USER_ENTERED")
            logger.info(f"Directly updated schedule for Brand '{brand}' on Tab Status via dynamic header mapping.")
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

