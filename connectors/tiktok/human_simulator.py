"""TikTok Human Simulation Engine (Stealth Anti-Bot).

Simulates natural human biometrics:
- Cubic Bézier curve mouse trajectories with micro-jittering and velocity easing
- Variable human keystroke typing with punctuation pauses
- Specialized TikTok hashtag typing (types #tag, pauses 1-2s, presses Enter to trigger interactive tag)
- Pre-upload browsing and exploratory scrolling
- Cookie health & expiration checker
"""

import json
import logging
import math
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def generate_bezier_curve(
    start: Tuple[float, float],
    end: Tuple[float, float],
    steps: int = 25,
    deviation: float = 1.0,
) -> List[Tuple[float, float]]:
    """Generate points along a cubic Bézier curve between start and end with randomized control points."""
    x0, y0 = start
    x3, y3 = end

    dx = x3 - x0
    dy = y3 - y0
    dist = math.hypot(dx, dy)

    if dist < 5:
        return [start, end]

    # Spread control points perpendicular to the direct path
    angle = math.atan2(dy, dx)
    perp_angle = angle + math.pi / 2

    # Two control points with natural organic offset
    offset1 = random.uniform(-0.25, 0.25) * dist * deviation
    offset2 = random.uniform(-0.2, 0.2) * dist * deviation

    x1 = x0 + dx * 0.3 + math.cos(perp_angle) * offset1
    y1 = y0 + dy * 0.3 + math.sin(perp_angle) * offset1

    x2 = x0 + dx * 0.7 + math.cos(perp_angle) * offset2
    y2 = y0 + dy * 0.7 + math.sin(perp_angle) * offset2

    points = []
    for i in range(steps + 1):
        t = i / steps
        # Cubic Bézier formula
        u = 1 - t
        tt = t * t
        uu = u * u
        uuu = uu * u
        ttt = tt * t

        px = uuu * x0 + 3 * uu * t * x1 + 3 * u * tt * x2 + ttt * x3
        py = uuu * y0 + 3 * uu * t * y1 + 3 * u * tt * y2 + ttt * y3

        # Add tiny hand tremor micro-jitter (except at absolute endpoints)
        if 0 < i < steps:
            px += random.uniform(-1.0, 1.0)
            py += random.uniform(-1.0, 1.0)

        points.append((px, py))

    return points


