"""Unit tests for Phase 4 platform uploaders with mock API calls."""
import os
import pytest
from unittest.mock import patch, MagicMock

from connectors.base import PostMetadata
from connectors.facebook.uploader import FacebookUploader
from connectors.youtube.uploader import YouTubeUploader
from connectors.instagram.uploader import InstagramUploader


def test_facebook_resumable_upload_success(tmp_path):
    dummy_video = tmp_path / "sample.mp4"
    dummy_video.write_bytes(b"A" * (5 * 1024 * 1024))  # 5MB dummy video

    metadata = PostMetadata(
        title="Test Facebook Video",
        description="Demo caption for Facebook page video upload",
    )

    uploader = FacebookUploader(page_id="12345", access_token="fake_token")

    with patch("requests.post") as mock_post:
        # Response 1: Start phase
        res_start = MagicMock()
        res_start.status_code = 200
        res_start.json.return_value = {
            "upload_session_id": "session_999",
            "video_id": "vid_001",
            "start_offset": 0,
            "end_offset": 4194304,
        }

        # Response 2: Transfer chunk phase
        res_transfer = MagicMock()
        res_transfer.status_code = 200
        res_transfer.json.return_value = {
            "start_offset": 5242880,
            "end_offset": 5242880,
        }

        # Response 3: Finish phase
        res_finish = MagicMock()
        res_finish.status_code = 200
        res_finish.json.return_value = {
            "success": True,
            "id": "vid_001",
        }

        mock_post.side_effect = [res_start, res_transfer, res_finish]

        result = uploader.upload(str(dummy_video), metadata)

        assert result["status"] == "success"
        assert result["post_id"] == "vid_001"
        assert result["platform"] == "facebook"
        assert mock_post.call_count == 3


def test_youtube_resumable_upload_success(tmp_path):
    dummy_video = tmp_path / "sample.mp4"
    dummy_video.write_bytes(b"B" * 1000)

    metadata = PostMetadata(
        title="Test YouTube Shorts",
        description="Demo description",
        tags=["shorts", "demo"],
    )

    mock_yt_service = MagicMock()
    mock_insert_req = MagicMock()
    mock_yt_service.videos().insert.return_value = mock_insert_req

    mock_status = MagicMock()
    mock_status.progress.return_value = 1.0
    mock_insert_req.next_chunk.return_value = (mock_status, {"id": "yt_video_123"})

    with patch("connectors.youtube.uploader.MediaFileUpload"):
        uploader = YouTubeUploader(youtube_service=mock_yt_service)
        result = uploader.upload(str(dummy_video), metadata)

        assert result["status"] == "success"
        assert result["post_id"] == "yt_video_123"
        assert "youtube.com/watch?v=yt_video_123" in result["video_url"]


def test_instagram_reels_upload_success(tmp_path):
    dummy_video = tmp_path / "reels.mp4"
    dummy_video.write_bytes(b"C" * 1000)

    metadata = PostMetadata(
        title="Test Instagram Reels",
        description="Awesome Reels content",
    )

    uploader = InstagramUploader(instagram_account_id="ig_123", access_token="fake_token")

    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        # 1. Init container response
        res_container = MagicMock()
        res_container.status_code = 200
        res_container.json.return_value = {"id": "container_777", "uri": "https://rupload.facebook.com/ig-reels-upload/v19.0/container_777"}

        # 2. Binary rupload response
        res_rupload = MagicMock()
        res_rupload.status_code = 200

        # 3. Publish container response
        res_publish = MagicMock()
        res_publish.status_code = 200
        res_publish.json.return_value = {"id": "ig_media_888"}

        mock_post.side_effect = [res_container, res_rupload, res_publish]

        # Poll status response
        res_status = MagicMock()
        res_status.status_code = 200
        res_status.json.return_value = {"status_code": "FINISHED", "id": "container_777"}
        mock_get.return_value = res_status

        result = uploader.upload(str(dummy_video), metadata)

        assert result["status"] == "success"
        assert result["post_id"] == "ig_media_888"
        assert result["platform"] == "instagram"


def test_tiktok_cookie_normalization():
    from connectors.tiktok.browser_uploader import _normalize_cookie_editor_export

    raw_cookies = [
        {
            "name": "sessionid",
            "value": "fake_session_12345",
            "domain": ".tiktok.com",
            "path": "/",
            "sameSite": "no_restriction",
            "secure": True,
            "httpOnly": True,
            "session": True,
        },
        {
            "name": "tt_csrf_token",
            "value": "token_abc",
            "domain": ".tiktok.com",
            "path": "/",
            "sameSite": "lax",
            "secure": True,
            "httpOnly": False,
            "expirationDate": 1789000000.5,
        },
    ]

    normalized = _normalize_cookie_editor_export(raw_cookies)
    assert len(normalized) == 2
    assert normalized[0]["name"] == "sessionid"
    assert normalized[0]["sameSite"] == "None"
    assert "expires" not in normalized[0]  # session cookie has no expires or -1 omitted

    assert normalized[1]["name"] == "tt_csrf_token"
    assert normalized[1]["sameSite"] == "Lax"
    assert normalized[1]["expires"] == 1789000000

