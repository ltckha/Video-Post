# Tài Liệu Ý Tưởng: Các Phương Án Tự Động Hẹn Giờ Đăng Bài (Dành Cho Phát Triển Sau)

Tài liệu này lưu trữ 2 phương án thiết kế cho hệ thống **Tự Động Hẹn Giờ Đăng Bài (Auto Scheduler)** để phát triển trong tương lai.

---

## 📌 PHƯƠNG ÁN 1: Hẹn Giờ Thủ Công Theo Khung Giờ Trên Tab `Status`

### 💡 Mô tả:
- Người dùng tự gõ các khung giờ mong muốn (dạng `08:30, 13:00, 20:00`) vào cột E đến J trên Tab **`Status`** cho từng Brand.
- Trình lập lịch chạy ngầm (`VideoScheduler`) quét Tab `Status` mỗi 1 phút:
  - Khi giờ hệ thống chạm mốc hẹn giờ của Brand X trên Nền tảng Y ➡️ Đọc Tab **`Master`**.
  - Lọc bài `status = 'pending'` của Brand X ➡️ Rút ngẫu nhiên 1 bài (`random.choice`).
  - Đăng bài ➡️ Cập nhật `status = 'published'` trực tiếp trên Google Sheet qua Webhook.

---

## 📌 PHƯƠNG ÁN 2: Tự Động Sinh Lịch Ngẫu Nhiên Phân Bổ Rải Đều (Random Smart Scheduler)

### 💡 Mô tả:
- Người dùng **không cần gõ giờ thủ công**.
- Vào đầu mỗi ngày (00:00) hoặc khi Trình lập lịch khởi động, hệ thống **tự động tính toán & sinh lịch ngẫu nhiên**:
  - Đảm bảo **mỗi Kênh/Brand có đúng 1 bài đăng / ngày**.
  - Giờ đăng phân bổ ngẫu nhiên trong Khung giờ vàng (**08:00 - 22:00**).
  - Khoảng cách tối thiểu giữa 2 bài đăng của các kênh khác nhau là **30 - 45 phút** (Tuyệt đối không bị trùng giờ hay dồn dập).
- Tự động điền các mốc giờ ngẫu nhiên đã tạo lên Tab `Status` để người dùng dễ dàng theo dõi trên Google Sheet.

---

## 📝 Trạng Thái Hiện Tại:
- **Đã lưu trữ thành ý tưởng (Ideas Backlog)**.
- Hệ thống hiện tại đang sử dụng chế độ **Đăng bài linh hoạt chọn Kênh & Brand trực tiếp (Phím 1)** hoạt động cực kỳ mượt mà và chuẩn xác.
