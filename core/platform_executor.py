"""Platform Executor module for executing social video uploads."""
import logging
from typing import Any, Dict, Optional
from connectors.base import PostMetadata

logger = logging.getLogger(__name__)


class PlatformExecutor:
    """Executes single platform video uploads using configured connector adapters."""

    def execute_upload(
        self,
        platform: str,
        connector: Any,
        video_path: str,
        metadata: PostMetadata,
        brand_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload video to target platform and return normalized result dictionary."""
        logger.info(f"Executing upload to {platform.upper()} (Brand: '{brand_name or 'Default'}')...")

        if platform == "tiktok":
            profile_dir = getattr(connector, "profile_dir", "config/browser_profiles/tiktok_default")
            caption_text = metadata.description or metadata.title
            res = connector.upload_video(
                video_path=video_path,
                caption=caption_text,
                profile_dir=profile_dir,
            )
        else:
            res = connector.upload_video(video_path, metadata)

        if not isinstance(res, dict):
            res = {"status": "success", "raw_response": str(res)}

        # Normalize status to 'published'
        if res.get("status") in ["success", "published", True]:
            res["status"] = "published"

        logger.info(f"Successfully published to {platform.upper()} for '{brand_name or 'Default'}': {res.get('video_url', res.get('post_id', 'OK'))}")
        return res
