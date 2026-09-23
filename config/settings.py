from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """Global configuration settings for Video-Post workflow."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # App Environment
    APP_ENV: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    DATABASE_PATH: str = Field(default="sqlite:///./video_post.db")

    # YouTube API
    YOUTUBE_CLIENT_ID: Optional[str] = Field(default=None)
    YOUTUBE_CLIENT_SECRET: Optional[str] = Field(default=None)
    YOUTUBE_REDIRECT_URI: str = Field(default="http://localhost:8080/oauth2callback")
    YOUTUBE_TOKEN_PATH: str = Field(default="./config/tokens/youtube_token.json")

    # Facebook API
    FACEBOOK_APP_ID: Optional[str] = Field(default=None)
    FACEBOOK_APP_SECRET: Optional[str] = Field(default=None)
    FACEBOOK_PAGE_ID: Optional[str] = Field(default=None)
    FACEBOOK_ACCESS_TOKEN: Optional[str] = Field(default=None)

    # Instagram API
    INSTAGRAM_ACCOUNT_ID: Optional[str] = Field(default=None)
    INSTAGRAM_ACCESS_TOKEN: Optional[str] = Field(default=None)

    # Directories
    INPUT_VIDEOS_DIR: Path = Field(default=Path("./input_videos"))
    PROCESSED_VIDEOS_DIR: Path = Field(default=Path("./processed_videos"))
    LOGS_DIR: Path = Field(default=Path("./logs"))

    # AI Engine Credentials
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    GEMINI_MODEL: str = Field(default="gemini-3.5-flash-lite")
    GEMINI_RPM_DELAY: int = Field(default=4)
    GEMINI_MAX_RPD: int = Field(default=500)

    # Master Sheet URL (Direct API v4)
    MASTER_SHEET_URL: str = Field(default="https://docs.google.com/spreadsheets/d/1Xg67qhp1J_Izt7v5uDKRgKjdEZapX9giKJ_ym0OMJN4/")

    # Alerts
    SLACK_WEBHOOK_URL: Optional[str] = Field(default=None)
    ALERT_EMAIL_RECIPIENT: Optional[str] = Field(default=None)

    # TikTok Browser Automation & IndexedDB Cleanup Settings
    # Modes: 'disabled' (no cleanup), 'dry-run' (measure & log without deleting), 'enabled' (cleanup draft database)
    TIKTOK_CLEANUP_MODE: str = Field(default="enabled")

settings = Settings()



