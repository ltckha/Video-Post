"""Main entrypoint CLI for Video-Post automated workflow."""
import time
import json
import sqlite3
import typer
from typing import List, Optional
from rich.console import Console
from rich.table import Table

from config import settings
from core.queue import JobQueue
from core.runner import JobRunner
from core.scheduler import VideoScheduler
from core.sheet_importer import GoogleSheetImporter
from core.reporter import DailyReporter
from connectors.youtube import YouTubeConnector
from connectors.facebook import FacebookConnector
from connectors.instagram import InstagramConnector

app = typer.Typer(help="Automated Social Media Video Publishing Tool")
console = Console()


@app.command()
def info():
    """Display system status and configuration summary."""
    console.print("[bold green]Video-Post Automation Framework[/bold green]")
    console.print(f"Environment: [yellow]{settings.APP_ENV}[/yellow]")
    console.print(f"Input Videos Dir: [cyan]{settings.INPUT_VIDEOS_DIR}[/cyan]")
    console.print(f"Processed Videos Dir: [cyan]{settings.PROCESSED_VIDEOS_DIR}[/cyan]")
    console.print(f"Logs Dir: [cyan]{settings.LOGS_DIR}[/cyan]")


@app.command()
def test_auth(
    platform: str = typer.Option("facebook", help="youtube, facebook, or instagram"),
    brand: Optional[str] = typer.Option(None, help="Brand name as defined in config/accounts.json"),
):
    """Test API authentication for a specific platform and brand."""
    console.print(f"[bold blue]Testing Authentication for platform: {platform} (Brand: '{brand or 'Default'}')...[/bold blue]")

    if platform.lower() == "facebook":
        fb = FacebookConnector(brand_name=brand)
        if fb.authenticate():
            console.print(f"[bold green]✅ Facebook Page Authentication SUCCESSFUL for Brand '{brand}'![/bold green]")
        else:
            console.print(f"[bold red]❌ Facebook Authentication FAILED for Brand '{brand}'. Please check config/accounts.json[/bold red]")
    elif platform.lower() == "youtube":
        yt = YouTubeConnector()
        if yt.authenticate():
            console.print("[bold green]✅ YouTube Authentication SUCCESSFUL![/bold green]")
        else:
            console.print("[bold red]❌ YouTube Authentication FAILED. Please check config/tokens/youtube_token.json[/bold red]")
    elif platform.lower() == "instagram":
        ig = InstagramConnector()
        if ig.authenticate():
            console.print("[bold green]✅ Instagram Authentication SUCCESSFUL![/bold green]")
        else:
            console.print("[bold red]❌ Instagram Authentication FAILED. Please check config/tokens/instagram_token.json[/bold red]")
    else:
        console.print(f"[red]Unknown platform: {platform}. Choose facebook, youtube, or instagram.[/red]")


@app.command()
def auth_youtube(
    client_secret: str = typer.Option("client_secret.json", help="Path to client_secret.json downloaded from Google Cloud"),
    token_path: str = typer.Option("config/tokens/youtube_token.json", help="Path to save the generated token"),
):
    """Run interactive Google OAuth flow in browser to authenticate YouTube channel."""
    import os
    if not os.path.exists(client_secret):
        console.print(f"[bold red]❌ Không tìm thấy tệp '{client_secret}'![/bold red]")
        console.print("[yellow]Vui lòng tải tệp OAuth Client ID JSON từ Google Cloud Console và lưu thành 'client_secret.json' ở thư mục dự án.[/yellow]")
        return

    console.print(f"[bold blue]🔑 Đang mở trình duyệt để xác thực tài khoản YouTube Google (Token lưu tại: {token_path})...[/bold blue]")
    try:
        yt = YouTubeConnector(token_path=token_path)
        yt.run_local_oauth_flow(client_secret)
        console.print(f"[bold green]🎉 Xác thực thành công! Token đã được lưu tự động vào '{token_path}'.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]❌ Lỗi xác thực YouTube: {e}[/bold red]")



@app.command()
def sync_all_sources():
    """Sync all connected Google Sheet sources configured in config/sheet_sources.json."""
    console.print("[bold blue]🔄 Syncing all connected Google Sheet sources with Gemini AI...[/bold blue]")
    from core.sheet_importer import sync_all_sources as do_sync
    count = do_sync()
    console.print(f"[bold green]✅ Sync complete! Total processed jobs: {count}[/bold green]")


