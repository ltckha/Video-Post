from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class PostMetadata(BaseModel):
    """Unified metadata model across all social media platforms."""
    title: str = Field(..., description="Video title")
    description: str = Field(default="", description="Video caption or description")
    tags: list[str] = Field(default_factory=list, description="List of hashtags or tags")
    privacy_status: str = Field(default="public", description="public, private, or unlisted")
    scheduled_time: Optional[str] = Field(default=None, description="ISO timestamp for scheduled post")
    thumbnail_path: Optional[str] = Field(default=None, description="Path to custom cover/thumbnail image")
    extra_options: Dict[str, Any] = Field(default_factory=dict, description="Platform-specific metadata overrides")


class BasePlatformConnector(ABC):
    """Abstract Base Class for social media platform connectors."""

    def __init__(self, platform_name: str):
        self.platform_name = platform_name

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the platform API or load valid tokens."""
        pass

    @abstractmethod
    def refresh_access_token(self) -> str:
        """Refresh expired access token."""
        pass

    @abstractmethod
    def upload_video(self, video_path: str, metadata: PostMetadata) -> Dict[str, Any]:
        """Upload video to the platform and return post details (e.g. post_id, URL)."""
        pass
