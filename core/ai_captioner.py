"""Google Gemini 3.1 Flash Lite API Social Media Caption Generator Module.

Uses Google Gemini 3.1 Flash Lite API to generate viral, high-converting social copy 
for 6 platforms (Facebook, YouTube, Instagram, TikTok, Shopee, Zalo):
- NO CTA (Call to action phrases) included in any caption.
- Shopee: STRICTLY < 150 characters TOTAL including 3 fixed tags (#shopeevideo #luotvuimualien #shopeecreator) 
  + 1 category tag (#videohangthoitrang, #videohanglamdep, etc.).
- Zalo: Includes 3-5 hashtags (same format as Facebook).
- YouTube Shorts: Link & key product info in top 2 lines + #Shorts.
- Instagram: Aesthetic post + 10-15 quality hashtags.
"""

import os
import re
import json
import time
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional

from config import settings

logger = logging.getLogger(__name__)

# Track daily API request count in-memory
DAILY_API_REQUEST_COUNT = 0


class AICaptionGenerator:
    """Generates social media captions for 6 platforms using Google Gemini 3.1 Flash Lite API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
        self.model_name = getattr(settings, "GEMINI_MODEL", "gemini-3.1-flash-lite")
        self.rpm_delay = getattr(settings, "GEMINI_RPM_DELAY", 4)
        self.max_rpd = getattr(settings, "GEMINI_MAX_RPD", 500)

    def detect_shopee_category(self, title: str, raw_caption: str) -> str:
        """Detect best matching category hashtag for Shopee."""
        text = f"{title} {raw_caption}".lower()
        if any(w in text for w in ["dép", "sục", "giày", "túi", "áo", "quần", "váy", "thời trang", "guốc"]):
            return "#videohangthoitrang"
        elif any(w in text for w in ["kem", "son", "mỹ phẩm", "da", "nước hoa", "làm đẹp", "skincare"]):
            return "#videohanglamdep"
        elif any(w in text for w in ["điện thoại", "tai nghe", "đèn", "led", "sạc", "máy"]):
            return "#videohangdientu"
        elif any(w in text for w in ["bút", "sách", "vở", "màu", "marker", "văn phòng phẩm"]):
            return "#videohangvanphongpham"
        elif any(w in text for w in ["nhà cửa", "bếp", "nội thất", "trang trí", "decor"]):
            return "#videohangnhacua"
        else:
            return "#videohangtieudung"

    def clean_cta(self, text: str) -> str:
        """Remove any unwanted Call-To-Action (CTA) phrases from generated copy."""
        clean = text.strip()
        cta_patterns = [
            r"(?i)sắm ngay tại đây.*",
            r"(?i)link mua.*bio.*",
            r"(?i)bấm vào giỏ hàng.*",
            r"(?i)click link.*",
            r"(?i)liên hệ ngay.*",
            r"(?i)mua ngay tại.*",
            r"(?i)đặt hàng ngay.*",
        ]
        for pattern in cta_patterns:
            clean = re.sub(pattern, "", clean).strip()
        return clean

    def generate_all_captions(
        self,
        title: str,
        raw_caption: str = "",
        affiliate_link: str = "",
        style_prompt: str = "",
        current_captions: str = "",
        product_usp: str = "",
        target_audience: str = "",
        brand_tone: str = "",
    ) -> Dict[str, str]:
        """Generate tailored captions for 6 platforms via Gemini API (or rule-based fallback)."""
        global DAILY_API_REQUEST_COUNT
        cat_tag = self.detect_shopee_category(title, raw_caption)

        if self.api_key and DAILY_API_REQUEST_COUNT < self.max_rpd:
            try:
                captions = self._call_gemini_api(
                    title=title,
                    raw_caption=raw_caption,
                    affiliate_link=affiliate_link,
                    cat_tag=cat_tag,
                    style_prompt=style_prompt,
                    current_captions=current_captions,
                    product_usp=product_usp,
                    target_audience=target_audience,
                    brand_tone=brand_tone,
                )
                if captions and len(captions) >= 6:
                    DAILY_API_REQUEST_COUNT += 1
                    logger.info(
                        f"Successfully generated captions via Gemini API ({self.model_name})! (Daily API count: {DAILY_API_REQUEST_COUNT}/{self.max_rpd})"
                    )
                    # Respect RPM rate limit by sleeping specified seconds (default 4s)
                    if self.rpm_delay > 0:
                        time.sleep(self.rpm_delay)

                    # Prioritize Gemini's deep reasoning for post_before, fallback to calendar detector
                    pb_gemini = str(captions.get("post_before", "")).strip()
                    ev_gemini = str(captions.get("detected_event", "")).strip()

                    if pb_gemini:
                        captions["post_before"] = pb_gemini
                        captions["detected_event"] = ev_gemini
                    else:
                        from core.event_detector import detect_event_deadline
                        detected = detect_event_deadline(title=title, description=raw_caption)
                        if detected:
                            event_name, deadline_str = detected
                            captions["post_before"] = deadline_str
                            captions["detected_event"] = event_name

                    return captions
            except Exception as e:
                logger.warning(f"Gemini API call failed, falling back to rule-based generation: {e}")

        # Rule-based fallback if API key not set or limit reached or error occurs
        fallback_captions = self._generate_fallback_captions(title, raw_caption, affiliate_link, cat_tag)
        from core.event_detector import detect_event_deadline
        detected = detect_event_deadline(title=title, description=raw_caption)
        if detected:
            event_name, deadline_str = detected
            fallback_captions["post_before"] = deadline_str
            fallback_captions["detected_event"] = event_name
        return fallback_captions


    def generate_tiktok_caption(
        self,
        title: str,
        raw_caption: str = "",
        brand_name: str = "",
        product_usp: str = "",
        target_audience: str = "",
        brand_tone: str = "",
    ) -> str:
        """Generate a single, deeply engaging Storytelling caption exclusively for TikTok."""
        global DAILY_API_REQUEST_COUNT
        if self.api_key and DAILY_API_REQUEST_COUNT < self.max_rpd:
            prompt = f"""