@app.command()
def add_tab(
    name: str = typer.Option(..., prompt="Nhập tên đại diện cho Tab này (VD: Omni-Video)", help="Name of the input tab"),
    tab_name: str = typer.Option(..., prompt="Nhập tên chính xác của Tab trên Google Sheet (VD: Omni-Video)", help="Exact Google Sheet Tab Name"),
):
    """Add a new input Tab from Master Sheet for synchronization."""
    import json
    import os
    config_path = "config/sheet_sources.json"
    
    console.print(f"[bold blue]🔄 Đang thêm Tab Đầu Vào: '{name}' (Tab: {tab_name})...[/bold blue]")
    
    data = {"sources": []}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except:
                pass
                
    # Check if tab already exists
    for src in data.get("sources", []):
        if src.get("tab_name") == tab_name:
            console.print(f"[bold yellow]⚠️ Tab '{tab_name}' đã tồn tại trong hệ thống![/bold yellow]")
            return
            
    data.setdefault("sources", []).append({"name": name, "tab_name": tab_name})
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    console.print(f"[bold green]✅ Đã thêm Tab '{tab_name}' thành công! Bây giờ bạn có thể chạy Đồng Bộ (Phím 5).[/bold green]")


@app.command()
def add_sheet(
    name: str = typer.Option(..., prompt="Nhập tên mô tả cho Tab/Sheet này", help="Name of the source"),
    tab_name: str = typer.Option(..., prompt="Nhập tên Tab trên Google Sheet (VD: Omni-Video)", help="Tab Name"),
):
    """Backward-compatible alias for add_tab."""
    add_tab(name=name, tab_name=tab_name)




@app.command()
def import_sheet(
    url: str = typer.Option("https://docs.google.com/spreadsheets/d/1PVaS8s_-H2qphDhlH5Mcz06qD8IKCVaDK6vk9O3Vt4k/", help="Google Sheet URL"),
    platforms: str = typer.Option("facebook", help="Comma separated platforms: facebook,youtube,instagram"),
):
    """Import video post jobs dynamically from any Google Sheet format into Queue."""
    console.print(f"[bold blue]Smart Importing video jobs from Google Sheet ({url[:45]}...)...[/bold blue]")
    from core.sheet_importer import SmartGoogleSheetImporter
    importer = SmartGoogleSheetImporter(sheet_url=url)
    target_platforms = [p.strip() for p in platforms.split(",") if p.strip()]
    count = importer.import_to_queue(target_platforms=target_platforms)
    console.print(f"[bold green]Successfully imported {count} video jobs into Queue![/bold green]")



@app.command()
def add_job(
    video: str = typer.Option(..., help="Path to video file"),
    title: str = typer.Option(..., help="Video title"),
    description: str = typer.Option("", help="Video description"),
    platforms: str = typer.Option("facebook", help="Comma separated platforms"),
):
    """Enqueue a new video job manually."""
    queue = JobQueue()
    target_platforms = [p.strip() for p in platforms.split(",") if p.strip()]
    job_id = queue.add_job(
        video_path=video,
        target_platforms=target_platforms,
        title=title,
        description=description,
    )
    console.print(f"[bold green]Enqueued Job #{job_id} for '{title}'[/bold green]")


