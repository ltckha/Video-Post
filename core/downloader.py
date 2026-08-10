"""Video Downloader module for remote input sources (Google Drive, S3, Direct URL)."""
from pathlib import Path


def download_video_from_url(url: str, output_dir: str = "./input_videos") -> str:
    """Download video from a direct URL or remote cloud storage to input_videos directory."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1].split("?")[0] or "downloaded_video.mp4"
    if not filename.endswith((".mp4", ".mov", ".mkv", ".avi")):
        filename += ".mp4"
    
    destination = out_dir / filename
    return str(destination.absolute())
