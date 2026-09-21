import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-lyricsync-2026")
    ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")

    # Data and media storage roots
    DATA_ROOT = Path(os.getenv("DATA_ROOT", str(BASE_DIR / "data")))
    MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", str(BASE_DIR / "data" / "media")))
    OUTPUT_ROOT = Path(os.getenv("OUTPUT_ROOT", str(BASE_DIR / "data" / "outputs")))
    TEMP_ROOT = Path(os.getenv("TEMP_ROOT", str(BASE_DIR / "data" / "temp")))

    # Database
    raw_db_url = os.getenv("DATABASE_URL", "")
    if not raw_db_url or (raw_db_url.startswith("sqlite:///") and not raw_db_url.startswith("sqlite:////") and ":memory:" not in raw_db_url):
        db_file = (BASE_DIR / "data" / "lyricsync.db").resolve()
        db_file.parent.mkdir(parents=True, exist_ok=True)
        # SQLite URL with 3 slashes followed by drive letter on Windows: sqlite:///C:/...
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_file.as_posix()}"
    else:
        SQLALCHEMY_DATABASE_URI = raw_db_url

    DATABASE_URL = SQLALCHEMY_DATABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis & Celery
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_TRANSCRIPTION_MODEL = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "whisper-1")

    # Upload and media constraints
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 600 * 1024 * 1024))  # 600MB
    UPLOAD_MAX_AUDIO_MB = int(os.getenv("UPLOAD_MAX_AUDIO_MB", 100))
    UPLOAD_MAX_VIDEO_MB = int(os.getenv("UPLOAD_MAX_VIDEO_MB", 500))
    MAX_PROJECT_DURATION_SECONDS = int(os.getenv("MAX_PROJECT_DURATION_SECONDS", 3600))  # 1 hour
    ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "ogg", "flac", "aac", "wma"}
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "webm", "mkv", "avi"}

    # FFmpeg executable override (can be auto-detected or explicit)
    FFMPEG_BINARY = os.getenv("FFMPEG_BINARY", "")
    FFPROBE_BINARY = os.getenv("FFPROBE_BINARY", "")

    @classmethod
    def ensure_directories(cls):
        for path in [cls.DATA_ROOT, cls.MEDIA_ROOT, cls.OUTPUT_ROOT, cls.TEMP_ROOT]:
            path.mkdir(parents=True, exist_ok=True)
