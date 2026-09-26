# 💡 SỔ TAY Ý TƯỞNG & NHIỆM VỤ (IDEAS & TASKS) - VIDEO-POST

> **Dự án:** `Video-Post` (Hệ sinh thái tự động xuất bản & lên lịch đăng video đa kênh)  
> **Kênh lưu trữ trung tâm:** Google Drive `Spark/Video-Post/ideas_videopost.md` & `IDEAS.md`  
> **Kiến trúc sư & Đạo diễn:** Gemini Spark (`spark-anti`, `fb-video-publisher`)  
> **Kỹ sư trưởng thực thi (IDE):** Antigravity  
> **Chỉ đạo & Phê duyệt:** Lưu Thái Chí Kha (Kha Luu)  

---

## 📌 QUY TẮC SỬ DỤNG SỔ TAY Ý TƯỞNG & NHIỆM VỤ

1. **File độc lập, sử dụng liên tục:** Lưu trữ toàn bộ các ý tưởng cải tiến, backlog nhiệm vụ và giải pháp kỹ thuật cho `Video-Post`.
2. **Quy trình phối hợp:** Spark lập kiến trúc & đề xuất -> Antigravity triển khai code trong IDE -> Anh Kha phê duyệt.
3. **Chuẩn nghiệm thu:** Đo kiểm hành vi output thực tế trước khi xác nhận hoàn thành.

---

## 🚀 DANH SÁCH NHIỆM VỤ & Ý TƯỞNG CẢI TIẾN

---

### 💡 Task #01: Tích Hợp Nguồn Video Cloud-First Từ Google Drive (Dual Video Source)
- **Thời gian ghi nhận:** 12/09/2026 19:05
- **Dự án:** `Video-Post`
- **Mức độ ưu tiên:** 🔴 Cao nhất (Critical P0)
- **Người chỉ đạo:** Lưu Thái Chí Kha
- **Trạng thái:** ✅ **HOÀN THÀNH (Completed)** - Triển khai bởi Antigravity

#### 1. Bản chất Vấn đề & Mục tiêu:
- Bảng tính Video-Post và database SQLite hỗ trợ linh hoạt cả đường dẫn file cục bộ (`/Volumes/Media/...`) và Google Drive URL (`https://drive.google.com/...`).
- Khi kiểm tra hoặc đăng video, không bị lỗi "File not found" đối với Cloud Video.

#### 2. Kết quả Triển khai:
- Cập nhật hàm kiểm tra video trong `main.py`, `core/runner.py`, `core/sheet_exporter.py`: Hỗ trợ linh hoạt cả file cục bộ và link Cloud (`http://` / `https://`).
- Đảm bảo hệ thống sẵn sàng cho n8n Publishing Layer và Spark Cloud API xuất bản trực tiếp.
- 100% kiểm thử đã vượt qua.

---

### 💡 Task #02: Tự Động Sao Lưu Video Omni & HNC Lên Google Drive & Ghi Nhận drive_url
- **Thời gian ghi nhận:** 15/09/2026 10:18
- **Dự án:** `Video-Post`
- **Mức độ ưu tiên:** 🔴 Cao nhất (Critical P0)
- **Người chỉ đạo:** Lưu Thái Chí Kha
- **Trạng thái:** ✅ **HOÀN THÀNH (Completed)** - Triển khai bởi Antigravity

#### 1. Bản chất Vấn đề & Mục tiêu:
- Tự động sao lưu video từ máy Mac lên Google Drive khi quét dữ liệu Tab đầu vào (`sync_all_sources`).
- Ghi nhận URL video Google Drive vĩnh viễn vào Cột D (`drive_url`) trên Tab `Master`.

#### 2. Quy tắc lọc thông minh & Tiết kiệm dung lượng:
- Chỉ sao lưu cho 2 nguồn: `Omni-Video` (`Spark/Omni-Video/Outputs/`) và `SANPHAM` (`Spark/HNC_Master/Outputs/`).
- Tuyệt đối không sao lưu `Auto-Video-Factory`.
- Tự động bỏ qua nếu đã có `drive_url` hoặc file cục bộ không tồn tại.
- Tự động bỏ qua nếu cả 3 kênh (`status_fb`, `status_yt`, `status_ig`) đều không ở trạng thái `pending`.

#### 3. Kết quả Triển khai:
- Xây dựng module `core/drive_uploader.py` với cơ chế **Pre-Warmed Cache + Local Sync Bridge + Polling Retry**.
- Đã đồng bộ thành công và ghi nhận toàn bộ URL Google Drive trên Tab `Master`.
- Bổ sung bộ kiểm thử `tests/test_drive_backup.py` bao quát 100% các điều kiện.

---

### 💡 Task #03: Tầng Xuất Bản Tự Động n8n Publishing Layer Đa Kênh (Multi-Platform Cloud Dispatcher)
- **Thời gian ghi nhận:** 16/09/2026 10:00
- **Dự án:** `Video-Post`
- **Mức độ ưu tiên:** 🔴 Cao nhất (Critical P0)
- **Người chỉ đạo:** Lưu Thái Chí Kha
- **Trạng thái:** ✅ **HOÀN THÀNH (Completed)** - Triển khai bởi Antigravity

