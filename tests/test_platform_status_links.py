"""Unit tests for live post URLs in status_fb, status_yt, status_ig, status_tt columns and Two-Way Sync."""

import sqlite3
import json
import csv
import pytest
from core.queue import JobQueue
from core.sheet_exporter import MasterSheetExporter


def test_export_master_sheet_with_all_platform_urls(tmp_path):
    db_file = tmp_path / "test_multi_urls.db"
    csv_file = tmp_path / "master_multi_urls.csv"

    queue = JobQueue(db_path=str(db_file))
    j_id = queue.add_job(
        video_path="/Volumes/Media/sample_all.mp4",
        target_platforms=["facebook", "youtube", "instagram", "tiktok"],
        title="Test Multi Platform Video",
        extra_options={
            "item_id": "SP_MULTI_01",
            "brand_map": {
                "facebook": "Mua Chuẩn Xài Lâu",
                "youtube": "Mua Chuẩn Xài Lâu",
                "instagram": "Mua Chuẩn Xài Lâu",
                "tiktok": "Mua Chuẩn Xài Lâu",
            },
        },
    )

    # Simulate completed jobs with video_urls in results_json
    with sqlite3.connect(str(db_file)) as conn:
        cursor = conn.cursor()
        results = {
            "facebook": {
                "status": "published",
                "video_url": "https://www.facebook.com/123456789_987654321",
                "post_id": "123456789_987654321",
            },
            "youtube": {
                "status": "published",
                "video_url": "https://www.youtube.com/shorts/abcShort123",
                "video_id": "abcShort123",
            },
            "instagram": {
                "status": "published",
                "video_url": "https://www.instagram.com/reel/C1234567890",
                "media_id": "C1234567890",
            },
            "tiktok": {
                "status": "published",
                "video_url": "https://www.tiktok.com/@muachuanxailau/video/7123456789012345678",
            },
        }
        cursor.execute(
            "UPDATE jobs SET status = 'completed', results_json = ? WHERE id = ?",
            (json.dumps(results), j_id),
        )
        conn.commit()

    exporter = MasterSheetExporter(db_path=str(db_file), output_csv=csv_file)
    exported = exporter.export_master_sheet()

    with open(exported, "r", encoding="utf-8-sig") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 1
        row = reader[0]
        assert row["status_fb"] == "https://www.facebook.com/123456789_987654321"
        assert row["status_yt"] == "https://www.youtube.com/shorts/abcShort123"
        assert row["status_ig"] == "https://www.instagram.com/reel/C1234567890"
        assert row["status_tt"] == "https://www.tiktok.com/@muachuanxailau/video/7123456789012345678"


def test_two_way_sync_multi_platform_urls(tmp_path):
    db_file = tmp_path / "test_multi_sync.db"
    csv_file = tmp_path / "master_multi_sync.csv"

    queue = JobQueue(db_path=str(db_file))
    j_id = queue.add_job(
        video_path="/Volumes/Media/video_sync.mp4",
        target_platforms=["facebook", "youtube", "instagram", "tiktok"],
        title="Sync Test Video",
        extra_options={"item_id": "SP_SYNC_01"},
    )

    exporter = MasterSheetExporter(db_path=str(db_file), output_csv=csv_file)
    exporter.export_master_sheet(skip_sync=True)

    # Edit CSV to include live URLs in status columns
    rows = []
    with open(csv_file, "r", encoding="utf-8-sig") as f:
        reader = list(csv.DictReader(f))
        for r in reader:
            if r["job_id"] == "SP_SYNC_01":
                r["status_fb"] = "https://www.facebook.com/fb_post_999"
                r["status_yt"] = "https://www.youtube.com/shorts/yt_short_999"
                r["status_ig"] = "https://www.instagram.com/reel/ig_reel_999"
                r["status_tt"] = "https://www.tiktok.com/@user/video/tt_vid_999"
            rows.append(r)

    with open(csv_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    edited_text = csv_file.read_text(encoding="utf-8-sig")
    exporter._sync_two_way_statuses(csv_text=edited_text)

    # Verify DB has recorded published status and video URLs
    with sqlite3.connect(str(db_file)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, results_json FROM jobs WHERE id = ?", (j_id,))
        row = cursor.fetchone()
        data = json.loads(row["results_json"])

        assert data["facebook"]["status"] == "published"
        assert data["facebook"]["video_url"] == "https://www.facebook.com/fb_post_999"

        assert data["youtube"]["status"] == "published"
        assert data["youtube"]["video_url"] == "https://www.youtube.com/shorts/yt_short_999"

        assert data["instagram"]["status"] == "published"
        assert data["instagram"]["video_url"] == "https://www.instagram.com/reel/ig_reel_999"

        assert data["tiktok"]["status"] == "published"
        assert data["tiktok"]["video_url"] == "https://www.tiktok.com/@user/video/tt_vid_999"
