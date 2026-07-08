import os
import re
import logging
import requests
import subprocess
from app.services.providers.base_provider import VideoProvider

logger = logging.getLogger("app")
VIMEO_TOKEN = os.getenv("VIMEO_TOKEN")

class VimeoProvider(VideoProvider):
    def _extract_video_id(self, url: str) -> str:
        match = re.search(r"(\d{6,})", url)
        if match:
            return match.group(1)
        return url.strip()

    def _get_player_config(self, video_id: str) -> dict:
        url = f"https://player.vimeo.com/video/{video_id}/config"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                return r.json()
            logger.warning(f"[VimeoProvider] Player config failed: status={r.status_code}")
        except Exception as e:
            logger.error(f"[VimeoProvider] Failed to fetch player config: {e}")
        return None

    def _stream_download(self, download_url: str, output_path: str):
        with requests.get(download_url, stream=True, allow_redirects=True) as r:
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        logger.info(f"[VimeoProvider] Saved file to: {output_path}")

    def _download_hls(self, hls_url: str, output_path: str) -> str:
        logger.info(f"[VimeoProvider] Downloading HLS stream using ffmpeg: {hls_url}")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", hls_url, "-c", "copy", output_path],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return output_path
        except Exception as e:
            logger.error(f"[VimeoProvider] FFmpeg HLS download error: {e}")
            raise RuntimeError(f"FFmpeg HLS download failed: {e}")

    def download(self, source: str, output_dir: str, **kwargs) -> str:
        video_id = self._extract_video_id(source)
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"vimeo_{video_id}_video.mp4")

        # Option 1: Use Vimeo API if VIMEO_TOKEN exists
        if VIMEO_TOKEN:
            try:
                logger.info(f"[VimeoProvider] Trying Vimeo API for video {video_id}")
                url = f"https://api.vimeo.com/videos/{video_id}"
                headers = {"Authorization": f"Bearer {VIMEO_TOKEN}"}
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    files = data.get("download") or data.get("files") or []
                    for f in files:
                        link = f.get("link") or f.get("url")
                        if link and link.endswith(".mp4"):
                            self._stream_download(link, out_path)
                            return out_path
            except Exception as e:
                logger.warning(f"[VimeoProvider] Vimeo API lookup failed: {e}")

        # Option 2: Fallback to player config (public video page parser)
        cfg = self._get_player_config(video_id)
        if cfg:
            try:
                files = cfg.get("request", {}).get("files", {})
                
                # Try progressive MP4 downloads
                progressive = files.get("progressive")
                if progressive:
                    progressive = sorted(progressive, key=lambda x: int(x.get("height", 0)), reverse=True)
                    video_url = progressive[0]["url"]
                    logger.info(f"[VimeoProvider] Downloading progressive stream: {video_url}")
                    self._stream_download(video_url, out_path)
                    return out_path
                
                # Try HLS download
                hls = files.get("hls", {}).get("cdns")
                if hls:
                    cdn = list(hls.values())[0]
                    hls_url = cdn["url"]
                    return self._download_hls(hls_url, out_path)
            except Exception as e:
                logger.error(f"[VimeoProvider] Failed parsing player config: {e}")

        raise RuntimeError(f"Could not download Vimeo video. Please check token or if video is public.")