"""Unit tests for TikTok IndexedDB Draft Storage Safe Cleanup."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from connectors.tiktok.browser_uploader import (
    get_directory_size_bytes,
    format_bytes_human,
    safe_cleanup_tiktok_draft_storage,
    TikTokBrowserConnector,
)


def test_directory_size_and_formatting(tmp_path):
    """Test directory size calculation and human readable byte formatting."""
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    
    # 0 bytes initially
    assert get_directory_size_bytes(test_dir) == 0
    assert format_bytes_human(500) == "0.5 KB"

    # Create a 5MB dummy file
    f1 = test_dir / "file1.bin"
    f1.write_bytes(b"x" * (5 * 1024 * 1024))
    
    size = get_directory_size_bytes(test_dir)
    assert size == 5 * 1024 * 1024
    assert format_bytes_human(size) == "5.00 MB"
    assert format_bytes_human(2 * 1024 * 1024 * 1024) == "2.00 GB"


def test_safe_cleanup_disabled_mode(tmp_path):
    """Test that disabled mode skips cleanup completely."""
    profile_dir = tmp_path / "tiktok_test_profile"
    idb_dir = profile_dir / "Default" / "IndexedDB"
    idb_dir.mkdir(parents=True)
    (idb_dir / "data.blob").write_bytes(b"x" * 1024)

    mock_page = MagicMock()
    
    res = safe_cleanup_tiktok_draft_storage(
        page=mock_page,
        profile_dir=profile_dir,
        brand_name="TestBrand",
        mode="disabled"
    )

    assert res["status"] == "skipped"
    assert res["mode"] == "disabled"
    # evaluate() should NOT be called to inspect or delete
    mock_page.evaluate.assert_not_called()


def test_safe_cleanup_dry_run_mode(tmp_path):
    """Test that dry-run mode identifies targets but does not delete them."""
    profile_dir = tmp_path / "tiktok_test_profile"
    idb_dir = profile_dir / "Default" / "IndexedDB"
    idb_dir.mkdir(parents=True)
    (idb_dir / "dummy.blob").write_bytes(b"x" * (10 * 1024 * 1024))

    mock_page = MagicMock()
    # Mock finding 'web_creation_draft'
    mock_page.evaluate.return_value = ["web_creation_draft"]

    res = safe_cleanup_tiktok_draft_storage(
        page=mock_page,
        profile_dir=profile_dir,
        brand_name="TestBrand",
        mode="dry-run"
    )

    assert res["status"] == "dry-run"
    assert res["mode"] == "dry-run"
    assert res["targets"] == ["web_creation_draft"]
    assert "10.00 MB" in res["size_before"]
    # Only 1 evaluate call (inspection), not deletion call
    assert mock_page.evaluate.call_count == 1


def test_safe_cleanup_enabled_mode(tmp_path):
    """Test that enabled mode triggers deleteDatabase and records metrics."""
    profile_dir = tmp_path / "tiktok_test_profile"
    idb_dir = profile_dir / "Default" / "IndexedDB"
    idb_dir.mkdir(parents=True)
    blob_file = idb_dir / "dummy.blob"
    blob_file.write_bytes(b"x" * (50 * 1024 * 1024))

    mock_page = MagicMock()
    # 1st call: returns target ['web_creation_draft']
    # 2nd call: returns deleted ['web_creation_draft']
    mock_page.evaluate.side_effect = [
        ["web_creation_draft"],
        ["web_creation_draft"],
    ]

    # Simulate browser deletion of the blob file
    def mock_wait(timeout):
        if blob_file.exists():
            blob_file.unlink()

    mock_page.wait_for_timeout.side_effect = mock_wait

    res = safe_cleanup_tiktok_draft_storage(
        page=mock_page,
        profile_dir=profile_dir,
        brand_name="TestBrand",
        mode="enabled"
    )

    assert res["status"] == "cleaned"
    assert res["mode"] == "enabled"
    assert res["deleted_databases"] == ["web_creation_draft"]
    assert "50.00 MB" in res["size_before"]
    assert "50.00 MB" in res["freed"]
    assert mock_page.evaluate.call_count == 2


def test_publish_failure_preserves_draft(tmp_path):
    """Test that if publishing fails, safe_cleanup is NEVER called, preserving draft data."""
    connector = TikTokBrowserConnector(brand_name="TestBrand", profile_dir=str(tmp_path))
    
    dummy_video = tmp_path / "test.mp4"
    dummy_video.write_bytes(b"dummy video content")

    mock_context = MagicMock()
    mock_page = MagicMock()
    mock_context.pages = [mock_page]
    mock_page.url = "https://www.tiktok.com/tiktokstudio/upload"
    
    # Simulate file input failure
    mock_page.locator.return_value.first.wait_for.side_effect = RuntimeError("File input locator timed out")

    with patch.object(connector, "_get_context", return_value=mock_context),          patch("connectors.tiktok.browser_uploader.safe_cleanup_tiktok_draft_storage") as mock_cleanup,          patch("connectors.tiktok.browser_uploader.HumanSimulator"):

        with pytest.raises(RuntimeError, match="File input locator timed out"):
            connector.upload_video(video_path=str(dummy_video))

        # Cleanup MUST NOT be called on failure
        mock_cleanup.assert_not_called()
