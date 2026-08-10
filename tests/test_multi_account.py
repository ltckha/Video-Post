"""Unit tests for Multi-Brand & Multi-Account Routing Architecture with Expiry Check."""

import json
import pytest
from unittest.mock import patch, MagicMock

from core.account_manager import AccountManager, is_token_expired, get_days_until_expiration
from core.sheet_importer import SmartGoogleSheetImporter
from core.runner import JobRunner
from core.queue import JobQueue


def test_is_token_expired():
    assert is_token_expired("2020-01-01T00:00:00Z") is True
    assert is_token_expired("2099-12-31T23:59:59Z") is False
    assert is_token_expired("never") is False


def test_account_manager_facebook_pages_lookup(tmp_path):
    pages_file = tmp_path / "facebook_pages.json"
    dummy_pages = {
        "pages": {
            "Ở Đà Lạt Vậy Thôi": {
                "page_id": "dalat_123",
                "access_token": "token_dalat_abc",
                "expires_at": "2099-12-31T23:59:59Z",
            },
            "Yen Handmade Leather": {
                "page_id": "leather_456",
                "access_token": "token_leather_xyz",
                "expires_at": "2020-01-01T00:00:00Z",
            },
        }
    }
    pages_file.write_text(json.dumps(dummy_pages))

    mgr = AccountManager(fb_pages_file=pages_file)

    creds_dalat = mgr.get_brand_credentials("Ở Đà Lạt Vậy Thôi", "facebook")
    assert creds_dalat["page_id"] == "dalat_123"
    assert creds_dalat["expires_at"] == "2099-12-31T23:59:59Z"

    creds_leather = mgr.get_brand_credentials("Yen Handmade Leather", "facebook")
    assert creds_leather["page_id"] == "leather_456"

    assert mgr.get_brand_credentials("NonExistentPage", "facebook") is None


def test_job_runner_brand_routing(tmp_path):
    db_file = tmp_path / "test_brand_routing.db"
    pages_file = tmp_path / "facebook_pages.json"

    dummy_pages = {
        "pages": {
            "Yen Handmade Leather": {
                "page_id": "page_leather_999",
                "access_token": "token_leather_xxx",
                "expires_at": "2099-12-31T23:59:59Z",
            }
        }
    }
    pages_file.write_text(json.dumps(dummy_pages))

    queue = JobQueue(db_path=str(db_file))
    j_id = queue.add_job(
        video_path="demo.mp4",
        target_platforms=["facebook"],
        title="Bao Da Handmade",
        extra_options={"brand_map": {"facebook": "Yen Handmade Leather"}},
    )

    runner = JobRunner(db_path=str(db_file))

    # Mock Facebook connector upload
    mock_fb = MagicMock()
    mock_fb.upload_video.return_value = {"status": "success", "post_id": "fb_post_111"}
    runner.connectors["facebook"] = mock_fb

    with patch("core.account_manager.FB_PAGES_FILE", pages_file):
        runner.process_due_jobs(dry_run=False)

        assert mock_fb.page_id == "page_leather_999"
        assert mock_fb.access_token == "token_leather_xxx"
        mock_fb.upload_video.assert_called_once()