@app.command()
def process_queue(
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate job processing without making API calls"),
    limit: int = typer.Option(1, help="Maximum number of jobs to process in this run (default: 1)"),
    platform: str = typer.Option("all", "--platform", help="Target platform to process (facebook, youtube, instagram, all)"),
    brand: str = typer.Option("", "--brand", help="Target brand/page name to filter"),
):
    """Process pending video posting jobs (Interactive Preview per platform & brand)."""
    mode = "DRY-RUN" if dry_run else "LIVE"
    platform_name = platform.upper()
    console.print(f"[bold yellow]⚡ TRẠM KIỂM DUYỆT BÀI ĐĂNG [{platform_name}] ({mode} mode, Limit: {limit})...[/bold yellow]")

    from core.sheet_importer import SmartGoogleSheetImporter
    from config import settings
    from pathlib import Path
    import requests, io, csv, json, random

    master_url = getattr(settings, "MASTER_SHEET_URL", "")
    webhook_url = getattr(settings, "GOOGLE_SHEET_WEBHOOK_URL", "")

    if not master_url:
        console.print("[bold red]❌ Chưa cấu hình MASTER_SHEET_URL trong .env[/bold red]")
        return

    importer = SmartGoogleSheetImporter(sheet_url=master_url)
    try:
        csv_data = importer.fetch_sheet_csv(tab_name="Master")
    except Exception as e:
        console.print(f"[bold red]❌ Lỗi đọc Tab Master: {e}[/bold red]")
        return

    reader = csv.DictReader(io.StringIO(csv_data))
    rows = list(reader)

    # Determine which target platforms to filter
    if platform == "youtube":
        target_p_list = ["youtube"]
    elif platform == "facebook":
        target_p_list = ["facebook"]
    elif platform == "instagram":
        target_p_list = ["instagram"]
    else:
        target_p_list = ["facebook", "youtube", "instagram"]

    # Collect ALL available brands dynamically from JSON configs + Google Sheet
    available_brands = set()
    for p in target_p_list:
        short_p = "fb" if p == "facebook" else ("yt" if p == "youtube" else ("ig" if p == "instagram" else p))
        
        if p == "facebook":
            cfg_path = Path("config/facebook_pages.json")
            if cfg_path.exists():
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        available_brands.update(json.load(f).get("pages", {}).keys())
                except Exception:
                    pass
        elif p == "youtube":
            cfg_path = Path("config/youtube_channels.json")
            if cfg_path.exists():
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        available_brands.update(json.load(f).get("channels", {}).keys())
                except Exception:
                    pass

        for r in rows:
            b_val = r.get(f"brand_{short_p}", "").strip()
            if b_val:
                available_brands.add(b_val)

    sorted_brands = sorted(list(available_brands))

    # Prompt user for Brand selection if not specified via CLI
    selected_brand = brand.strip()
    if not selected_brand and len(target_p_list) == 1 and sorted_brands:
        console.print(f"\n[bold cyan]📌 Danh sách TẤT CẢ Brand/Fanpage khả dụng cho [{platform_name}]:[/bold cyan]")
        for idx, b_name in enumerate(sorted_brands, 1):
            console.print(f"  [bold yellow]{idx}[/bold yellow]) {b_name}")
        all_idx = len(sorted_brands) + 1
        console.print(f"  [bold yellow]{all_idx}[/bold yellow]) Tất cả các Brand (Đăng ngẫu nhiên bài của bất kỳ Brand nào)")

        from rich.prompt import Prompt
        b_choice = Prompt.ask(
            f"👉 Vui lòng chọn Brand (1-{all_idx})",
            default=str(all_idx)
        )
        try:
            choice_num = int(b_choice.strip())
            if 1 <= choice_num <= len(sorted_brands):
                selected_brand = sorted_brands[choice_num - 1]
        except ValueError:
            selected_brand = ""

    if selected_brand:
        console.print(f"[bold green]🎯 Thương hiệu đã chọn: '{selected_brand}'[/bold green]")
    else:
        console.print("[bold dim]🎯 Chế độ: Đăng ngẫu nhiên bài của bất kỳ Brand nào.[/bold dim]")

    # Filter rows where status == 'pending' and matches selected brand
    matching_rows = []
    for r in rows:
        p_match = False
        for p in target_p_list:
            short_p = "fb" if p == "facebook" else ("yt" if p == "youtube" else ("ig" if p == "instagram" else p))
            st = r.get(f"status_{short_p}", "").strip().lower()
            b_val = r.get(f"brand_{short_p}", "").strip()
            
            if st == "pending":
                if not selected_brand or b_val.lower() == selected_brand.lower():
                    p_match = True
                    break
        if p_match:
            matching_rows.append(r)

    if not matching_rows:
        brand_msg = f" cho Brand '{selected_brand}'" if selected_brand else ""
        console.print(f"[bold green]✨ Không có bài nào đang ở trạng thái 'pending'{brand_msg} cho kênh [{platform_name}] trên Tab Master.[/bold green]")
        return

    # Draw 1 random job from matching rows
    selected_row = random.choice(matching_rows)
    pending_rows = [selected_row]

    from core.queue import JobQueue
    queue = JobQueue()
    runner = JobRunner()
    processed = 0

    for r in pending_rows[:limit]:
        job_id = r.get("job_id", "")
        title = r.get("title", "")
        video_path = r.get("video_path", "")

        # Prepare active platforms for this row
        active_platforms = []
        brand_map = {}
        captions = {}

        for p in target_p_list:
            short_p = "fb" if p == "facebook" else ("yt" if p == "youtube" else ("ig" if p == "instagram" else p))
            st = r.get(f"status_{short_p}", "").strip().lower()
            if st == "pending":
                active_platforms.append(p)
                brand_map[p] = r.get(f"brand_{short_p}", "")
                captions[p] = r.get(f"caption_{short_p}", "") or title

        if not active_platforms:
            continue

        console.print("\n[bold cyan]=======================================================[/bold cyan]")
        console.print(f"🎬 [bold magenta]BÀI VIẾT #{job_id}: {title}[/bold magenta]")
        console.print(f"🌍 [bold]Nền tảng kiểm duyệt:[/bold] {', '.join(active_platforms).upper()}")
        console.print(f"📁 [bold]File Video:[/bold] {video_path}")

        if brand_map:
            console.print(f"🏢 [bold]Thương hiệu / Fanpage:[/bold] {brand_map}")

        console.print("\n📝 [bold]NỘI DUNG SẼ ĐĂNG:[/bold]")
        for p in active_platforms:
            cap = captions.get(p, title)
            if len(cap) > 300: cap = cap[:300] + " ... (còn tiếp)"
            console.print(f"  [bold blue][{p.upper()}][/bold blue]\n{cap}\n")

        console.print("[bold cyan]=======================================================[/bold cyan]")
        console.print("[bold green]y[/bold green]: Đăng bài ngay")
        console.print("[bold yellow]e[/bold yellow]: Cần chỉnh sửa (needs_edit) - Đánh dấu để AI viết lại")
        console.print("[bold dim]n[/bold dim]: Bỏ qua lúc này (Vẫn giữ pending)")

        from rich.prompt import Prompt
        choice = Prompt.ask(
            "👉 Bạn xử lý bài này thế nào?",
            choices=["y", "n", "e"],
            default="n",
            show_choices=False
        )

        if choice == "y":
            console.print("[bold green]🚀 Tiến hành đăng bài...[/bold green]")
            
            # Save or update job in local SQLite queue so JobRunner can process
            numeric_id = queue.add_job(
                video_path=video_path,
                target_platforms=active_platforms,
                title=title,
                description=title,
                extra_options={
                    "item_id": job_id,
                    "brand_map": brand_map,
                    "platform_captions": captions,
                }
            )

            job_dict = {
                "id": numeric_id,
                "title": title,
                "video_path": video_path,
                "target_platforms": ",".join(active_platforms),
                "description": title,
                "results_json": json.dumps({
                    "brand_map": brand_map,
                    "platform_captions": captions,
                    "item_id": job_id,
                })
            }

            runner._execute_single_job(job_dict, dry_run=dry_run)

            # Update statuses to published on Master tab via Webhook
            updated_rec = dict(r)
            for p in active_platforms:
                short_p = "fb" if p == "facebook" else ("yt" if p == "youtube" else ("ig" if p == "instagram" else p))
                updated_rec[f"status_{short_p}"] = "published"
            
            if webhook_url:
                try:
                    requests.post(webhook_url, json={"action": "update_rows", "records": [updated_rec]}, timeout=15)
                except Exception as ex:
                    console.print(f"[bold red]⚠️ Lỗi cập nhật Webhook: {ex}[/bold red]")

            processed += 1
        elif choice == "e":
            console.print("[bold yellow]📝 Đã đánh dấu bài này là 'needs_edit'.[/bold yellow]")
            updated_rec = dict(r)
            for p in active_platforms:
                short_p = "fb" if p == "facebook" else ("yt" if p == "youtube" else ("ig" if p == "instagram" else p))
                updated_rec[f"status_{short_p}"] = "needs_edit"
            
            if webhook_url:
                try:
                    requests.post(webhook_url, json={"action": "update_rows", "records": [updated_rec]}, timeout=15)
                except Exception as ex:
                    console.print(f"[bold red]⚠️ Lỗi cập nhật Webhook: {ex}[/bold red]")
        else:
            console.print("[dim]Đã bỏ qua bài này. Trạng thái giữ nguyên 'pending'.[/dim]")

    console.print(f"\n[bold green]✅ Đã kiểm duyệt xong. Có {processed} bài được đăng.[/bold green]")


