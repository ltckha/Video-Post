# Video-Post Automation System 🎬🚀

Hệ thống tự động hóa đăng video đa nền tảng (**Facebook, YouTube, Instagram, TikTok, Shopee, Zalo**) tích hợp Trí Tuệ Nhân Tạo **Google Gemini 3.1 Flash Lite** và đồng bộ trực tiếp lên **Master Google Sheet Online**.

---

## 🌟 TÍNH NĂNG NỔI BẬT

1. 📥 **Thu Gom Dữ Liệu Đa Nguồn (Multi-Source Ingestion)**:
   - Tự động quét nhiều Google Sheet dự án cùng lúc (*Shopee Nesty Affiliate*, *Auto Video Factory*...).
   - Lưu vết danh sách dự án dài hạn tại [`config/sheet_sources.json`](file:///Users/khan/Developer/Video-Post/config/sheet_sources.json).

2. 🧠 **Chống Trùng Lặp & Phân Biệt Bài Cũ/Mới Thông Minh**:
   - Sử dụng **Khóa chính Cột A** (`job_id`: Mã SP / Project ID) và `video_path` để phân biệt.
   - Bài cũ đã đăng giữ nguyên trạng thái `published` và **không tốn Quota API**.
   - Bài mới tự động được gọi **Google Gemini 3.1 Flash Lite** để biên soạn nội dung.

3. 🤖 **Biên Soạn Nội Dung AI Cho 6 Nền Tảng ([`core/ai_captioner.py`](file:///Users/khan/Developer/Video-Post/core/ai_captioner.py))**:
   - Tự động sinh 6 mẫu caption độc đáo chuẩn quy tắc (Bỏ CTA, Shopee < 150 ký tự + 4 tags cố định).

4. 📊 **Đồng Bộ Master Sheet Online Siêu Tốc (19 Cột Tiếng Anh Ngắn Gọn)**:
   - Tự động nạp mảng `setValues` trực tiếp qua Google Apps Script Webhook.

5. 📱 **Quản Lý Nhiều Tài Khoản / Fanpage ([`config/facebook_pages.json`](file:///Users/khan/Developer/Video-Post/config/facebook_pages.json))**:
   - Nạp tự động Page Token cho 7 Fanpage Facebook (có bộ đọc hạn token tiếng Việt `"5 Tháng 10, 2026"`).

6. 🖥️ **Ứng Dụng Nhấp Đúp Trên macOS ([`Run_Menu.command`](file:///Users/khan/Developer/Video-Post/Run_Menu.command))**:
   - Giao diện menu tương tác nhấp đúp chạy trực tiếp từ macOS Finder.

---

## 📊 BẢNG 19 CỘT MASTER SHEET ONLINE

```text
 1. job_id           Mã ID sản phẩm / Project ID (Cột A)
 2. title            Tiêu đề video / sản phẩm
 3. video_path       Đường dẫn tuyệt đối file video local (/Volumes/Media/...)
 4. shopee_link      Link ưu đãi Shopee Affiliate
 5. caption_fb       Bài viết AI cho Facebook
 6. caption_yt       Bài viết AI cho YouTube
 7. caption_ig       Bài viết AI cho Instagram
 8. caption_tt       Bài viết AI cho TikTok
 9. caption_shopee   Bài viết AI cho Shopee (< 150 chars total)
10. caption_zalo     Bài viết AI cho Zalo
11. brand_fb         Tên Fanpage Facebook nhận bài (Mua Chuẩn Xài Lâu...)
12. brand_yt         Tên Kênh YouTube nhận bài
13. brand_ig         Tên Tài khoản Instagram nhận bài
14. status_fb        Trạng thái Facebook (published / pending / failed)
15. status_yt        Trạng thái YouTube (published / pending / failed)
16. status_ig        Trạng thái Instagram (published / pending)
17. status_tt        Trạng thái TikTok Đăng tay (manual_pending / manual_done)
18. status_shopee    Trạng thái Shopee Đăng tay (manual_pending / manual_done)
19. status_zalo      Trạng thái Zalo Đăng tay (manual_pending / manual_done)
```

---

## 🛠️ CẤU HÌNH & HƯỚNG DẪN SỬ DỤNG

### 1. Cấu Hình File `.env`
Tạo file `.env` ở thư mục gốc:
```env
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_RPM_DELAY=4
GEMINI_MAX_RPD=500
MASTER_SHEET_URL=https://docs.google.com/spreadsheets/d/1Xg67qhp1J_Izt7v5uDKRgKjdEZapX9giKJ_ym0OMJN4/
GOOGLE_SHEET_WEBHOOK_URL=https://script.google.com/macros/s/AKfycbw0CdP4CTYLmUvOMMyShmbFoqBS1LlvV6aMQon4PIJ2d53AD1Gnk_7OcsD5ZFllOsBQ/exec
```

### 2. Chạy Bằng Giao Diện Nhấp Đúp Finder
Nhấp đúp vào tệp **[`Run_Menu.command`](file:///Users/khan/Developer/Video-Post/Run_Menu.command)** trên macOS Finder để mở Menu quản lý (Các phím 0-7).

### 3. Chạy Bằng Lệnh Terminal (CLI)
```bash
# 同步 tất cả các nguồn dự án liên kết với Gemini AI
./venv/bin/python main.py sync-all-sources

# Xử lý hàng chờ đăng bài (Mỗi lần 1 bài theo yêu cầu)
./venv/bin/python main.py process-queue --limit 1

# Xuất lại dữ liệu sang Master Sheet Online
./venv/bin/python main.py export-master-sheet

# Chạy kiểm thử tự động
./venv/bin/pytest tests/
```

---

## 🧪 ĐƠN VỊ KIỂM THỬ (UNIT TESTS)

Tất cả **24/24 test cases** trong thư mục `tests/` đã được kiểm thử thành công 100% 🟢.
