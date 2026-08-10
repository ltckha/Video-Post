#!/usr/bin/env bash

# Navigate to project directory
cd "$(dirname "$0")" || exit 1

PYTHON_BIN="./venv/bin/python"

if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

while true; do
    clear
    echo "=================================================="
    echo "  🚀 VIDEO-POST: BỘ CÔNG CỤ TỰ ĐỘNG ĐĂNG VIDEO 🚀"
    echo "=================================================="
    echo " 1) ĐĂNG THẬT (Chọn kênh: Facebook / YouTube / Instagram)"
    echo " 2) Nhờ AI viết lại các bài cần chỉnh sửa (rewrite-needs-edit)"
    echo " 3) Đăng bù các bài bị lỗi (retry-partial)"
    echo " 4) Thêm Tab đầu vào mới trên Master Sheet (add-tab)"
    echo " 5) Đồng bộ tất cả Tab Đầu Vào & AI Biên Soạn (sync-all-sources)"
    echo " 0) Thoát"
    echo "=================================================="
    read -rp "👉 Vui lòng chọn (0-5): " choice

    case $choice in
        1)
            echo ""
            echo "--- ĐĂNG THẬT BÀI VIẾT ---"
            echo "Chọn nền tảng bạn muốn đăng:"
            echo " 1) Facebook Reels"
            echo " 2) YouTube Shorts"
            echo " 3) Instagram Reels"
            echo " 4) Tất cả các kênh tự động (FB, YT, IG)"
            read -rp "👉 Chọn nền tảng (1-4): " p_choice
            
            PLATFORM="all"
            case $p_choice in
                1) PLATFORM="facebook" ;;
                2) PLATFORM="youtube" ;;
                3) PLATFORM="instagram" ;;
                4) PLATFORM="all" ;;
                *) PLATFORM="all" ;;
            esac
            
            $PYTHON_BIN main.py process-queue --platform "$PLATFORM" --limit 1
            echo ""
            read -rp "Nhấn Enter để quay lại menu..."
            ;;
        2)
            echo ""
            echo "--- NHỜ AI VIẾT LẠI CÁC BÀI CẦN CHỈNH SỬA ---"
            $PYTHON_BIN main.py rewrite-needs-edit
            echo ""
            read -rp "Nhấn Enter để quay lại menu..."
            ;;
        3)
            echo ""
            echo "--- ĐĂNG BÙ CÁC NỀN TẢNG BỊ LỖI ---"
            $PYTHON_BIN main.py retry-partial --limit 1
            echo ""
            read -rp "Nhấn Enter để quay lại menu..."
            ;;
        4)
            echo ""
            echo "--- THÊM TAB ĐẦU VÀO MỚI TRÊN MASTER SHEET ---"
            $PYTHON_BIN main.py add-tab
            echo ""
            read -rp "Nhấn Enter để quay lại menu..."
            ;;
        5)
            echo ""
            echo "--- ĐỒNG BỘ & AI BIÊN SOẠN ---"
            $PYTHON_BIN main.py sync-all-sources
            echo ""
            read -rp "Nhấn Enter để quay lại menu..."
            ;;
        0)
            echo "Cảm ơn bạn đã sử dụng Video-Post! Tạm biệt! 👋"
            exit 0
            ;;
        *)
            echo "Lựa chọn không hợp lệ! Vui lòng nhập từ 0 đến 5."
            sleep 1
            ;;
    esac
done
