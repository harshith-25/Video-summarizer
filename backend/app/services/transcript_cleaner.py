import re
import logging
from typing import List, Dict

logger = logging.getLogger("app")

class TranscriptCleaner:
    def __init__(self):
        # Set of common filler words to remove (only word-bounded)
        self.filler_words_pattern = re.compile(
            r'\b(uh|um|er|ah|like|you know|so basically)\b', 
            re.IGNORECASE
        )
        # Extra spaces
        self.multi_spaces_pattern = re.compile(r'\s+')

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
            
        # 1. Remove HTML tags if present
        text = re.sub(r"<[^>]+>", "", text)
        
        # 2. Remove filler words
        text = self.filler_words_pattern.sub("", text)
        
        # 3. Clean up multiple spaces and strip
        text = self.multi_spaces_pattern.sub(" ", text).strip()
        
        return text

    def remove_internal_repetition(self, text: str) -> str:
        words = text.split()
        if not words:
            return ""
            
        # Iteratively find and remove duplicate contiguous sub-sequences of words
        i = 0
        while i < len(words):
            duplicated_found = False
            # Check for repeated blocks starting at index i
            for size in range(1, (len(words) - i) // 2 + 1):
                block1 = words[i : i + size]
                block2 = words[i + size : i + 2 * size]
                if block1 == block2:
                    del words[i + size : i + 2 * size]
                    duplicated_found = True
                    break
            if not duplicated_found:
                i += 1
                
        return " ".join(words)

    def merge_segments(self, segments: List[Dict], min_paragraph_duration: float = 40.0, hard_max_duration: float = 90.0) -> List[Dict]:
        """
        Merges raw Whisper segments into longer paragraph segments to avoid wordy/fragmented text.
        Splits at sentence endings (. or ? or !) when min_paragraph_duration is met,
        and hard-splits at hard_max_duration.
        """
        if not segments:
            return []
            
        logger.info(f"[TranscriptCleaner] Merging {len(segments)} raw segments (min_dur={min_paragraph_duration}s, max_dur={hard_max_duration}s)")
        
        merged_list = []
        current = {
            "start": None,
            "end": None,
            "start_s": None,
            "end_s": None,
            "text": "",
            "timestamps": []
        }
        
        for seg in segments:
            seg_start_s = seg["start_s"]
            seg_end_s = seg["end_s"]
            cleaned_seg_text = self.remove_internal_repetition(self.clean_text(seg["text"]))
            
            if not cleaned_seg_text:
                continue
                
            if current["start"] is None:
                current["start"] = seg["start"]
                current["end"] = seg["end"]
                current["start_s"] = seg_start_s
                current["end_s"] = seg_end_s
                current["text"] = cleaned_seg_text
                current["timestamps"] = [f"[{seg['start']} → {seg['end']}]"]
                continue
                
            duration = seg_end_s - current["start_s"]
            
            # If the duration with the new segment exceeds hard maximum, flush the current first
            if duration > hard_max_duration:
                merged_list.append({
                    "start": current["start"],
                    "end": current["end"],
                    "start_s": current["start_s"],
                    "end_s": current["end_s"],
                    "text": current["text"].strip(),
                    "timestamps": current["timestamps"].copy(),
                    "duration": current["end_s"] - current["start_s"]
                })
                current = {
                    "start": seg["start"],
                    "end": seg["end"],
                    "start_s": seg_start_s,
                    "end_s": seg_end_s,
                    "text": cleaned_seg_text,
                    "timestamps": [f"[{seg['start']} → {seg['end']}]"]
                }
                continue
                
            # Append text and update end timestamps
            current["end"] = seg["end"]
            current["end_s"] = seg_end_s
            current["text"] += " " + cleaned_seg_text
            current["timestamps"].append(f"[{seg['start']} → {seg['end']}]")
            
            current_duration = current["end_s"] - current["start_s"]
            ends_with_punctuation = current["text"].strip().endswith((".", "?", "!"))
            
            # Flush if minimum paragraph length is reached and it ends a sentence
            if current_duration >= min_paragraph_duration and ends_with_punctuation:
                merged_list.append({
                    "start": current["start"],
                    "end": current["end"],
                    "start_s": current["start_s"],
                    "end_s": current["end_s"],
                    "text": current["text"].strip(),
                    "timestamps": current["timestamps"].copy(),
                    "duration": current_duration
                })
                current = {
                    "start": None,
                    "end": None,
                    "start_s": None,
                    "end_s": None,
                    "text": "",
                    "timestamps": []
                }
                
        # Flush residual current segment
        if current["text"]:
            merged_list.append({
                "start": current["start"],
                "end": current["end"],
                "start_s": current["start_s"],
                "end_s": current["end_s"],
                "text": current["text"].strip(),
                "timestamps": current["timestamps"].copy(),
                "duration": (current["end_s"] - current["start_s"]) if current["start_s"] else 0.0
            })
            
        logger.info(f"[TranscriptCleaner] Merged into {len(merged_list)} paragraph segments.")
        return merged_list