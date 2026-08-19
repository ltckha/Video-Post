# Video-Post Automation Engine 🎬🚀

Hệ thống tự động hóa xuất bản video đa nền tảng E-Commerce (**Facebook Reels, YouTube Shorts, Instagram Reels, TikTok Studio, Shopee, Zalo**) tích hợp Trí Tuệ Nhân Tạo **Google Gemini 3.5 Flash Lite** và đồng bộ trực tiếp qua **Google Sheets API v4 (Service Account)**.

---

## 🌟 TÍNH NĂNG NỔI BẬT

1. 🚀 **Đăng Bài 1-Click Đa Nền Tảng (`main.py auto-post-active`)**:
   - Tự động phát hiện các Brand & Kênh đã sẵn sàng Token/Cookie.
   - Quét tìm bài viết `pending` tuần tự từ trên xuống dưới và xuất bản ngay lập tức mà không cần hỏi lại.
   - Tự động cập nhật `status = published` trên Google Sheet Tab `Master` và ghi lại mốc giờ đăng thực tế trên Tab `Status`.

2. 📥 **Thu Gom Đa Tab Đầu Vào & Chống Trùng Lặp**:
   - Quét trực tiếp các Tab đầu vào (`Omni-Video`, `Auto-Video-Factory`...) trên cùng 1 file Master Google Sheet.
   - Chống trùng lặp theo **Khóa chính Cột A** (`job_id`: Mã SP / Project ID) kết hợp đường dẫn video.
   - Bảo toàn 100% thứ tự các dòng cũ trên Master, bài mới tinh chỉ thêm nối tiếp ở hàng dưới cùng.

