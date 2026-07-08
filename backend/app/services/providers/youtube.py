import os
import logging
from app.services.providers.base_provider import VideoProvider

logger = logging.getLogger("app")

try:
    from pytubefix import YouTube
    PYTUBEFIX_AVAILABLE = True
except Exception:
    PYTUBEFIX_AVAILABLE = False
    logger.warning("[YoutubeProvider] pytubefix not available")

class YoutubeProvider(VideoProvider):
    def download(self, source: str, output_dir: str, **kwargs) -> str:
        if not PYTUBEFIX_AVAILABLE:
            raise RuntimeError("pytubefix is not installed and available.")
            
        os.makedirs(output_dir, exist_ok=True)
        try:
            logger.info(f"[YoutubeProvider] Downloading video: {source}")
            # Initialize YouTube instance without OAuth to prevent hanging in background tasks
            yt = YouTube(source, use_oauth=False)
                
            stream = None
            if kwargs.get("only_audio", False):
                # Filter for audio streams
                stream = (
                    yt.streams.filter(only_audio=True, file_extension="mp4")
                    .order_by("abr")
                    .desc()
                    .first()
                )
                if not stream:
                    stream = (
                        yt.streams.filter(only_audio=True)
                        .order_by("abr")
                        .desc()
                        .first()
                    )
            
            # Filter for progressive mp4 streams first (video + audio combined)
            if not stream:
                stream = (
                    yt.streams.filter(progressive=True, file_extension="mp4")
                    .order_by("resolution")
                    .desc()
                    .first()
                )

            # Fallback to any mp4 stream (highest resolution)
            if not stream:
                stream = (
                    yt.streams.filter(file_extension="mp4")
                    .order_by("resolution")
                    .desc()
                    .first()
                )
                
            if not stream:
                raise RuntimeError("No valid streams found for this YouTube URL.")
                
            downloaded_path = stream.download(output_path=output_dir)
            logger.info(f"[YoutubeProvider] Downloaded YouTube video to: {downloaded_path}")
            return downloaded_path
            
        except Exception as e:
            logger.error(f"[YoutubeProvider] YouTube download failed for {source}: {e}", exc_info=True)
            raise RuntimeError(f"YouTube download failed: {str(e)}")