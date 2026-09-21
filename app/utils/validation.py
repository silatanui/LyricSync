from pathlib import Path
from typing import Tuple, Optional
from config import Config

def validate_audio_file(filename: str, size_bytes: int) -> Tuple[bool, Optional[str]]:
    ext = Path(filename).suffix.lstrip(".").lower()
    if ext not in Config.ALLOWED_AUDIO_EXTENSIONS:
        return False, f"Unsupported audio format '.{ext}'. Allowed: {', '.join(Config.ALLOWED_AUDIO_EXTENSIONS)}"
    
    max_bytes = Config.UPLOAD_MAX_AUDIO_MB * 1024 * 1024
    if size_bytes > max_bytes:
        return False, f"Audio file exceeds maximum size of {Config.UPLOAD_MAX_AUDIO_MB} MB"
        
    return True, None

def validate_video_file(filename: str, size_bytes: int) -> Tuple[bool, Optional[str]]:
    ext = Path(filename).suffix.lstrip(".").lower()
    if ext not in Config.ALLOWED_VIDEO_EXTENSIONS:
        return False, f"Unsupported video format '.{ext}'. Allowed: {', '.join(Config.ALLOWED_VIDEO_EXTENSIONS)}"
        
    max_bytes = Config.UPLOAD_MAX_VIDEO_MB * 1024 * 1024
    if size_bytes > max_bytes:
        return False, f"Video file exceeds maximum size of {Config.UPLOAD_MAX_VIDEO_MB} MB"
        
    return True, None