#### 1. Bản chất Vấn đề & Mục tiêu:
- Xây dựng Workflow n8n Cloud tự động tải video từ Google Drive và phân phối đa nền tảng (YouTube Shorts, Facebook Page Reels, Instagram Reels).
- Giải quyết bài toán đa kênh / đa fanpage (Dynamic Multi-Brand Credential Routing) mà không cần cấu hình hàng chục node thủ công trong n8n.

#### 2. Kết quả Triển khai:
- Tạo bộ workflow chuẩn: `n8n_workflows/video_post_master_workflow.json`.
- Tạo node Code JS `n8n_workflows/scripts/parse_candidate_jobs.js`: Tự động ánh xạ `brand_fb_page_id`, `brand_fb_access_token`, `brand_ig_user_id`, `brand_ig_access_token` từ danh sách cấu hình thương hiệu.
- Tạo node định dạng ghi nhận kết quả `n8n_workflows/scripts/format_publish_result.js`.
- Bổ sung tài liệu hướng dẫn `n8n_workflows/README.md` và kiểm thử schema `tests/test_n8n_workflow_schema.py`.

---

### 💡 Task #04: 🛍️ Đưa Sản Phẩm Vào Instagram Từ Link Shopee
- **Dự án:** `Video-Post`
- **Mức độ ưu tiên:** 🟡 Trung bình (P1)
- **Trạng thái:** ⏳ **ĐANG LÊN KẾ HOẠCH (Backlog)**

#### 1. Mục tiêu:
- Tự động trích xuất thông tin sản phẩm từ Shopee link trên Tab Master để đưa vào bài đăng Instagram Reels / Posts.

#### 2. Giải pháp đề xuất:
- Tự động cào/trích xuất thông tin sản phẩm (Tên, hình ảnh, phân loại) từ URL Shopee.
- Tự động tạo link rút gọn / Bio link tương thích với Instagram.
- Hỗ trợ gắn thẻ sản phẩm / sticker liên kết (Link sticker) hoặc caption hướng dẫn mua hàng thẩm mỹ.

---

### 💡 Task #05: ⏰ Tự Động Lên Lịch Đăng TikTok Giờ Vàng (Schedule Posting on TikTok Studio)
- **Dự án:** `Video-Post`
- **Mức độ ưu tiên:** 🟡 Trung bình (P1)
- **Trạng thái:** ⏳ **ĐANG LÊN KẾ HOẠCH (Backlog)**

#### 1. Mục tiêu:
- Tận dụng tính năng Lên lịch đăng (Schedule) trên TikTok Studio để tự động phân bổ bài đăng vào các khung giờ vàng (11:30 - 12:30, 19:30 - 21:00) thay vì xuất bản ngay lập tức.

#### 2. Giải pháp đề xuất:
- Nhận diện bộ chọn ngày và giờ (Date & Time Picker) trên giao diện TikTok Studio.
- Tự động tính toán khung giờ vàng kế tiếp phù hợp cho từng Brand.
- Chọn radio "Schedule" và thiết lập giờ phát tự động qua Playwright.

---

### 💡 Task #06: ✍️ Cá Nhân Hóa Giọng Điệu Prompt AI Theo Từng content_type
- **Dự án:** `Video-Post`
- **Mức độ ưu tiên:** 🟢 Thấp (P2)
- **Trạng thái:** ⏳ **ĐANG LÊN KẾ HOẠCH (Backlog)**

#### 1. Mục tiêu:
- Điều chỉnh Tone of Voice của Google Gemini để viết phong cách bài đăng phù hợp tuyệt đối với từng loại video:
  - `tips_tricks`: Giọng chuyên gia chia sẻ giá trị, câu cú ngắn gọn, checklist rõ ràng, nhắc lưu lại khi cần.
  - `real_product`: Miêu tả cảm giác on-feet thực tế, độ êm, độ bền da bò thật (không lấy giá).
  - `ai_product`: Nhấn mạnh visual hiện đại, thời thượng, bắt trend công nghệ.
  - `real_accessory` / `ai_accessory`: Viết về phong cách phối đồ tinh tế, nâng tầm gu thẩm mỹ.

---

### 💡 Task #07: 🌐 AI Market Intelligence Pipeline: Radar Thời Tiết, Lễ Hội & Xu Hướng Sàn TMĐT
- **Dự án:** `Video-Post`
- **Mức độ ưu tiên:** 🟡 Trung bình (P1)
- **Trạng thái:** ⏳ **ĐANG LÊN KẾ HOẠCH (Backlog)**

#### 1. Mục tiêu:
- Xây dựng cỗ máy tự động hoá thông minh kết hợp với Gemini chạy lịch định kỳ (Daily 6:00 AM & Weekly Thứ Hai) đóng vai trò "trinh sát viên thị trường".
- Tự động thu thập thời tiết, chiến dịch sàn TMĐT (Mega Sale, Flash Sale), lễ hội văn hóa để đề xuất các video đón đầu mùa vụ và tự động cập nhật hạn chót `post_before` khẩn cấp trên Tab `Master`.

