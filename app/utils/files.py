import hashlib
import mimetypes
from pathlib import Path
from werkzeug.utils import secure_filename
from config import Config

def get_project_dir(project_id: str) -> Path:
    p = Config.MEDIA_ROOT / project_id
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_project_output_dir(project_id: str) -> Path:
    p = Config.OUTPUT_ROOT / project_id
    p.mkdir(parents=True, exist_ok=True)
    return p

def calculate_checksum(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def detect_mime_type(file_path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(file_path))
    if mime:
        return mime
    suffix = file_path.suffix.lower()
    if suffix in (".mp3",):
        return "audio/mpeg"
    elif suffix in (".wav",):
        return "audio/wav"
    elif suffix in (".m4a",):
        return "audio/mp4"
    elif suffix in (".mp4",):
        return "video/mp4"
    elif suffix in (".webm",):
        return "video/webm"
    elif suffix in (".webp",):
        return "image/webp"
    elif suffix in (".png",):
        return "image/png"
    elif suffix in (".jpg", ".jpeg"):
        return "image/jpeg"
    return "application/octet-stream"
