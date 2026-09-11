"""Unit tests for YouTube URL in status_yt column and Two-Way Sync with Spark audit scores."""

import sqlite3
import json
import csv
import pytest
from core.queue import JobQueue
from core.sheet_exporter import MasterSheetExporter


def test_export_master_sheet_with_youtube_url(tmp_path):
    db_file = tmp_path / "test_yt_link.db"
    csv_file = tmp_path / "master_yt_link.csv"

    queue = JobQueue(db_path=str(db_file))
    j_id = queue.add_job(
        video_path="/Volumes/Media/sample.mp4",
        target_platforms=["youtube"],
        title="Test YouTube Shorts",
        extra_options={
            "brand_map": {"youtube": "Mua Chuẩn Xài Lâu"},
            "platform_captions": {"youtube": "Caption Shorts #Shorts"},
        },
    )

    # Simulate completed YouTube job with video_url in results_json
    with sqlite3.connect(str(db_file)) as conn:
        cursor = conn.cursor()
        results = {
            "youtube": {
                "status": "published",
                "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "video_id": "dQw4w9WgXcQ",
            }
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
        assert row["status_yt"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_two_way_sync_youtube_url_and_audit_score(tmp_path):
    db_file = tmp_path / "test_yt_sync.db"
    csv_file = tmp_path / "master_yt_sync.csv"

    queue = JobQueue(db_path=str(db_file))
    j_id1 = queue.add_job(
        video_path="/Volumes/Media/video1.mp4",
        target_platforms=["youtube"],
        title="Video 1",
        extra_options={"item_id": "SP_01"},
    )
    j_id2 = queue.add_job(
        video_path="/Volumes/Media/video2.mp4",
        target_platforms=["youtube"],
        title="Video 2",
        extra_options={"item_id": "SP_02"},
    )

    # Create CSV simulating edits:
    # Row 1 has a YouTube URL in status_yt
    # Row 2 has an audit score "8.5/10" in status_yt
    exporter = MasterSheetExporter(db_path=str(db_file), output_csv=csv_file)
    exporter.export_master_sheet(skip_sync=True)

    # Edit CSV
    rows = []
    with open(csv_file, "r", encoding="utf-8-sig") as f:
        reader = list(csv.DictReader(f))
        for r in reader:
            if r["job_id"] == "SP_01":
                r["status_yt"] = "https://youtu.be/abc123xyz"
            elif r["job_id"] == "SP_02":
                r["status_yt"] = "8.5/10"
            rows.append(r)

    with open(csv_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # Run two-way sync from edited CSV text
    edited_text = csv_file.read_text(encoding="utf-8-sig")
    exporter._sync_two_way_statuses(csv_text=edited_text)

    # Verify DB
    with sqlite3.connect(str(db_file)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, results_json FROM jobs WHERE id = ?", (j_id1,))
        r1 = cursor.fetchone()
        data1 = json.loads(r1["results_json"])
        assert data1["youtube"]["status"] == "published"
        assert data1["youtube"]["video_url"] == "https://youtu.be/abc123xyz"

        cursor.execute("SELECT id, results_json FROM jobs WHERE id = ?", (j_id2,))
        r2 = cursor.fetchone()
        data2 = json.loads(r2["results_json"])
        assert data2["youtube"]["status"] == "published"