---

### 💡 Task #08: 🧠 AI Tự Động Nhận Diện Dịp Lễ / Sự Kiện Để Điền post_before
- **Dự án:** `Video-Post`
- **Mức độ ưu tiên:** 🔴 Cao nhất (Critical P0)
- **Trạng thái:** ✅ **HOÀN THÀNH (Completed)** - Triển khai bởi Antigravity

#### 1. Kết quả Triển khai:
- Đã tích hợp hoàn chỉnh qua module `core/event_detector.py` và cơ sở tri thức 10 năm `config/events_calendar.json`.
- Tự động suy luận ngữ nghĩa (ví dụ: "lồng đèn", "bánh trung thu" -> Tết Trung Thu; "balo tựu trường" -> Khai Giảng...) khi AI biên soạn caption và tự động điền vào Cột E trên Tab `Master`.

---

### 💡 Task #09: 🔗 Gắn Link Tiếp Thị Liên Kết (Shopee / Lazada Affiliate) & Auto First/Pinned Comment
- **Dự án:** `Video-Post`
- **Mức độ ưu tiên:** 🟡 Trung bình (P1)
- **Trạng thái:** ⏳ **ĐÃ LƯU KẾ HOẠCH (Backlog - Sẵn sàng triển khai)**
- **Tài liệu chi tiết:** [Kế hoạch Nghiên cứu & Thiết kế](file:///Users/khan/.gemini/antigravity/brain/d39a12d2-a7ad-4b8b-83a9-8e9025827c64/implementation_plan.md)

#### 1. Bản chất Vấn đề:
- Khi dán link trên điện thoại hoặc trình duyệt web, giao diện ứng dụng tự động phân giải (DeepLink / OpenGraph / Redirect) để tạo **Product Card / Thẻ sản phẩm nổi**.
- Tuy nhiên, khi gửi qua API (Facebook Graph API Reels, YouTube Data API upload), hệ thống chỉ nhận `description` dưới dạng chuỗi text thuần, không tự sinh Product Card và link trong caption YouTube Shorts bị vô hiệu hóa click.

#### 2. Giải pháp kỹ thuật lưu trữ:
- **Auto First Comment & Pin Link**: Ngay sau khi video xuất bản thành công (đã có link bài post trên FB, YT, IG, TT), tự động chạy tác vụ đăng 1 bình luận đầu tiên chứa `shopee_link` / `lazada_link` kèm CTA hấp dẫn và ghim (Pin) lên top 1 (hỗ trợ Facebook Page, YouTube Shorts, TikTok).
- **Playwright Shopping Tag Automation**: Với TikTok Studio Web, bổ sung thao tác click tự động vào ô "Thêm liên kết / Thêm sản phẩm" qua Playwright nếu kênh kích hoạt TikTok Shop Affiliate.

---

### 💡 Task #10: 💬 AI Smart Comment Responder: Tự Động Phản Hồi Bình Luận Dựa Trên Dữ Liệu Video
- **Dự án:** `Video-Post`
- **Mức độ ưu tiên:** 🟡 Trung bình (P1)
- **Trạng thái:** ⏳ **ĐÃ LƯU KẾ HOẠCH (Backlog - Sẵn sàng triển khai)**
- **Tài liệu chi tiết:** [Kế hoạch Nghiên cứu & Thiết kế](file:///Users/khan/.gemini/antigravity/brain/d39a12d2-a7ad-4b8b-83a9-8e9025827c64/implementation_plan.md)

#### 1. Mục tiêu:
- Tận dụng 100% kho dữ liệu video đã có trên Master Google Sheet & SQLite DB (`title`, `content_type`, `shopee_link`, `caption_*`, `brand_*`, URL bài đăng `status_*`) để tự động trả lời bình luận của khán giả một cách thông minh, tự nhiên và kích thích chuyển đổi đơn hàng.

#### 2. Thiết kế Kiến trúc:
- **Module Quét Bình Luận (`connectors/*/comments.py`)**: Lấy danh sách comment mới nhất theo định kỳ từ Facebook Graph API, YouTube Data API, Instagram API và TikTok Playwright.
- **Bộ Não Phân Loại Ý Định & Soạn Thảo Phản Hồi (Gemini 3.5 Flash Lite)**:
  - Khách hỏi giá / mua hàng / xin link $\rightarrow$ Trả lời thân thiện + gửi kèm link mua hàng Shopee/Lazada.
  - Khách hỏi tư vấn size / chất liệu / công dụng $\rightarrow$ Dựa vào caption và tiêu đề để tư vấn chính xác.
  - Khách khen ngợi $\rightarrow$ Cảm ơn duyên dáng, tăng tương tác đẩy xu hướng video.
- **Bộ Chống Trùng Lặp (`comment_history` SQLite)**: Lưu cache ID các bình luận đã xử lý để đảm bảo không bao giờ trả lời trùng lặp.


