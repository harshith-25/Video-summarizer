import os
import subprocess
import logging

logger = logging.getLogger("app")

class AudioExtractor:
    def extract_audio(self, video_path: str, output_dir: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        wav_path = os.path.join(output_dir, f"{base_name}_audio.wav")
        
        logger.info(f"[AudioExtractor] Extracting mono 16kHz audio from '{video_path}' -> '{wav_path}'")
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found at: {video_path}")
            
        try:
            # -y: overwrite output file if it exists
            # -vn: omit video stream
            # -acodec pcm_s16le: write uncompressed 16-bit PCM wav
            # -ac 1: convert to mono channel
            # -ar 16000: set sample rate to 16000 Hz (Whisper requirement)
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vn",
                "-acodec", "pcm_s16le",
                "-ac", "1",
                "-ar", "16000",
                wav_path
            ]
            
            logger.info(f"[AudioExtractor] Command: {' '.join(cmd)}")
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            
            if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
                raise RuntimeError("Extracted audio file is empty or missing.")
                
            logger.info(f"[AudioExtractor] Extracted audio file: {os.path.basename(wav_path)} (Size: {os.path.getsize(wav_path)} bytes)")
            return wav_path
            
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode('utf-8', errors='ignore')
            logger.error(f"[AudioExtractor] FFmpeg failed with code {e.returncode}: {err_msg}")
            raise RuntimeError(f"FFmpeg audio extraction failed: {err_msg}")
        except Exception as e:
            logger.error(f"[AudioExtractor] Unexpected error during audio extraction: {e}", exc_info=True)
            raise