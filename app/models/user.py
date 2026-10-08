import os
from datetime import date, datetime, timezone
from sqlalchemy import String, DateTime, Date, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db
from app.utils.ids import generate_user_id

# Prefer env so the admin identity is not the only source of truth in public docs.
ADMIN_EMAIL = (os.getenv("ADMIN_EMAIL") or "silatanuikipngetich@gmail.com").strip().lower()
DEFAULT_DAILY_IMAGE_CREDITS = 2


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_user_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    google_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=True, index=True)
    avatar_url: Mapped[str] = mapped_column(String(1024), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Remaining AI image generations for the current UTC day (refreshed daily).
    image_credits: Mapped[int] = mapped_column(Integer, default=DEFAULT_DAILY_IMAGE_CREDITS, nullable=False)
    image_credits_reset_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Purchased / premium pack credits that do not reset daily.
    bonus_image_credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    stripe_customer_id: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return bool(self.password_hash and check_password_hash(self.password_hash, raw_password))

    @property
    def is_admin(self) -> bool:
        """Admin only after the configured admin email is authenticated and verified."""
        if not self.email or self.email.strip().lower() != ADMIN_EMAIL:
            return False
        # Password accounts must verify inbox ownership; Google sign-in already proves it.
        return bool(self.email_verified or self.google_id)

    @property
    def has_image_credits(self) -> bool:
        """Admin is unlimited; others need daily or bonus credits."""
        if self.is_admin:
            return True
        return int(self.image_credits or 0) > 0 or int(self.bonus_image_credits or 0) > 0

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
        daily = int(self.image_credits or 0)
        bonus = int(self.bonus_image_credits or 0)
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name or (self.email.split("@")[0] if self.email else ""),
            "initials": self.initials,
            "avatar_url": self.avatar_url,
            "is_admin": self.is_admin,
            "is_premium": bool(self.is_premium),
            "image_credits": -1 if self.is_admin else (daily + bonus),
            "daily_image_credits": -1 if self.is_admin else daily,
            "bonus_image_credits": 0 if self.is_admin else bonus,
            "has_image_credits": self.has_image_credits,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
