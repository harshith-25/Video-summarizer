import json
import logging
import re
from typing import List, Dict, Any, Optional, Callable
from app.llm.mistral_provider import MistralProvider

logger = logging.getLogger("app")

class Summarizer:
    def __init__(self):
        self.llm = MistralProvider()

    def _extract_json(self, llm_output: str) -> Dict[str, Any]:
        """Cleans and extracts JSON content from the LLM output."""
        content = ""
        try:
            # Look for markdown JSON block
            json_match = re.search(r'```json\s*(.*?)\s*```', llm_output, re.DOTALL)
            if json_match:
                content = json_match.group(1).strip()
            else:
                content = llm_output.strip()
                
            return json.loads(content, strict=False)
        except Exception as e:
            logger.error(f"[Summarizer] Failed to parse JSON from LLM: {e}. Output: {llm_output}")
            # Try to sanitize and parse
            try:
                content_clean = content.replace("```json", "").replace("```", "").strip()
                return json.loads(content_clean, strict=False)
            except Exception as inner_e:
                logger.error(f"[Summarizer] Inner parser failed: {inner_e}")
                
            # Return a fallback structured dictionary
            return {
                "executive_summary": "Failed to parse structured summary.",
                "detailed_summary": llm_output,
                "key_topics": [],
                "important_points": [],
                "action_items": [],
                "timeline": [],
                "conclusion": "Please check the detailed logs."
            }

    def chunk_transcript(self, segments: List[Dict], max_words: int = 1500) -> List[List[Dict]]:
        """Groups segments into chunks that do not exceed the max word count."""
        chunks = []
        current_chunk = []
        current_words = 0
        
        for seg in segments:
            seg_text = seg.get("text", "")
            seg_words = len(seg_text.split())
            
            if current_words + seg_words > max_words and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_words = 0
                
            current_chunk.append(seg)
            current_words += seg_words
            
        if current_chunk:
            chunks.append(current_chunk)
            
        logger.info(f"[Summarizer] Grouped {len(segments)} segments into {len(chunks)} LLM chunks.")
        return chunks

    def summarize_chunk(self, chunk: List[Dict]) -> str:
        """Summarizes an individual chunk of transcript segments, preserving timelines."""
        context = ""
        for seg in chunk:
            context += f"[{seg.get('start')} -> {seg.get('end')}]: {seg.get('text')}\n"
            
        system_prompt = (
            "You are an expert video analyst assistant. Summarize the following section of a video transcript. "
            "Highlight the key topics, decisions, and discussions, preserving any relevant timelines or timestamps."
        )
        
        prompt = (
            f"Here is a section of the video transcript with timestamps:\n\n{context}\n\n"
            "Provide a concise summary of what was discussed, what key facts were mentioned, and notes on critical moments."
        )
        
        try:
            summary = self.llm.generate(prompt=prompt, system_prompt=system_prompt, max_tokens=1000)
            return summary
        except Exception as e:
            logger.error(f"[Summarizer] Error summarizing chunk: {e}")
            return "Error summarizing this section."

    def generate_final_summary(self, segments: List[Dict], video_title: str, source_type: str = "URL", target_language: str = "en", progress_callback: Optional[Callable[[str, int], None]] = None) -> Dict[str, Any]:
        """
        Processes segments, summarizes them (using chunking if necessary), 
        and outputs the final well-structured JSON document in the target language.
        """
        # Determine total word count
        full_text = " ".join(seg.get("text", "") for seg in segments)
        total_words = len(full_text.split())
        
        logger.info(f"[Summarizer] Starting final summary pipeline for '{video_title}'. Target language: {target_language}. Word count: {total_words}")

        # If transcript is short, summarize in one shot. Otherwise chunk first.
        if total_words < 2000:
            logger.info("[Summarizer] Video transcript is short. Executing single-pass summarization.")
            chunk_summaries_str = f"Transcript:\n\n"
            for seg in segments:
                chunk_summaries_str += f"[{seg.get('start')} -> {seg.get('end')}]: {seg.get('text')}\n"
        else:
            logger.info("[Summarizer] Video transcript is long. Executing multi-pass chunk summarization.")
            chunks = self.chunk_transcript(segments, max_words=1500)
            partial_summaries = []

            for i, chunk in enumerate(chunks):
                if progress_callback:
                    # Update progress dynamically between 80% and 86% depending on chunk number
                    chunk_prog = 80 + int((i / len(chunks)) * 6)
                    progress_callback(f"Generating video summaries (Section {i+1}/{len(chunks)})...", chunk_prog)
                logger.info(f"[Summarizer] Summarizing chunk {i+1}/{len(chunks)}")
                p_sum = self.summarize_chunk(chunk)
                partial_summaries.append(f"Section {i+1} Summary:\n{p_sum}")

            chunk_summaries_str = "\n\n".join(partial_summaries)
 
        # Reconstruct timeline from segments (take 10 key timestamps)
        timeline_context = ""
        # Sample up to 15 segments evenly distributed across the video to build the timeline
        step = max(1, len(segments) // 15)
        sampled_segments = segments[::step][:15]
        for seg in sampled_segments:
            timeline_context += f"[{seg.get('start')}]: {seg.get('text')[:120]}...\n"

        language_mapping = {
            "en": "English",
            "hi": "Hindi",
            "bn": "Bengali",
            "gu": "Gujarati",
            "kn": "Kannada",
            "ml": "Malayalam",
            "mr": "Marathi",
            "pa": "Punjabi",
            "ta": "Tamil",
            "te": "Telugu",
            "ur": "Urdu"
        }
        target_lang_name = language_mapping.get(target_language.lower(), "English")

        system_prompt = (
            "You are an expert AI Video Summarizer.\n\n"
            "Your objective is to produce a concise, information-dense summary of a video transcript, "
            f"compressing the information while preserving all critical meaning, facts, decisions, metrics, and outcomes. The target language for the summary output is {target_lang_name}.\n\n"
            f"CRITICAL LANGUAGE CONSTRAINT: You MUST write all textual content inside the output JSON (including the executive_summary, detailed_summary, topic names and descriptions, important points, action items, timeline event descriptions, and conclusion) in the language: {target_lang_name}.\n\n"
            "Strict Output Constraints:\n"
            "- Executive Summary: 80-120 words (2-5 concise sentences summarizing the entire video).\n"
            "- Detailed Summary: 150-250 words (one concise paragraph covering the complete flow without unnecessary details).\n"
            "- Key Topics: Maximum 8 topics, with each topic description restricted to a maximum of 25 words.\n"
            "- Important Points: Maximum 10 bullets, with each bullet restricted to a maximum of 20 words.\n"
            "- Action Items: Only include if explicitly mentioned or clearly implied; otherwise return [].\n"
            "- Timeline: Only major topic changes or milestones, maximum 10 entries. Event description should be very short. The 'timestamp' MUST be a video playback offset from the transcript (formatted as HH:MM:SS.mmm), NOT a calendar date or historical year (like 1632).\n"
            "- Conclusion: Exactly 1 concise concluding sentence.\n\n"
            "Negative Guidelines (Do NOT):\n"
            "- Do NOT repeat the same information across different sections.\n"
            "- Do NOT mention obvious or trivial details.\n"
            "- Do NOT rewrite or copy-paste large portions of the transcript.\n"
            "- Do NOT explain every example in detail (summarize them instead).\n"
            "- Do NOT use marketing or promotional language.\n"
            "- Do NOT add conversational introductions like 'The video discusses...' or 'In this video...'.\n"
            "- Do NOT use calendar years or historical dates (like 1632 or 2024) as timeline timestamps. Use only video playback offsets.\n\n"
            "You MUST respond ONLY with a raw JSON block in {target_lang_name} matching this schema:\n"
            "{\n"
            "  \"executive_summary\": \"2-5 concise sentences (80-120 words).\",\n"
            "  \"detailed_summary\": \"One concise paragraph (150-250 words) covering the complete flow without repeating the executive summary.\",\n"
            "  \"key_topics\": [\n"
            "     {\"topic\": \"Topic Name\", \"description\": \"One sentence (max 25 words).\"}\n"
            "  ],\n"
            "  \"important_points\": [\n"
            "     \"Short bullet point highlighting a key fact, metric, or outcome (max 20 words).\"\n"
            "  ],\n"
            "  \"action_items\": [\n"
            "     \"Actionable task or next step explicitly mentioned or clearly implied.\"\n"
            "  ],\n"
            "  \"timeline\": [\n"
            "     {\"timestamp\": \"HH:MM:SS.mmm\", \"event\": \"Very short event description. The timestamp MUST match a playback offset from the transcript (e.g. 00:01:30.000), NOT a calendar year (like 1632).\"}\n"
            "  ],\n"
            "  \"conclusion\": \"One concise concluding sentence.\"\n"
            "}"
        )

        prompt = (
            f"Video Title: {video_title}\n"
            f"Source Type: {source_type}\n\n"
            "Your goal is to compress the following transcript/summary sections to approximately 10-15% of their original length while preserving all essential facts, decisions, metrics, and outcomes. Remove conversational filler, redundant explanations, and repeated ideas.\n\n"
            f"Transcript sections:\n\n{chunk_summaries_str}\n\n"
            f"Timeline reference moments:\n\n{timeline_context}\n\n"
            "Synthesize this information and output the final valid JSON document according to the system instructions and constraints."
        )

        if progress_callback:
            progress_callback("Synthesizing final video summary (AI)...", 88)

        try:
            llm_output = self.llm.generate(prompt=prompt, system_prompt=system_prompt, max_tokens=2500)
            return self._extract_json(llm_output)
        except Exception as e:
            logger.error(f"[Summarizer] Final summarization failed: {e}", exc_info=True)
            raise RuntimeError(f"Summarization generation failed: {e}")