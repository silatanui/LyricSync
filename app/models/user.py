from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db
from app.utils.ids import generate_user_id

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_user_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    google_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=True, index=True)
    avatar_url: Mapped[str] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, raw_password)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name or self.email.split("@")[0],
            "avatar_url": self.avatar_url,
            "created_at": self.created_at.isoformat()
        }

