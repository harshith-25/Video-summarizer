import os
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger("app")

try:
    import whisper
    WHISPER_AVAILABLE = True
except Exception:
    WHISPER_AVAILABLE = False
    logger.warning("[WhisperTranscriber] whisper package not available. Stubbing transcripts.")

class WhisperTranscriber:
    def __init__(self):
        if not WHISPER_AVAILABLE:
            logger.warning("[WhisperTranscriber] Running in mock/fallback mode because Whisper is not installed.")

    def _format_timestamp(self, seconds: float) -> str:
        if seconds < 0:
            seconds = 0.0
        total_ms = int(round(seconds * 1000))
        total_sec, ms = divmod(total_ms, 1000)
        h, rem = divmod(total_sec, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    def transcribe(self, wav_file: str, model_name: str = "base", language: Optional[str] = None) -> Tuple[List[Dict], str]:
        logger.info(f"[WhisperTranscriber] Beginning transcription on: {wav_file} (model={model_name}, lang={language or 'auto'})")
        
        if not os.path.exists(wav_file):
            raise FileNotFoundError(f"Audio file not found: {wav_file}")

        if not WHISPER_AVAILABLE:
            # Fallback mock for testing in case environment lacks torch/whisper
            logger.warning("[WhisperTranscriber] Whisper not installed! Returning stub transcription.")
            stub_segments = [
                {
                    "start": "00:00:00.000",
                    "end": "00:00:05.000",
                    "start_s": 0.0,
                    "end_s": 5.0,
                    "text": "This is a mock transcription of the video segment."
                },
                {
                    "start": "00:00:05.000",
                    "end": "00:00:10.000",
                    "start_s": 5.0,
                    "end_s": 10.0,
                    "text": "We will summarize this mock content for verification."
                }
            ]
            stub_text = "This is a mock transcription of the video segment. We will summarize this mock content for verification."
            return stub_segments, stub_text

        try:
            # Load local whisper model (on CPU to avoid driver conflicts)
            model = whisper.load_model(model_name, device="cpu")
            
            # Run transcription
            result = model.transcribe(
                wav_file,
                language=language,
                verbose=False,
                fp16=False
            )
            
            raw_segments = result.get("segments") or []
            segments = []
            
            for seg in raw_segments:
                start_s = float(seg.get("start", 0.0))
                end_s = float(seg.get("end", 0.0))
                text = (seg.get("text") or "").strip()
                if not text:
                    continue
                
                segments.append({
                    "start": self._format_timestamp(start_s),
                    "end": self._format_timestamp(end_s),
                    "start_s": start_s,
                    "end_s": end_s,
                    "text": text
                })
                
            full_text = result.get("text", "").strip()
            
            # If whisper doesn't return segments but has text, mock one segment
            if not segments and full_text:
                segments.append({
                    "start": "00:00:00.000",
                    "end": self._format_timestamp(5.0), # arbitrary end
                    "start_s": 0.0,
                    "end_s": 5.0,
                    "text": full_text
                })
                
            logger.info(f"[WhisperTranscriber] Transcription done. Segments: {len(segments)}, Chars: {len(full_text)}")
            return segments, full_text
            
        except Exception as e:
            logger.error(f"[WhisperTranscriber] Whisper transcription failed: {e}", exc_info=True)
            raise RuntimeError(f"Whisper transcription failed: {e}")