class HumanSimulator:
    """Provides human-like interaction helpers for Playwright pages."""

    def __init__(self, page):
        self.page = page
        self.current_mouse_pos = (random.uniform(200, 500), random.uniform(200, 400))

    def move_mouse_to(self, target_x: float, target_y: float, steps: Optional[int] = None):
        """Smoothly move mouse from current position to target coordinates using Bézier curve."""
        dist = math.hypot(target_x - self.current_mouse_pos[0], target_y - self.current_mouse_pos[1])
        num_steps = steps or max(15, min(40, int(dist / 20)))

        points = generate_bezier_curve(self.current_mouse_pos, (target_x, target_y), steps=num_steps)

        for px, py in points:
            self.page.mouse.move(px, py)
            time_delay = random.uniform(0.005, 0.018)
            time.sleep(time_delay)

        self.current_mouse_pos = (target_x, target_y)
        self.page.wait_for_timeout(random.randint(50, 150))

    def human_click_locator(self, locator):
        """Move smoothly to a locator element and click with realistic dwell time."""
        try:
            box = locator.bounding_box()
            if not box:
                locator.click()
                return

            target_x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
            target_y = box["y"] + box["height"] * random.uniform(0.3, 0.7)

            self.move_mouse_to(target_x, target_y)
            self.page.wait_for_timeout(random.randint(100, 250))
            self.page.mouse.down()
            self.page.wait_for_timeout(random.randint(60, 140))
            self.page.mouse.up()
            self.page.wait_for_timeout(random.randint(100, 300))
        except Exception:
            locator.click()

    def human_scroll(self, distance: int, steps: int = 5):
        """Scroll naturally in incremental chunks."""
        per_step = distance / steps
        for _ in range(steps):
            jitter = per_step * random.uniform(0.8, 1.2)
            self.page.mouse.wheel(0, jitter)
            self.page.wait_for_timeout(random.randint(80, 180))

    def pre_upload_browse(self):
        """Perform natural exploratory browsing on TikTok Studio upload page."""
        logger.info("Mô phỏng hành vi người thật: Lướt xem giao diện TikTok Studio...")
        self.dismiss_popups()
        self.move_mouse_to(random.uniform(400, 800), random.uniform(300, 600), steps=20)
        self.page.wait_for_timeout(random.randint(800, 1500))

        self.human_scroll(random.randint(150, 300), steps=4)
        self.page.wait_for_timeout(random.randint(1000, 2000))
        self.human_scroll(random.randint(-250, -100), steps=3)
        self.page.wait_for_timeout(random.randint(800, 1500))
        self.dismiss_popups()

    def dismiss_popups(self):
        """Actively search and dismiss all tooltips, intro guide overlays, modals, and popups."""
        logger.info("Đang quét và tắt các popup/modal/hướng dẫn trên TikTok Studio...")
        try:
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(200)
            self.page.keyboard.press("Escape")
        except Exception:
            pass

        popup_selectors = [
            "button:has-text('Got it')",
            "button:has-text('Đã hiểu')",
            "button:has-text('Dismiss')",
            "button:has-text('Bỏ qua')",
            "button:has-text('Skip')",
            "button:has-text('Close')",
            "button:has-text('Đóng')",
            "div[class*='modal'] button[class*='close']",
            "div[role='dialog'] button:has-text('Got it')",
            "div[role='dialog'] button:has-text('Đã hiểu')",
            "div[class*='guide'] button",
            "div[class*='tooltip'] button",
            "div[class*='popover'] button",
            ".TUXModal-close",
            "[data-testid*='close']",
        ]
        for sel in popup_selectors:
            try:
                btn = self.page.locator(sel).first
                if btn.is_visible(timeout=500):
                    logger.info(f"Tắt popup qua selector: '{sel}'")
                    btn.click(timeout=1000)
                    self.page.wait_for_timeout(300)
            except Exception:
                pass

    def clear_contenteditable(self, locator):
        """Thoroughly clear contenteditable div using multiple robust fallback mechanisms."""
        self.human_click_locator(locator)
        self.page.wait_for_timeout(300)

        # 1. Native DOM Selection Range + delete
        try:
            self.page.evaluate("""(el) => {
                el.focus();
                const range = document.createRange();
                range.selectNodeContents(el);
                const sel = window.getSelection();
                sel.removeAllRanges();
                sel.addRange(range);
            }""", locator.element_handle())
            self.page.wait_for_timeout(200)
            self.page.keyboard.press("Backspace")
            self.page.wait_for_timeout(200)
        except Exception:
            pass

        # 2. Key combo backups (lowercase 'a')
        self.page.keyboard.press("Meta+a")
        self.page.keyboard.press("Control+a")
        self.page.keyboard.press("Backspace")
        self.page.wait_for_timeout(200)

        # 3. If text still exists, force innerText = '' and dispatch input events
        try:
            self.page.evaluate("""(el) => {
                if (el.innerText.trim().length > 0) {
                    el.innerText = '';
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }""", locator.element_handle())
            self.page.wait_for_timeout(200)
        except Exception:
            pass

    def type_caption_with_tiktok_hashtags(self, locator, full_caption: str):
        """Type caption naturally and format hashtags by typing #tag -> wait 1-2s -> press Enter.
        
        This converts raw text hashtags into TikTok's native interactive hashtag chips.
        """
        clean_text = full_caption.strip()
        lines = clean_text.split("\n")

        for line_idx, line in enumerate(lines):
            line_str = line.strip()
            if not line_str:
                self.page.keyboard.press("Enter")
                self.page.wait_for_timeout(random.randint(150, 350))
                continue

            tokens = line_str.split(" ")
            for token_idx, token in enumerate(tokens):
                if not token:
                    continue

                if token.startswith("#") and len(token) > 1:
                    # Specialized TikTok hashtag typing
                    logger.info(f"Typing TikTok hashtag: '{token}'...")
                    for char in token:
                        locator.type(char, delay=random.randint(30, 80))

                    # Wait 1-2 seconds for TikTok's hashtag autocomplete suggestion box to render
                    wait_ms = random.randint(1200, 1800)
                    logger.info(f"Waiting {wait_ms}ms for TikTok hashtag dropdown suggestion...")
                    self.page.wait_for_timeout(wait_ms)

                    # Press Enter to select/confirm the hashtag chip
                    self.page.keyboard.press("Enter")
                    self.page.wait_for_timeout(random.randint(300, 600))

                    # Add space after hashtag
                    locator.type(" ", delay=random.randint(50, 100))
                else:
                    # Regular word typing with human cadence
                    for char in token:
                        locator.type(char, delay=random.randint(25, 65))
                        if char in [".", ",", "!", "?", ":", ";"]:
                            self.page.wait_for_timeout(random.randint(200, 450))

                    if token_idx < len(tokens) - 1:
                        locator.type(" ", delay=random.randint(40, 90))

            if line_idx < len(lines) - 1:
                self.page.keyboard.press("Enter")
                self.page.wait_for_timeout(random.randint(200, 450))

        self.page.wait_for_timeout(random.randint(1000, 2000))


def check_cookie_health(cookie_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Inspect essential TikTok cookies and check expiration status."""
    now = time.time()
    session_id_found = False
    session_expired = False
    earliest_exp = None

    for c in cookie_list:
        name = c.get("name", "")
        exp = c.get("expirationDate") or c.get("expires")

        if name == "sessionid":
            session_id_found = True
            if exp and exp != -1 and exp < now:
                session_expired = True

        if exp and exp != -1 and exp > 0:
            if earliest_exp is None or exp < earliest_exp:
                earliest_exp = exp

    if not session_id_found:
        return {
            "valid": False,
            "reason": "Thiếu cookie quan trọng 'sessionid' (chưa đăng nhập tài khoản).",
            "expires_in_days": 0,
        }

    if session_expired:
        return {
            "valid": False,
            "reason": "Cookie 'sessionid' đã hết hạn.",
            "expires_in_days": 0,
        }

    days_left = max(0, int((earliest_exp - now) / 86400)) if earliest_exp else 999
    return {
        "valid": True,
        "reason": "Cookie hợp lệ.",
        "expires_in_days": days_left,
    }
