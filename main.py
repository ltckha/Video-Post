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
    job_id: str = typer.Option("", "--job-id", help="Target specific job_id to process"),
):
    """Process pending video posting jobs (Interactive Preview per platform, brand, or job_id)."""
    mode = "DRY-RUN" if dry_run else "LIVE"
    platform_name = platform.upper()
    console.print(f"[bold yellow]⚡ TRẠM KIỂM DUYỆT BÀI ĐĂNG [{platform_name}] ({mode} mode, Limit: {limit})...[/bold yellow]")

    from core.sheet_importer import SmartGoogleSheetImporter
    from config import settings
    from pathlib import Path
    import requests, io, csv, json, random, unicodedata

    def norm_text(s: str) -> str:
        return unicodedata.normalize('NFC', s.strip()) if s else ""

    from core.sheet_client import GoogleSheetDirectClient
    try:
        sc = GoogleSheetDirectClient()
        rows = sc.fetch_all_records("Master")
    except Exception as e:
        console.print(f"[bold red]❌ Lỗi đọc Tab Master qua Service Account: {e}[/bold red]")
        return

    # Determine which target platforms to filter
    if platform == "youtube":
        target_p_list = ["youtube"]
    elif platform == "facebook":
        target_p_list = ["facebook"]
    elif platform == "instagram":
        target_p_list = ["instagram"]
    else:
        target_p_list = ["facebook", "youtube", "instagram"]

    # Collect ALL available brands dynamically with NFC Unicode normalization
    brand_dict = {}
    for p in target_p_list:
        short_p = "fb" if p == "facebook" else ("yt" if p == "youtube" else ("ig" if p == "instagram" else p))
        
        if p == "facebook":
            cfg_path = Path("config/facebook_pages.json")
            if cfg_path.exists():
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        for b_k in json.load(f).get("pages", {}).keys():
                            n_b = norm_text(b_k)
                            if n_b and n_b.lower() not in brand_dict:
                                brand_dict[n_b.lower()] = n_b
                except Exception:
                    pass
        elif p == "youtube":
            cfg_path = Path("config/youtube_channels.json")
            if cfg_path.exists():
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        for b_k in json.load(f).get("channels", {}).keys():
                            n_b = norm_text(b_k)
                            if n_b and n_b.lower() not in brand_dict:
                                brand_dict[n_b.lower()] = n_b
                except Exception:
                    pass

        for r in rows:
            b_val = norm_text(r.get(f"brand_{short_p}", ""))
            if b_val and b_val.lower() not in brand_dict:
                brand_dict[b_val.lower()] = b_val

    sorted_brands = sorted(list(brand_dict.values()))

    # Prompt user for Brand selection if not specified via CLI
    selected_brand = norm_text(brand)
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
        console.print("[bold dim]🎯 Chế độ: Đăng bài tuần tự từ trên xuống của bất kỳ Brand nào.[/bold dim]")

    # Select mode: 1) Top-to-Bottom FIFO vs 2) Specific job_id
    target_job_id = norm_text(job_id)
    if not target_job_id:
        console.print("\n[bold cyan]📌 Chọn phương thức tìm bài viết để kiểm duyệt:[/bold cyan]")
        console.print("  [bold yellow]1[/bold yellow]) Lấy bài ĐẦU TIÊN từ trên xuống (Tuần tự theo thời gian)")
        console.print("  [bold yellow]2[/bold yellow]) Nhập mã 'job_id' cụ thể")
        from rich.prompt import Prompt
        mode_choice = Prompt.ask("👉 Vui lòng chọn (1-2)", choices=["1", "2"], default="1", show_choices=False)
        if mode_choice == "2":
            target_job_id = norm_text(Prompt.ask("👉 Nhập mã job_id bạn muốn kiểm duyệt"))

    pending_rows = []

    if target_job_id:
        # User specified a specific job_id
        matched_row = None
        for r in rows:
            if norm_text(r.get("job_id", "")).lower() == target_job_id.lower():
                matched_row = r
                break
        
        if not matched_row:
            console.print(f"[bold red]❌ Không tìm thấy mã bài viết #{target_job_id} trên Tab Master![/bold red]")
            return

        # Check if matched_row has status == 'pending' for target platform
        is_pending = False
        status_summary = []
        for p in target_p_list:
            short_p = "fb" if p == "facebook" else ("yt" if p == "youtube" else ("ig" if p == "instagram" else p))
            st = norm_text(r.get(f"status_{short_p}", "")).lower()
            status_summary.append(f"{p.upper()}: {st or 'chưa có'}")
            if st == "pending":
                is_pending = True

        if is_pending:
            pending_rows = [matched_row]
        else:
            console.print(f"\n[bold yellow]⚠️ Bài viết #{target_job_id} hiện KHÔNG ở trạng thái 'pending'![/bold yellow]")
            console.print(f"[bold cyan]📋 Trạng thái thực tế hiện tại:[/bold cyan] {', '.join(status_summary)}")
            console.print("[dim]👉 Bài viết phải ở trạng thái 'pending' thì mới tiến hành kiểm duyệt & đăng bài được.[/dim]\n")
            return
    else:
        # Filter rows where status == 'pending' and matches selected brand
        matching_rows = []
        for r in rows:
            p_match = False
            for p in target_p_list:
                short_p = "fb" if p == "facebook" else ("yt" if p == "youtube" else ("ig" if p == "instagram" else p))
                st = norm_text(r.get(f"status_{short_p}", "")).lower()
                b_val = norm_text(r.get(f"brand_{short_p}", ""))
                
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

        # Pick the FIRST job in order from top to bottom (FIFO)
        selected_row = matching_rows[0]
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

            # Update statuses to published on Master tab directly via Service Account API
            updated_rec = dict(r)
            for p in active_platforms:
                short_p = "fb" if p == "facebook" else ("yt" if p == "youtube" else ("ig" if p == "instagram" else p))
                updated_rec[f"status_{short_p}"] = "published"
            
            try:
                from core.sheet_client import GoogleSheetDirectClient
                sc = GoogleSheetDirectClient()
                sc.update_master_rows([updated_rec])
                for p in active_platforms:
                    b_name = brand_map.get(p) or r.get(f"brand_{p}") or r.get("brand_fb") or "Default"
                    sc.record_post_timestamp(brand=b_name, platform=p)
            except Exception as ex:
                console.print(f"[bold red]❌ Lỗi cập nhật Tab Master: {ex}[/bold red]")

            processed += 1
        elif choice == "e":
            console.print("[bold yellow]📝 Đã đánh dấu bài này là 'needs_edit'.[/bold yellow]")
            updated_rec = dict(r)
            for p in active_platforms:
                short_p = "fb" if p == "facebook" else ("yt" if p == "youtube" else ("ig" if p == "instagram" else p))
                updated_rec[f"status_{short_p}"] = "needs_edit"
            
            try:
                from core.sheet_client import GoogleSheetDirectClient
                sc = GoogleSheetDirectClient()
                sc.update_master_rows([updated_rec])
            except Exception as ex:
                console.print(f"[bold red]❌ Lỗi cập nhật Tab Master: {ex}[/bold red]")
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

    from core.sheet_client import GoogleSheetDirectClient
    console.print("[bold cyan]📥 Đang đọc dữ liệu mới nhất từ Tab Master trên Google Sheet...[/bold cyan]")
    try:
        sc = GoogleSheetDirectClient()
        rows = sc.fetch_all_records("Master")
    except Exception as e:
        console.print(f"[bold red]❌ Lỗi đọc Tab Master qua Service Account: {e}[/bold red]")
        return

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
                    if p in ["shopee", "zalo"]:
                        updated_rec[f"status_{p}"] = "manual_pending"
                    else:
                        updated_rec[f"status_{p}"] = "pending"

            updated_records.append(updated_rec)
            console.print(f"  [bold green]✅ Đã tạo 6 caption mới cho #{job_id}! Trạng thái chuyển sang 'pending'.[/bold green]")

    if updated_records:
        console.print("[bold blue]📡 Đang đẩy các bài viết mới biên soạn trực tiếp lên Tab Master...[/bold blue]")
        try:
            from core.sheet_client import GoogleSheetDirectClient
            sc = GoogleSheetDirectClient()
            sc.update_master_rows(updated_records)
            console.print(f"[bold green]🎉 Hoàn tất! Đã cập nhật {len(updated_records)} bài trực tiếp lên Google Sheet Tab Master qua Sheets API v4.[/bold green]")
        except Exception as e:
            console.print(f"[bold red]❌ Lỗi cập nhật Tab Master: {e}[/bold red]")


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
        if (Path("config") / secret_file).exists():
            secret_path = Path("config") / secret_file
        else:
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