@app.command()
def retry_partial(
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate job processing"),
    limit: int = typer.Option(1, help="Maximum number of jobs to process"),
):
    """Retry jobs that partially failed (skipping already published platforms)."""
    mode = "DRY-RUN" if dry_run else "LIVE"
    console.print(f"[bold yellow]🔄 Retrying Partial/Failed Jobs in {mode} mode (Limit: {limit} job)...[/bold yellow]")
    runner = JobRunner()
    processed = runner.process_partial_jobs(dry_run=dry_run, limit=limit)
    console.print(f"[bold green]Retry processing complete. Processed {processed} job(s).[/bold green]")


@app.command()
def export_master_sheet():
    """Export all jobs and AI captions to 19-column Master Output Sheet CSV."""
    console.print("[bold blue]📊 Exporting Master Output Sheet (19 Columns)...[/bold blue]")
    from core.sheet_exporter import MasterSheetExporter
    exporter = MasterSheetExporter()
    output_file = exporter.export_master_sheet()
    console.print(f"[bold green]✅ Master Output Sheet exported successfully: {output_file}[/bold green]")


@app.command()
def report():
    """Display daily publishing statistics summary report."""
    reporter = DailyReporter()
    reporter.render_cli_report(console)


@app.command()
def start_scheduler(interval: int = typer.Option(1, help="Check interval in minutes")):
    """Start persistent background scheduler daemon."""
    console.print(f"[bold green]Starting Background Video Scheduler (polling every {interval}m)...[/bold green]")
    scheduler = VideoScheduler(interval_minutes=interval)
    scheduler.start()
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()
        console.print("[bold yellow]Scheduler stopped.[/bold yellow]")


