# Quy tắc làm việc cho Agent (AGENTS.md)

## 📌 RULE TỐI CAO: LUÔN LUÔN THẢO LUẬN TRƯỚC KHI THỰC HIỆN
- **BẮT BUỘC KHÔNG ĐƯỢC BỎ QUA**: Agent **LUÔN LUÔN thảo luận, trình bày giải pháp chi tiết và xin ý kiến chốt/đồng ý từ người dùng TRƯỚC KHI thực hiện** bất kỳ thay đổi nào (viết code, sửa file, tạo module mới, chạy lệnh terminal hay thay đổi cấu trúc dự án).
- **Quy trình tương tác chuẩn 3 bước**:
  1. **Lắng nghe & Phân tích**: Hiểu rõ yêu cầu của người dùng.
  2. **Đề xuất & Thảo luận**: Trình bày giải pháp chi tiết (nêu rõ các file sẽ sửa/tạo, lý do và cách xử lý).
  3. **Chờ xác nhận**: Hỏi ý kiến người dùng và **chỉ bắt tay vào thực hiện khi người dùng đã đồng ý/chốt phương án**.

---

## 🏗️ Tổng Quan Kiến Trúc Hệ Thống (Video-Post Architecture)

Hệ thống **Video-Post** là bộ công cụ tự động hóa E-Commerce đa nền tảng (Facebook, YouTube, Instagram, TikTok, Shopee, Zalo) kết hợp Trí Tuệ Nhân Tạo **Google Gemini 3.1 Flash Lite**:

### 1. Thu Gom Đa Tab Đầu Vào ([`config/sheet_sources.json`](file:///Users/khan/Developer/Video-Post/config/sheet_sources.json))
- Quét và đọc trực tiếp từ các **Tab đầu vào** (`Omni-Video`, `Auto-Video-Factory`...) nằm trong duy nhất 1 file Master Google Sheet.
- Tự động lọc chống trùng lặp dựa trên **Khóa chính Cột A** (`job_id`: Mã SP / Project ID) và đường dẫn video tuyệt đối (`video_path`).

### 2. Biên Soạn Nội Dung AI ([`core/ai_captioner.py`](file:///Users/khan/Developer/Video-Post/core/ai_captioner.py))
- Kết nối trực tiếp với **Google Gemini 3.1 Flash Lite API** (`gemini-3.1-flash-lite`).
- Sinh bài viết tự động cho 6 nền tảng:
  - **Facebook**: Bài viết chi tiết + 3-5 hashtags (Không CTA).
  - **YouTube Shorts**: 2 dòng đầu có tên SP, KHÔNG để link + `#Shorts` + 3 hashtags.
  - **Instagram**: Thẩm mỹ + 10-15 hashtags.
  - **TikTok**: Dài, chi tiết, giật gân, giữ chân người xem + 3-5 hashtags.
  - **Shopee**: Nghiêm ngặt < 150 ký tự + 4 tags quy định (`#shopeevideo #luotvuimualien #shopeecreator #videohangthoitrang`).
  - **Zalo**: Bán hàng + 3-5 hashtags.

### 3. Đồng Bộ Trực Tiếp Tab Trung Tâm Master Sheet ([`core/sheet_exporter.py`](file:///Users/khan/Developer/Video-Post/core/sheet_exporter.py))
- Gửi HTTP Webhook tới Google Apps Script (`GOOGLE_SHEET_WEBHOOK_URL`).
- Nạp/cập nhật mảng dữ liệu siêu tốc (`update_rows` / `setValues`) lên Tab **`Master_Post`** trên Google Sheet với **19 Tiêu Đề Cột Tiếng Anh Ngắn Gọn**:
  `job_id`, `title`, `video_path`, `shopee_link`, `caption_fb`, `caption_yt`, `caption_ig`, `caption_tt`, `caption_shopee`, `caption_zalo`, `brand_fb`, `brand_yt`, `brand_ig`, `status_fb`, `status_yt`, `status_ig`, `status_tt`, `status_shopee`, `status_zalo`.

### 4. Đăng Bài Tự Động & Đăng Tay
- **Facebook Page**: Tự động đăng video dạng Reel 3 giai đoạn (Resumable Upload) với Token hạn dài nạp từ [`config/facebook_pages.json`](file:///Users/khan/Developer/Video-Post/config/facebook_pages.json).
- **YouTube Shorts**: Tự động đăng qua YouTube Data API v3 với token đa kênh từ [`config/youtube_channels.json`](file:///Users/khan/Developer/Video-Post/config/youtube_channels.json).
- **TikTok / Shopee / Zalo**: Đăng tay nhanh từ dữ liệu 19 cột trên Tab `Master_Post`.