3. 🤖 **Biên Soạn Nội Dung AI Cho 6 Nền Tảng ([`core/ai_captioner.py`](file:///Users/khan/Developer/Video-Post/core/ai_captioner.py))**:
   - Tích hợp **Google Gemini 3.5 Flash Lite** (kèm cơ chế tự động fallback `gemini-3.1-flash-lite` và `gemini-3.7-flash`).
   - Tự động sinh 6 mẫu caption chuẩn phong cách cho từng kênh:
     - **Facebook**: Bài viết chi tiết + 3-5 hashtags (Không CTA).
     - **YouTube Shorts**: Tên SP 2 dòng đầu, không link + `#Shorts` + 3 hashtags.
     - **Instagram**: Thẩm mỹ nghệ thuật + 10-15 hashtags.
     - **TikTok**: Storytelling (Quote emoji + Bối cảnh + Checklist ✔ + Đúc kết 💡 + Giữ chân 🔥 + 5 hashtags).
     - **Shopee**: Nghiêm ngặt < 150 ký tự + 4 tags quy định (`#shopeevideo #luotvuimualien #shopeecreator #videohangthoitrang`).
     - **Zalo**: Bán hàng súc tích + 3-5 hashtags.

4. 📊 **Đồng Bộ Trực Tiếp Google Sheets API v4 (Dynamic Header Mapping)**:
   - Kết nối trực tiếp qua **Google Sheets API v4** bằng Service Account ([`config/service_account.json`](file:///Users/khan/Developer/Video-Post/config/service_account.json)) — **Loại bỏ 100% Google Apps Script**.
   - **Cơ Chế Dynamic Header Mapping**: Tự động quét dòng 1 trên Google Sheet (`header_map = {normalize(h): col_idx}`) để xác định chính xác tọa độ cột cho từng trường dữ liệu, đảm bảo không bao giờ bị lệch cột.

5. 🔌 **Hệ Thống Kết Nối Đa Nền Tảng (Connectors)**:
   - **Facebook Page**: Tải lên dạng Reel (Resumable Upload) với Token dài hạn từ [`config/facebook_pages.json`](file:///Users/khan/Developer/Video-Post/config/facebook_pages.json).
   - **YouTube Shorts**: Tải lên qua YouTube Data API v3 với token đa kênh từ [`config/youtube_channels.json`](file:///Users/khan/Developer/Video-Post/config/youtube_channels.json).
   - **Instagram Reels**: Tải lên chính thức qua Meta Graph API Resumable Upload (`rupload.facebook.com`).
   - **TikTok Studio**: Đăng bài tự động bằng Playwright với Chrome Profile độc lập & Cookie Injection từ [`config/tiktok_accounts.json`](file:///Users/khan/Developer/Video-Post/config/tiktok_accounts.json).

---

## 📊 BẢNG 20 CỘT MASTER SHEET ONLINE

```text
 1. job_id           Mã ID sản phẩm / Project ID (Cột A)
 2. title            Tiêu đề video / sản phẩm
 3. video_path       Đường dẫn tuyệt đối file video MP4 local (/Volumes/Media/...)
 4. shopee_link      Link ưu đãi Shopee Affiliate
 5. caption_fb       Bài viết AI cho Facebook
 6. caption_yt       Bài viết AI cho YouTube
 7. caption_ig       Bài viết AI cho Instagram
 8. caption_tt       Bài viết AI cho TikTok
 9. caption_shopee   Bài viết AI cho Shopee (< 150 chars total)
10. caption_zalo     Bài viết AI cho Zalo
11. brand_fb         Tên Fanpage Facebook nhận bài
12. brand_yt         Tên Kênh YouTube nhận bài
13. brand_ig         Tên Tài khoản Instagram nhận bài
14. brand_tt         Tên Kênh TikTok nhận bài
15. status_fb        Trạng thái Facebook (published / pending / needs_edit / failed)
16. status_yt        Trạng thái YouTube (published / pending / needs_edit / failed)
17. status_ig        Trạng thái Instagram (published / pending / needs_edit / failed)
18. status_tt        Trạng thái TikTok (published / pending / needs_edit / failed)
19. status_shopee    Trạng thái Shopee Đăng tay (manual_pending / manual_done / needs_edit)
20. status_zalo      Trạng thái Zalo Đăng tay (manual_pending / manual_done / needs_edit)
```

---

## 🛠️ CẤU HÌNH & HƯỚNG DẪN SỬ DỤNG

### 1. Cấu Hình File `.env`
Tạo file `.env` ở thư mục gốc:
```env
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_RPM_DELAY=4
GEMINI_MAX_RPD=500
MASTER_SHEET_URL=https://docs.google.com/spreadsheets/d/1Xg67qhp1J_Izt7v5uDKRgKjdEZapX9giKJ_ym0OMJN4/
```

### 2. Chạy Bằng Menu Điều Khiển (`run.sh` / `Run_Menu.command`)
Nhấp đúp vào tệp **[`Run_Menu.command`](file:///Users/khan/Developer/Video-Post/Run_Menu.command)** hoặc chạy:
```bash
./run.sh
```

### 3. Các Lệnh Terminal Chính (CLI)
```bash
# 1-Click Đăng tự động tất cả các kênh đã sẵn sàng Token/Cookie
./venv/bin/python main.py auto-post-active

# Đồng bộ dữ liệu từ các Tab đầu vào sang Tab Master
./venv/bin/python main.py sync-all-sources

# Nhờ AI viết lại các bài có trạng thái needs_edit
./venv/bin/python main.py rewrite-needs-edit

# Nạp Cookie TikTok cho Brand từ file JSON xuất bởi Cookie-Editor
./venv/bin/python main.py tiktok-import-cookies --brand "Hiệu giày Hải Nancy" --cookies-file "path/to/cookies.json"

# Chạy kiểm thử tự động
./venv/bin/pytest tests/
```

---

## 🧪 ĐƠN VỊ KIỂM THỬ (UNIT TESTS)

Tất cả **25/25 test cases** trong thư mục `tests/` đã được kiểm thử thành công 100% 🟢.
