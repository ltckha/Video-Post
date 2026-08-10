"""SQLite Job Queue Manager module.

Stores and manages video posting jobs, rate limiting counters, and post execution status.
"""
import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class JobQueue:
    """Manages video publishing job queue stored in SQLite database."""

    def __init__(self, db_path: str = "video_post.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_path TEXT NOT NULL,
                    target_platforms TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    tags TEXT,
                    privacy_status TEXT DEFAULT 'public',
                    scheduled_at DATETIME,
                    status TEXT DEFAULT 'pending',
                    attempts INTEGER DEFAULT 0,
                    error_message TEXT,
                    results_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_job(
        self,
        video_path: str,
        target_platforms: List[str],
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        privacy_status: str = "public",
        scheduled_at: Optional[str] = None,
        extra_options: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Enqueue a new video posting job or update existing if item_id/video_path matches (Deduplication)."""
        platforms_str = ",".join(target_platforms)
        tags_str = ",".join(tags) if tags else ""
        results_str = json.dumps(extra_options) if extra_options else None
        item_id = extra_options.get("item_id") if extra_options else None

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Check if job with same video_path or same item_id exists
            existing_job = None
            if video_path:
                cursor.execute("SELECT * FROM jobs WHERE video_path = ?", (video_path,))
                existing_job = cursor.fetchone()

            if existing_job:
                # Update existing job instead of duplicating
                j_id = existing_job["id"]
                cursor.execute(
                    """
                    UPDATE jobs
                    SET target_platforms = ?, title = ?, description = ?, tags = ?, results_json = ?, updated_at = datetime('now', 'localtime')
                    WHERE id = ?
                """,
                    (platforms_str, title, description, tags_str, results_str, j_id),
                )
                conn.commit()
                logger.info(f"Updated existing Job #{j_id} (Deduplicated by video_path/item_id): {title}")
                return j_id

            # Insert new job if not found
            cursor.execute(
                """
                INSERT INTO jobs (
                    video_path, target_platforms, title, description, tags, privacy_status, scheduled_at, status, results_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
                (video_path, platforms_str, title, description, tags_str, privacy_status, scheduled_at, results_str),
            )
            conn.commit()
            job_id = cursor.lastrowid
            logger.info(f"Enqueued NEW Job #{job_id}: {title} -> [{platforms_str}]")
            return job_id



    def fetch_due_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch pending jobs ready for processing (due now or unscheduled)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM jobs 
                WHERE status = 'pending' 
                AND (scheduled_at IS NULL OR scheduled_at <= datetime('now', 'localtime'))
                ORDER BY created_at ASC 
                LIMIT ?
            """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def fetch_partial_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch jobs that were partially successful or failed and need retry."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM jobs 
                WHERE status IN ('partial', 'failed')
                ORDER BY updated_at ASC 
                LIMIT ?
            """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def fetch_pending_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Backward-compatible alias for fetch_due_jobs."""
        return self.fetch_due_jobs(limit=limit)


    def update_job_status(
        self,
        job_id: int,
        status: str,
        error_message: Optional[str] = None,
        results: Optional[Dict[str, Any]] = None,
    ):
        """Update status, attempts, error message and results JSON for a job."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if results is not None:
                results_str = json.dumps(results)
                cursor.execute(
                    """
                    UPDATE jobs 
                    SET status = ?, 
                        attempts = attempts + 1, 
                        error_message = ?, 
                        results_json = ?, 
                        updated_at = datetime('now', 'localtime')
                    WHERE id = ?
                """,
                    (status, error_message, results_str, job_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE jobs 
                    SET status = ?, 
                        attempts = attempts + 1, 
                        error_message = ?, 
                        updated_at = datetime('now', 'localtime')
                    WHERE id = ?
                """,
                    (status, error_message, job_id),
                )
            conn.commit()
            logger.info(f"Updated Job #{job_id} status to '{status}'")


    def get_hourly_post_count(self, platform: str) -> int:
        """Count successful posts for a platform within the last 1 hour for rate limiting."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM jobs 
                WHERE status = 'completed' 
                AND target_platforms LIKE ?
                AND updated_at >= datetime('now', '-1 hour', 'localtime')
            """,
                (f"%{platform}%",),
            )
            return cursor.fetchone()[0]
