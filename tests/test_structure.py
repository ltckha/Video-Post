"""Unit tests for Phase 1 project structure and imports."""
import pytest
from config.settings import settings
from connectors.base import BasePlatformConnector, PostMetadata
from connectors.youtube import YouTubeConnector
from connectors.facebook import FacebookConnector
from connectors.instagram import InstagramConnector
from core.media_processor import get_video_info
from core.queue import JobQueue


def test_settings_load():
    assert settings.APP_ENV in ["development", "production", "testing"]
    assert settings.LOGS_DIR is not None


def test_connectors_instantiation():
    yt = YouTubeConnector()
    fb = FacebookConnector()
    ig = InstagramConnector()

    assert yt.platform_name == "youtube"
    assert fb.platform_name == "facebook"
    assert ig.platform_name == "instagram"


def test_post_metadata_creation():
    meta = PostMetadata(
        title="Test Video",
        description="Test Caption #shorts",
        tags=["test", "shorts"],
    )
    assert meta.title == "Test Video"
    assert meta.privacy_status == "public"


def test_job_queue_init(tmp_path):
    db_file = tmp_path / "test_jobs.db"
    queue = JobQueue(db_path=str(db_file))
    job_id = queue.add_job(
        video_path="input_videos/demo.mp4",
        target_platforms=["youtube", "facebook"],
        title="Test Job",
    )
    assert job_id == 1
    pending = queue.fetch_pending_jobs()
    assert len(pending) == 1
    assert pending[0]["title"] == "Test Job"
