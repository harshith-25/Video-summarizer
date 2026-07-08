import sys
import os
import json
import re

# Add backend directory to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.video import Video
from app.models.summary import Summary
from app.models.document import Document
from app.services.document_generator import DocumentGenerator
from app.config import Config

def run_recovery():
    db = SessionLocal()
    try:
        # Find Video 3
        video = db.query(Video).filter(Video.id == 3).first()
        if not video:
            print("Video ID 3 not found.")
            return

        print(f"Found Video ID 3: {video.title}")
        
        summary = db.query(Summary).filter(Summary.video_id == video.id).first()
        if not summary:
            print("Summary not found for Video ID 3.")
            return

        print(f"Current Executive Summary in DB: {summary.executive_summary}")
        
        # If it failed to parse or we want to force re-parse
        raw_output = summary.detailed_summary
        if not raw_output.startswith("```json") and not raw_output.strip().startswith("{"):
            print("Raw output does not look like LLM output.")
            return
            
        print("Extracting and parsing JSON from raw LLM output...")
        
        # Extract JSON block
        json_match = re.search(r'```json\s*(.*?)\s*```', raw_output, re.DOTALL)
        if json_match:
            content = json_match.group(1).strip()
        else:
            content = raw_output.strip()
            
        try:
            summary_data = json.loads(content, strict=False)
            print("Successfully parsed LLM JSON!")
        except Exception as e:
            print(f"Failed to parse JSON even with strict=False: {e}")
            return
            
        # Update summary fields
        summary.executive_summary = summary_data.get("executive_summary", "N/A")
        summary.detailed_summary = summary_data.get("detailed_summary", "N/A")
        summary.key_topics = summary_data.get("key_topics", [])
        summary.action_items = summary_data.get("action_items", [])
        summary.timeline = summary_data.get("timeline", [])
        summary.conclusion = summary_data.get("conclusion", "N/A")
        
        db.commit()
        print("Updated Summary database fields successfully.")
        
        # Re-generate documents
        # 1. Delete old documents from DB & disk for this summary
        old_docs = db.query(Document).filter(Document.summary_id == summary.id).all()
        for doc in old_docs:
            if doc.file_path and os.path.exists(doc.file_path):
                try:
                    os.remove(doc.file_path)
                    print(f"Deleted old document file: {doc.file_path}")
                except Exception as ex:
                    print(f"Error deleting file {doc.file_path}: {ex}")
            db.delete(doc)
        db.commit()
        print("Removed old document database records.")
        
        # 2. Generate new documents
        meta = {
            "title": video.title,
            "source_url": video.source_url or "Direct Upload",
            "source_type": video.source_type,
            "duration_str": f"{video.duration:.1f}s" if video.duration else "N/A"
        }
        
        print("Generating documents...")
        gen = DocumentGenerator()
        doc_paths = gen.generate_all(summary_data, meta, video.user_id, Config.USER_DOCUMENTS_PATH)
        
        for file_type, file_info in doc_paths.items():
            doc_rec = Document(
                summary_id=summary.id,
                file_name=file_info["name"],
                file_path=file_info["path"],
                file_type=file_type,
                file_size=os.path.getsize(file_info["path"])
            )
            db.add(doc_rec)
            print(f"Saved new document to DB: {file_info['name']} ({file_type})")
            
        db.commit()
        print("Document regeneration and database update complete!")
        
    except Exception as e:
        db.rollback()
        print(f"Recovery failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_recovery()
