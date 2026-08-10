"""Unit tests for Phase 5 Queue, JobRunner, Scheduler & Google Sheet Importer."""
import pytest
from unittest.mock import patch, MagicMock

from core.queue import JobQueue
from core.runner import JobRunner
from core.sheet_importer import GoogleSheetImporter


def test_google_sheet_importer_parse():
    mock_csv = (
        "Mã sản phẩm,Tên sản phẩm,Giá,Doanh thu,Tên cửa hàng,Tỉ lệ hoa hồng,Hoa hồng,Link sản phẩm,Link ưu đãi,Link ảnh CDN chọn lọc,File ảnh lưu local,Trạng thái Master Prompt\n"
        "24438735904,[NE01] Dép Sục Nam Nữ NESTY,120k,10k+,Nesty,19%,22k,https://shopee.vn/p1,https://s.shopee.vn/aff1,http://cdn1,Product_Assets/24438735904/,Đã tạo Video\n"
    )

    importer = GoogleSheetImporter()
    with patch.object(importer, "fetch_sheet_csv", return_value=mock_csv):
        jobs = importer.parse_jobs_from_sheet(target_platforms=["facebook"])

        assert len(jobs) == 1
        assert jobs[0]["product_id"] == "24438735904"
        assert "[NE01]" in jobs[0]["title"]
        assert jobs[0]["affiliate_link"] == "https://s.shopee.vn/aff1"
        assert set(jobs[0]["target_platforms"]) == {"facebook", "youtube", "instagram"}



def test_job_runner_execution(tmp_path):
    db_file = tmp_path / "test_runner.db"
    dummy_video = tmp_path / "video.mp4"
    dummy_video.write_bytes(b"DATA")

    queue = JobQueue(db_path=str(db_file))
    job_id = queue.add_job(
        video_path=str(dummy_video),
        target_platforms=["facebook"],
        title="Test Runner Video",
        description="Caption content",
    )

    runner = JobRunner(db_path=str(db_file))

    # Mock FacebookConnector upload_video response
    mock_fb = MagicMock()
    mock_fb.upload_video.return_value = {
        "status": "success",
        "post_id": "fb_post_999",
        "video_url": "https://facebook.com/fb_post_999",
    }
    runner.connectors["facebook"] = mock_fb

    processed = runner.process_due_jobs()

    assert processed == 1
    mock_fb.upload_video.assert_called_once()

    # Check updated job status in DB
    due = queue.fetch_due_jobs()
    assert len(due) == 0  # No more pending due jobs


def test_job_runner_rate_limit(tmp_path):
    db_file = tmp_path / "test_rate.db"
    queue = JobQueue(db_path=str(db_file))

    # Populate hourly limit (5 posts completed for facebook)
    for i in range(5):
        j_id = queue.add_job(video_path="v.mp4", target_platforms=["facebook"], title=f"Job {i}")
        queue.update_job_status(j_id, "completed", results={"facebook": {"post_id": f"p_{i}"}})

    runner = JobRunner(db_path=str(db_file))

    # Add 6th job which should be deferred by rate limit
    j6_id = queue.add_job(video_path="v.mp4", target_platforms=["facebook"], title="Job 6 Rate Limited")

    mock_fb = MagicMock()
    runner.connectors["facebook"] = mock_fb

    runner.process_due_jobs()

    # Connector should NOT be called due to rate limit
    mock_fb.upload_video.assert_not_called()
