from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db
from app.utils.ids import generate_user_id

ADMIN_EMAIL = "silatanuikipngetich@gmail.com"

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_user_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    google_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=True, index=True)
    avatar_url: Mapped[str] = mapped_column(String(1024), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return bool(self.password_hash and check_password_hash(self.password_hash, raw_password))

    @property
    def is_admin(self) -> bool:
        """Only silatanuikipngetich@gmail.com has system administrator privileges."""
        return bool(self.email and self.email.strip().lower() == ADMIN_EMAIL)

    @property
    def initials(self) -> str:
        """Derive 1 or 2 uppercase letters (e.g. 'SK') for avatar monograms."""
        name = (self.display_name or "").strip()
        if name:
            parts = [p for p in name.split() if p]
            if len(parts) >= 2:
                return f"{parts[0][0]}{parts[1][0]}".upper()
            elif parts:
                return parts[0][:2].upper()
        email_prefix = self.email.split("@")[0].strip() if self.email else "U"
        parts = [p for p in email_prefix.replace(".", " ").replace("_", " ").replace("-", " ").split() if p]
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[1][0]}".upper()
        return email_prefix[:2].upper()

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name or (self.email.split("@")[0] if self.email else ""),
            "initials": self.initials,
            "avatar_url": self.avatar_url,
            "is_admin": self.is_admin,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

