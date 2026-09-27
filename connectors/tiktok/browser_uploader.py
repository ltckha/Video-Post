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
from .human_simulator import HumanSimulator, check_cookie_health

logger = logging.getLogger(__name__)

TIKTOK_UPLOAD_URL = "https://www.tiktok.com/upload"
TIKTOK_LOGIN_URL = "https://www.tiktok.com/login"

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = { runtime: {} };
"""

POST_BUTTON_PATTERN = re.compile(r"^(Đăng|Post|Publish)$", re.IGNORECASE)


def get_directory_size_bytes(directory_path: Path) -> int:
    """Calculate total size of directory in bytes."""
    total = 0
    if not directory_path.exists():
        return 0
    try:
        for entry in directory_path.rglob('*'):
            if entry.is_file() and not entry.is_symlink():
                try:
                    total += entry.stat().st_size
                except (OSError, FileNotFoundError):
                    pass
    except Exception:
        pass
    return total


def format_bytes_human(num_bytes: int) -> str:
    """Format bytes to human readable format (KB/MB/GB)."""
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


def safe_cleanup_tiktok_draft_storage(
    page,
    profile_dir: Path,
    brand_name: str = "Default",
    mode: Optional[str] = None,
) -> Dict[str, Any]:
    """Safely cleanup TikTok temporary upload / draft IndexedDB database ('web_creation_draft').

    CRITICAL SAFETY RULES:
    1. Does NOT delete the entire browser profile, preserving cookies and session logins.
    2. Does NOT rm -rf .indexeddb.blob directly on OS, avoiding LevelDB corruption.
    3. Deletes draft database via in-page standard W3C window.indexedDB.deleteDatabase().
    4. Modes supported: 'disabled', 'dry-run', 'enabled'.
    5. Never logs cookies, tokens, or credentials.
    """
    from config import settings

    configured_mode = mode or getattr(settings, "TIKTOK_CLEANUP_MODE", "disabled") or os.environ.get("TIKTOK_CLEANUP_MODE", "disabled")
    clean_mode = str(configured_mode).strip().lower()

    if clean_mode not in ("disabled", "dry-run", "enabled"):
        clean_mode = "disabled"

    indexeddb_dir = profile_dir / "Default" / "IndexedDB"
    size_before_bytes = get_directory_size_bytes(indexeddb_dir)

    if clean_mode == "disabled":
        logger.info(f"[TikTok/{brand_name}] Draft storage cleanup mode is 'disabled'. Skipping IndexedDB cleanup.")
        return {
            "status": "skipped",
            "mode": "disabled",
            "size_before": format_bytes_human(size_before_bytes),
        }

    # Identify target draft databases in browser context
    try:
        draft_dbs = page.evaluate('''async () => {
            if (!window.indexedDB || !window.indexedDB.databases) {
                return [];
            }
            const dbs = await window.indexedDB.databases();
            const targets = [];
            for (const db of dbs) {
                const name = db.name || '';
                if (name === 'web_creation_draft' || name.includes('creation_draft') || name.includes('upload_draft')) {
                    targets.push(name);
                }
            }
            return targets;
        }''')
    except Exception as eval_err:
        logger.warning(f"[TikTok/{brand_name}] Could not inspect IndexedDB databases: {eval_err}")
        draft_dbs = []

    if clean_mode == "dry-run":
        logger.info(
            f"[TikTok/{brand_name}] [DRY-RUN] Phát hiện {len(draft_dbs)} draft database: {draft_dbs}. "
            f"Dung lượng IndexedDB: {format_bytes_human(size_before_bytes)}. "
            f"(Không thực hiện xóa vì đang ở chế độ dry-run)."
        )
        return {
            "status": "dry-run",
            "mode": "dry-run",
            "targets": draft_dbs,
            "size_before": format_bytes_human(size_before_bytes),
        }

    # Enabled mode: perform safe deletion via standard IndexedDB API
    deleted_dbs = []
    if draft_dbs:
        try:
            deleted_dbs = page.evaluate('''async (targets) => {
                const results = [];
                for (const name of targets) {
                    try {
                        await new Promise((resolve, reject) => {
                            const req = window.indexedDB.deleteDatabase(name);
                            req.onsuccess = () => resolve();
                            req.onerror = () => reject(req.error);
                            req.onblocked = () => resolve();
                        });
                        results.push(name);
                    } catch (e) {
                        // pass
                    }
                }
                return results;
            }''', draft_dbs)
        except Exception as del_err:
            logger.warning(f"[TikTok/{brand_name}] Error deleting draft databases via IndexedDB API: {del_err}")

    # Brief wait for Chromium storage engine to flush LevelDB / unlink blob files
    page.wait_for_timeout(1000)
    size_after_bytes = get_directory_size_bytes(indexeddb_dir)
    freed_bytes = max(0, size_before_bytes - size_after_bytes)

    logger.info(
        f"[TikTok/{brand_name}] [CLEANUP] Đã dọn dẹp database draft TikTok: {deleted_dbs}. "
        f"Dung lượng IndexedDB: {format_bytes_human(size_before_bytes)} -> {format_bytes_human(size_after_bytes)} "
        f"(Đã giải phóng: {format_bytes_human(freed_bytes)}). Session/Cookies giữ nguyên vẹn."
    )

    return {
        "status": "cleaned",
        "mode": "enabled",
        "deleted_databases": deleted_dbs,
        "size_before": format_bytes_human(size_before_bytes),
        "size_after": format_bytes_human(size_after_bytes),
        "freed": format_bytes_human(freed_bytes),
    }



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
            from core.account_manager import AccountManager
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
            "--disk-cache-size=20971520",
            "--media-cache-size=10485760",
        ]

        realistic_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        viewport_cfg = {"width": 1440, "height": 900}

        # Prioritize real Google Chrome installed on macOS
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=target_dir,
                channel="chrome",
                headless=is_headless,
                user_agent=realistic_ua,
                viewport=viewport_cfg,
                ignore_default_args=["--enable-automation"],
                args=args,
            )
        except Exception as e:
            logger.info(f"Fallback to bundled Chromium (Chrome channel error: {e})")
            context = p.chromium.launch_persistent_context(
                user_data_dir=target_dir,
                headless=is_headless,
                user_agent=realistic_ua,
                viewport=viewport_cfg,
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

        health = check_cookie_health(raw_cookies)
        if not health["valid"]:
            raise ValueError(f"Cookie không hợp lệ: {health['reason']}")
        logger.info(f"[TikTok/{self.brand_name}] Cookie health check PASS! (Hạn còn ~{health['expires_in_days']} ngày)")

        normalized = _normalize_cookie_editor_export(raw_cookies)
        logger.info(f"[TikTok/{self.brand_name}] Đã chuẩn hóa {len(normalized)} cookie cho Playwright.")

        with sync_playwright() as p:
            context = self._get_context(p, headless=True)
            try:
                context.add_cookies(normalized)
                page = context.pages[0] if context.pages else context.new_page()

                logger.info(f"[TikTok/{self.brand_name}] Khởi động phiên và điều hướng xác thực cookie...")
                try:
                    page.goto("https://www.tiktok.com/explore", wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(2000)
                except Exception:
                    pass

                for test_url in ["https://www.tiktok.com/tiktokstudio/upload", "https://www.tiktok.com/creator-center/upload", "https://www.tiktok.com/upload"]:
                    try:
                        page.goto(test_url, wait_until="domcontentloaded", timeout=40000)
                        page.wait_for_timeout(3000)
                        if "login" not in page.url and "chrome-error" not in page.url:
                            break
                    except Exception:
                        pass

                current_url = page.url
                if "login" in current_url:
                    raise RuntimeError("❌ Cookie không hợp lệ hoặc đã hết hạn (bị redirect về /login). Hãy đăng nhập lại trên Chrome cá nhân và xuất JSON mới!")

                # Check if upload file input is present
                try:
                    file_input = page.locator('input[type="file"]').first
                    file_input.wait_for(state="attached", timeout=20000)
                    logger.info(f"[TikTok/{self.brand_name}] 🎉 XÁC THỰC THÀNH CÔNG! Đã tìm thấy ô upload video.")
                    self._mark_account_active()
                    print(f"\n🎉 XÁC THỰC THÀNH CÔNG CHO BRAND '{self.brand_name}'! (Hạn cookie còn ~{health['expires_in_days']} ngày)")
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
            sim = HumanSimulator(page)

            try:
                # 1. Natural Session Warm-up & Navigate to TikTok Studio
                logger.info("Khởi động phiên tự nhiên (Session Warm-up) trên TikTok...")
                try:
                    page.goto("https://www.tiktok.com/explore", wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(random.randint(1500, 2500))
                except Exception as warm_err:
                    logger.debug(f"Warm-up step notice: {warm_err}")

                logger.info("Navigating to TikTok Studio Upload...")
                nav_success = False
                upload_urls = [
                    "https://www.tiktok.com/tiktokstudio/upload",
                    "https://www.tiktok.com/creator-center/upload",
                    "https://www.tiktok.com/upload",
                ]
                for target_url in upload_urls:
                    try:
                        logger.info(f"Connecting to {target_url}...")
                        resp = page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
                        page.wait_for_timeout(3000)
                        if "login" not in page.url and "chrome-error" not in page.url:
                            nav_success = True
                            break
                    except Exception as nav_err:
                        logger.warning(f"Thử kết nối {target_url} gặp sự cố ({nav_err}), thử cổng tiếp theo...")
                        page.wait_for_timeout(2000)

                page.wait_for_timeout(2000)

                if "login" in page.url:
                    raise RuntimeError(
                        f"Tài khoản TikTok '{self.brand_name}' chưa đăng nhập hoặc cookie đã hết hạn. "
                        f"Vui lòng chạy lệnh 'tiktok-import-cookies --brand \"{self.brand_name}\" --cookies-file \"<file.json>\"'."
                    )

                # Pre-upload natural browsing simulation
                sim.pre_upload_browse()

                # 2. Attach Video File via CDP Protocol
                logger.info("Locating file input and attaching video file...")
                file_input = page.locator('input[type="file"]').first
                file_input.wait_for(state="attached", timeout=45000)
                file_input.set_input_files(str(path))
                logger.info(f"Video file '{path.name}' attached successfully!")

                # Wait for upload processing and dismiss all popups / modals
                page.wait_for_timeout(4000)
                sim.dismiss_popups()

                # 3. Enter Caption with Human Typing & TikTok Native Hashtag Suggestion Enter
                logger.info("Entering Caption and Interactive Hashtags...")
                caption_editor = page.locator("div[contenteditable='true']").first
                caption_editor.wait_for(state="visible", timeout=60000)

                # Focus and thoroughly clear default file name
                sim.dismiss_popups()
                sim.clear_contenteditable(caption_editor)
                page.wait_for_timeout(400)

                clean_caption = caption_text.strip()
                logger.info(f"Typing caption via HumanSimulator ({len(clean_caption)} chars)...")
                sim.type_caption_with_tiktok_hashtags(caption_editor, clean_caption)

                # Dismiss any overlay tooltip after typing
                sim.dismiss_popups()

                # 4. Copyright Check Automation
                try:
                    logger.info("Checking for Copyright Check toggle...")
                    copyright_toggle = page.locator("input[type='checkbox'][name*='copyright'], div:has-text('Run a copyright check'), div:has-text('Kiểm tra bản quyền')").first
                    if copyright_toggle.is_visible(timeout=3000):
                        logger.info("Activating Copyright Check on TikTok Studio...")
                        sim.human_click_locator(copyright_toggle)
                        page.wait_for_timeout(2500)
                except Exception as e:
                    logger.debug(f"Copyright check toggle optional step: {e}")

                # 5. Scroll down and locate Post / Publish button
                logger.info("Scrolling to bottom and locating Post button...")
                sim.human_scroll(500, steps=6)
                page.wait_for_timeout(1500)

                # Prioritize dedicated post button selectors on TikTok Studio
                post_selectors = [
                    "div.btn-post button",
                    "button[data-e2e='post_video_button']",
                    "button.btn-post",
                    "button:has-text('Post'):not(:has-text('Save'))",
                    "button:has-text('Đăng'):not(:has-text('Lưu'))",
                    "button:has-text('Publish')",
                ]

                post_btn = None
                for sel in post_selectors:
                    loc = page.locator(sel).last
                    try:
                        if loc.is_visible(timeout=1500):
                            post_btn = loc
                            logger.info(f"Found Post button with selector: '{sel}'")
                            break
                    except Exception:
                        pass

                if not post_btn:
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

                # Natural human hesitation before clicking Post
                page.wait_for_timeout(random.randint(2000, 3500))

                # Step 5.1: Click Post button with Dual-Action (Human Move + Force Click)
                logger.info("Moving smoothly and clicking Post button...")
                try:
                    sim.human_click_locator(post_btn)
                except Exception:
                    pass
                page.wait_for_timeout(500)
                try:
                    post_btn.click(force=True, timeout=3000)
                except Exception:
                    pass

                # Step 5.2: Check if confirmation modal / popup appears
                page.wait_for_timeout(2000)
                confirm_selectors = [
                    "button:has-text('Post now')",
                    "button:has-text('Đăng ngay')",
                    "button:has-text('Vẫn đăng')",
                    "button:has-text('Continue to post')",
                    "button:has-text('Tiếp tục đăng')",
                    "div[role='dialog'] button:has-text('Post')",
                    "div[role='dialog'] button:has-text('Đăng')",
                ]
                for c_sel in confirm_selectors:
                    try:
                        c_btn = page.locator(c_sel).first
                        if c_btn.is_visible(timeout=1500):
                            logger.info(f"Found Post Confirmation popup ('{c_sel}'). Clicking to confirm...")
                            c_btn.click(force=True, timeout=3000)
                            page.wait_for_timeout(2000)
                            break
                    except Exception:
                        pass

                # 6. Strict Publish Verification (Poll for actual success confirmation)
                logger.info("Waiting and verifying actual publish confirmation from TikTok Studio...")
                success_published = False
                verify_start = time.time()

                success_indicators = [
                    "text=Your video has been uploaded",
                    "text=Video của bạn đã được tải lên",
                    "text=Video đã được tải lên",
                    "text=Manage your posts",
                    "text=Quản lý bài đăng",
                    "text=Upload another video",
                    "text=Tải lên video khác",
                    "text=Post another video",
                    "button:has-text('Manage your posts')",
                    "button:has-text('Quản lý bài đăng')",
                    "button:has-text('Upload another video')",
                    "button:has-text('Tải lên video khác')",
                ]

                while time.time() - verify_start < 45:
                    current_url = page.url
                    # Check URL redirect
                    if "content" in current_url or "manage" in current_url or "posts" in current_url:
                        logger.info(f"TikTok redirected to content management page: {current_url}")
                        success_published = True
                        break

                    # Check success modal / message
                    for s_ind in success_indicators:
                        try:
                            if page.locator(s_ind).first.is_visible(timeout=500):
                                logger.info(f"Detected TikTok upload success indicator: '{s_ind}'")
                                success_published = True
                                break
                        except Exception:
                            pass

                    if success_published:
                        break

                    # Check for explicit error banner/toast
                    try:
                        err_toast = page.locator("div[class*='toast'][class*='error'], div[role='alert'], div[class*='error-message']").first
                        if err_toast.is_visible(timeout=500):
                            err_txt = err_toast.inner_text().strip()
                            if err_txt:
                                raise RuntimeError(f"TikTok thông báo lỗi: '{err_txt}'")
                    except Exception:
                        pass

                    page.wait_for_timeout(2000)

                if not success_published:
                    raise RuntimeError(
                        "TikTok chưa hoàn tất xuất bản sau khi bấm nút Đăng (không nhận được thông báo xác nhận thành công từ TikTok Studio)."
                    )

                logger.info(f"[TikTok/{self.brand_name}] ✅ Đăng video thành công 100%!")

                # Extract public or studio video link if available
                post_url = ""
                try:
                    video_link_loc = page.locator("a[href*='/video/']").first
                    if video_link_loc.is_visible(timeout=1000):
                        href = video_link_loc.get_attribute("href")
                        if href:
                            post_url = href if href.startswith("http") else f"https://www.tiktok.com{href}"
                except Exception:
                    pass

                if not post_url:
                    current_url = page.url
                    if "manage" in current_url or "content" in current_url:
                        post_url = current_url
                    else:
                        post_url = "https://www.tiktok.com/tiktokstudio/content"

                # Post-Publish Draft Storage Cleanup (Safe cleanup of TikTok temporary upload database)
                cleanup_info = {}
                try:
                    cleanup_info = safe_cleanup_tiktok_draft_storage(
                        page=page,
                        profile_dir=target_profile,
                        brand_name=self.brand_name
                    )
                except Exception as cl_err:
                    logger.warning(f"[TikTok/{self.brand_name}] Cảnh báo khi dọn dẹp draft database: {cl_err}")

                return {
                    "status": "success",
                    "platform": "tiktok",
                    "brand": self.brand_name,
                    "video_path": str(path),
                    "video_url": post_url,
                    "cleanup": cleanup_info,
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
