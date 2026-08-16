"""Multi-Brand & Multi-Account Credentials Manager.

Supports platform-specific account configuration files:
- config/facebook_pages.json for Facebook Pages
- config/youtube_channels.json for YouTube Channels
- config/accounts.json for General Multi-Brand mappings
"""

import json
import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

FB_PAGES_FILE = Path("./config/facebook_pages.json")
YT_CHANNELS_FILE = Path("./config/youtube_channels.json")
TIKTOK_ACCOUNTS_FILE = Path("./config/tiktok_accounts.json")
ACCOUNTS_FILE = Path("./config/accounts.json")


def parse_expiry_date(expires_at_str: Optional[str]) -> Optional[datetime]:
    """Parse various expiration date formats (ISO, Vietnamese text, DD/MM/YYYY)."""
    if not expires_at_str or str(expires_at_str).strip().lower() in ["never", "none", ""]:
        return None

    clean_str = str(expires_at_str).strip()

    # Match Vietnamese text format e.g. "5 Tháng 10, 2026" or "05 Tháng 10 2026"
    vn_match = re.match(r"(\d{1,2})\s*Tháng\s*(\d{1,2})[,\s]*(\d{4})", clean_str, re.IGNORECASE)
    if vn_match:
        day, month, year = map(int, vn_match.groups())
        return datetime(year, month, day, 23, 59, 59, tzinfo=timezone.utc)

    # Match DD/MM/YYYY format
    slash_match = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", clean_str)
    if slash_match:
        day, month, year = map(int, slash_match.groups())
        return datetime(year, month, day, 23, 59, 59, tzinfo=timezone.utc)

    # ISO timestamp fallback e.g. "2026-10-05T00:00:00Z"
    try:
        dt = datetime.fromisoformat(clean_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        logger.warning(f"Could not parse expiration timestamp string: '{expires_at_str}'")
        return None


def is_token_expired(expires_at_str: Optional[str]) -> bool:
    """Check if an expiration timestamp has already passed."""
    expiry_dt = parse_expiry_date(expires_at_str)
    if not expiry_dt:
        return False
    now_dt = datetime.now(timezone.utc)
    return now_dt >= expiry_dt


def get_days_until_expiration(expires_at_str: Optional[str]) -> Optional[int]:
    """Calculate remaining days until token expiration."""
    expiry_dt = parse_expiry_date(expires_at_str)
    if not expiry_dt:
        return None
    now_dt = datetime.now(timezone.utc)
    delta = expiry_dt - now_dt
    return max(0, delta.days)


class AccountManager:
    """Manages credentials routing and token expiry checks for multiple brands and platforms."""

    def __init__(
        self,
        fb_pages_file: Optional[Path] = None,
        yt_channels_file: Optional[Path] = None,
        tiktok_accounts_file: Optional[Path] = None,
        accounts_file: Optional[Path] = None,
    ):
        self.fb_pages_file = fb_pages_file or FB_PAGES_FILE
        self.yt_channels_file = yt_channels_file or YT_CHANNELS_FILE
        self.tiktok_accounts_file = tiktok_accounts_file or TIKTOK_ACCOUNTS_FILE
        self.accounts_file = accounts_file or ACCOUNTS_FILE

        self.fb_pages = self._load_json_file(self.fb_pages_file, "pages")
        self.yt_channels = self._load_json_file(self.yt_channels_file, "channels")
        self.tiktok_accounts = self._load_json_file(self.tiktok_accounts_file, "accounts")
        self.accounts_brands = self._load_json_file(self.accounts_file, "brands")

    def _load_json_file(self, file_path: Path, root_key: str) -> Dict[str, Any]:
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f).get(root_key, {})
            except Exception as e:
                logger.warning(f"Error reading {file_path.name}: {e}")
        return {}

    def get_brand_credentials(self, brand_name: str, platform: str) -> Optional[Dict[str, Any]]:
        """Get API credentials and check expiration for a specific brand and platform."""
        plat = platform.lower()

        # 1. Search in platform-specific dedicated JSON files first
        if plat == "facebook":
            creds = self._find_case_insensitive(self.fb_pages, brand_name)
            if creds:
                self._check_expiry_warning(brand_name, platform, creds.get("expires_at"))
                return creds

        elif plat == "youtube":
            creds = self._find_case_insensitive(self.yt_channels, brand_name)
            if creds:
                self._check_expiry_warning(brand_name, platform, creds.get("expires_at"))
                return creds

        elif plat == "instagram":
            creds = self._find_case_insensitive(self.fb_pages, brand_name)
            if creds:
                self._check_expiry_warning(brand_name, platform, creds.get("expires_at"))
                return creds

        elif plat == "tiktok":
            creds = self._find_case_insensitive(self.tiktok_accounts, brand_name)
            if creds:
                return creds

        # 2. Fallback to general accounts.json file
        brand = self._find_case_insensitive(self.accounts_brands, brand_name)
        if brand and plat in brand:
            creds = brand[plat]
            self._check_expiry_warning(brand_name, platform, creds.get("expires_at"))
            return creds

        return None

    def _find_case_insensitive(self, dictionary: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
        if key in dictionary:
            return dictionary[key]
        clean_key = key.strip().lower()
        for k, v in dictionary.items():
            if str(k).strip().lower() == clean_key:
                return v
        return None

    def _check_expiry_warning(self, brand_name: str, platform: str, expires_at: Optional[str]):
        if not expires_at:
            return

        if is_token_expired(expires_at):
            logger.error(
                f"🚨 TOKEN EXPIRED for Brand '{brand_name}' on {platform.upper()}! Expiry: {expires_at}. Please renew token."
            )
        else:
            days_left = get_days_until_expiration(expires_at)
            if days_left is not None and days_left <= 7:
                logger.warning(
                    f"⚠️ Token for Brand '{brand_name}' on {platform.upper()} will expire soon ({days_left} days left, on {expires_at})."
                )

    def list_all_brands(self) -> List[str]:
        """Get unique list of all brands configured across all platforms."""
        brands = set()
        for k in self.fb_pages.keys():
            brands.add(k)
        for k in self.yt_channels.keys():
            brands.add(k)
        for k in self.tiktok_accounts.keys():
            brands.add(k)
        for k in self.accounts_brands.keys():
            brands.add(k)
        return sorted(list(brands))

    def get_active_platforms_for_brand(self, brand_name: str) -> List[str]:
        """Detect which platforms are currently active, authenticated, and ready to post for a brand."""
        active = []

        # 1. Check Facebook
        fb_creds = self.get_brand_credentials(brand_name, "facebook")
        if fb_creds and fb_creds.get("page_id") and not is_token_expired(fb_creds.get("expires_at")):
            active.append("fb")

        # 2. Check YouTube
        yt_creds = self.get_brand_credentials(brand_name, "youtube")
        if yt_creds and yt_creds.get("token_path"):
            t_path = Path(yt_creds["token_path"])
            if t_path.exists():
                active.append("yt")

        # 3. Check Instagram
        ig_creds = self.get_brand_credentials(brand_name, "instagram")
        if ig_creds and ig_creds.get("instagram_account_id") and not is_token_expired(ig_creds.get("expires_at")):
            active.append("ig")

        # 4. Check TikTok (Ready ONLY IF cookie has been imported and verified with status: active)
        tt_creds = self.get_brand_credentials(brand_name, "tiktok")
        if tt_creds and tt_creds.get("status") == "active":
            active.append("tt")

        return active
