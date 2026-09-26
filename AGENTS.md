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
- Kết nối trực tiếp với **Google Gemini API** (mặc định: `gemini-3.5-flash-lite`, hạn ngạch 500 RPD / 15 RPM, kèm tự động fallback `gemini-3.1-flash-lite` và `gemini-3.7-flash`).
- Sinh bài viết tự động cho 6 nền tảng:
  - **Facebook**: Bài viết chi tiết + 3-5 hashtags (Không CTA).
  - **YouTube Shorts**: 2 dòng đầu có tên SP, KHÔNG để link + `#Shorts` + 3 hashtags.
  - **Instagram**: Thẩm mỹ + 10-15 hashtags.
  - **TikTok**: Cấu trúc Storytelling nghệ thuật (Quote mở đầu emoji + Dẫn dắt bối cảnh + Checklist ✔ chi tiết + Đúc kết chiều sâu 💡 + Giữ chân xem hết video 🔥 + 5 hashtags).
  - **Shopee**: Nghiêm ngặt < 150 ký tự + 4 tags quy định (`#shopeevideo #luotvuimualien #shopeecreator #videohangthoitrang`).
  - **Zalo**: Bán hàng + 3-5 hashtags.

### 3. Đồng Bộ Trực Tiếp Tab Trung Tâm Master Sheet ([`core/sheet_client.py`](file:///Users/khan/Developer/Video-Post/core/sheet_client.py))
- Kết nối trực tiếp qua **Google Sheets API v4** bằng chìa khóa Service Account ([`config/service_account.json`](file:///Users/khan/Developer/Video-Post/config/service_account.json)) — **Loại bỏ 100% Google Apps Script**.
- **Cơ Chế Dynamic Header Mapping (100% Không dùng cột cố định)**: Tự động quét dòng 1 trên Google Sheet (`header_map = {normalize(h): col_idx}`) để xác định chính xác tọa độ cột cho từng trường dữ liệu, đảm bảo không bao giờ bị lệch cột.
- Nạp/cập nhật mảng dữ liệu siêu tốc lên Tab **`Master`** trên Google Sheet với **22 Tiêu Đề Cột Tiếng Anh Ngắn Gọn**:
  `job_id`, `title`, `video_path`, `post_before`, `content_type`, `shopee_link`, `caption_fb`, `caption_yt`, `caption_ig`, `caption_tt`, `caption_shopee`, `caption_zalo`, `brand_fb`, `brand_yt`, `brand_ig`, `brand_tt`, `status_fb`, `status_yt`, `status_ig`, `status_tt`, `status_shopee`, `status_zalo`.
- **Cơ Chế Ưu Tiên Hạn Chót & Đăng Xen Kẽ Đa Trụ Cột (Smart Interleaving)** ([`core/queue_scheduler.py`](file:///Users/khan/Developer/Video-Post/core/queue_scheduler.py)): 
  - Phân tầng 5 cấp độ theo `post_before` (khẩn cấp $\le 3$ ngày lên đầu).
  - Tự động nhận diện 5 loại `content_type`: `real_product`, `ai_product`, `real_accessory`, `ai_accessory`, `tips_tricks`.
  - Luân phiên xen kẽ (Round-Robin) các loại nội dung chống "một màu" kênh. Hỗ trợ đăng nhiều bài/ngày (`--limit`).

### 4. Đăng Bài Tự Động (1-Click Multi-Platform Auto Post)
- **1-Click Auto Post (`main.py auto-post-active`)**: Tự động phát hiện các Brand & Nền tảng đã hoàn tất thiết lập Token/Cookie (FB, YT, IG, TT). Tự động lấy 1 video `pending` và xuất bản ngay lập tức mà không cần hỏi lại, cập nhật đồng loạt `status = published` trên Google Sheet.
- **Facebook Page**: Tự động đăng video dạng Reel 3 giai đoạn (Resumable Upload) với Token hạn dài nạp từ [`config/facebook_pages.json`](file:///Users/khan/Developer/Video-Post/config/facebook_pages.json).
- **YouTube Shorts**: Tự động đăng qua YouTube Data API v3 với token đa kênh từ [`config/youtube_channels.json`](file:///Users/khan/Developer/Video-Post/config/youtube_channels.json).
- **Instagram Reels**: Tự động tải lên qua Graph API Video Container từ [`connectors/instagram/uploader.py`](file:///Users/khan/Developer/Video-Post/connectors/instagram/uploader.py).
- **TikTok Studio**: Tự động đăng bằng Playwright với Chrome Profile độc lập & Cookie Injection từ [`connectors/tiktok/browser_uploader.py`](file:///Users/khan/Developer/Video-Post/connectors/tiktok/browser_uploader.py).
- **Shopee / Zalo**: Đăng tay nhanh từ dữ liệu chuẩn trên Tab `Master`.

---

## 💡 Ý Tưởng & Tính Năng Phát Triển Tiếp Theo ([`docs/IDEAS.md`](file:///Users/khan/Developer/Video-Post/docs/IDEAS.md))
1. **Đưa sản phẩm vào Instagram từ link Shopee & Gắn Link Affiliate**: Tự động trích xuất thông tin sản phẩm, đăng First Comment & Pinned Comment chứa link tiếp thị liên kết Shopee/Lazada sau khi xuất bản.
2. **AI Smart Comment Responder**: Tự động phân loại ý định bình luận của khách hàng và dùng Gemini soạn thảo câu trả lời thân thiện kèm link mua hàng dựa trên dữ liệu video sẵn có.
3. **Audit & Hoàn thiện Hệ thống Đa Kênh cho từng Brand (Brand Channel Matrix)**: Bổ sung Instagram ID, YouTube Token, Facebook Page còn thiếu cho các thương hiệu (Macadamia, Đà Lạt, Yen Handmade, Elegant Steps, YenYen Deals, YenYen Farm).
4. **Tối ưu hóa hành vi đăng bài TikTok giống người thật**: Bổ sung mô phỏng di chuyển chuột tự nhiên (Bezier Curve), ngắt nghỉ gõ phím (Human Keystroke Dynamics).
5. **AI Market Intelligence Pipeline**: Kết hợp Gemini thu thập thời tiết, lễ hội, xu hướng sàn TMĐT để tự động đẩy hạn chót `post_before` đón đầu mùa vụ.



