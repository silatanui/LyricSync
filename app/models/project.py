from datetime import datetime, timezone
import json
from typing import Optional, Dict, Any
from sqlalchemy import String, Float, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db
from app.utils.ids import generate_project_id

class Project(db.Model):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_project_id)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("users.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled Project")
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)  # draft, ready, processing, completed, error
    
    # Media paths & probed metadata
    audio_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    video_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    audio_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    video_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fps: Mapped[Optional[float]] = mapped_column(Float, default=30.0)
    width: Mapped[Optional[int]] = mapped_column(Integer, default=1920)
    height: Mapped[Optional[int]] = mapped_column(Integer, default=1080)
    
    # Canonical JSON (Section 5.1 of specification)
    canonical_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_revision: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="projects")
    media_assets = relationship("MediaAsset", back_populates="project", cascade="all, delete-orphan")
    transcriptions = relationship("Transcription", back_populates="project", cascade="all, delete-orphan")
    lyric_lines = relationship("LyricLine", back_populates="project", cascade="all, delete-orphan", order_by="LyricLine.line_index")
    render_jobs = relationship("RenderJob", back_populates="project", cascade="all, delete-orphan")

    def get_canonical_json(self) -> Dict[str, Any]:
        if self.canonical_data:
            try:
                return json.loads(self.canonical_data)
            except Exception:
                pass
        return self._default_canonical_json()

    def set_canonical_json(self, data: Dict[str, Any]):
        self.canonical_data = json.dumps(data, indent=2)

    def _default_canonical_json(self) -> Dict[str, Any]:
        return {
            "project_id": self.id,
            "media": {
                "audio_path": self.audio_path or "",
                "video_path": self.video_path or "",
                "audio_duration": self.audio_duration or 0.0,
                "video_duration": self.video_duration or 0.0,
                "fps": self.fps or 30.0,
                "width": self.width or 1920,
                "height": self.height or 1080,
            },
            "transcription": {
                "provider": "openai",
                "model": "whisper-1",
                "language": "en",
                "raw_text": "",
                "version": self.current_revision,
            },
            "lyrics": [],
            "meta": {
                "description": "",
                "background_template": "burgundy_studio",
                "is_public": False,
            },
            "style": {
                "mode": "karaoke",
                "format": "stanza",
                "font": "Caveat",
                "font_size": 34,
                "line_height": 1.0,
                "position": "center",
                "text_align": "center",
                "primary_color": "#FFFFFF",
                "highlight_color": "#10B981",
                "outline": 2,
                "shadow": 1,
            },
            "render": {
                "aspect_ratio": "16:9",
                "resolution": "1920x1080",
                "audio_policy": "replace",
                "video_policy": "loop",
            },
        }

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "audio": {
                "path": self.audio_path,
                "duration": self.audio_duration,
            },
            "video": {
                "path": self.video_path,
                "duration": self.video_duration,
                "width": self.width,
                "height": self.height,
                "fps": self.fps,
            },
            "lyrics_revision": self.current_revision,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @property
    def is_video_background(self) -> bool:
        if not self.video_path:
            return False
        ext = self.video_path.lower().rsplit(".", 1)[-1] if "." in self.video_path else ""
        return ext in ["mp4", "webm", "mov", "mkv", "avi"]
