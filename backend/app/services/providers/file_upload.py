import os
import logging
from fastapi import UploadFile

logger = logging.getLogger("app")

class FileUploadProvider:
    def __init__(self, allowed_extensions=None, max_file_size_bytes=None):
        # Default allowed formats
        self.allowed_extensions = allowed_extensions or {'mp4', 'mov', 'avi', 'mkv', 'webm', 'mp3', 'wav', 'm4a'}
        # Default max upload size: 500 MB
        self.max_file_size = max_file_size_bytes or (500 * 1024 * 1024)

    def validate_file(self, filename: str) -> str:
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        if ext not in self.allowed_extensions:
            raise ValueError(f"Unsupported file format: '.{ext}'. Allowed: {', '.join(self.allowed_extensions)}")
        return ext

    def save_upload(self, upload_file: UploadFile, dest_dir: str, custom_filename: str = None) -> str:
        filename = upload_file.filename
        ext = self.validate_file(filename)
        
        target_name = custom_filename if custom_filename else filename
        if not target_name.endswith(f".{ext}"):
            target_name = f"{target_name}.{ext}"
            
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, target_name)
        
        logger.info(f"[FileUploadProvider] Saving upload '{filename}' -> '{dest_path}'")
        
        try:
            total_size = 0
            # Read and write in chunks to avoid memory pressure
            with open(dest_path, "wb") as buffer:
                while True:
                    chunk = upload_file.file.read(1024 * 1024)  # 1MB chunk
                    if not chunk:
                        break
                    total_size += len(chunk)
                    if total_size > self.max_file_size:
                        buffer.close()
                        os.remove(dest_path)
                        max_mb = self.max_file_size // (1024 * 1024)
                        raise ValueError(f"Uploaded file size exceeds the limit of {max_mb} MB.")
                    buffer.write(chunk)
            
            logger.info(f"[FileUploadProvider] Save completed. Total size: {total_size} bytes")
            return dest_path
        except Exception as e:
            logger.error(f"[FileUploadProvider] File save failed: {e}", exc_info=True)
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except Exception:
                    pass
            raise