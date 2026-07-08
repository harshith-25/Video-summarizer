import os
import re
import logging
import requests
from app.services.providers.base_provider import VideoProvider

logger = logging.getLogger("app")

class DriveProvider(VideoProvider):
    def _extract_file_id(self, url: str) -> str:
        # Match standard drive link patterns
        patterns = [
            r'/file/d/([a-zA-Z0-9_-]+)',
            r'[?&]id=([a-zA-Z0-9_-]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return url

    def download(self, source: str, output_dir: str, **kwargs) -> str:
        file_id = self._extract_file_id(source)
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"drive_{file_id}_video.mp4")
        
        logger.info(f"[DriveProvider] Resolving Google Drive ID: {file_id}")
        
        session = requests.Session()
        download_url = "https://docs.google.com/uc?export=download"
        
        try:
            # First request to get the confirm token
            response = session.get(download_url, params={'id': file_id}, stream=True, timeout=30)
            
            # Find the confirmation token
            confirm_token = None
            for key, value in response.cookies.items():
                if key.startswith('download_warning'):
                    confirm_token = value
                    break
                    
            if not confirm_token:
                # Scan response text for confirm token if cookies did not have it
                html_content = response.text if response.headers.get('content-type', '').startswith('text/html') else ''
                match = re.search(r'confirm=([a-zA-Z0-9_-]+)', html_content)
                if match:
                    confirm_token = match.group(1)
            
            if confirm_token:
                logger.info(f"[DriveProvider] Large file warning detected. Using confirmation token.")
                response = session.get(download_url, params={'id': file_id, 'confirm': confirm_token}, stream=True, timeout=30)
                
            response.raise_for_status()
            
            # Write out file
            with open(out_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"[DriveProvider] Google Drive download completed: {out_path}")
            return out_path
        except Exception as e:
            logger.error(f"[DriveProvider] Google Drive download failed: {e}")
            raise RuntimeError(f"Google Drive download failed: {e}")


class DropboxProvider(VideoProvider):
    def download(self, source: str, output_dir: str, **kwargs) -> str:
        os.makedirs(output_dir, exist_ok=True)
        # Parse Dropbox URL to make it a direct download link
        # e.g., change dl=0 to dl=1
        direct_url = source
        if 'dl=0' in direct_url:
            direct_url = direct_url.replace('dl=0', 'dl=1')
        elif 'dl=1' not in direct_url:
            separator = '&' if '?' in direct_url else '?'
            direct_url += f"{separator}dl=1"

        # Replaces www.dropbox.com with dl.dropboxusercontent.com for direct file retrieval
        direct_url = direct_url.replace('www.dropbox.com', 'dl.dropboxusercontent.com')
        
        # Deduce a temporary name from URL or use a default
        filename_match = re.search(r'/s/[^/]+/([^?]+)', source)
        filename = filename_match.group(1) if filename_match else "dropbox_video.mp4"
        out_path = os.path.join(output_dir, f"dropbox_{filename}")
        
        logger.info(f"[DropboxProvider] Downloading from URL: {direct_url}")
        
        try:
            with requests.get(direct_url, stream=True, allow_redirects=True, timeout=30) as r:
                r.raise_for_status()
                with open(out_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
            logger.info(f"[DropboxProvider] Dropbox download completed: {out_path}")
            return out_path
        except Exception as e:
            logger.error(f"[DropboxProvider] Dropbox download failed: {e}")
            raise RuntimeError(f"Dropbox download failed: {e}")


class OneDriveProvider(VideoProvider):
    def download(self, source: str, output_dir: str, **kwargs) -> str:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "onedrive_video.mp4")
        
        logger.info(f"[OneDriveProvider] Resolving OneDrive URL: {source}")
        
        try:
            # Resolve short URLs if present
            resolved_url = source
            if "1drv.ms" in source:
                r = requests.head(source, allow_redirects=True, timeout=10)
                resolved_url = r.url
                logger.info(f"[OneDriveProvider] Resolved short link to: {resolved_url}")
                
            # Convert share link to direct download link
            # Shared link: https://onedrive.live.com/redir?resid=...&authkey=...
            # Direct link: https://onedrive.live.com/download?resid=...&authkey=...
            direct_url = resolved_url
            if "onedrive.live.com/redir" in direct_url:
                direct_url = direct_url.replace("onedrive.live.com/redir", "onedrive.live.com/download")
            elif "onedrive.live.com/edit.aspx" in direct_url:
                direct_url = direct_url.replace("onedrive.live.com/edit.aspx", "onedrive.live.com/download")
                
            logger.info(f"[OneDriveProvider] Downloading from direct link: {direct_url}")
            
            with requests.get(direct_url, stream=True, allow_redirects=True, timeout=30) as r:
                r.raise_for_status()
                with open(out_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
            logger.info(f"[OneDriveProvider] OneDrive download completed: {out_path}")
            return out_path
        except Exception as e:
            logger.error(f"[OneDriveProvider] OneDrive download failed: {e}")
            raise RuntimeError(f"OneDrive download failed: {e}")