Bạn là chuyên gia sáng tạo nội dung video ngắn và Storytelling hàng đầu trên TikTok Việt Nam.
Hãy viết DUY NHẤT 1 bài viết TikTok thật dài, sâu sắc, giàu chi tiết, nghệ thuật và cuốn hút cho sản phẩm dưới đây:

Tên sản phẩm: {title}
Mô tả/Bối cảnh: {raw_caption}
Thương hiệu: {brand_name}
"""
            if product_usp:
                prompt += f"Điểm nổi bật / USP: {product_usp}\n"
            if target_audience:
                prompt += f"Đối tượng mục tiêu: {target_audience}\n"
            if brand_tone:
                prompt += f"Tone giọng: {brand_tone}\n"

            prompt += """
QUY TẮC BẮT BUỘC:
1. TUYỆT ĐỐI KHÔNG thêm bất kỳ câu Kêu Gọi Mua Hàng / CTA nào (NHƯ: "Mua ngay tại...", "Bấm vào link...", "Sắm ngay...", "Link bio..."). Trong video đã có CTA rồi.
2. TUYỆT ĐỐI KHÔNG nhắc tên các nền tảng khác như Shopee, Facebook, Lazada, v.v.
3. BẮT BUỘC VIẾT THEO ĐÚNG VĂN PHONG VÀ BỐ CỤC BÀI MẪU TIÊU CHUẨN SAU ĐÂY:

--- BÀI MẪU TIÊU CHUẨN TIKTOK (HÃY HỌC TẬP CHÍNH XÁC PHONG CÁCH NÀY CHO SẢN PHẨM HIỆN TẠI) ---
“Một đôi giày cổ điển xứng đáng có thêm một hành trình mới.” 👞✨

Đôi giày Brogue này đã bạc màu theo thời gian, nhưng chất da vẫn còn rất tốt. Thay vì thay mới, mình lựa chọn phục hồi bằng phương pháp nhuộm thủ công.

✔ Làm sạch và xử lý bề mặt da
✔ Pha màu phù hợp với màu gốc
✔ Nhuộm từng lớp mỏng để màu lên tự nhiên
✔ Hoàn thiện giúp đôi giày lấy lại vẻ lịch lãm

💡 Mỗi công đoạn đều cần sự kiên nhẫn và tỉ mỉ. Chính điều đó tạo nên thành phẩm có chiều sâu, giữ được nét đẹp cổ điển của da thật thay vì một lớp sơn dày che phủ.

