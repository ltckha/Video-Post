# 💡 Ý TƯỞNG & THIẾT KẾ KIẾN TRÚC: CHROME EXTENSION TỰ ĐỘNG ĐĂNG VIDEO LÊN TIKTOK STUDIO

Tài liệu phân tích giải pháp tự động hóa đăng video lên **TikTok Studio** thông qua **Chrome Extension**, tận dụng phiên đăng nhập (Cookie) có sẵn trên trình duyệt để vượt qua rào cản hạn chế của TikTok API.

---

## 🎯 1. BỐI CẢNH & ĐỘNG LỰC
- **Khó khăn của TikTok API chính thức**: TikTok kiểm duyệt API rất gắt gao, chỉ cấp quyền Direct Post cho các đối tác doanh nghiệp lớn.
- **Thực tế người dùng**: Đã đăng nhập sẵn tài khoản TikTok trên Google Chrome tại `https://www.tiktok.com/creator-center/upload` hoặc `https://www.tiktok.com/tiktokstudio/upload`.
- **Mục tiêu**: Khi mở trình duyệt hoặc chỉ với **1 cú click**, Chrome Extension sẽ tự động lấy bài từ Tab **`Master`** trên Google Sheet, nạp video, điền caption chuẩn AI và bấm Đăng tự động.

---

## 🏗️ 2. QUY TRÌNH HOẠT ĐỘNG (WORKFLOW TỪNG BƯỚC)

```mermaid
graph TD
    GS["📊 Tab Master Google Sheet<br/>(Lấy bài có status_tt = manual_pending)"] -->|Đọc caption_tt & video| EXT["🧩 TikTok Auto-Post Chrome Extension"]
    EXT -->|1. Mở trang upload| TT["🎬 TikTok Studio (creator-center/upload)"]
    EXT -->|2. Tự động nạp video| TT
    EXT -->|3. Tự động điền Caption AI & 5 Hashtags| TT
    EXT -->|4. Tự động bấm nút ĐĂNG (POST)| TT
    TT -->|5. Xác nhận thành công| EXT
    EXT -->|6. Đổi status_tt = published| GS
```

---

## ⭐ 3. CÁC TÍNH NĂNG CHÍNH CỦA EXTENSION:

1. **Tự Động Đọc Dữ Liệu Từ Google Sheet**:
   - Kết nối trực tiếp qua Google Sheets API để lấy danh sách bài cần đăng (`caption_tt`, đường dẫn video, lịch đăng).
2. **Tự Động Điền & Upload (DOM Automation)**:
   - Tự động nạp file video vào khung upload của TikTok Studio.
   - Tự động dán nội dung `caption_tt` (đã được Gemini AI viết chi tiết, giật gân kèm 5 hashtags chuẩn).
   - Tự động thiết lập quyền riêng tư (Công khai, Cho phép Duet / Stitch).
3. **Cơ Chế Chống Quét Bot (Human-like Simulation)**:
   - Giả lập gõ phím và độ trễ ngẫu nhiên giống người thật thao tác để tài khoản luôn an toàn tuyệt đối.
4. **Cập Nhật Hai Chiều**:
   - Sau khi xuất bản xong, tự động cập nhật `status_tt` thành `published` trên Tab `Master`.

---

## 📋 4. ĐỀ XUẤT LỘ TRÌNH THỰC HIỆN:
- **Bước 1**: Xây dựng khung Extension (Manifest V3 + Popup quản lý hàng đợi TikTok).
- **Bước 2**: Viết Content Script tự động nhận diện và tương tác với các thành phần trên trang TikTok Creator Center.
- **Bước 3**: Thử nghiệm đăng 1 video mẫu để kiểm tra tính ổn định.