@app.command()
def rewrite_needs_edit():
    """Tự động dùng AI viết lại toàn bộ caption cho các bài có trạng thái needs_edit trực tiếp từ Tab Master."""
    console.print("[bold yellow]🤖 Đang triệu hồi Gemini AI để viết lại các bài cần chỉnh sửa...[/bold yellow]")
    
    from core.sheet_importer import SmartGoogleSheetImporter
    from core.ai_captioner import AICaptionGenerator
    from config import settings
    import requests, io, csv, json

    master_url = getattr(settings, "MASTER_SHEET_URL", "")
    webhook_url = getattr(settings, "GOOGLE_SHEET_WEBHOOK_URL", "")

    if not master_url or not webhook_url:
        console.print("[bold red]❌ Lỗi: Chưa cấu hình MASTER_SHEET_URL hoặc GOOGLE_SHEET_WEBHOOK_URL trong .env[/bold red]")
        return

    console.print("[bold cyan]📥 Đang đọc dữ liệu mới nhất từ Tab Master trên Google Sheet...[/bold cyan]")
    importer = SmartGoogleSheetImporter(sheet_url=master_url)
    try:
        csv_data = importer.fetch_sheet_csv(tab_name="Master")
    except Exception as e:
        console.print(f"[bold red]❌ Lỗi đọc Tab Master: {e}[/bold red]")
        return

    reader = csv.DictReader(io.StringIO(csv_data))
    rows = list(reader)

    # Filter rows that have any status set to 'needs_edit'
    needs_edit_rows = []
    for r in rows:
        statuses = [r.get(f"status_{p}", "").strip().lower() for p in ["fb", "yt", "ig", "tt", "shopee", "zalo"]]
        if "needs_edit" in statuses:
            needs_edit_rows.append(r)

    if not needs_edit_rows:
        console.print("[bold green]✨ Tuyệt vời! Không có bài nào trên Tab Master đang ở trạng thái 'needs_edit'.[/bold green]")
        return

    console.print(f"[bold yellow]🔍 Phát hiện {len(needs_edit_rows)} bài cần AI viết lại trên Tab Master.[/bold yellow]")
    ai = AICaptionGenerator()
    updated_records = []

    for r in needs_edit_rows:
        job_id = r.get("job_id", "")
        title = r.get("title", "")
        shopee_link = r.get("shopee_link", "")
        raw_caption = r.get("caption_fb", "") or title

        console.print(f"  [cyan]🔄 Đang viết lại bài #{job_id}: {title[:50]}...[/cyan]")

        current_captions = json.dumps({
            "facebook": r.get("caption_fb", ""),
            "youtube": r.get("caption_yt", ""),
            "instagram": r.get("caption_ig", ""),
            "tiktok": r.get("caption_tt", ""),
            "shopee": r.get("caption_shopee", ""),
            "zalo": r.get("caption_zalo", "")
        }, ensure_ascii=False, indent=2)

        new_captions = ai.generate_all_captions(
            title=title,
            raw_caption=raw_caption,
            affiliate_link=shopee_link,
            style_prompt="Hãy viết lại bài viết cực kỳ sáng tạo, giật gân, cuốn hút và tối ưu chuyển đổi.",
            current_captions=current_captions
        )

        if new_captions:
            updated_rec = dict(r)
            for p in ["fb", "yt", "ig", "tt", "shopee", "zalo"]:
                platform_key = "facebook" if p == "fb" else ("youtube" if p == "yt" else ("instagram" if p == "ig" else p))
                if platform_key in new_captions:
                    updated_rec[f"caption_{p}"] = new_captions[platform_key]
                
                cur_status = updated_rec.get(f"status_{p}", "").strip().lower()
                if cur_status == "needs_edit" or not cur_status:
                    if p in ["tt", "shopee", "zalo"]:
                        updated_rec[f"status_{p}"] = "manual_pending"
                    else:
                        updated_rec[f"status_{p}"] = "pending"

            updated_records.append(updated_rec)
            console.print(f"  [bold green]✅ Đã tạo 6 caption mới cho #{job_id}! Trạng thái chuyển sang 'pending'.[/bold green]")

    if updated_records:
        console.print("[bold blue]📡 Đang đẩy các bài viết mới biên soạn lên Tab Master...[/bold blue]")
        try:
            res = requests.post(webhook_url, json={"action": "update_rows", "records": updated_records}, timeout=30)
            if res.status_code == 200:
                console.print(f"[bold green]🎉 Hoàn tất! Đã cập nhật {len(updated_records)} bài trực tiếp lên Google Sheet Tab Master.[/bold green]")
            else:
                console.print(f"[bold red]⚠️ Lỗi Webhook Apps Script: {res.text}[/bold red]")
        except Exception as e:
            console.print(f"[bold red]❌ Lỗi gửi Webhook: {e}[/bold red]")


