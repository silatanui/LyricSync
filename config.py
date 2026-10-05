import os
from pathlib import Path
from dotenv import load_dotenv

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("LC_ALL", "C.UTF-8")

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-lyricsync-2026")
    ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")

    # Data and media storage roots (always absolute to prevent cwd issues on shared hosting)
    _data_root = os.getenv("DATA_ROOT", "data")
    DATA_ROOT = Path(_data_root) if Path(_data_root).is_absolute() else (BASE_DIR / _data_root).resolve()

    _media_root = os.getenv("MEDIA_ROOT", "data/media")
    MEDIA_ROOT = Path(_media_root) if Path(_media_root).is_absolute() else (BASE_DIR / _media_root).resolve()

    _output_root = os.getenv("OUTPUT_ROOT", "data/outputs")
    OUTPUT_ROOT = Path(_output_root) if Path(_output_root).is_absolute() else (BASE_DIR / _output_root).resolve()

    _temp_root = os.getenv("TEMP_ROOT", "data/temp")
    TEMP_ROOT = Path(_temp_root) if Path(_temp_root).is_absolute() else (BASE_DIR / _temp_root).resolve()

    _fonts_root = os.getenv("FONTS_ROOT", "data/fonts")
    FONTS_ROOT = Path(_fonts_root) if Path(_fonts_root).is_absolute() else (BASE_DIR / _fonts_root).resolve()

    # Database
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "lyricsync_studio")

    raw_db_url = os.getenv("DATABASE_URL", "")
    if raw_db_url:
        SQLALCHEMY_DATABASE_URI = raw_db_url
    else:
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
            "?charset=utf8mb4"
        )

    DATABASE_URL = SQLALCHEMY_DATABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    # Redis & Celery
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_TRANSCRIPTION_MODEL = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "whisper-1")
    OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
    OPENAI_IMAGE_QUALITY = os.getenv("OPENAI_IMAGE_QUALITY", "medium")
    OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "360"))
    OPENAI_TRANSCRIPTION_RETRIES = int(os.getenv("OPENAI_TRANSCRIPTION_RETRIES", "1"))

    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

    # Freemium AI image credits (OpenAI image cost control)
    # New signed-in users get IMAGE_FREE_CREDITS; admin is unlimited.
    IMAGE_FREE_CREDITS = int(os.getenv("IMAGE_FREE_CREDITS", "2"))
    IMAGE_PREMIUM_CREDITS = int(os.getenv("IMAGE_PREMIUM_CREDITS", "100"))
    IMAGE_PREMIUM_PRICE_CENTS = int(os.getenv("IMAGE_PREMIUM_PRICE_CENTS", "500"))  # $5.00
    IMAGE_PREMIUM_PRICE_LABEL = os.getenv("IMAGE_PREMIUM_PRICE_LABEL", "$5/month")
    IMAGE_PREMIUM_PRODUCT_NAME = os.getenv(
        "IMAGE_PREMIUM_PRODUCT_NAME",
        "LyricSync Premium — 100 AI images / month",
    )

    # Stripe (optional — leave blank until you enable card payments)
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")  # optional recurring Price id

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
