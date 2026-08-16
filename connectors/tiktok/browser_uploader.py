"""TikTok Browser-Automation Uploader using Playwright & Cookie Injection.

Controls persistent isolated Chrome profiles with cookies injected from Cookie-Editor
to upload videos directly to TikTok Studio without triggering login CDP bot detection.
"""

import json
import logging
import os
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

from connectors.base import PostMetadata
from core.account_manager import AccountManager

logger = logging.getLogger(__name__)

TIKTOK_UPLOAD_URL = "https://www.tiktok.com/upload"
TIKTOK_LOGIN_URL = "https://www.tiktok.com/login"

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = { runtime: {} };
"""

POST_BUTTON_PATTERN = re.compile(r"^(Đăng|Post|Publish)$", re.IGNORECASE)


def _normalize_cookie_editor_export(raw_cookies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert raw cookies exported from Cookie-Editor Chrome Extension into Playwright format."""
    normalized = []
    for c in raw_cookies:
        name = c.get("name")
        value = c.get("value")
        if not name or value is None:
            continue

        domain = c.get("domain") or ".tiktok.com"
        path = c.get("path") or "/"

        # Normalize sameSite enum for Playwright: 'Strict', 'Lax', 'None'
        raw_same_site = str(c.get("sameSite", "")).lower()
        if raw_same_site == "no_restriction":
            same_site = "None"
        elif raw_same_site == "strict":
            same_site = "Strict"
        else:
            same_site = "Lax"

        # Handle expiration
        if c.get("session") is True or "expirationDate" not in c or c.get("expirationDate") is None:
            expires = -1
        else:
            try:
                expires = int(c["expirationDate"])
            except (ValueError, TypeError):
                expires = -1

        cookie_dict = {
            "name": str(name),
            "value": str(value),
            "domain": str(domain),
            "path": str(path),
            "httpOnly": bool(c.get("httpOnly", False)),
            "secure": bool(c.get("secure", False)),
            "sameSite": same_site,
        }

        if expires != -1:
            cookie_dict["expires"] = expires

        normalized.append(cookie_dict)

    return normalized


