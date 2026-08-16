# 💡 NGHIÊN CỨU & NÂNG CẤP KIẾN TRÚC: CHUYỂN TỪ APPS SCRIPT SANG GOOGLE SHEETS API V4 (SERVICE ACCOUNT)

Tài liệu phân tích và đề xuất giải pháp thay thế hoàn toàn Google Apps Script Webhook bằng **Google Sheets API v4 (Service Account)** cho 3 dự án:
1. **Video-Post**
2. **Auto-Video-Factory**
3. **Omni-Video**

---

## 🛑 1. NHỮNG HẠN CHẾ CỦA GOOGLE APPS SCRIPT HIỆN TẠI

1. **Phiền Phức Khi Triển Khai (Redeployment Friction)**:
   - Mỗi lần cập nhật code trong file `google_apps_script.gs`, bạn phải thủ công copy mã ➡️ mở Apps Script ➡️ tạo Bản triển khai mới (New Version) ➡️ Deploy lại.
2. **Giới Hạn Quota & Timeout**:
   - Google Apps Script giới hạn thời gian chạy 6 giây/request (hoặc tối đa 30s), và giới hạn 90 phút/ngày.
3. **Không Đồng Bộ Trực Tiếp (Latency)**:
   - Webhook phải qua nhiều cổng trung gian của Google Cloud, đôi khi bị trễ hoặc chậm.

---

## 🚀 2. GIẢI PHÁP TỐI ƯU THAY THẾ: GOOGLE SHEETS API V4 + SERVICE ACCOUNT

### 💡 Nguyên lý hoạt động:
- Bạn chỉ cần tạo **1 Service Account duy nhất** trên Google Cloud Console (miễn phí 100%, tạo trong 2 phút) và tải file chìa khóa `service_account.json`.
- Chia sẻ file Google Sheet Master cho email của Service Account đó (Ví dụ: `video-post-bot@project.iam.gserviceaccount.com`) với quyền **Người chỉnh sửa (Editor)** đúng 1 lần duy nhất.
- Cả 3 dự án (`Video-Post`, `Auto-Video-Factory`, `Omni-Video`) đều dùng chung file `config/service_account.json` này và sử dụng thư viện Python **`gspread`** hoặc **`google-api-python-client`**.

---

## ⭐ 3. ƯU ĐIỂM VƯỢT TRỘI CỦA GIẢI PHÁP MỚI

1. **TỪ BỎ HOÀN TOÀN GOOGLE APPS SCRIPT**:
   - **Không bao giờ phải copy/paste code hay Deploy Apps Script nữa!**
   - Mọi thay đổi logic cập nhật dữ liệu đều nằm 100% trong code Python của bạn.
2. **TỐC ĐỘ SIÊU TỐC (VÀI TRĂM MILISECOND)**:
   - Python gọi trực tiếp API của Google Sheets để đọc/ghi hàng loạt (`batchUpdate`, `append`, `update_cell`), tô màu, thay đổi định dạng ô cực kỳ nhanh.
3. **DÙNG CHUNG BỘ MÃ CHO CẢ 3 DỰ ÁN**:
   - Cả `Video-Post`, `Auto-Video-Factory`, và `Omni-Video` chỉ cần đọc chung 1 file `service_account.json`.
   - `Auto-Video-Factory` tạo video xong ➡️ tự gọi API ghi thẳng vào Tab `Auto-Video-Factory`.
   - `Omni-Video` quét sản phẩm xong ➡️ tự gọi API ghi thẳng vào Tab `Omni-Video`.
   - `Video-Post` biên soạn AI / đăng bài xong ➡️ tự gọi API cập nhật thẳng vào Tab `Master` và `Status`.

---

## 📋 4. LỘ TRÌNH THỰC HIỆN KHI CHUYỂN ĐỔI

1. **Bước 1**: Tạo Service Account trên Google Cloud Console & Tải file `service_account.json` lưu vào thư mục `config/`.
2. **Bước 2**: Chia sẻ Google Sheet Master cho email Service Account với quyền Editor.
3. **Bước 3**: Viết 1 module Python chuẩn `core/sheet_client.py` dùng chung cho cả 3 project để thay thế hoàn toàn các lệnh gọi Webhook cũ.
