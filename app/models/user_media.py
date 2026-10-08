from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db
from app.utils.ids import generate_id


def generate_library_asset_id() -> str:
    return generate_id("ulib")


class UserMediaAsset(db.Model):
    """User-scoped media that persists across projects."""

    __tablename__ = "user_media_assets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_library_asset_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # audio, image, video
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False, default="upload")
    source_project_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="media_library")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "kind": self.kind,
            "storage_key": self.storage_key,
            "file_path": self.file_path,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "duration": self.duration,
            "checksum": self.checksum,
            "display_name": self.display_name,
            "source_project_id": self.source_project_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
