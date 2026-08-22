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
    echo " 1) 🚀 ĐĂNG TỰ ĐỘNG 1-CLICK (Đăng ngay các kênh đã sẵn sàng)"
    echo " 2) Đăng thủ công theo kênh (Facebook / YouTube / Instagram / TikTok)"
    echo " 3) Nhờ AI viết lại các bài cần chỉnh sửa (rewrite-needs-edit)"
    echo " 4) Thêm Tab đầu vào mới trên Master Sheet (add-tab)"
    echo " 5) Đồng bộ tất cả Tab Đầu Vào & AI Biên Soạn (sync-all-sources)"
    echo " 6) Nạp Cookie TikTok từ file JSON Cookie-Editor (tiktok-import-cookies)"
    echo " 0) Thoát"
    echo "=================================================="
    read -rp "👉 Vui lòng chọn (0-6): " choice

    case $choice in
        1)
            echo ""
            echo "--- 🚀 ĐĂNG TỰ ĐỘNG 1-CLICK (CÁC KÊNH ĐÃ SẴN SÀNG) ---"
            $PYTHON_BIN main.py auto-post-active
            echo ""
            read -rp "Nhấn Enter để quay lại menu..."
            ;;
        2)
            echo ""
            echo "--- ĐĂNG THỦ CÔNG THEO NỀN TẢNG ---"
            echo "Chọn nền tảng bạn muốn đăng:"
            echo " 1) Facebook Reels"
            echo " 2) YouTube Shorts"
            echo " 3) Instagram Reels"
            echo " 4) TikTok Studio (Playwright Browser)"
            echo " 5) Đăng tự động tất cả các kênh sẵn sàng (1-Click)"
            read -rp "👉 Chọn nền tảng (1-5): " p_choice
            
            PLATFORM="all"
            case $p_choice in
                1) PLATFORM="facebook" ;;
                2) PLATFORM="youtube" ;;
                3) PLATFORM="instagram" ;;
                4) PLATFORM="tiktok" ;;
                5) PLATFORM="all" ;;
                *) PLATFORM="all" ;;
            esac
            
            if [ "$PLATFORM" == "tiktok" ]; then
                eval $($PYTHON_BIN -c "
import json
data = json.load(open('config/tiktok_accounts.json'))
accs = data.get('accounts', {})
for k, var in [
    ('Hiệu giày Hải Nancy', 'ST_HAINANCY'),
    ('Mua Chuẩn Xài Lâu', 'ST_MUACHUAN'),
    ('Macadamia Hải Nancy', 'ST_MACADAMIA'),
    ('Ờ Đà Lạt vậy thôi', 'ST_DALAT'),
    ('Yen Handmade Leather', 'ST_YEN'),
    ('YenYen Deals', 'ST_YENYEN'),
    ('Elegant Steps', 'ST_ELEGANT')
]:
    is_act = accs.get(k, {}).get('status') == 'active'
    print(f'{var}=\"(' + ('✅ Đã nạp Cookie' if is_act else '⚠️ Chưa nạp Cookie') + ')\"')
")
                echo ""
                echo "=================================================="
                echo "  🎬 ĐĂNG BÀI TIKTOK (CHỌN THƯƠNG HIỆU / BRAND)"
                echo "=================================================="
                echo " 1) Hiệu giày Hải Nancy $ST_HAINANCY"
                echo " 2) Mua Chuẩn Xài Lâu $ST_MUACHUAN"
                echo " 3) Macadamia Hải Nancy $ST_MACADAMIA"
                echo " 4) Ờ Đà Lạt vậy thôi $ST_DALAT"
                echo " 5) Yen Handmade Leather $ST_YEN"
                echo " 6) YenYen Deals $ST_YENYEN"
                echo " 7) Elegant Steps $ST_ELEGANT"
                echo " 0) Quay lại Menu chính"
                echo "=================================================="
                read -rp "👉 Chọn Brand muốn đăng TikTok (0-7): " tt_post_choice

                case $tt_post_choice in
                    1) target_tt_brand="Hiệu giày Hải Nancy" ;;
                    2) target_tt_brand="Mua Chuẩn Xài Lâu" ;;
                    3) target_tt_brand="Macadamia Hải Nancy" ;;
                    4) target_tt_brand="Ờ Đà Lạt vậy thôi" ;;
                    5) target_tt_brand="Yen Handmade Leather" ;;
                    6) target_tt_brand="YenYen Deals" ;;
                    7) target_tt_brand="Elegant Steps" ;;
                    0) continue ;;
                    *) target_tt_brand="Hiệu giày Hải Nancy" ;;
                esac

                $PYTHON_BIN main.py tiktok-post --brand "$target_tt_brand"
            elif [ "$PLATFORM" == "all" ]; then
                $PYTHON_BIN main.py auto-post-active
            else
                $PYTHON_BIN main.py process-queue --platform "$PLATFORM" --limit 1
            fi
            echo ""
            read -rp "Nhấn Enter để quay lại menu..."
            ;;
        3)
            echo ""
            echo "--- NHỜ AI VIẾT LẠI CÁC BÀI CẦN CHỈNH SỬA ---"
            $PYTHON_BIN main.py rewrite-needs-edit
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
        6)
            eval $($PYTHON_BIN -c "
import json
data = json.load(open('config/tiktok_accounts.json'))
accs = data.get('accounts', {})
for k, var in [
    ('Hiệu giày Hải Nancy', 'ST_HAINANCY'),
    ('Mua Chuẩn Xài Lâu', 'ST_MUACHUAN'),
    ('Macadamia Hải Nancy', 'ST_MACADAMIA'),
    ('Ờ Đà Lạt vậy thôi', 'ST_DALAT'),
    ('Yen Handmade Leather', 'ST_YEN'),
    ('YenYen Deals', 'ST_YENYEN'),
    ('Elegant Steps', 'ST_ELEGANT')
]:
    is_act = accs.get(k, {}).get('status') == 'active'
    print(f'{var}=\"(' + ('✅ Đã nạp Cookie' if is_act else '⚠️ Chưa nạp Cookie') + ')\"')
")
            echo ""
            echo "=================================================="
            echo "  🍪 NẠP COOKIE TIKTOK CHO BRAND (TỪ FILE JSON)"
            echo "=================================================="
            echo " 1) Hiệu giày Hải Nancy $ST_HAINANCY"
            echo " 2) Mua Chuẩn Xài Lâu $ST_MUACHUAN"
            echo " 3) Macadamia Hải Nancy $ST_MACADAMIA"
            echo " 4) Ờ Đà Lạt vậy thôi $ST_DALAT"
            echo " 5) Yen Handmade Leather $ST_YEN"
            echo " 6) YenYen Deals $ST_YENYEN"
            echo " 7) Elegant Steps $ST_ELEGANT"
            echo " 0) Quay lại Menu chính"
            echo "=================================================="
            read -rp "👉 Chọn tài khoản Brand (0-7): " tt_brand_choice

            case $tt_brand_choice in
                1) target_brand="Hiệu giày Hải Nancy" ;;
                2) target_brand="Mua Chuẩn Xài Lâu" ;;
                3) target_brand="Macadamia Hải Nancy" ;;
                4) target_brand="Ờ Đà Lạt vậy thôi" ;;
                5) target_brand="Yen Handmade Leather" ;;
                6) target_brand="YenYen Deals" ;;
                7) target_brand="Elegant Steps" ;;
                0) continue ;;
                *) target_brand="Hiệu giày Hải Nancy" ;;
            esac

            echo ""
            echo "👉 Kéo-thả file JSON xuất từ Cookie-Editor vào đây (hoặc nhập đường dẫn):"
            read -rp "📁 Đường dẫn file Cookie JSON: " raw_cookie_file
            # Strip outer quotes and spaces
            cookie_file=$(echo "$raw_cookie_file" | sed "s/^['\"]//;s/['\"]$//" | xargs)

            if [ -z "$cookie_file" ]; then
                echo "⚠️ Bạn chưa nhập đường dẫn file cookie!"
            else
                $PYTHON_BIN main.py tiktok-import-cookies --brand "$target_brand" --cookies-file "$cookie_file"
            fi
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
