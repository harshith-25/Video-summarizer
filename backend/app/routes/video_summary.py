from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import uuid
import logging
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl

from app.database import get_db, SessionLocal
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.models.video import Video
from app.models.transcript import Transcript
from app.models.summary import Summary
from app.models.job import Job
from app.models.document import Document
from app.config import Config

# Import providers and services
from app.services.providers.youtube import YoutubeProvider
from app.services.providers.vimeo import VimeoProvider
from app.services.providers.cloud_storage import DriveProvider, DropboxProvider, OneDriveProvider
from app.services.providers.file_upload import FileUploadProvider
from app.services.audio_extractor import AudioExtractor
from app.services.whisper_transcriber import WhisperTranscriber
from app.services.transcript_cleaner import TranscriptCleaner
from app.services.summarizer import Summarizer
from app.services.document_generator import DocumentGenerator

logger = logging.getLogger("app")
video_router = APIRouter(prefix="/api", tags=["video_summarizer"])

# Schemas
class URLSummaryRequest(BaseModel):
    url: str
    title: Optional[str] = None
    language: Optional[str] = "en"

class SummarizeRequest(BaseModel):
    video_id: int
    language: Optional[str] = "en"

def detect_provider(url: str) -> str:
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    elif "vimeo.com" in url_lower:
        return "vimeo"
    elif "drive.google.com" in url_lower or "docs.google.com" in url_lower:
        return "google_drive"
    elif "dropbox.com" in url_lower:
        return "dropbox"
    elif "onedrive.live.com" in url_lower or "1drv.ms" in url_lower:
        return "onedrive"
    else:
        # Check standard video extensions
        clean_path = url.split("?")[0]
        if any(clean_path.endswith(f".{ext}") for ext in ["mp4", "mov", "avi", "mkv", "webm"]):
            return "direct_video"
        raise ValueError("Unsupported video URL source provider. Only YouTube, Vimeo, Google Drive, Dropbox, OneDrive, or direct video file links are supported.")

# Direct video downloader helper
def download_direct_video(url: str, dest_path: str):
    import requests
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)

def get_video_duration(video_path: str) -> float:
    try:
        import subprocess
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        duration_str = result.stdout.strip()
        if duration_str:
            return float(duration_str)
    except Exception as e:
        logger.warning(f"[Pipeline] Failed to resolve video duration via ffprobe for {video_path}: {e}")
    return 0.0

