from abc import ABC, abstractmethod

class VideoProvider(ABC):
    @abstractmethod
    def download(self, source: str, output_dir: str, **kwargs) -> str:
        """
        Downloads or retrieves a video file and saves it locally.
        
        Args:
            source: The video URL, identifier, or local file identifier.
            output_dir: The directory to save the downloaded file.
            
        Returns:
            The absolute or relative local path to the downloaded video file.
        """
        pass