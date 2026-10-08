"""Persistent per-user media library (survives new projects / project deletes)."""
from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Optional

from flask import url_for
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import MediaAsset, Project
from app.models.user_media import UserMediaAsset
from app.utils.files import calculate_checksum, detect_mime_type
from config import Config


AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}
IMAGE_EXTS = {".webp", ".png", ".jpg", ".jpeg", ".gif"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".avi"}


def get_user_library_dir(user_id: str) -> Path:
    safe = secure_filename(str(user_id)) or "user"
    path = Config.MEDIA_ROOT / "library" / safe
    path.mkdir(parents=True, exist_ok=True)
    return path


def normalize_library_kind(kind: str, path: Path | None = None) -> str:
    kind = (kind or "").lower().strip()
    if kind in ("audio", "image", "video"):
        return kind
    if kind == "library_video":
        return "video"
    if path:
        suffix = path.suffix.lower()
        if suffix in AUDIO_EXTS:
            return "audio"
        if suffix in IMAGE_EXTS:
            return "image"
        if suffix in VIDEO_EXTS:
            return "video"
    return "image"


def register_user_media(
    user_id: str | None,
    src_path: Path | str,
    kind: str,
    display_name: str | None = None,
    source_project_id: str | None = None,
    duration: float | None = None,
    *,
    commit: bool = False,
) -> Optional[UserMediaAsset]:
    """Copy a file into the user's library (deduped by checksum)."""
    if not user_id:
        return None
    src = Path(src_path)
    if not src.exists() or not src.is_file():
        return None

    try:
        checksum = calculate_checksum(src)
    except Exception:
        checksum = None

    if checksum:
        existing = (
            db.session.query(UserMediaAsset)
            .filter_by(user_id=user_id, checksum=checksum)
            .first()
        )
        if existing and Path(existing.file_path).exists():
            if display_name and existing.display_name in ("upload", "master_audio", existing.storage_key):
                existing.display_name = display_name
            if duration is not None and existing.duration is None:
                existing.duration = duration
            if commit:
                db.session.commit()
            return existing

    lib_kind = normalize_library_kind(kind, src)
    lib_dir = get_user_library_dir(user_id)
    safe_name = secure_filename(display_name or src.name) or f"{lib_kind}{src.suffix.lower()}"
    archive_name = f"{lib_kind}_{int(time.time() * 1000)}_{safe_name}"
    if not Path(archive_name).suffix and src.suffix:
        archive_name = f"{archive_name}{src.suffix.lower()}"
    dest = lib_dir / archive_name
    shutil.copy2(src, dest)

    asset = UserMediaAsset(
        user_id=user_id,
        kind=lib_kind,
        storage_key=archive_name,
        file_path=str(dest.resolve()),
        mime_type=detect_mime_type(dest),
        size_bytes=dest.stat().st_size,
        duration=duration,
        checksum=checksum,
        display_name=(display_name or src.name or archive_name)[:255],
        source_project_id=source_project_id,
    )
    db.session.add(asset)
    if commit:
        db.session.commit()
    return asset


def _is_catalog_theme_file(path: Path, kind: str) -> bool:
    """True for generated studio theme beds (not user uploads / AI / custom)."""
    name = path.name.lower()
    if name.startswith("files/") or "/files/" in str(path).replace("\\", "/").lower():
        return False
    if any(tok in name for tok in ("ai_lyric_scene", "background_custom", "background_library", "background_video", "upload_")):
        return False
    if kind == "audio" or name.startswith("master_audio"):
        return False
    if name.startswith("background_") and path.suffix.lower() in IMAGE_EXTS | {".mp4", ".webm", ".mov"}:
        return True
    return False


