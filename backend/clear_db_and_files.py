import os
import sys
import shutil

# Add backend directory to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from sqlalchemy import text

def clear_db_and_files():
    db = SessionLocal()
    try:
        # 1. Truncate database tables
        print("Truncating tables in database...")
        # TRUNCATE with RESTART IDENTITY CASCADE resets the auto-incrementing serial IDs to start from 1
        query = text("TRUNCATE TABLE documents, summaries, transcripts, jobs, videos RESTART IDENTITY CASCADE;")
        db.execute(query)
        db.commit()
        print("Database truncation completed successfully. Sequence IDs reset to 1.")
        
        # 2. Clear files in backend/data/
        data_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        print(f"Clearing files in data root folder: {data_root} ...")
        if os.path.exists(data_root):
            for sub_folder in ["user_documents", "test_media"]:
                sub_dir = os.path.join(data_root, sub_folder)
                if os.path.exists(sub_dir):
                    for filename in os.listdir(sub_dir):
                        file_path = os.path.join(sub_dir, filename)
                        try:
                            if os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                                print(f"Deleted directory: {file_path}")
                            else:
                                os.remove(file_path)
                                print(f"Deleted file: {file_path}")
                        except Exception as ex:
                            print(f"Failed to delete {file_path}: {ex}")
                    # Recreate the directory empty
                    os.makedirs(sub_dir, exist_ok=True)
            print("Finished clearing data folder.")
        else:
            print("data root folder does not exist.")
            
    except Exception as e:
        db.rollback()
        print(f"Database/File clearance failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    clear_db_and_files()
