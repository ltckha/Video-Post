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

## 2. 🛡️ Tối Ưu Hóa Hành Vi Đăng Bài TikTok Giống Người Thật (Anti-Bot / Stealth Posting)
- **Mục tiêu**: Nâng cấp module Playwright trong [`connectors/tiktok/browser_uploader.py`](file:///Users/khan/Developer/Video-Post/connectors/tiktok/browser_uploader.py) để mô phỏng 100% thao tác người thật, giảm thiểu tối đa rủi ro bị TikTok phát hiện và bóp tương tác hoặc chặn tài khoản.
- **Giải pháp đề xuất**:
  - **Mô phỏng di chuyển chuột tự nhiên (Bezier Curve Mouse Movements)**: Không nhảy tọa độ tức thì mà di chuyển chuột có quán tính, độ cong và rung nhẹ (jitter) giống tay người.
  - **Hành vi xem trang trước khi tải (Pre-upload Browsing)**: Khi vừa mở TikTok Studio, cuộn trang lên xuống nhẹ nhàng, dừng 1-3 giây như đang đọc thông tin trước khi chọn tải video.
  - **Gõ phím ngẫu nhiên & ngắt nghỉ tự nhiên (Human Typing Dynamics)**:
    - Thay đổi độ trễ giữa các phím ngẫu nhiên (15ms - 120ms).
    - Thỉnh thoảng gõ nhầm 1 ký tự và bấm Backspace sửa lại để tăng tính tự nhiên.
  - **Giãn cách thời gian chờ tự nhiên trước khi bấm Đăng (Human Delay)**: Sau khi tải và điền caption xong, dừng xem trước 3-7 giây rồi mới rê chuột đến nút Đăng và click.
  - **Ngẫu nhiên hóa Viewport & Window Position**: Tránh việc mọi phiên chạy đều có kích thước cửa sổ cố định.
