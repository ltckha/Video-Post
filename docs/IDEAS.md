# 💡 DANH SÁCH Ý TƯỞNG & TÍNH NĂNG PHÁT TRIỂN TIẾP THEO

Tài liệu này lưu trữ các ý tưởng cải tiến hệ thống **Video-Post** được đề xuất bởi người dùng để chuẩn bị cho các đợt cập nhật tiếp theo.

---

## 1. 🛍️ Đưa Sản Phẩm Vào Instagram Từ Link Shopee
- **Mục tiêu**: Tự động hóa việc lấy dữ liệu sản phẩm từ link Shopee trên Tab Master và tích hợp vào nội dung đăng bài Instagram.
- **Giải pháp đề xuất**:
  - Tự động cào/trích xuất thông tin sản phẩm (Tên, giá, hình ảnh, phân loại) từ URL Shopee.
  - Tự động tạo link rút gọn / Bio link tương thích với Instagram.
  - Hỗ trợ gắn thẻ sản phẩm / sticker liên kết (Link sticker) hoặc caption hướng dẫn mua hàng thẩm mỹ trên Instagram Reels / Posts.

---

## 2. ⏰ Tự Động Lên Lịch Đăng TikTok Giờ Vàng (Schedule Posting on TikTok Studio)
- **Mục tiêu**: Tận dụng tính năng Lên lịch đăng (Schedule) trên TikTok Studio để tự động phân bổ bài đăng vào các khung giờ vàng (11:30 - 12:30, 19:30 - 21:00) thay vì xuất bản ngay lập tức.
- **Giải pháp đề xuất**:
  - Nhận diện bộ chọn ngày và giờ (Date & Time Picker) trên giao diện TikTok Studio.
  - Tự động tính toán khung giờ vàng kế tiếp phù hợp cho từng Brand.
  - Chọn radio "Schedule" và thiết lập giờ phát tự động.

---

## 3. 🧠 [ĐÃ HOÀN THÀNH ✅] AI Tự Động Nhận Diện Dịp Lễ / Sự Kiện Để Điền `post_before`
- **Hiện trạng**: Đã tích hợp hoàn chỉnh qua module [`core/event_detector.py`](file:///Users/khan/Developer/Video-Post/core/event_detector.py) và cơ sở tri thức 10 năm [`config/events_calendar.json`](file:///Users/khan/Developer/Video-Post/config/events_calendar.json).
- **Cơ chế**: Tự động suy luận ngữ nghĩa (ví dụ: "lồng đèn", "bánh trung thu" $\rightarrow$ Tết Trung Thu `25/09/2026`; "balo tựu trường" $\rightarrow$ Khai Giảng `05/09/2026`...) khi AI viết lại caption và tự động điền vào Cột D trên Tab `Master`.

---

## 4. ✍️ Cá Nhân Hóa Giọng Điệu Prompt AI Theo Từng `content_type`
- **Mục tiêu**: Điều chỉnh Tone of Voice của Google Gemini để viết phong cách bài đăng phù hợp tuyệt đối với từng loại video:
  - `tips_tricks`: Giọng chuyên gia chia sẻ giá trị, câu cú ngắn gọn, checklist rõ ràng, nhắc lưu lại khi cần, không ép mua hàng.
  - `real_product`: Miêu tả cảm giác on-feet thực tế, độ êm, độ bền, da thật.
  - `ai_product`: Nhấn mạnh visual hiện đại, thời thượng, bắt trend công nghệ.
  - `real_accessory` / `ai_accessory`: Viết về phong cách phối đồ tinh tế, nâng tầm gu thẩm mỹ, quà tặng sang trọng.

---

## 5. 🌐 AI Market Intelligence Pipeline: Tự Động Thu Thập Xu Hướng, Thời Tiết & Sự Kiện Theo Lịch Định Kỳ
- **Mục tiêu**: Xây dựng một cỗ máy tự động hoá thông minh kết hợp với **Gemini** chạy lịch định kỳ (hàng ngày / hàng tuần) đóng vai trò "trinh sát viên thị trường", tự động thu thập tin tức, phân tích và định hướng lịch đăng bài đón đầu nhu cầu mua sắm.
- **Kiến trúc & Cơ chế vận hành**:
  1. **Lịch Chạy Định Kỳ (Scheduled Automation)**:
     - *Hàng ngày (Daily 6:00 AM)*: Cập nhật biến động thời tiết hôm nay (mưa bão, rét đậm, đợt nóng) và các chủ đề hot trend trong 24h.
     - *Hàng tuần (Weekly Sáng Thứ Hai)*: Lập bức tranh toàn cảnh tuần mới (khoảng cách đến ngày Payday 25th, chiến dịch ngày đôi sàn Shopee/TikTok Shop, các ngày lễ văn hóa sắp diễn ra trong 15-30 ngày tới).
  2. **Thu Thập Đa Nguồn (Multi-Source Intelligence)**:
     - *Dự báo thời tiết*: Mưa bão, nắng gắt, không khí lạnh, độ ẩm nồm theo từng vùng miền.
     - *Chiến dịch sàn TMĐT*: Lịch Mega Sale (9.9, 10.10, 11.11, 12.12), Flash Sale, tuần lễ FreeShip.
     - *Hành vi văn hóa & Độ trễ mua sắm (Lead Time)*: Nhận diện thời điểm vàng khách bắt đầu mua online trước ngày lễ 10 - 20 ngày (Trung Thu, Vu Lan, Khai Giảng, Mùa Cưới, Giáng Sinh, Tết).
     - *Tín hiệu mạng xã hội (Social Signals)*: Trend TikTok, nhạc viral, sự kiện giải trí/thể thao.
  3. **Bộ Não Xử Lý & Chắt Lọc Bằng Gemini (Gemini Reasoning)**:
     - Tiếp nhận dữ liệu thô và đối chiếu với danh mục sản phẩm của shop (Giày dép, Đồ da, Phụ kiện, Quà tặng...).
     - Đưa ra khuyến nghị cụ thể: Sản phẩm nào nên được đẩy mạnh ĐĂNG NGAY TRONG TUẦN để chốt đơn kịp thời điểm.
  4. **Lưu Trữ & Kích Hoạt Tự Động (Actionable Data Storage)**:
     - Lưu trữ kết quả phân tích vào Tab `Market_Radar` trên Google Sheet hoặc file tri thức `config/market_intelligence.json`.
     - Tự động gán/điều chỉnh ngày `post_before` ngắn hạn (3 - 5 ngày) cho các video phù hợp trong Tab `Master` để bộ lập lịch `queue_scheduler.py` gắp lên đăng ưu tiên ngay lập tức.