@app.command()
def list_jobs():
    """List pending and recent posting jobs in queue."""
    queue = JobQueue()
    jobs = queue.fetch_due_jobs(limit=20)

    if not jobs:
        console.print("[yellow]No pending jobs found in queue.[/yellow]")
        return

    table = Table(title="Pending Video Jobs")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Title", style="magenta")
    table.add_column("Platforms", style="green")
    table.add_column("Status", style="bold yellow")
    table.add_column("Created At", style="dim")

    for job in jobs:
        table.add_row(
            str(job["id"]),
            job["title"],
            job["target_platforms"],
            job["status"],
            str(job["created_at"]),
        )
    console.print(table)


@app.command()
def auth_youtube(
    secret_file: str = typer.Option("giayhainancy_client_secret.json", help="Path to client secret JSON"),
    channel_name: str = typer.Option("", help="YouTube Channel Name to register"),
):
    """Xác thực OAuth 2.0 để lấy Token cho Kênh YouTube mới."""
    from pathlib import Path
    from connectors.youtube.auth import YouTubeConnector

    secret_path = Path(secret_file)
    if not secret_path.exists():
        console.print(f"[bold red]❌ Không tìm thấy file: {secret_file}[/bold red]")
        return

    safe_name = secret_path.stem.replace("client_secret_", "").replace("_client_secret", "")
    token_file = f"config/tokens/youtube_{safe_name}.json"
    
    console.print(f"[bold cyan]🔑 Đang khởi động trình duyệt để đăng nhập YouTube ({secret_file})...[/bold cyan]")
    yt = YouTubeConnector(token_path=token_file)
    yt.run_local_oauth_flow(str(secret_path))

    console.print(f"[bold green]✅ Đã lưu thành công Token tại: {token_file}[/bold green]")

    if channel_name:
        import json
        config_path = Path("config/youtube_channels.json")
        ch_data = {"channels": {}}
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    ch_data = json.load(f)
            except Exception:
                pass
        
        ch_data.setdefault("channels", {})[channel_name] = {"token_path": token_file}
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(ch_data, f, ensure_ascii=False, indent=2)
        console.print(f"[bold green]✅ Đã tự động đăng ký kênh '{channel_name}' vào config/youtube_channels.json![/bold green]")


if __name__ == "__main__":
    app()
