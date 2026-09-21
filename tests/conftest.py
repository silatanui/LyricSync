import os
import tempfile
import subprocess
from pathlib import Path
import pytest
from app import create_app
from app.extensions import db
from app.services.media_probe import get_ffmpeg_binary
from config import Config

class TestConfig(Config):
    TESTING = True
    DATABASE_URL = "sqlite:///:memory:"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    OPENAI_API_KEY = "mock"  # Forces deterministic mock transcription

@pytest.fixture(scope="session")
def test_media_dir(tmp_path_factory):
    """Generates synthetic test audio and video using FFmpeg for self-contained testing."""
    media_dir = tmp_path_factory.mktemp("test_media")
    ffmpeg = get_ffmpeg_binary()

    audio_path = media_dir / "test_audio.wav"
    video_path = media_dir / "test_video.mp4"

    # Generate 3-second test sine tone audio (WAV)
    cmd_audio = [
        ffmpeg, "-y",
        "-f", "lavfi",
        "-i", "sine=frequency=440:duration=3",
        "-c:a", "pcm_s16le",
        str(audio_path)
    ]
    subprocess.run(cmd_audio, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # Generate 2-second test color video (MP4)
    cmd_video = [
        ffmpeg, "-y",
        "-f", "lavfi",
        "-i", "color=c=blue:s=640x360:d=2:r=25",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(video_path)
    ]
    subprocess.run(cmd_video, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    return {
        "audio": audio_path,
        "video": video_path,
        "dir": media_dir,
    }

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()
