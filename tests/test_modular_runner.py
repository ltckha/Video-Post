"""Unit tests for Stage 2 Modular Architecture: RateLimiter, AccountResolver, PlatformExecutor, and AI Metadata."""
import pytest
from unittest.mock import MagicMock
from pathlib import Path

from core.rate_limiter import RateLimiter
from core.account_resolver import AccountResolver
from core.platform_executor import PlatformExecutor
from core.ai_captioner import AICaptionGenerator
from connectors.base import PostMetadata


def test_rate_limiter_logic():
    limiter = RateLimiter(limits={"facebook": 3, "youtube": 5})
    
    # Under limit
    allowed, msg = limiter.check_rate_limit("facebook", 2)
    assert allowed is True
    assert msg == ""

    # At limit
    allowed, msg = limiter.check_rate_limit("facebook", 3)
    assert allowed is False
    assert "Rate limit reached" in msg


def test_platform_executor_success():
    executor = PlatformExecutor()
    mock_connector = MagicMock()
    mock_connector.upload_video.return_value = {
        "status": "success",
        "post_id": "test_post_123",
        "video_url": "https://example.com/video/123",
    }

    metadata = PostMetadata(title="Test Video", description="Awesome content")
    res = executor.execute_upload(
        platform="facebook",
        connector=mock_connector,
        video_path="video.mp4",
        metadata=metadata,
        brand_name="Test Brand",
    )

    assert res["status"] == "published"
    assert res["post_id"] == "test_post_123"
    mock_connector.upload_video.assert_called_once_with("video.mp4", metadata)


def test_ai_captioner_publishing_package_prompt():
    ai = AICaptionGenerator(api_key=None)  # Offline fallback
    captions = ai.generate_all_captions(
        title="[NE50] Dép Sục Nguyên Khối NESTY",
        raw_caption="Dép siêu êm",
        product_usp="Đúc nguyên khối 120g chống trơn trượt",
        target_audience="Học sinh sinh viên",
        brand_tone="Trẻ trung năng động",
    )

    assert len(captions) == 6
    assert "facebook" in captions
    assert "youtube" in captions
    assert "instagram" in captions
    assert "tiktok" in captions
    assert "shopee" in captions
    assert "zalo" in captions
    assert len(captions["shopee"]) <= 150
