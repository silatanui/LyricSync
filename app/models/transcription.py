from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db
from app.utils.ids import generate_id

class Transcription(db.Model):
    __tablename__ = "transcriptions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_id("tx"))
    project_id: Mapped[str] = mapped_column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(64), default="whisper-1")
    language: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    json_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="transcriptions")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "model": self.model,
            "language": self.language,
            "raw_text": self.raw_text,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
        }
