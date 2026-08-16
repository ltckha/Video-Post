"""Job Runner & Platform Rate Limiter module.

Orchestrates job execution from SQLite queue to target platform connectors.
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

RATE_LIMITS = {
    "facebook": 5,
    "youtube": 10,
    "instagram": 5,
    "tiktok": 5,
}


class JobRunner:
    def __init__(self, db_path: str = "video_post.db"):
        self.queue = JobQueue(db_path=db_path)
        self.alerter = AlertManager()
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
        job_id = job["id"]
        title = job["title"]
        video_path = job["video_path"]
        platforms = [p.strip() for p in job["target_platforms"].split(",") if p.strip()]

        # Load brand routing map and platform captions if available
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
        # Khôi phục kết quả cũ để không bị ghi đè khi chạy lại (retry partial)
        if job.get("results_json"):
            try:
                old_data = json.loads(job["results_json"])
                if isinstance(old_data, dict):
                    results = old_data
            except Exception:
                pass

        errors = []

        from core.account_manager import AccountManager
        account_mgr = AccountManager()


        for platform in platforms:
            # Bỏ qua các platform đã 'published' nếu chạy lại (retry)
            if results.get(platform, {}).get("status") == "published":
                logger.info(f"Skipping {platform} for Job #{job_id} as it is already published.")
                continue

            if platform not in self.connectors:
                err = f"Unsupported platform: {platform}"
                logger.error(err)
                results[platform] = {"status": "failed", "error": err}
                errors.append(err)
                continue

            # Resolve brand-specific credentials
            brand_name = brand_map.get(platform)
            connector = self.connectors[platform]
            
            is_configured = False

            if brand_name:
                creds = account_mgr.get_brand_credentials(brand_name, platform)
                if creds:
                    logger.info(f"Routed Job #{job_id} on {platform.upper()} to Brand: '{brand_name}'")
                    if platform == "facebook" and creds.get("page_id") and creds.get("access_token"):
                        connector.page_id = creds["page_id"]
                        connector.access_token = creds["access_token"]
                        is_configured = True
                    elif platform == "youtube" and creds.get("token_path"):
                        from pathlib import Path
                        connector.token_path = Path(creds["token_path"])
                        if hasattr(connector, 'authenticate') and callable(connector.authenticate):
                            is_configured = connector.authenticate()
                        else:
                            is_configured = True
                    elif platform == "instagram" and creds.get("access_token"):
                        connector.access_token = creds["access_token"]
                        if creds.get("instagram_account_id"):
                            connector.instagram_account_id = creds["instagram_account_id"]
                        is_configured = True
                    elif platform == "tiktok":
                        connector.brand_name = brand_name
                        profile_dir = creds.get("profile_dir", f"config/browser_profiles/tiktok_{brand_name.replace(' ', '_').lower()}")
                        from pathlib import Path
                        connector.profile_dir = Path(profile_dir).resolve()
                        is_configured = True
            else:
                # Nếu brand_name là None, kiểm tra xem connector đã có cấu hình mặc định (hoặc mock) chưa
                if hasattr(connector, 'access_token') and connector.access_token:
                    is_configured = True
                elif platform == "youtube":
                    if hasattr(connector, 'authenticate') and callable(connector.authenticate):
                        is_configured = connector.authenticate()
                    else:
                        is_configured = True

            if not is_configured:
                err = f"Missing credentials for {platform} (brand: {brand_name})."
                logger.warning(err)
                results[platform] = {"status": "not_configured", "error": err}
                errors.append(err)
                continue

            # Check Rate Limit
            max_hourly = RATE_LIMITS.get(platform, 10)
            current_hourly = self.queue.get_hourly_post_count(platform)
            if current_hourly >= max_hourly:
                err = f"Rate limit reached for {platform} ({current_hourly}/{max_hourly} posts in last hour). Job deferred."
                logger.warning(err)
                results[platform] = {"status": "failed", "error": err}
                errors.append(err)
                continue

            # Assign platform-specific AI generated caption if available
            specific_caption = platform_captions.get(platform)
            if specific_caption:
                metadata.description = specific_caption
            else:
                metadata.description = job["description"] or ""

            try:
                logger.info(f"Uploading Job #{job_id} to {platform.upper()} (Brand: '{brand_name or 'Default'}')...")
                if platform == "tiktok":
                    profile_dir = getattr(connector, "profile_dir", "config/browser_profiles/tiktok_default")
                    caption_text = metadata.description or metadata.title
                    upload_res = connector.upload_video(
                        video_path=video_path,
                        caption=caption_text,
                        profile_dir=profile_dir
                    )
                else:
                    upload_res = connector.upload_video(video_path, metadata)
                upload_res["status"] = "published"  # Chuẩn hóa từ khóa
                results[platform] = upload_res
                logger.info(f"Successfully posted Job #{job_id} on {platform} for '{brand_name or 'Default'}': {upload_res.get('video_url', 'OK')}")
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


        # Final status determination (overall job status)
        # Bất kỳ nền tảng nào chưa "published" đều coi là error/partial
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

        # Auto-update 19-column Master Output Sheet
        try:
            from core.sheet_exporter import MasterSheetExporter
            exporter = MasterSheetExporter(db_path=self.queue.db_path)
            exporter.export_master_sheet(ignore_job_ids=[job_id], only_job_ids=[job_id])
        except Exception as e:
            logger.warning(f"Could not update Master Output Sheet: {e}")