# Background pipeline task
def run_video_pipeline(job_id: str, user_id: int, source_type: str, source_value: str, video_title: str, language: Optional[str] = "en"):
    db: Session = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"[Pipeline] Job {job_id} not found in database.")
        db.close()
        return

    logger.info(f"[Pipeline] Starting background task for job: {job_id}")
    video_path = None
    wav_path = None
    duration = 0.0
    has_youtube_captions = False
    raw_segments = []
    raw_text = ""
    user_docs_dir = os.path.join(Config.USER_DOCUMENTS_PATH, str(user_id))
    user_media_dir = os.path.join(user_docs_dir, "media")
    user_temp_dir = os.path.join(user_docs_dir, "temp")
    
    os.makedirs(user_docs_dir, exist_ok=True)
    os.makedirs(user_media_dir, exist_ok=True)
    os.makedirs(user_temp_dir, exist_ok=True)

    try:
        # 1. Download or retrieve video file
        job.status = 'processing'
        job.progress = 10
        job.message = 'Downloading video from source...'
        db.commit()

        if source_type == 'upload':
            video_path = source_value
            logger.info(f"[Pipeline] Using pre-uploaded video: {video_path}")
        else:
            logger.info(f"[Pipeline] Resolving provider for URL: {source_value}")
            provider_type = detect_provider(source_value)
            
            if provider_type == 'youtube':
                try:
                    from pytubefix import YouTube
                    yt = YouTube(source_value, use_oauth=False)
                    if video_title == "Online Video File":
                        video_title = yt.title
                    if yt.length:
                        duration = float(yt.length)
                    
                    # Prioritize English captions, fall back to any available captions (manual first, then auto-generated)
                    caption = None
                    index = yt.captions.lang_code_index
                    
                    if "en" in index:
                        caption = index["en"]
                    elif "a.en" in index:
                        caption = index["a.en"]
                    else:
                        # Prioritize any manual caption (no 'a.' prefix)
                        for code in index.keys():
                            if not code.startswith("a."):
                                caption = index[code]
                                logger.info(f"[Pipeline] English captions not found. Using manual captions: {code}")
                                break
                        # Fallback to the first available auto-generated caption
                        if not caption and len(index) > 0:
                            first_code = list(index.keys())[0]
                            caption = index[first_code]
                            logger.info(f"[Pipeline] English captions not found. Using auto-generated captions: {first_code}")
                            
                    if caption:
                        logger.info(f"[Pipeline] Found YouTube captions for {source_value} before download. Parsing captions...")
                        xml_content = caption.xml_captions
                        
                        import xml.etree.ElementTree as ET
                        import html
                        
                        def format_timestamp(seconds: float) -> str:
                            if seconds < 0:
                                seconds = 0.0
                            total_ms = int(round(seconds * 1000))
                            total_sec, ms = divmod(total_ms, 1000)
                            h, rem = divmod(total_sec, 3600)
                            m, s = divmod(rem, 60)
                            return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
                        
                        root = ET.fromstring(xml_content)
                        full_text_parts = []
                        for child in root:
                            if child.tag == 'text':
                                start_s = float(child.attrib.get('start', 0.0))
                                dur_s = float(child.attrib.get('dur', 0.0))
                                end_s = start_s + dur_s
                                text = html.unescape(child.text or "").strip()
                                if not text:
                                    continue
                                raw_segments.append({
                                    "start": format_timestamp(start_s),
                                    "end": format_timestamp(end_s),
                                    "start_s": start_s,
                                    "end_s": end_s,
                                    "text": text
                                })
                                full_text_parts.append(text)
                                
                        raw_text = " ".join(full_text_parts)
                        if raw_text.strip():
                            has_youtube_captions = True
                            logger.info(f"[Pipeline] Successfully parsed YouTube captions. {len(raw_segments)} segments retrieved.")
                except Exception as e:
                    logger.warning(f"[Pipeline] Failed to resolve YouTube metadata/captions: {e}")
                
                if has_youtube_captions:
                    # Skip downloading entirely! Use a placeholder path
                    video_path = f"youtube_online_{yt.video_id}"
                    logger.info(f"[Pipeline] Skipping download because captions exist. Local path set to: {video_path}")
                else:
                    # Download only the audio stream to make transcription much faster!
                    logger.info(f"[Pipeline] No English captions found. Downloading audio-only stream for Whisper...")
                    video_path = YoutubeProvider().download(source_value, user_media_dir, only_audio=True)
            elif provider_type == 'vimeo':
                try:
                    v_id = VimeoProvider()._extract_video_id(source_value)
                    cfg = VimeoProvider()._get_player_config(v_id)
                    if cfg:
                        if video_title == "Online Video File":
                            video_title = cfg.get("video", {}).get("title", "Vimeo Video")
                        v_dur = cfg.get("video", {}).get("duration")
                        if v_dur:
                            duration = float(v_dur)
                except Exception as e:
                    logger.warning(f"[Pipeline] Failed to resolve Vimeo metadata: {e}")
                video_path = VimeoProvider().download(source_value, user_media_dir)
            elif provider_type == 'google_drive':
                video_path = DriveProvider().download(source_value, user_media_dir)
            elif provider_type == 'dropbox':
                video_path = DropboxProvider().download(source_value, user_media_dir)
            elif provider_type == 'onedrive':
                video_path = OneDriveProvider().download(source_value, user_media_dir)
            elif provider_type == 'direct_video':
                filename = f"direct_{uuid.uuid4().hex}.mp4"
                video_path = os.path.join(user_media_dir, filename)
                download_direct_video(source_value, video_path)
            else:
                raise ValueError("Unknown provider type")

        # Fallback cleanup of title from filename if still default
        if video_title == "Online Video File" and video_path:
            try:
                base_name = os.path.basename(video_path)
                for prefix in ['dropbox_', 'drive_', 'vimeo_', 'direct_', 'onedrive_']:
                    if base_name.startswith(prefix):
                        base_name = base_name[len(prefix):]
                cleaned_title = os.path.splitext(base_name)[0]
                video_title = cleaned_title.replace("_", " ").replace("-", " ").title()
            except Exception as e:
                logger.warning(f"[Pipeline] Failed to parse title from filename: {e}")

        job.progress = 30
        job.message = 'Video retrieved successfully. Registering video metadata...'
        db.commit()

        # Check file size & duration
        file_size = os.path.getsize(video_path) if (video_path and os.path.exists(video_path)) else 0
        if duration == 0.0 and video_path and os.path.exists(video_path):
            duration = get_video_duration(video_path)
        
        # Save Video record
        video = Video(
            user_id=user_id,
            title=video_title,
            source_type=source_type if source_type == 'upload' else detect_provider(source_value),
            source_url=None if source_type == 'upload' else source_value,
            local_path=video_path,
            file_size=file_size,
            duration=duration
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        
        job.video_id = video.id
        db.commit()

        # Check if we can use pre-existing YouTube captions
        if has_youtube_captions:
            logger.info("[Pipeline] Using YouTube captions pre-extracted during metadata phase. Skipping download and transcription.")

        if has_youtube_captions:
            job.progress = 70
            job.message = 'Using YouTube captions. Skipping transcription...'
            db.commit()
            
            cleaner = TranscriptCleaner()
            cleaned_text = cleaner.remove_internal_repetition(cleaner.clean_text(raw_text))
            merged_segments = cleaner.merge_segments(raw_segments)
            
            # Save Transcript to DB
            transcript = Transcript(
                video_id=video.id,
                raw_text=raw_text,
                cleaned_text=cleaned_text,
                segments_json=merged_segments,
                model_name="youtube-captions",
                language=language
            )
            db.add(transcript)
            db.commit()
        else:
            job.progress = 40
            job.message = 'Extracting audio track...'
            db.commit()

            # 2. Extract Audio
            wav_path = AudioExtractor().extract_audio(video_path, user_temp_dir)

            duration_desc = f" ({int(duration // 60)} min video)" if duration > 0 else ""
            job.progress = 50
            job.message = f'Transcribing speech to text (AI){duration_desc}... This may take a few minutes.'
            db.commit()

            # 3. Speech to text
            raw_segments, raw_text = WhisperTranscriber().transcribe(wav_path)

            if not raw_text.strip():
                raise ValueError("Whisper transcription yielded no speech elements.")

            job.progress = 70
            job.message = 'Cleaning and formatting transcript...'
            db.commit()

            # 4. Transcript Cleanup
            cleaner = TranscriptCleaner()
            cleaned_text = cleaner.remove_internal_repetition(cleaner.clean_text(raw_text))
            merged_segments = cleaner.merge_segments(raw_segments)

            # Save Transcript to DB
            transcript = Transcript(
                video_id=video.id,
                raw_text=raw_text,
                cleaned_text=cleaned_text,
                segments_json=merged_segments,
                model_name="whisper-base",
                language=language
            )
            db.add(transcript)
            db.commit()

        job.progress = 80
        job.message = 'Generating video summaries...'
        db.commit()

        # 5. Summarization
        def update_progress_callback(msg: str, prg: int):
            job.progress = prg
            job.message = msg
            db.commit()

        summary_data = Summarizer().generate_final_summary(
            segments=merged_segments,
            video_title=video_title,
            source_type=video.source_type,
            target_language=language,
            progress_callback=update_progress_callback
        )

        # Save Summary to DB
        summary = Summary(
            video_id=video.id,
            executive_summary=summary_data.get("executive_summary", "N/A"),
            detailed_summary=summary_data.get("detailed_summary", "N/A"),
            key_topics=summary_data.get("key_topics", []),
            action_items=summary_data.get("action_items", []),
            timeline=summary_data.get("timeline", []),
            conclusion=summary_data.get("conclusion", "N/A")
        )
        db.add(summary)
        db.commit()
        db.refresh(summary)

        job.progress = 90
        job.message = 'Formatting documents (PDF, DOCX, MD)...'
        db.commit()

        # 6. Document Generation
        meta = {
            "title": video_title,
            "source_url": video.source_url or "Direct Upload",
            "source_type": video.source_type,
            "duration_str": f"{video.duration:.1f}s" if video.duration else "N/A"
        }
        gen = DocumentGenerator()
        doc_paths = gen.generate_all(summary_data, meta, user_id, Config.USER_DOCUMENTS_PATH)

        for file_type, file_info in doc_paths.items():
            doc_rec = Document(
                summary_id=summary.id,
                file_name=file_info["name"],
                file_path=file_info["path"],
                file_type=file_type,
                file_size=os.path.getsize(file_info["path"])
            )
            db.add(doc_rec)
        db.commit()

        job.status = 'completed'
        job.progress = 100
        job.message = 'Summarization completed successfully.'
        db.commit()
        logger.info(f"[Pipeline] Job {job_id} completed successfully for video ID {video.id}")

    except Exception as e:
        logger.error(f"[Pipeline] Exception occurred in job {job_id}: {e}", exc_info=True)
        job.status = 'failed'
        job.progress = 100
        job.error_message = str(e)
        job.message = 'Processing failed.'
        db.commit()
    finally:
        # Cleanup temporary audio files
        if wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
                logger.info(f"[Pipeline] Cleaned up temporary wav: {wav_path}")
            except Exception:
                pass
        db.close()

# API Endpoints
@video_router.post("/video/upload", status_code=status.HTTP_202_ACCEPTED)
def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    language: Optional[str] = Form("en"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Determine safe title
    video_title = title if title else os.path.splitext(file.filename)[0]
    
    # Save the file upload in user's media directory first
    user_docs_dir = os.path.join(Config.USER_DOCUMENTS_PATH, str(current_user.id))
    user_media_dir = os.path.join(user_docs_dir, "media")
    
    try:
        uploader = FileUploadProvider()
        saved_path = uploader.save_upload(file, user_media_dir, custom_filename=f"upload_{uuid.uuid4().hex}")
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"File upload saving failed: {err}")

    # Create Job record
    job = Job(
        user_id=current_user.id,
        status='queued',
        progress=0,
        message='Job queued. Waiting to start upload pipeline.'
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue background processing task
    background_tasks.add_task(
        run_video_pipeline,
        job.id,
        current_user.id,
        'upload',
        saved_path,
        video_title,
        language
    )

    return {
        "success": True,
        "job_id": job.id,
        "message": "Video file upload received and processing started in background."
    }

@video_router.post("/video/url", status_code=status.HTTP_202_ACCEPTED)
def submit_url(
    req: URLSummaryRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        detect_provider(req.url)
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))

    video_title = req.title if req.title else "Online Video File"

    # Create Job record
    job = Job(
        user_id=current_user.id,
        status='queued',
        progress=0,
        message='Job queued. Resolving download provider.'
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue background task
    background_tasks.add_task(
        run_video_pipeline,
        job.id,
        current_user.id,
        'url',
        req.url,
        video_title,
        req.language
    )

    return {
        "success": True,
        "job_id": job.id,
        "message": "Video URL submission received and processing started in background."
    }

@video_router.post("/video/summarize", status_code=status.HTTP_202_ACCEPTED)
def summarize_video(
    req: SummarizeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    video = db.query(Video).filter(Video.id == req.video_id, Video.user_id == current_user.id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")

    # Create Job record
    job = Job(
        user_id=current_user.id,
        video_id=video.id,
        status='queued',
        progress=0,
        message='Re-triggering summarization pipeline.'
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Run pipeline in background using existing video path
    background_tasks.add_task(
        run_video_pipeline,
        job.id,
        current_user.id,
        video.source_type,
        video.local_path,
        video.title,
        req.language
    )

    return {
        "success": True,
        "job_id": job.id,
        "message": "Summarization task triggered."
    }

@video_router.get("/videos", status_code=status.HTTP_200_OK)
def list_videos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    videos = db.query(Video).filter(Video.user_id == current_user.id).order_by(Video.created_at.desc()).all()
    active_jobs = db.query(Job).filter(Job.user_id == current_user.id, Job.video_id == None).order_by(Job.created_at.desc()).all()
    
    result = []
    for job in active_jobs:
        result.append({
            "id": None,
            "job_id": job.id,
            "title": "Processing video...",
            "source_type": "unknown",
            "source_url": None,
            "file_size": 0,
            "duration": 0.0,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "status": job.status,
            "progress": job.progress,
            "message": job.message,
            "error_message": job.error_message
        })
        
    for v in videos:
        latest_job = db.query(Job).filter(Job.video_id == v.id).order_by(Job.created_at.desc()).first()
        video_dict = v.to_dict()
        video_dict["job_id"] = latest_job.id if latest_job else None
        video_dict["status"] = latest_job.status if latest_job else "completed"
        video_dict["progress"] = latest_job.progress if latest_job else 100
        video_dict["message"] = latest_job.message if latest_job else "Completed"
        video_dict["error_message"] = latest_job.error_message if latest_job else None
        result.append(video_dict)
        
    return {"success": True, "videos": result}


@video_router.get("/video/{video_id}/stream")
def stream_video(
    video_id: int,
    request: Request,
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    from fastapi import HTTPException
    from app.utils.jwt_helper import decode_token
    
    actual_token = None
    if token:
        actual_token = token
    else:
        # Check authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header:
            if auth_header.startswith("Bearer "):
                parts = auth_header.split(" ")
                if len(parts) == 2:
                    actual_token = parts[1]
            else:
                actual_token = auth_header
                
    if not actual_token:
        raise HTTPException(status_code=401, detail="Authentication token is missing.")
        
    payload = decode_token(actual_token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
        
    user_id = payload.get("user_id")
    video = db.query(Video).filter(Video.id == video_id, Video.user_id == user_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video record not found.")
        
    if not video.local_path or not os.path.exists(video.local_path):
        raise HTTPException(status_code=404, detail="Video file not found on disk.")
        
    return FileResponse(
        path=video.local_path,
        media_type="video/mp4",
        headers={"Accept-Ranges": "bytes"}
    )


@video_router.get("/summary/{video_id}")
def get_summary(video_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    video = db.query(Video).filter(Video.id == video_id, Video.user_id == current_user.id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video or summary not found.")
        
    summary = db.query(Summary).filter(Summary.video_id == video.id).first()
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not generated yet.")

    return {
        "success": True,
        "video": video.to_dict(),
        "summary": summary.to_dict()
    }

@video_router.get("/summary/{video_id}/status")
def get_job_status(video_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Find latest job associated with this video or user
    job = db.query(Job).filter(Job.video_id == video_id, Job.user_id == current_user.id).order_by(Job.created_at.desc()).first()
    if not job:
        # Fallback to check by ID direct if parameter corresponds to Job UUID
        raise HTTPException(status_code=404, detail="Processing job status not found.")
        
    return {
        "success": True,
        "job": job.to_dict()
    }

# Additional endpoint to poll job directly by Job UUID string
@video_router.get("/job/{job_id}/status")
def get_job_status_by_id(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job status not found.")
    return {
        "success": True,
        "job": job.to_dict()
    }

@video_router.get("/summary/{video_id}/download/{file_type}")
def download_summary_file(video_id: int, file_type: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if file_type not in ["pdf", "docx", "md"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Support: pdf, docx, md")
        
    video = db.query(Video).filter(Video.id == video_id, Video.user_id == current_user.id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")
        
    summary = db.query(Summary).filter(Summary.video_id == video.id).first()
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not generated.")
        
    doc = db.query(Document).filter(Document.summary_id == summary.id, Document.file_type == file_type).first()
    if not doc or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Requested summary document file not found on disk.")
        
    return FileResponse(
        path=doc.file_path,
        filename=doc.file_name,
        media_type="application/octet-stream"
    )

@video_router.delete("/summary/{video_id}")
def delete_summary(video_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    video = db.query(Video).filter(Video.id == video_id, Video.user_id == current_user.id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video record not found.")

    try:
        # Delete files from disk first
        if video.local_path and os.path.exists(video.local_path):
            try:
                os.remove(video.local_path)
            except Exception:
                pass
                
        summary = db.query(Summary).filter(Summary.video_id == video.id).first()
        if summary:
            docs = db.query(Document).filter(Document.summary_id == summary.id).all()
            for doc in docs:
                if doc.file_path and os.path.exists(doc.file_path):
                    try:
                        os.remove(doc.file_path)
                    except Exception:
                        pass
        
        # Database cascade will delete transcripts, summaries, jobs, and documents
        db.delete(video)
        db.commit()
        
        logger.info(f"Video {video_id} and all summarization assets deleted successfully.")
        return {
            "success": True,
            "message": "Video summary and all linked documents and media files deleted successfully."
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed deleting video summary {video_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed deleting resources: {e}")

@video_router.delete("/job/{job_id}", status_code=status.HTTP_200_OK)
def delete_job(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
        
    try:
        db.delete(job)
        db.commit()
        logger.info(f"Job {job_id} deleted successfully.")
        return {
            "success": True,
            "message": "Pipeline job record deleted successfully."
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed deleting job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed deleting job: {e}")