@app.command()
def generate_schedule(
    start_time: str = typer.Option("07:30", help="Start time in HH:MM format"),
    end_time: str = typer.Option("20:30", help="End time in HH:MM format"),
    all_brands: bool = typer.Option(True, "--all-brands", help="Generate schedule for all eligible brands"),
):
    """Sinh mốc giờ ngẫu nhiên rải đều từ 07:30 đến 20:30 cho tất cả các Kênh/Brand và cập nhật lên Tab Status qua Direct API."""
    import random
    from core.sheet_client import GoogleSheetDirectClient
    from core.account_manager import AccountManager

    s_h, s_m = map(int, start_time.split(":"))
    e_h, e_m = map(int, end_time.split(":"))
    start_min = s_h * 60 + s_m
    end_min = e_h * 60 + e_m

    from core.account_manager import AccountManager
    mgr = AccountManager()

    # Known brands list (in preferred priority order)
    candidate_brands = [
        "Hiệu giày Hải Nancy",
        "Mua Chuẩn Xài Lâu",
        "Macadamia Hải Nancy",
        "Ở Đà Lạt vậy thôi",
        "Yen Handmade Leather",
        "YenYen Deals",
        "Elegant Steps",
    ]

    # Dynamically scan only platforms that are authenticated and ready!
    brand_platforms = []
    for b in candidate_brands:
        active_p = mgr.get_active_platforms_for_brand(b)
        if active_p:
            brand_platforms.append((b, active_p))

    total_slots = sum(len(p) for _, p in brand_platforms)
    if total_slots == 0:
        console.print("[bold yellow]⚠️ Không tìm thấy kênh nào đang ở trạng thái sẵn sàng (ready/active).[/bold yellow]")
        return
    
    # Generate non-overlapping time slots
    step = max(15, (end_min - start_min) // (total_slots + 2))
    available_times = list(range(start_min, end_min - 15, step))
    random.shuffle(available_times)
    selected_times = sorted(available_times[:total_slots])
    random.shuffle(selected_times)

    time_idx = 0
    console.print(f"\n[bold cyan]🎲 ĐÃ SINH LỊCH NGẪU NHIÊN CHO {total_slots} KÊNH ĐÃ SẴN SÀNG ({start_time} - {end_time}):[/bold cyan]\n")

    for brand_name, platforms in brand_platforms:
        times_payload = {
            "action": "update_brand_schedule",
            "brand": brand_name,
            "times_fb": "",
            "times_yt": "",
            "times_ig": "",
            "times_tt": "",
        }
        summary_str = []
        for p in ["fb", "yt", "ig", "tt"]:
            if p in platforms:
                t_min = selected_times[time_idx]
                time_idx += 1
                t_str = f"{t_min // 60:02d}:{t_min % 60:02d}"
                times_payload[f"times_{p}"] = t_str
                p_label = "📘 FB" if p == "fb" else ("🔴 YT" if p == "yt" else ("📸 IG" if p == "ig" else "🎬 TT"))
                summary_str.append(f"{p_label}: [bold green]{t_str}[/bold green]")

        console.print(f"📌 [bold yellow]{brand_name:<22}[/bold yellow] ➡️  " + "  |  ".join(summary_str))

        try:
            sc = GoogleSheetDirectClient()
            sc.update_brand_schedule(
                brand=brand_name,
                times_fb=times_payload.get("times_fb"),
                times_yt=times_payload.get("times_yt"),
                times_ig=times_payload.get("times_ig"),
                times_tt=times_payload.get("times_tt"),
            )
        except Exception as e:
            console.print(f"[bold red]❌ Lỗi cập nhật lịch brand '{brand_name}': {e}[/bold red]")

    console.print("\n[bold green]🎉 HOÀN TẤT! Đã sinh và cập nhật lịch ngẫu nhiên mới nhất lên Google Sheet Tab Status qua Sheets API v4![/bold green]\n")



@app.command()
def tiktok_import_cookies(
    brand: str = typer.Option(..., help="Tên tài khoản TikTok (Ví dụ: Hiệu giày Hải Nancy, Elegant Steps)"),
    cookies_file: str = typer.Option(..., help="Đường dẫn file JSON xuất từ Cookie-Editor"),
):
    """Nạp cookie phiên đăng nhập (xuất từ Chrome cá nhân) vào profile Playwright của 1 tài khoản TikTok."""
    from connectors.tiktok.browser_uploader import TikTokBrowserConnector

    console.print(f"\n[bold cyan]🍪 ĐANG NẠP COOKIE CHO TÀI KHOẢN TIKTOK: '{brand}'...[/bold cyan]")
    console.print(f"📄 Tệp Cookie nguồn: [yellow]{cookies_file}[/yellow]")

    try:
        connector = TikTokBrowserConnector(brand_name=brand)
        connector.import_cookies_from_file(cookies_file)
        console.print(f"[bold green]🎉 Hoàn tất! Tài khoản TikTok '{brand}' đã được nạp cookie và sẵn sàng đăng video tự động.[/bold green]\n")
    except Exception as e:
        console.print(f"[bold red]❌ Lỗi khi nạp cookie: {e}[/bold red]\n")


@app.command()
def tiktok_login(
    brand: str = typer.Option("Hiệu giày Hải Nancy", help="Target TikTok brand name"),
):
    """[DEPRECATED] Mở trình duyệt để đăng nhập TikTok Studio (Khuyến nghị dùng tiktok-import-cookies)."""
    from core.account_manager import AccountManager
    from connectors.tiktok.browser_uploader import TikTokBrowserUploader

    mgr = AccountManager()
    creds = mgr.get_brand_credentials(brand, "tiktok") or {}
    profile_dir = creds.get("profile_dir", f"config/browser_profiles/tiktok_{brand.replace(' ', '_').lower()}")

    console.print(f"\n[bold yellow]⚠️ CẢNH BÁO: Đăng nhập trực tiếp dễ bị TikTok chặn CDP. Vui lòng ưu tiên dùng lệnh 'tiktok-import-cookies'.[/bold yellow]")
    uploader = TikTokBrowserUploader(headless=False)
    uploader.login_interactive(profile_dir=profile_dir)


@app.command()
def tiktok_post(
    job_id: Optional[str] = typer.Option(None, help="Specific Job ID from Master sheet"),
    brand: Optional[str] = typer.Option(None, help="Filter by brand name"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without posting"),
):
    """Tự động đăng bài lên TikTok Studio từ dữ liệu Tab Master trên Google Sheet."""
    from core.account_manager import AccountManager
    from core.sheet_client import GoogleSheetDirectClient
    from connectors.tiktok.browser_uploader import TikTokBrowserConnector
    from connectors.base import PostMetadata

    console.print(f"\n[bold magenta]🎬 KHỞI CHẠY ĐĂNG BÀI TỰ ĐỘNG LÊN TIKTOK STUDIO (Mode: {'DRY-RUN' if dry_run else 'LIVE'})...[/bold magenta]")
    
    mgr = AccountManager()
    sc = GoogleSheetDirectClient()
    records = sc.fetch_all_records("Master")
    
    # Filter candidate jobs
    candidates = []
    for r in records:
        st = str(r.get("status_tt", "")).strip().lower()
        if st in ["pending", "manual_pending"]:
            b_tt = str(r.get("brand_tt") or r.get("brand_fb") or "").strip()
            
            # If user explicitly requested a brand
            if brand and b_tt.lower() != str(brand).strip().lower():
                continue

            # If no brand requested, ONLY take candidates from brands that have active TikTok cookies
            if not brand and "tt" not in mgr.get_active_platforms_for_brand(b_tt):
                continue

            if job_id and str(r.get("job_id", "")).strip() != str(job_id).strip():
                continue

            candidates.append(r)

    if not candidates:
        if brand:
            console.print(f"[bold yellow]✨ Không tìm thấy bài nào đang 'pending' cho Brand: '{brand}'[/bold yellow]")
        else:
            console.print("[bold yellow]✨ Không có bài nào đang ở trạng thái 'pending' cho các Brand TikTok đã nạp Cookie.[/bold yellow]")
        return

    console.print(f"[bold cyan]🔍 Tìm thấy {len(candidates)} bài sẵn sàng đăng TikTok.[/bold cyan]")
    target = candidates[0]
    j_id = target.get("job_id")
    title = target.get("title")
    video_path = target.get("video_path")
    caption_tt = target.get("caption_tt") or title
    brand_tt = target.get("brand_tt") or target.get("brand_fb") or "Default"

    # Check if brand is active
    if "tt" not in mgr.get_active_platforms_for_brand(brand_tt):
        console.print(f"[bold red]❌ Lỗi: Brand '{brand_tt}' chưa được nạp Cookie! Vui lòng nạp Cookie trước bằng Phím 5.[/bold red]\n")
        return

    console.print(f"\n📌 [bold yellow]Job #{j_id}:[/bold yellow] {title}")
    console.print(f"  🏢 Brand: [bold green]{brand_tt}[/bold green]")
    console.print(f"  🎬 Video: [dim]{video_path}[/dim]")
    console.print(f"  📝 Caption: {caption_tt[:100]}...\n")

    if dry_run:
        console.print("[bold green]✅ [DRY-RUN] Giả lập đăng TikTok thành công![/bold green]")
        return

    try:
        connector = TikTokBrowserConnector(brand_name=brand_tt)
        metadata = PostMetadata(title=title, description=caption_tt)
        res = connector.upload_video(video_path=video_path, metadata=metadata)
        
        if res.get("status") == "success":
            # Update status_tt on Google Sheet
            updated_rec = dict(target)
            updated_rec["status_tt"] = "published"
            sc.update_master_rows([updated_rec])
            sc.record_post_timestamp(brand=brand_tt, platform="tt")
            console.print(f"[bold green]🎉 Hoàn tất! Đã đăng thành công lên TikTok và cập nhật status_tt = 'published' trên Google Sheet![/bold green]\n")
        else:
            console.print(f"[bold red]❌ Đăng bài không thành công: {res}[/bold red]\n")
    except Exception as e:
        console.print(f"[bold red]❌ Lỗi khi đăng TikTok cho '{brand_tt}': {e}[/bold red]\n")


@app.command()
def auto_post_active(
    dry_run: bool = typer.Option(False, "--dry-run", help="Giả lập không thực sự gọi API / browser"),
    brand: str = typer.Option("", "--brand", help="Chỉ định đăng cho 1 Brand cụ thể (để trống để đăng cho tất cả Brand đã sẵn sàng)"),
    limit_per_brand: int = typer.Option(1, "--limit", help="Số lượng video đăng cho mỗi Brand (mặc định: 1)"),
):
    """🚀 ĐĂNG TỰ ĐỘNG 1-CLICK: Tự động đăng video cho các Kênh/Brand ĐÃ HOÀN TẤT THIẾT LẬP TOKEN/COOKIE."""
    mode = "DRY-RUN" if dry_run else "LIVE"
    console.print(f"\n[bold green]🚀 KHỞI CHẠY ĐĂNG TỰ ĐỘNG 1-CLICK (Mode: {mode})[/bold green]")
    console.print("[dim]Chỉ đăng cho các Kênh và Nền tảng ĐÃ SẴN SÀNG Token / Cookie...[/dim]\n")

    from pathlib import Path
    from core.account_manager import AccountManager
    from core.sheet_client import GoogleSheetDirectClient
    from connectors.base import PostMetadata
    from connectors.facebook import FacebookConnector
    from connectors.youtube import YouTubeConnector
    from connectors.instagram import InstagramConnector
    from connectors.tiktok import TikTokBrowserConnector

    mgr = AccountManager()
    all_brands = [
        "Hiệu giày Hải Nancy",
        "Mua Chuẩn Xài Lâu",
        "Macadamia Hải Nancy",
        "Ở Đà Lạt vậy thôi",
        "Yen Handmade Leather",
        "YenYen Deals",
        "Elegant Steps",
    ]

    target_brands = [brand] if brand else all_brands

    # Filter only brands that have at least 1 active platform
    ready_brands_map = {}
    for b in target_brands:
        active_p = mgr.get_active_platforms_for_brand(b)
        if active_p:
            ready_brands_map[b] = active_p

    if not ready_brands_map:
        console.print("[bold yellow]⚠️ Không tìm thấy Brand nào có Token / Cookie sẵn sàng![/bold yellow]")
        return

    console.print(f"[bold cyan]🔍 Tìm thấy {len(ready_brands_map)} Thương hiệu đã sẵn sàng thiết lập:[/bold cyan]")
    for b, plats in ready_brands_map.items():
        p_labels = []
        for p in plats:
            p_labels.append("📘 FB" if p == "fb" else ("🔴 YT" if p == "yt" else ("📸 IG" if p == "ig" else "🎬 TT")))
        console.print(f"  🏢 [bold yellow]{b:<22}[/bold yellow] ➡️  " + "  ".join(p_labels))

    console.print("\n[bold cyan]📥 Đang đọc dữ liệu từ Tab Master trên Google Sheet...[/bold cyan]")
    sc = GoogleSheetDirectClient()
    rows = sc.fetch_all_records("Master")

    total_posted = 0

    for b, active_platforms in ready_brands_map.items():
        console.print(f"\n==================================================")
        console.print(f"🏢 ĐANG XỬ LÝ BRAND: [bold yellow]{b}[/bold yellow]")
        console.print(f"==================================================")

        brand_posted_count = 0

        # Process each active platform independently so that every ready channel gets 1 video posted
        for p in active_platforms:
            p_label = "📘 Facebook Reels" if p == "fb" else ("🔴 YouTube Shorts" if p == "yt" else ("📸 Instagram Reels" if p == "ig" else "🎬 TikTok Studio"))
            console.print(f"\n--- 🚀 Đang tìm bài cho nền tảng: [bold cyan]{p_label}[/bold cyan] ---")

            # Find the FIRST candidate row for this brand where status_<p> == 'pending' and video_path is valid
            candidate = None
            for r in rows:
                col_brand = r.get(f"brand_{p}", "").strip() or r.get("brand_fb", "").strip()
                if col_brand.lower() != b.lower():
                    continue

                st = (r.get(f"status_{p}") or "").strip().lower()
                if st != "pending":
                    continue

                v_path = (r.get("video_path") or "").strip()
                if not v_path or not Path(v_path).exists():
                    continue

                candidate = r
                break

            if not candidate:
                console.print(f"  ⏩ [{p.upper()}]: Không tìm thấy bài nào đang 'pending' có video hợp lệ cho '{b}'.")
                continue

            j_id = candidate.get("job_id")
            title = candidate.get("title", "")
            video_path = candidate.get("video_path", "")
            caption = candidate.get(f"caption_{p}") or title

            console.print(f"  📌 [bold yellow]Job #{j_id}:[/bold yellow] {title}")
            console.print(f"  🎬 Video: [dim]{video_path}[/dim]")
            console.print(f"  🚀 Đang đăng [{p.upper()}]...")

            if dry_run:
                console.print(f"     ✅ [DRY-RUN] Giả lập đăng thành công [{p.upper()}]!")
                candidate[f"status_{p}"] = "published"
                brand_posted_count += 1
                continue

            # Live upload execution
            try:
                if p == "fb":
                    fb_creds = mgr.get_brand_credentials(b, "facebook")
                    fb_conn = FacebookConnector()
                    fb_conn.page_id = fb_creds.get("page_id")
                    fb_conn.access_token = fb_creds.get("access_token")
                    meta = PostMetadata(title=title, description=caption)
                    res = fb_conn.upload_video(video_path=video_path, metadata=meta)
                    
                    candidate["status_fb"] = "published"
                    updated_row = dict(candidate)
                    sc.update_master_rows([updated_row])
                    sc.record_post_timestamp(brand=b, platform="fb")
                    console.print(f"     ✅ Đăng Facebook thành công: {res.get('post_id', 'OK')}")
                    brand_posted_count += 1

                elif p == "yt":
                    yt_creds = mgr.get_brand_credentials(b, "youtube")
                    yt_conn = YouTubeConnector()
                    from pathlib import Path
                    yt_conn.token_path = Path(yt_creds.get("token_path"))
                    if hasattr(yt_conn, 'authenticate') and callable(yt_conn.authenticate):
                        yt_conn.authenticate()
                    meta = PostMetadata(title=title, description=caption)
                    res = yt_conn.upload_video(video_path=video_path, metadata=meta)
                    
                    candidate["status_yt"] = "published"
                    updated_row = dict(candidate)
                    sc.update_master_rows([updated_row])
                    sc.record_post_timestamp(brand=b, platform="yt")
                    console.print(f"     ✅ Đăng YouTube Shorts thành công: {res.get('video_url', 'OK')}")
                    brand_posted_count += 1

                elif p == "ig":
                    ig_creds = mgr.get_brand_credentials(b, "instagram")
                    ig_conn = InstagramConnector()
                    ig_conn.access_token = ig_creds.get("access_token")
                    ig_conn.instagram_account_id = ig_creds.get("instagram_account_id")
                    meta = PostMetadata(title=title, description=caption)
                    res = ig_conn.upload_video(video_path=video_path, metadata=meta)
                    
                    candidate["status_ig"] = "published"
                    updated_row = dict(candidate)
                    sc.update_master_rows([updated_row])
                    sc.record_post_timestamp(brand=b, platform="ig")
                    console.print(f"     ✅ Đăng Instagram Reels thành công: {res.get('video_url', 'OK')}")
                    brand_posted_count += 1

                elif p == "tt":
                    tt_conn = TikTokBrowserConnector(brand_name=b)
                    meta = PostMetadata(title=title, description=caption)
                    res = tt_conn.upload_video(video_path=video_path, metadata=meta)
                    if res.get("status") == "success":
                        candidate["status_tt"] = "published"
                        updated_row = dict(candidate)
                        sc.update_master_rows([updated_row])
                        sc.record_post_timestamp(brand=b, platform="tt")
                        console.print(f"     ✅ Đăng TikTok Studio thành công!")
                        brand_posted_count += 1
                    else:
                        console.print(f"     ❌ Đăng TikTok thất bại: {res}")
            except Exception as ex:
                console.print(f"     ❌ Lỗi khi đăng [{p.upper()}]: {ex}")

        if brand_posted_count > 0:
            total_posted += 1

    console.print(f"\n[bold green]🎉 HOÀN TẤT ĐĂNG TỰ ĐỘNG! Đã xuất bản video cho {total_posted} thương hiệu sẵn sàng![/bold green]\n")


@app.command()
def tiktok_daemon():
    """Khởi động tiến trình chạy nền tự động đăng bài TikTok đúng giờ ngẫu nhiên mỗi ngày."""
    import time
    from core.tiktok_scheduler import TikTokDailyScheduler

    console.print("[bold green]🚀 Đang khởi động TikTok Daily Scheduler Daemon (Chạy nền 24/7)...[/bold green]")
    scheduler = TikTokDailyScheduler()
    scheduler.start()
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()
        console.print("[bold yellow]TikTok Scheduler đã dừng.[/bold yellow]")


if __name__ == "__main__":
    app()
