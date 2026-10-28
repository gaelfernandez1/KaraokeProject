import logging
import os

import yt_dlp

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = "input"


def download_youtube(url: str, dest_dir: str = DOWNLOAD_DIR) -> str:
    """Download a YouTube video and return the path to the merged mp4.

    Runs in the worker (it needs ffmpeg + yt-dlp), not the web request.
    """
    # YouTube serves modern video/audio as separate DASH streams; a single
    # progressive mp4 rarely exists above 360p. So pick the best video+audio
    # under 1080p and let yt-dlp merge them, remuxing to mp4 so the rest of the
    # pipeline (which assumes a .mp4 path) keeps working.
    opcions_ydl = {
        "outtmpl": os.path.join(dest_dir, "%(title)s.%(ext)s"),
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "extract_flat": False,
        "concurrent_fragment_downloads": 1,
    }
    with yt_dlp.YoutubeDL(opcions_ydl) as ydl:
        info = ydl.extract_info(url, download=True)
        # After a merge/remux prepare_filename returns the pre-merge container,
        # so prefer the real path yt-dlp records in requested_downloads.
        downloads = info.get("requested_downloads")
        if downloads:
            return downloads[0]["filepath"]
        return ydl.prepare_filename(info)
