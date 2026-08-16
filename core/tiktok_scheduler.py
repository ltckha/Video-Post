"""TikTok Daily Random-Time Scheduler.

Mỗi tài khoản TikTok khai báo trong config/tiktok_accounts.json sẽ được tự động
đăng đúng 1 video/ngày vào một giờ ngẫu nhiên trong khung giờ đã cấu hình
(mặc định 08:00–21:00, có thể ghi đè riêng theo từng tài khoản qua "post_time_window").

Sau mỗi lần chạy (thành công hay thất bại), scheduler tự động random giờ mới
cho ngày kế tiếp của đúng tài khoản đó.
"""
import random
import logging
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

from config import settings
from core.account_manager import AccountManager
from core.sheet_client import GoogleSheetDirectClient
from connectors.tiktok import TikTokBrowserConnector
from connectors.base import PostMetadata

logger = logging.getLogger(__name__)


def _parse_hhmm(value: str) -> tuple:
    h, m = value.strip().split(":")
    return int(h), int(m)


def _random_time_today_or_tomorrow(window_start: str, window_end: str) -> datetime:
    """Tính 1 mốc thời gian ngẫu nhiên trong khung giờ cho hôm nay; nếu đã qua giờ đó thì lùi sang ngày mai."""
    now = datetime.now()
    sh, sm = _parse_hhmm(window_start)
    eh, em = _parse_hhmm(window_end)

    start_today = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
    end_today = now.replace(hour=eh, minute=em, second=0, microsecond=0)

    window_seconds = int((end_today - start_today).total_seconds())
    if window_seconds <= 0:
        window_seconds = 3600  # fallback an toàn nếu cấu hình sai (end <= start)

    offset = random.randint(0, window_seconds)
    candidate = start_today + timedelta(seconds=offset)

    if candidate <= now:
        # Giờ ngẫu nhiên hôm nay đã trôi qua -> tính cho ngày mai
        candidate += timedelta(days=1)

    return candidate


class TikTokDailyScheduler:
    """Quản lý lịch đăng ngẫu nhiên hằng ngày cho tất cả tài khoản TikTok đã cấu hình."""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.account_mgr = AccountManager()

    def start(self):
        brands = self.account_mgr.list_tiktok_brands()
        if not brands:
            logger.warning(
                "Không có tài khoản TikTok nào trong config/tiktok_accounts.json. "
                "Hãy copy từ tiktok_accounts.json.example và điền tài khoản trước."
            )
            return

        for brand in brands:
            self._schedule_next_run(brand)

        self.scheduler.start()
        logger.info(f"TikTokDailyScheduler đã khởi động cho {len(brands)} tài khoản: {', '.join(brands)}")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("TikTokDailyScheduler đã dừng.")

    def _get_window_for_brand(self, brand: str) -> tuple:
        creds = self.account_mgr.get_brand_credentials(brand, "tiktok") or {}
        window = creds.get("post_time_window")
        if window and len(window) == 2:
            return window[0], window[1]
        return settings.TIKTOK_POST_WINDOW_START, settings.TIKTOK_POST_WINDOW_END

    def _schedule_next_run(self, brand: str):
        window_start, window_end = self._get_window_for_brand(brand)
        run_date = _random_time_today_or_tomorrow(window_start, window_end)

        self.scheduler.add_job(
            self._run_for_brand,
            trigger="date",
            run_date=run_date,
            args=[brand],
            id=f"tiktok_post_{brand}",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info(f"[TikTok/{brand}] Đã lên lịch đăng lúc {run_date.strftime('%H:%M %d/%m/%Y')}.")

    def _run_for_brand(self, brand: str):
        try:
            process_one_tiktok_job(brand)
        except Exception as e:
            logger.error(f"[TikTok/{brand}] Lỗi khi chạy job theo lịch: {e}")
        finally:
            # Luôn random lịch cho ngày kế tiếp, kể cả khi job hôm nay lỗi hoặc không có video nào để đăng
            self._schedule_next_run(brand)


def process_one_tiktok_job(brand: str) -> Optional[dict]:
    """Lấy 1 video đang chờ (manual_pending) của brand này trên Master Sheet, đăng lên TikTok, cập nhật status."""
    sheet = GoogleSheetDirectClient()
    job = sheet.get_pending_tiktok_job(brand)

    if not job:
        logger.info(f"[TikTok/{brand}] Không có video nào đang chờ đăng (status_tt = manual_pending).")
        return None

    job_id = job.get("job_id")
    video_path = job.get("video_path", "")
    caption = job.get("caption_tt", "") or job.get("title", "")

    logger.info(f"[TikTok/{brand}] Chuẩn bị đăng job_id={job_id}: {job.get('title', '')}")

    connector = TikTokBrowserConnector(brand_name=brand)
    metadata = PostMetadata(title=job.get("title", ""), description=caption)

    try:
        result = connector.upload_video(video_path, metadata)
        sheet.update_master_rows([{"job_id": job_id, "status_tt": "published"}])
        logger.info(f"[TikTok/{brand}] ✅ job_id={job_id} đã cập nhật status_tt = published.")
        return result
    except Exception as e:
        sheet.update_master_rows([{"job_id": job_id, "status_tt": "manual_pending"}])
        logger.error(f"[TikTok/{brand}] ❌ job_id={job_id} đăng thất bại, giữ nguyên manual_pending để thử lại: {e}")
        raise