def backfill_user_library(user_id: str) -> int:
    """Index existing project media into the user library (copies onto library disk)."""
    if not user_id:
        return 0
    projects = db.session.query(Project).filter_by(user_id=user_id).all()
    added = 0
    for project in projects:
        assets = (
            db.session.query(MediaAsset)
            .filter(
                MediaAsset.project_id == project.id,
                MediaAsset.kind.in_(("audio", "image", "library_video", "video")),
            )
            .all()
        )
        for asset in assets:
            path = Path(asset.file_path) if asset.file_path else None
            if not path or not path.exists():
                continue
            kind = normalize_library_kind(asset.kind, path)
            if _is_catalog_theme_file(path, kind):
                continue
            before_ids = {
                row.id
                for row in db.session.query(UserMediaAsset.id).filter_by(user_id=user_id).all()
            }
            registered = register_user_media(
                user_id,
                path,
                kind,
                display_name=(asset.storage_key.split("/")[-1] if asset.storage_key else path.name),
                source_project_id=project.id,
                duration=asset.duration,
            )
            if registered and registered.id not in before_ids:
                added += 1
    db.session.commit()
    return added


def library_entry_dict(asset: UserMediaAsset) -> dict:
    path = Path(asset.file_path) if asset.file_path else None
    exists = bool(path and path.exists())
    size = int(asset.size_bytes or 0)
    if exists and not size:
        try:
            size = path.stat().st_size
        except Exception:
            size = 0
    kind = normalize_library_kind(asset.kind, path)
    section = "audio" if kind == "audio" else ("images" if kind == "image" else "videos")
    label = asset.display_name or asset.storage_key or asset.id
    if label.startswith("files/"):
        label = label.split("/", 1)[-1]
    return {
        "id": asset.id,
        "kind": "video" if section == "videos" else kind,
        "section": section,
        "name": label,
        "mime_type": asset.mime_type or (detect_mime_type(path) if path else "application/octet-stream"),
        "size_bytes": size,
        "duration": asset.duration,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "url": url_for(
            "media.stream_library_file",
            asset_id=asset.id,
            t=int(time.time() * 1000),
        ),
        "source": "library",
        "scope": "library",
        "exists": exists,
    }


def list_user_library(user_id: str, *, backfill: bool = True) -> dict:
    if not user_id:
        return {"audio": [], "images": [], "videos": []}
    if backfill:
        try:
            backfill_user_library(user_id)
        except Exception:
            db.session.rollback()
    assets = (
        db.session.query(UserMediaAsset)
        .filter_by(user_id=user_id)
        .order_by(UserMediaAsset.created_at.desc())
        .all()
    )
    entries = []
    seen = set()
    for asset in assets:
        path = Path(asset.file_path) if asset.file_path else None
        if not path or not path.exists():
            continue
        key = asset.checksum or str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        entries.append(library_entry_dict(asset))
    return {
        "audio": [e for e in entries if e["section"] == "audio"],
        "images": [e for e in entries if e["section"] == "images"],
        "videos": [e for e in entries if e["section"] == "videos"],
    }


def resolve_library_asset(user_id: str, asset_id: str) -> Optional[UserMediaAsset]:
    if not user_id or not asset_id:
        return None
    asset = db.session.get(UserMediaAsset, asset_id)
    if not asset or asset.user_id != user_id:
        return None
    path = Path(asset.file_path) if asset.file_path else None
    if not path or not path.exists():
        return None
    return asset


def copy_library_into_project(project: Project, library_asset: UserMediaAsset) -> MediaAsset:
    """Copy a library file into the project's files/ archive and register MediaAsset."""
    from app.utils.files import get_project_dir

    src = Path(library_asset.file_path)
    proj_dir = get_project_dir(project.id)
    files_dir = proj_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    kind = normalize_library_kind(library_asset.kind, src)
    suffix = src.suffix.lower() or ".bin"
    archive_name = f"library_{int(time.time() * 1000)}{suffix}"
    dest = files_dir / archive_name
    shutil.copy2(src, dest)

    media_kind = "audio" if kind == "audio" else ("image" if kind == "image" else "library_video")
    asset = MediaAsset(
        project_id=project.id,
        kind=media_kind,
        storage_key=f"files/{archive_name}",
        file_path=str(dest.resolve()),
        mime_type=detect_mime_type(dest),
        size_bytes=dest.stat().st_size,
        duration=library_asset.duration,
        checksum=library_asset.checksum,
    )
    db.session.add(asset)
    db.session.commit()
    return asset
