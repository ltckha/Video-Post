# 🚀 n8n Cloud Workflow: Tự Động Xuất Bản Đa Nền Tảng (Video-Post)

Tài liệu hướng dẫn triển khai hệ thống xuất bản video tự động **100% Cloud-First** bằng **n8n Workflow** cho YouTube Shorts, Facebook Reels và Instagram Reels.

---

## 🏗️ 1. Kiến Trúc Luồng Hoạt Động

```text
[Cron Giờ Vàng (11:30 & 19:30) / Webhook]
 ⬇
[Đọc Tab Master trên Google Sheet]
 ⬇
[Lọc video pending có drive_url ➔ Ưu tiên hạn chót <= 3 ngày]
 ⬇
[Tải file MP4 từ Google Drive qua drive_file_id]
 ⬇
 ├── 🔴 Nhánh 1: Đăng YouTube Shorts (Data API v3 Resumable + #Shorts)
 ├── 📘 Nhánh 2: Đăng Facebook Page Reels (Graph API v19.0)
 └── 📸 Nhánh 3: Đăng Instagram Reels (Graph API v19.0 Media Container)
 ⬇
[Cập nhật trạng thái status_yt, status_fb, status_ig lên Google Sheet]
 ⬇
[22:30 Hàng ngày: Spark AI Critic thẩm định video YouTube và chấm điểm /10]
```

---

## 📥 2. Hướng Dẫn Import 1-Click Vào n8n

1. Mở giao diện **n8n** (Cloud hoặc Self-Hosted).
2. Chọn **Workflows** ➔ Bấm nút **Add Workflow** (hoặc dấu `+`).
3. Bấm vào biểu tượng menu **`...`** ở góc trên bên phải ➔ Chọn **Import from File** (hoặc **Import from URL / Clipboard**).
4. Chọn file: [`n8n_workflows/video_post_master_workflow.json`](./video_post_master_workflow.json).
5. n8n sẽ tự động hiển thị toàn bộ sơ đồ các node kết nối hoàn chỉnh.

---

## 🔑 3. Cấu Hình Credentials (Chỉ Cần Làm 1 Lần)

Trong n8n, bạn chỉ cần gán các thông tin xác thực cho các node tương ứng:

### A. Google Sheets & Google Drive
- **Node sử dụng:** `📥 Đọc Tab Master`, `🎬 Tải Video Từ Google Drive`, `💾 Cập Nhật Trạng Thái`.
- **Cách kết nối:** Chọn **Google Service Account** (nạp từ `config/service_account.json`) hoặc **Google OAuth2**.
- **Scopes cần thiết:** `spreadsheets`, `drive.readonly`.

### B. YouTube Data API v3 (YouTube Shorts)
- **Node sử dụng:** `🔴 Xuất Bản YouTube Shorts`.
- **Cách kết nối:** Tạo Credential loại **YouTube OAuth2 API** (sử dụng Client ID và Secret từ Google Cloud Console).
- **Scope:** `https://www.googleapis.com/auth/youtube.upload`.

### C. Meta Graph API (Facebook Page Reels & Instagram Reels)
- **Node sử dụng:** `📘 Xuất Bản Facebook Reels`, `📸 Xuất Bản Instagram Reels`.
- **Cách kết nối:** Sử dụng **Header Auth** hoặc gán biến môi trường `FACEBOOK_PAGE_ACCESS_TOKEN`.
- **Quyền hạn (Permissions) trên Meta App:**
  - `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`
  - `instagram_basic`, `instagram_content_publish`

---

## ⚡ 4. Kiểm Thử & Kích Hoạt (Testing & Activation)

1. **Chạy Thử Nghiệm (Test Step)**:
   - Bấm nút **Test step** ở node `📥 Đọc Tab Master` để n8n lấy dữ liệu thật từ Google Sheet.
   - Bấm **Test workflow** để chạy thử luồng đăng 1 video mẫu.
2. **Kích Hoạt Tự Động (Active)**:
   - Bật công tắc **Active** (chuyển sang màu xanh) ở góc trên bên phải workflow.
   - Từ thời điểm này, n8n sẽ tự động kích hoạt vào lúc **11:30** và **19:30** mỗi ngày để đăng bài mà không cần mở máy tính Mac!
