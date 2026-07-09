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
        use_oauth = kwargs.get("use_oauth", False)
        token_file = kwargs.get("token_file", None)
        
        try:
            logger.info(f"[YoutubeProvider] Downloading video: {source} (use_oauth={use_oauth})")
            yt = YouTube(
                source,
                use_oauth=use_oauth,
                allow_oauth_cache=True if use_oauth else False,
                token_file=token_file
            )
            return self._execute_download(yt, output_dir, **kwargs)
        except Exception as e:
            if use_oauth:
                logger.warning(f"[YoutubeProvider] OAuth download failed: {e}. Retrying without OAuth...")
                try:
                    yt = YouTube(source, use_oauth=False)
                    return self._execute_download(yt, output_dir, **kwargs)
                except Exception as fallback_err:
                    logger.error(f"[YoutubeProvider] Fallback download failed: {fallback_err}", exc_info=True)
                    raise RuntimeError(f"YouTube download failed: {str(fallback_err)}")
            else:
                logger.error(f"[YoutubeProvider] YouTube download failed: {e}", exc_info=True)
                raise RuntimeError(f"YouTube download failed: {str(e)}")

    def _execute_download(self, yt: YouTube, output_dir: str, **kwargs) -> str:
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