"""Job Runner Orchestrator module.

Coordinates job execution from SQLite queue using RateLimiter, AccountResolver, and PlatformExecutor.
"""
import json
from typing import Dict, Any, List, Optional
from config import settings
from connectors.base import PostMetadata
from connectors.facebook import FacebookConnector
from connectors.youtube import YouTubeConnector
from connectors.instagram import InstagramConnector
from connectors.tiktok.browser_uploader import TikTokBrowserUploader
from core.queue import JobQueue
from core.alerter import AlertManager
from core.logger import logger
from core.rate_limiter import RateLimiter, DEFAULT_RATE_LIMITS, RATE_LIMITS
from core.account_resolver import AccountResolver
from core.platform_executor import PlatformExecutor


class JobRunner:
    """Orchestrates video posting jobs across multi-platform connectors."""

    def __init__(self, db_path: str = "video_post.db"):
        self.queue = JobQueue(db_path=db_path)
        self.alerter = AlertManager()
        self.rate_limiter = RateLimiter()
        self.account_resolver = AccountResolver()
        self.platform_executor = PlatformExecutor()

        self.connectors = {
            "facebook": FacebookConnector(),
            "youtube": YouTubeConnector(),
            "instagram": InstagramConnector(),
            "tiktok": TikTokBrowserUploader(),
        }

    def process_due_jobs(self, limit: int = 1, dry_run: bool = False) -> int:
        """Process all pending due jobs in queue respecting rate limits (default 1 job per run)."""
        due_jobs = self.queue.fetch_due_jobs(limit=limit)

        if not due_jobs:
            logger.info("No due jobs found in queue.")
            return 0

        processed_count = 0
        for job in due_jobs:
            self._execute_single_job(job, dry_run=dry_run)
            processed_count += 1

        return processed_count

    def process_partial_jobs(self, limit: int = 1, dry_run: bool = False) -> int:
        """Process jobs that partially failed and retry only the failed platforms."""
        partial_jobs = self.queue.fetch_partial_jobs(limit=limit)

        if not partial_jobs:
            logger.info("No partial/failed jobs found to retry.")
            return 0

        processed_count = 0
        for job in partial_jobs:
            logger.info(f"🔄 Retrying partial/failed Job #{job['id']}: {job['title']}")
            self._execute_single_job(job, dry_run=dry_run)
            processed_count += 1

        return processed_count

    def _execute_single_job(self, job: Dict[str, Any], dry_run: bool = False):
        """Execute a single multi-platform posting job with clean sub-module delegation."""
        job_id = job["id"]
        title = job["title"]
        video_path = job["video_path"]
        platforms = [p.strip() for p in job["target_platforms"].split(",") if p.strip()]

        # 1. Parse brand routing and platform captions
        brand_map = {}
        platform_captions = {}
        if job.get("results_json"):
            try:
                data = json.loads(job["results_json"])
                if isinstance(data, dict):
                    b_data = data.get("brand_map", data)
                    if isinstance(b_data, dict):
                        brand_map = b_data
                    elif isinstance(b_data, str):
                        brand_map = {p: b_data for p in platforms}
                    platform_captions = data.get("platform_captions", {})
            except Exception as e:
                logger.warning(f"Error parsing results_json: {e}")

        # 2. Handle DRY-RUN Mode
        if dry_run:
            brand_info = ", ".join([f"{p.upper()}: '{brand_map.get(p, 'Default')}'" for p in platforms])
            logger.info(f"[DRY-RUN] Simulating Job #{job_id}: '{title}' on platforms {platforms} 👉 (Fanpage Target: {brand_info})")
            mock_results = {p: {"status": "dry_run_success", "post_id": f"mock_post_{job_id}"} for p in platforms}
            self.queue.update_job_status(job_id, "completed", results=mock_results)
            return

        logger.info(f"Processing Job #{job_id}: '{title}' for platforms {platforms}...")
        self.queue.update_job_status(job_id, "processing")

        metadata = PostMetadata(
            title=job["title"],
            description=job["description"] or "",
            tags=[t.strip() for t in job["tags"].split(",") if t.strip()] if job.get("tags") else [],
            privacy_status=job.get("privacy_status", "public"),
        )

        results = {}
        if job.get("results_json"):
            try:
                old_data = json.loads(job["results_json"])
                if isinstance(old_data, dict):
                    results = old_data
            except Exception:
                pass

        errors = []

        # 3. Iterate platforms and delegate to specialized sub-modules
        for platform in platforms:
            if results.get(platform, {}).get("status") == "published":
                logger.info(f"Skipping {platform} for Job #{job_id} as it is already published.")
                continue

            if platform not in self.connectors:
                err = f"Unsupported platform: {platform}"
                logger.error(err)
                results[platform] = {"status": "failed", "error": err}
                errors.append(err)
                continue

            brand_name = brand_map.get(platform)
            connector = self.connectors[platform]

            # Module 1: Account Resolver
            is_configured = self.account_resolver.configure_connector(platform, brand_name, connector)
            if not is_configured:
                err = f"Missing credentials for {platform} (brand: {brand_name})."
                logger.warning(err)
                results[platform] = {"status": "not_configured", "error": err}
                errors.append(err)
                continue

            # Module 2: Rate Limiter
            current_hourly = self.queue.get_hourly_post_count(platform)
            allowed, limit_msg = self.rate_limiter.check_rate_limit(platform, current_hourly)
            if not allowed:
                results[platform] = {"status": "failed", "error": limit_msg}
                errors.append(limit_msg)
                continue

            # Assign platform-specific caption if available
            specific_caption = platform_captions.get(platform)
            metadata.description = specific_caption if specific_caption else (job["description"] or "")

            # Module 3: Platform Executor
            try:
                upload_res = self.platform_executor.execute_upload(
                    platform=platform,
                    connector=connector,
                    video_path=video_path,
                    metadata=metadata,
                    brand_name=brand_name,
                )
                results[platform] = upload_res
            except Exception as e:
                err_msg = f"Failed to upload to {platform} for brand '{brand_name}': {e}"
                logger.error(err_msg)
                results[platform] = {"status": "failed", "error": err_msg}
                errors.append(err_msg)
                self.alerter.notify_failure(
                    job_id=job_id,
                    title=title,
                    platform=f"{platform} ({brand_name or 'default'})",
                    error_message=str(e),
                    attempts=job.get("attempts", 0) + 1,
                )

        # 4. Final status determination & Master Sheet update
        all_published = all(results.get(p, {}).get("status") == "published" for p in platforms)
        any_published = any(results.get(p, {}).get("status") == "published" for p in platforms)

        if all_published:
            self.queue.update_job_status(job_id, "completed", results=results)
        elif any_published:
            self.queue.update_job_status(
                job_id, "partial", error_message="; ".join(errors), results=results
            )
        else:
            self.queue.update_job_status(
                job_id, "failed", error_message="; ".join(errors) or "All platforms failed.", results=results
            )

        try:
            from core.sheet_exporter import MasterSheetExporter
            exporter = MasterSheetExporter(db_path=self.queue.db_path)
            exporter.export_master_sheet(ignore_job_ids=[job_id], only_job_ids=[job_id])
        except Exception as e:
            logger.warning(f"Could not update Master Output Sheet: {e}")

