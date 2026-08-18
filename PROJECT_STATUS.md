# 📝 Video-Post - Project Status & Architecture

> **Cập nhật mới nhất:** 17/08/2026

---

## 1. 🌟 Kiến Trúc Hiện Tại (Current Architecture)

### 📊 Direct Google Sheets API v4 (100% Zero Google Apps Script)
* **Kết nối:** Dùng trực tiếp Google Sheets API v4 qua `gspread` kết hợp khóa xác thực `config/service_account.json`.
* **Spreadsheet ID:** `1Xg67qhp1J_Izt7v5uDKRgKjdEZapX9giKJ_ym0OMJN4`
* **Module điều khiển:** [`core/sheet_client.py`](core/sheet_client.py).
* **Các tính năng Direct API:**
  * Đồng bộ video render và đọc danh sách bài đăng từ Tab `STATUS`.
  * Cập nhật Caption 6 nền tảng (Facebook, YouTube Shorts, Instagram Reels, TikTok, Shopee Video, Zalo Video).
  * Điều phối lịch đăng tự động và cập nhật lịch ngẫu nhiên (`random_slots`) cho từng Brand/Kênh.

### 🧠 Chiến Lược Phân Bổ Mô Hình Gemini AI
* **Viết Caption Social Mạng Xã Hội (`core/ai_captioner.py`):**
  * Mặc định: **`gemini-3.5-flash-lite`** (Hạn ngạch cực cao **500 RPD** / 15 RPM).
  * Tự động fallback: `gemini-3.5-flash-lite` ➔ `gemini-3.1-flash-lite` ➔ `gemini-3.7-flash`.
  * Đảm bảo viết caption chuẩn cho 6 nền tảng E-Commerce, đúng định dạng JSON, không vi phạm CTA cứng nhắc, Shopee < 150 ký tự.

---

## 2. 🚀 Đa Nền Tảng & Đa Kênh (Brand/Account Manager)

* **6 Nền tảng hỗ trợ:** Facebook Reels, YouTube Shorts, TikTok, Instagram Reels, Shopee Video, Zalo Video.
* **7 Thương hiệu / Kênh nội dung:**
  1. Hiệu giày Hải Nancy
  2. Mua Chuẩn Xài Lâu
  3. Macadamia Hải Nancy
  4. Ở Đà Lạt vậy thôi
  5. Yen Handmade Leather
  6. YenYen Deals
  7. Elegant Steps
* **Quản lý phiên đăng nhập:** Quản lý cookies & tokens qua `core/account_manager.py`.

---

## 3. 🛡️ Quy Tắc Làm Việc Của AI Assistant
1. **BẮT BUỘC THẢO LUẬN TRƯỚC KHI LÀM (`.agents/rules/always_consult_user_first.md`):** Luôn trình bày kế hoạch và xin ý kiến duyệt từ User trước khi sửa code hoặc chạy lệnh.
2. **KHÔNG TỰ Ý PUSH GIT:** Chỉ thực hiện lệnh push Git khi User yêu cầu rõ ràng.