Xem hết video để theo dõi hành trình hồi sinh của đôi giày Brogue từ cũ kỹ đến chỉn chu như mới nhé! 🔥

#phuchoigiay #giayda #brogue #customgiay #leathercare
--- HẾT BÀI MẪU ---

Chỉ trả về trực tiếp nội dung bài viết TikTok (Không bọc trong JSON, không thêm lời chào hay giải thích gì khác).
"""
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1500},
            }

            models_to_try = [self.model_name, "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.7-flash"]
            seen_models = set()
            unique_models = [m for m in models_to_try if m and not (m in seen_models or seen_models.add(m))]

            for model in unique_models:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                url = f"{endpoint}?key={self.api_key}"
                try:
                    res = requests.post(url, headers=headers, json=payload, timeout=20)
                    if res.status_code == 200:
                        data = res.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            text_response = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                            if text_response:
                                DAILY_API_REQUEST_COUNT += 1
                                logger.info(f"Successfully generated TikTok caption via Gemini API ({model})! (Daily API count: {DAILY_API_REQUEST_COUNT}/{self.max_rpd})")
                                if self.rpm_delay > 0:
                                    time.sleep(self.rpm_delay)
                                return self.clean_cta(text_response)
                except Exception as e:
                    logger.warning(f"Gemini model '{model}' failed for TikTok: {e}. Trying next...")

        # Fallback if API fails
        return self._generate_fallback_captions(title, raw_caption, "", "#videohangthoitrang")["tiktok"]


    def _call_gemini_api(
        self,
        title: str,
        raw_caption: str,
        affiliate_link: str,
        cat_tag: str,
        style_prompt: str = "",
        current_captions: str = "",
        product_usp: str = "",
        target_audience: str = "",
        brand_tone: str = "",
    ) -> Optional[Dict[str, str]]:
        """Call Google Gemini API with model gemini-3.1-flash-lite or configured model."""
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
        url = f"{endpoint}?key={self.api_key}"

        prompt = f"""
Bạn là chuyên gia sáng tạo nội dung mạng xã hội E-Commerce hàng đầu Việt Nam.
Hãy viết bài cho 6 nền tảng xã hội dựa trên thông tin sản phẩm dưới đây:

Tiêu đề/Tên sản phẩm: {title}
Mô tả gốc: {raw_caption}
Link sản phẩm: {affiliate_link}
Hashtag ngành hàng Shopee: {cat_tag}
"""
        if product_usp:
            prompt += f"Điểm nổi bật / USP sản phẩm: {product_usp}\n"
        if target_audience:
            prompt += f"Đối tượng mục tiêu (Target Audience): {target_audience}\n"
        if brand_tone:
            prompt += f"Tone giọng thương hiệu: {brand_tone}\n"

        if current_captions and style_prompt:
            prompt += f"""
ĐÂY LÀ BẢN NHÁP CŨ DO BẠN VIẾT:
{current_captions}

YÊU CẦU ĐẶC BIỆT LẦN NÀY: Khách hàng chưa hài lòng với bản nháp cũ. {style_prompt}
"""

        today_str = datetime.now().strftime("%d/%m/%Y")
        prompt += f"""