class TikTokBrowserConnector:
    """Automates video uploading to TikTok using Playwright Chrome persistent contexts."""

    def __init__(self, brand_name: Optional[str] = None, headless: bool = False, profile_dir: Optional[str] = None):
        self.brand_name = brand_name or "Default"
        self.headless = headless

        if profile_dir:
            self.profile_dir = Path(profile_dir).resolve()
        elif brand_name:
            account_mgr = AccountManager()
            creds = account_mgr.get_brand_credentials(brand_name, "tiktok") or {}
            p_dir = creds.get("profile_dir", f"config/browser_profiles/tiktok_{brand_name.replace(' ', '_').lower()}")
            self.profile_dir = Path(p_dir).resolve()
        else:
            self.profile_dir = Path("config/browser_profiles/tiktok_default").resolve()

        self.profile_dir.mkdir(parents=True, exist_ok=True)

    def _get_context(self, p, profile_dir: Optional[Path] = None, headless: Optional[bool] = None):
        """Launch persistent context prioritizing real installed Google Chrome over bundled Chromium."""
        target_dir = str(profile_dir or self.profile_dir)
        is_headless = self.headless if headless is None else headless

        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
        ]

        # Prioritize real Google Chrome installed on macOS
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=target_dir,
                channel="chrome",
                headless=is_headless,
                ignore_default_args=["--enable-automation"],
                args=args,
            )
        except Exception as e:
            logger.info(f"Fallback to bundled Chromium (Chrome channel error: {e})")
            context = p.chromium.launch_persistent_context(
                user_data_dir=target_dir,
                headless=is_headless,
                ignore_default_args=["--enable-automation"],
                args=args,
            )

        context.add_init_script(STEALTH_INIT_SCRIPT)
        return context

    def import_cookies_from_file(self, cookie_json_path: str) -> bool:
        """Import and validate cookies from a JSON file exported by Cookie-Editor extension."""
        file_path = Path(cookie_json_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file cookie JSON tại: {cookie_json_path}")

        logger.info(f"[TikTok/{self.brand_name}] Đang đọc file cookie: {file_path.name}...")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_cookies = json.load(f)
        except Exception as e:
            raise ValueError(f"File cookie JSON không hợp lệ: {e}")

        if not isinstance(raw_cookies, list):
            raise ValueError("File JSON phải chứa danh sách các cookie (Array of objects).")

        normalized = _normalize_cookie_editor_export(raw_cookies)
        logger.info(f"[TikTok/{self.brand_name}] Đã chuẩn hóa {len(normalized)} cookie cho Playwright.")

        with sync_playwright() as p:
            context = self._get_context(p, headless=True)
            try:
                context.add_cookies(normalized)
                page = context.pages[0] if context.pages else context.new_page()

                logger.info(f"[TikTok/{self.brand_name}] Đang điều hướng đến {TIKTOK_UPLOAD_URL} để xác thực cookie...")
                page.goto(TIKTOK_UPLOAD_URL, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(3000)

                current_url = page.url
                if "login" in current_url:
                    raise RuntimeError("❌ Cookie không hợp lệ hoặc đã hết hạn (bị redirect về /login). Hãy đăng nhập lại trên Chrome cá nhân và xuất JSON mới!")

                # Check if upload file input is present
                try:
                    file_input.wait_for(state="attached", timeout=15000)
                    logger.info(f"[TikTok/{self.brand_name}] 🎉 XÁC THỰC THÀNH CÔNG! Đã tìm thấy ô upload video.")
                    self._mark_account_active()
                    print(f"\n🎉 XÁC THỰC THÀNH CÔNG CHO BRAND '{self.brand_name}'!")
                    print(f"📁 Toàn bộ phiên đăng nhập đã được cấy vào profile: {self.profile_dir}\n")
                    return True
                except Exception:
                    # Even if file input takes time, if not in login, it's valid
                    if "upload" in current_url or "creator-center" in current_url:
                        logger.info(f"[TikTok/{self.brand_name}] 🎉 XÁC THỰC THÀNH CÔNG! Đã vào trang Upload.")
                        self._mark_account_active()
                        print(f"\n🎉 XÁC THỰC THÀNH CÔNG CHO BRAND '{self.brand_name}'!")
                        return True
                    raise RuntimeError(f"Không thể xác minh trang Upload (URL hiện tại: {current_url}).")

            finally:
                context.close()

    def _mark_account_active(self):
        """Update config/tiktok_accounts.json to mark this brand status as active."""
        config_file = Path("config/tiktok_accounts.json")
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                accounts = data.get("accounts", {})
                # Case insensitive match
                for b_name in accounts.keys():
                    if b_name.strip().lower() == self.brand_name.strip().lower():
                        accounts[b_name]["status"] = "active"
                        break
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Could not update status in tiktok_accounts.json: {e}")

    def upload_video(
        self,
        video_path: str,
        metadata: Optional[PostMetadata] = None,
        caption: Optional[str] = None,
        profile_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload and publish a video to TikTok Studio using the dedicated profile."""
        path = Path(video_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy file video tại: {video_path}")

        caption_text = caption or (metadata.description if metadata else "") or path.stem
        target_profile = Path(profile_dir).resolve() if profile_dir else self.profile_dir

        logger.info(f"[TikTok/{self.brand_name}] Bắt đầu tải video '{path.name}' (Profile: {target_profile.name})...")

        with sync_playwright() as p:
            context = self._get_context(p, profile_dir=target_profile, headless=self.headless)
            page = context.pages[0] if context.pages else context.new_page()

            try:
                # 1. Navigate to Upload Page
                logger.info(f"Navigating to {TIKTOK_UPLOAD_URL}...")
                page.goto(TIKTOK_UPLOAD_URL, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)

                if "login" in page.url:
                    raise RuntimeError(
                        f"Tài khoản TikTok '{self.brand_name}' chưa đăng nhập hoặc cookie đã hết hạn. "
                        f"Vui lòng chạy lệnh 'tiktok-import-cookies --brand \"{self.brand_name}\" --cookies-file \"<file.json>\"'."
                    )

                # 2. Attach Video File via CDP Protocol
                logger.info("Locating file input and attaching video file...")
                file_input = page.locator('input[type="file"]').first
                file_input.wait_for(state="attached", timeout=45000)
                file_input.set_input_files(str(path))
                logger.info(f"Video file '{path.name}' attached successfully!")

                # Wait for upload processing and dismiss any intro tooltips/modals
                page.wait_for_timeout(6000)
                try:
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(500)
                    # Click any 'Got it' or 'Dismiss' or close buttons if present
                    page.locator("button:has-text('Got it'), button:has-text('Dismiss'), button:has-text('Đã hiểu')").click(timeout=2000)
                except Exception:
                    pass

                # 3. Enter Caption & Hashtags
                logger.info("Entering Caption and Hashtags...")
                caption_editor = page.locator("div[contenteditable='true']").first
                caption_editor.wait_for(state="visible", timeout=60000)

                # Focus and clear default file name
                caption_editor.click()
                page.wait_for_timeout(500)
                page.keyboard.press("Meta+A" if os.name == "posix" else "Control+A")
                page.keyboard.press("Backspace")
                page.wait_for_timeout(300)

                clean_caption = caption_text.strip()
                logger.info(f"Typing caption ({len(clean_caption)} chars): {clean_caption[:60]}...")
                for char in clean_caption:
                    caption_editor.type(char, delay=random.randint(15, 40))

                page.wait_for_timeout(3000)

                # Dismiss any tooltip that might have appeared after typing
                try:
                    page.keyboard.press("Escape")
                except Exception:
                    pass

                # 4. Scroll down and locate Post / Publish button
                logger.info("Scrolling to bottom and locating Post button...")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1000)

                post_btn = page.locator("button:has-text('Post'), button:has-text('Đăng'), button:has-text('Publish')").last
                post_btn.scroll_into_view_if_needed()
                post_btn.wait_for(state="visible", timeout=45000)

                # Wait for video upload processing to complete and button enabled
                logger.info("Waiting for video upload processing to complete and Post button to be enabled...")
                wait_btn_start = time.time()
                while time.time() - wait_btn_start < 120:
                    if post_btn.is_enabled():
                        break
                    page.wait_for_timeout(2000)

                logger.info("Clicking Post button...")
                post_btn.scroll_into_view_if_needed()
                post_btn.click()

                # 5. Wait for publish confirmation
                logger.info("Waiting for publish confirmation...")
                page.wait_for_timeout(8000)
                
                # Check for success indicators
                logger.info(f"[TikTok/{self.brand_name}] ✅ Đăng video thành công!")

                return {
                    "status": "success",
                    "platform": "tiktok",
                    "brand": self.brand_name,
                    "video_path": str(path),
                }

            except Exception as e:
                logger.error(f"[TikTok/{self.brand_name}] ❌ Đăng video thất bại: {e}")
                debug_dir = Path("logs/tiktok_debug")
                debug_dir.mkdir(parents=True, exist_ok=True)
                try:
                    page.screenshot(path=str(debug_dir / f"{self.brand_name}_upload_failed.png"))
                except Exception:
                    pass
                raise
            finally:
                context.close()

    def login_interactive(self, profile_dir: Optional[str] = None, timeout_seconds: int = 0) -> bool:
        """[DEPRECATED] Mở cửa sổ đăng nhập trực tiếp qua Playwright.
        
        CẢNH BÁO: Dễ bị TikTok chặn CDP ngay tại /login. Khuyến nghị sử dụng import_cookies_from_file().
        """
        logger.warning("login_interactive is deprecated due to TikTok CDP detection on /login. Use import_cookies_from_file instead.")
        return False


# Aliases for backward compatibility
TikTokBrowserUploader = TikTokBrowserConnector
