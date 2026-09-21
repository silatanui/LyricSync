from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db
from app.utils.ids import generate_job_id

class RenderJob(db.Model):
    __tablename__ = "render_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_job_id)
    project_id: Mapped[str] = mapped_column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # States: queued, running, transcribing, aligning, rendering, validating, completed, failed, cancelled
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    stage: Mapped[str] = mapped_column(String(64), default="Initialized")
    
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    output_asset_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    output_file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="render_jobs")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "status": self.status,
            "progress": self.progress,
            "stage": self.stage,
            "output_asset_id": self.output_asset_id,
            "output_file_path": self.output_file_path,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