QUY TẮC BẮT BUỘC:
1. KHÔNG thêm bất kỳ câu Kêu Gọi Mua Hàng / CTA nào (NHƯ: "Mua ngay tại...", "Bấm vào link...", "Sắm ngay...", "Link bio..."). Trong video đã có CTA rồi.
2. TUYỆT ĐỐI KHÔNG nhắc tên nền tảng chéo nhau (VD: Đang viết cho TikTok thì KHÔNG được nhắc từ "Shopee", "Facebook"...).
3. CẤU TRÚC BÀI VIẾT CHO TỪNG KÊNH:
   - "facebook": Bài viết Facebook hay, mô tả đặc tính + 3-5 hashtags.
   - "youtube": Bài viết YouTube Shorts (2 dòng đầu có tên SP, tuyệt đối KHÔNG chứa link sản phẩm, có #Shorts + 3 hashtags).
   - "instagram": Bài viết Instagram phong cách thẩm mỹ + 10-15 hashtags hot.
   - "tiktok": BẮT BUỘC VIẾT DÀI, GIÀU CHI TIẾT, NGHỆ THUẬT VÀ CUỐN HÚT CHÍNH XÁC THEO VĂN PHONG VÀ BỐ CỤC BÀI MẪU SAU ĐÂY:
     
     --- BÀI MẪU TIÊU CHUẨN TIKTOK (HÃY HỌC TẬP CHÍNH XÁC PHONG CÁCH NÀY CHO SẢN PHẨM HIỆN TẠI) ---
     “Một đôi giày cổ điển xứng đáng có thêm một hành trình mới.” 👞✨

     Đôi giày Brogue này đã bạc màu theo thời gian, nhưng chất da vẫn còn rất tốt. Thay vì thay mới, mình lựa chọn phục hồi bằng phương pháp nhuộm thủ công.

     ✔ Làm sạch và xử lý bề mặt da
     ✔ Pha màu phù hợp với màu gốc
     ✔ Nhuộm từng lớp mỏng để màu lên tự nhiên
     ✔ Hoàn thiện giúp đôi giày lấy lại vẻ lịch lãm

     💡 Mỗi công đoạn đều cần sự kiên nhẫn và tỉ mỉ. Chính điều đó tạo nên thành phẩm có chiều sâu, giữ được nét đẹp cổ điển của da thật thay vì một lớp sơn dày che phủ.

     Xem hết video để theo dõi hành trình hồi sinh của đôi giày Brogue từ cũ kỹ đến chỉn chu như mới nhé! 🔥

     #phuchoigiay #giayda #brogue #customgiay #leathercare
     --- HẾT BÀI MẪU ---

    - "shopee": TỔNG ĐỘ DÀI TOÀN BỘ BÀI VIẾT KỂ CẢ HASHTAG PHẢI DƯỚI 150 KÝ TỰ (< 150 chars total). Bắt buộc chứa 4 tags này ở cuối: #shopeevideo #luotvuimualien #shopeecreator {cat_tag}.
    - "zalo": Bài viết Zalo bán hàng + 3-5 hashtags (giống Facebook).

4. PHÂN TÍCH HẠN CHÓT MÙA VỤ & SỰ KIỆN (post_before):
   - Mốc thời gian thực tế: HÔM NAY LÀ NGÀY {today_str}.
   - QUY TẮC CỬA SỔ THỜI GIAN (TIME HORIZON):
     + CHỈ được gán hạn chót "post_before" nếu sự kiện hoặc chiến dịch diễn ra TRONG VÒNG 30 ĐẾN TỐI ĐA 60 NGÀY TỚI kể từ hôm nay ({today_str})!
     + TUYỆT ĐỐI KHÔNG gán sự kiện cách xa trên 60 ngày (Ví dụ: Đang tháng 9 mà gán tận Tết Nguyên Đán năm sau là SAI, vì sẽ làm video bị xếp vào độ ưu tiên thấp nhất và bị giam không được đăng trong suốt các tháng tới).
     + Ngoại lệ duy nhất được gán xa là các sản phẩm độc quyền chỉ dùng được đúng duy nhất cho ngày đó (như Bánh chưng Tết, Phong bao lì xì, Cây thông Noel).
   - QUY TẮC SẢN PHẨM QUANH NĂM / ĐA DỤNG:
     + Các sản phẩm bán quanh năm (như túi du lịch, giày dép, ví da, phụ kiện thông thường, đồ gia dụng...):
       * Nếu sản phẩm có công năng đón đầu thời tiết hiện tại (như chống thấm nước, bọc đi mưa, sấy giày trong mùa mưa bão hiện tại): Có thể gán hạn chót ngắn hạn trong tháng (từ 7 - 14 ngày tới).
       * Nếu là sản phẩm quanh năm bình thường: BẮT BUỘC ĐỂ TRỐNG "post_before": "" và "detected_event": "" để hệ thống tự động phân bổ đều đặn!
   - Nếu đủ điều kiện gán: Tính "post_before" theo định dạng "DD/MM/YYYY" trước sự kiện 7 - 15 ngày để kịp giao hàng, và điền lý do vào "detected_event".

TRẢ VỀ CHỈ DUY NHẤT 1 OBJECT JSON HỢP LỆ (KHÔNG THÊM CÂU TỪ NÀO KHÁC):
{{
  "post_before": "DD/MM/YYYY hoặc để trống nếu bán quanh năm",
  "detected_event": "Tên sự kiện/ngữ cảnh phát hiện hoặc để trống",
  "facebook": "...",
  "youtube": "...",
  "instagram": "...",
  "tiktok": "...",
  "shopee": "...",
  "zalo": "..."
}}
"""
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 3000},
        }

        models_to_try = [self.model_name, "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.7-flash"]
        seen_models = set()
        unique_models = [m for m in models_to_try if m and not (m in seen_models or seen_models.add(m))]

        for model in unique_models:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            url = f"{endpoint}?key={self.api_key}"
            try:
                res = requests.post(url, headers=headers, json=payload, timeout=20)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text_response = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        json_match = re.search(r"\{.*\}", text_response, re.DOTALL)
                        if json_match:
                            result = json.loads(json_match.group(0))
                            if "shopee" in result and len(result["shopee"]) > 150:
                                shopee_tags = f"#shopeevideo #luotvuimualien #shopeecreator {cat_tag}"
                                result["shopee"] = f"{title[:80]} {shopee_tags}"[:150]
                            cleaned = {}
                            for k, v in result.items():
                                if k in ["post_before", "detected_event"]:
                                    cleaned[k] = str(v).strip()
                                else:
                                    cleaned[k] = self.clean_cta(str(v))

                            # Safety check: Do not allow general products to be scheduled > 60 days in future
                            pb_val = cleaned.get("post_before", "")
                            if pb_val:
                                from core.market_intel import parse_date_safely
                                dt = parse_date_safely(pb_val)
                                if dt:
                                    delta_days = (dt - datetime.now()).days
                                    exclusive_keywords = ["bánh chưng", "lì xì", "cây thông noel", "ông già noel", "lồng đèn", "bánh trung thu"]
                                    is_exclusive = any(kw in title.lower() for kw in exclusive_keywords)
                                    if delta_days > 60 and not is_exclusive:
                                        logger.info(f"Clearing post_before '{pb_val}' for '{title}' because deadline is too far in future ({delta_days} days) for a general product.")
                                        cleaned["post_before"] = ""
                                        cleaned["detected_event"] = ""

                            return cleaned
                else:
                    logger.warning(f"Gemini API model '{model}' trả về status HTTP {res.status_code}: {res.text}. Thử model kế tiếp...")


            except Exception as e:
                logger.warning(f"Gemini API model '{model}' gặp ngoại lệ: {e}. Thử model kế tiếp...")

        return None

    def _generate_fallback_captions(
        self,
        title: str,
        raw_caption: str,
        affiliate_link: str,
        cat_tag: str,
    ) -> Dict[str, str]:
        """Structured rule-based generator used when API is unavailable."""
        clean_desc = self.clean_cta(raw_caption or title)

        fb_caption = f"{title}\n\n{clean_desc}\n\n#nesty #review #sanpham #shopping #deal"
        if affiliate_link:
            fb_caption += f"\n\nLink: {affiliate_link}"

        yt_caption = f"{title}\n\n{clean_desc[:200]}\n\n#shorts #review #shortsvideo"

        ig_tags = "#lifestyle #review #shopping #fashion #style #vietnam #shopeevietnam #ootd #dailylook #recommended #bestseller #trends #trending #musthave #hotitem"
        ig_caption = f"{title}\n\n{clean_desc[:180]}\n\n{ig_tags}"

        tt_caption = f"{title}\n\n{clean_desc[:500]}\n\n#tiktokshop #review #xuhuong #trending #viral"

        shopee_fixed = f"#shopeevideo #luotvuimualien #shopeecreator {cat_tag}"
        max_len = max(10, 145 - len(shopee_fixed))
        shopee_caption = f"{title[:max_len]} {shopee_fixed}"[:150]

        zalo_caption = f"{title}\n\n{clean_desc}\n\n#nesty #review #sanpham #shopping #deal"
        if affiliate_link:
            zalo_caption += f"\n\nLink: {affiliate_link}"

        return {
            "facebook": self.clean_cta(fb_caption),
            "youtube": self.clean_cta(yt_caption),
            "instagram": self.clean_cta(ig_caption),
            "tiktok": self.clean_cta(tt_caption),
            "shopee": self.clean_cta(shopee_caption),
            "zalo": self.clean_cta(zalo_caption),
        }
