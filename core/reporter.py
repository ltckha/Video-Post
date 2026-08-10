"""Daily Summary Reporting Module for Video-Post framework."""
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.table import Table

logger = logging.getLogger("video_post.reporter")


class DailyReporter:
    def __init__(self, db_path: str = "video_post.db"):
        self.db_path = db_path

    def generate_daily_summary(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """Generate publishing statistics summary for today or target date (YYYY-MM-DD)."""
        date_clause = "date('now', 'localtime')" if not target_date else f"date('{target_date}')"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Query overall counts
            cursor.execute(
                f"""
                SELECT 
                    COUNT(*) as total_jobs,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                    SUM(CASE WHEN status = 'partial' THEN 1 ELSE 0 END) as partial_count,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count
                FROM jobs
                WHERE date(created_at, 'localtime') = {date_clause}
                   OR date(updated_at, 'localtime') = {date_clause}
            """
            )
            summary_row = dict(cursor.fetchone())

            # Query detailed job records
            cursor.execute(
                f"""
                SELECT id, title, target_platforms, status, attempts, error_message, updated_at
                FROM jobs
                WHERE date(created_at, 'localtime') = {date_clause}
                   OR date(updated_at, 'localtime') = {date_clause}
                ORDER BY updated_at DESC
            """
            )
            job_rows = [dict(r) for r in cursor.fetchall()]

        total = summary_row["total_jobs"] or 0
        completed = summary_row["completed_count"] or 0
        failed = summary_row["failed_count"] or 0
        success_rate = (completed / total * 100) if total > 0 else 0.0

        report = {
            "date": target_date or "Today",
            "total_jobs": total,
            "completed": completed,
            "failed": failed,
            "partial": summary_row["partial_count"] or 0,
            "pending": summary_row["pending_count"] or 0,
            "success_rate_percent": round(success_rate, 1),
            "job_details": job_rows,
        }

        logger.info(
            f"Daily Report Summary: {completed}/{total} completed ({report['success_rate_percent']}% success rate)."
        )
        return report

    def render_cli_report(self, console: Optional[Console] = None):
        """Render beautiful CLI summary table using Rich."""
        if console is None:
            console = Console()

        report = self.generate_daily_summary()

        console.print("\n[bold cyan]📊 VIDEO-POST DAILY SUMMARY REPORT[/bold cyan]")
        console.print(f"Date: [yellow]{report['date']}[/yellow]")
        console.print(f"Total Jobs Processed: [bold]{report['total_jobs']}[/bold]")
        console.print(f"Successfully Posted: [bold green]{report['completed']}[/bold green]")
        console.print(f"Failed Jobs: [bold red]{report['failed']}[/bold red]")
        console.print(f"Success Rate: [bold magenta]{report['success_rate_percent']}%[/bold magenta]\n")

        if report["job_details"]:
            table = Table(title="Today's Job Executions")
            table.add_column("ID", justify="right", style="cyan")
            table.add_column("Title", style="magenta")
            table.add_column("Platforms", style="green")
            table.add_column("Status", style="bold yellow")
            table.add_column("Attempts", justify="right")
            table.add_column("Updated At", style="dim")

            for job in report["job_details"]:
                table.add_row(
                    str(job["id"]),
                    job["title"][:40],
                    job["target_platforms"],
                    job["status"],
                    str(job["attempts"]),
                    str(job["updated_at"]),
                )
            console.print(table)
