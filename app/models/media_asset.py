from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db
from app.utils.ids import generate_asset_id

class MediaAsset(db.Model):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_asset_id)
    project_id: Mapped[str] = mapped_column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # audio, video, output, subtitle
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="media_assets")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "kind": self.kind,
            "storage_key": self.storage_key,
            "file_path": self.file_path,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "duration": self.duration,
            "checksum": self.checksum,
            "created_at": self.created_at.isoformat(),
        }
