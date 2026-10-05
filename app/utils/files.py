import hashlib
import mimetypes
from pathlib import Path
from werkzeug.utils import secure_filename
from config import Config

def get_project_dir(project_id: str) -> Path:
    p = Config.MEDIA_ROOT / project_id
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_project_output_dir(project_id: str) -> Path:
    p = Config.OUTPUT_ROOT / project_id
    p.mkdir(parents=True, exist_ok=True)
    return p

def calculate_checksum(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def detect_mime_type(file_path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(file_path))
    if mime:
        return mime
    suffix = file_path.suffix.lower()
    if suffix in (".mp3",):
        return "audio/mpeg"
    elif suffix in (".wav",):
        return "audio/wav"
    elif suffix in (".m4a",):
        return "audio/mp4"
    elif suffix in (".mp4",):
        return "video/mp4"
    elif suffix in (".webm",):
        return "video/webm"
    elif suffix in (".webp",):
        return "image/webp"
    elif suffix in (".png",):
        return "image/png"
    elif suffix in (".jpg", ".jpeg"):
        return "image/jpeg"
    return "application/octet-stream"

def resolve_project_media(project, kind: str) -> Path | None:
    """
    Robustly resolves a project's audio or video media path across Windows, Linux, and moved directories.
    Handles legacy Windows paths on Linux, checks project media directory, MediaAsset records,
    auto-generates missing background templates, and auto-heals database paths.
    """
    if not project:
        return None

    raw_path_str = project.audio_path if kind == "audio" else project.video_path
    project_id = str(project.id)
    proj_dir = get_project_dir(project_id)

    # 1. Direct path check if path exists and is non-empty
    if raw_path_str:
        p = Path(raw_path_str)
        try:
            if p.exists() and p.is_file() and p.stat().st_size > 0:
                return p
        except Exception:
            pass

        # Check relative to base directory
        normalized = raw_path_str.replace("\\", "/")
        try:
            from config import BASE_DIR
            base_p = (BASE_DIR / normalized).resolve()
            if base_p.exists() and base_p.is_file() and base_p.stat().st_size > 0:
                return base_p
        except Exception:
            pass

        # Check filename within project media directory
        fname = Path(normalized).name
        if fname:
            cand = proj_dir / fname
            if cand.exists() and cand.is_file() and cand.stat().st_size > 0:
                _heal_project_media_path(project, kind, cand)
                return cand

        # If path contains project_id, extract relative subpath
        if project_id in normalized:
            sub = normalized.split(project_id, 1)[-1].lstrip("/")
            cand = proj_dir / sub
            if cand.exists() and cand.is_file() and cand.stat().st_size > 0:
                _heal_project_media_path(project, kind, cand)
                return cand

    # 2. Check MediaAsset record in database
    try:
        from app.models import MediaAsset
        from app.extensions import db
        asset = db.session.query(MediaAsset).filter_by(project_id=project_id, kind=kind).order_by(MediaAsset.created_at.desc()).first()
        if asset:
            if asset.file_path:
                ap = Path(asset.file_path)
                if ap.exists() and ap.is_file() and ap.stat().st_size > 0:
                    _heal_project_media_path(project, kind, ap)
                    return ap
            if asset.storage_key:
                sk_cand = proj_dir / asset.storage_key
                if sk_cand.exists() and sk_cand.is_file() and sk_cand.stat().st_size > 0:
                    _heal_project_media_path(project, kind, sk_cand)
                    return sk_cand
    except Exception:
        pass

    # 3. Fallback scan in project media directory
    if proj_dir.exists():
        if kind == "audio":
            for prefix in ("master_audio.", "audio.", "track.", "sound."):
                for match in proj_dir.glob(f"{prefix}*"):
                    if match.is_file() and match.stat().st_size > 0:
                        _heal_project_media_path(project, kind, match)
                        return match
            for match in proj_dir.iterdir():
                if match.is_file() and match.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"):
                    if match.stat().st_size > 0:
                        _heal_project_media_path(project, kind, match)
                        return match
        elif kind == "video":
            # Prefer the template currently selected on the project.
            try:
                canonical = project.get_canonical_json()
                template_id = (canonical.get("meta", {}) or {}).get("background_template") or ""
                media_type = (canonical.get("meta", {}) or {}).get("background_media_type") or ""
            except Exception:
                canonical = {}
                template_id, media_type = "", ""
            if template_id and template_id != "custom_video":
                preferred_exts = (
                    (".mp4", ".webm", ".mov", ".mkv", ".webp", ".png")
                    if media_type == "video"
                    else (".webp", ".png", ".jpg", ".jpeg", ".mp4", ".webm", ".mov", ".mkv")
                )
                for ext in preferred_exts:
                    cand = proj_dir / f"background_{template_id}{ext}"
                    if cand.is_file() and cand.stat().st_size > 0:
                        _heal_project_media_path(project, kind, cand)
                        return cand
            for prefix in ("background_video.", "video.", "master_video."):
                for match in proj_dir.glob(f"{prefix}*"):
                    if match.is_file() and match.stat().st_size > 0:
                        _heal_project_media_path(project, kind, match)
                        return match
            # Prefer archived AI generations over any leftover catalog still.
            if template_id == "ai_lyric_scene" or bool((canonical.get("meta") or {}).get("ai_background")):
                try:
                    files_dir = proj_dir / "files"
                    if files_dir.is_dir():
                        archives = sorted(
                            (
                                p for p in files_dir.glob("ai_lyric_scene_*.webp")
                                if p.is_file() and p.stat().st_size > 0
                            ),
                            key=lambda p: p.stat().st_mtime,
                            reverse=True,
                        )
                        if archives:
                            active = proj_dir / "background_ai_lyric_scene.webp"
                            try:
                                if not active.exists() or active.stat().st_size <= 0:
                                    import shutil
                                    shutil.copy2(archives[0], active)
                            except Exception:
                                active = archives[0]
                            if active.exists() and active.stat().st_size > 0:
                                _heal_project_media_path(project, kind, active)
                                return active
                except Exception:
                    pass
            if template_id != "ai_lyric_scene":
                for match in proj_dir.iterdir():
                    if match.is_file() and match.suffix.lower() in (".mp4", ".mov", ".webm", ".mkv"):
                        if match.stat().st_size > 0:
                            _heal_project_media_path(project, kind, match)
                            return match
                for match in proj_dir.glob("background_*.webp"):
                    if match.is_file() and match.stat().st_size > 0:
                        _heal_project_media_path(project, kind, match)
                        return match
                for match in proj_dir.glob("background_*.png"):
                    if match.is_file() and match.stat().st_size > 0:
                        _heal_project_media_path(project, kind, match)
                        return match

    # 4. If kind == 'video' and missing on disk, regenerate from the chosen theme.
    # Never synthesize placeholders for AI / custom / library backgrounds — that
    # would overwrite the user's painted or uploaded scene on reload.
    if kind == "video":
        canonical = project.get_canonical_json()
        template_id = (canonical.get("meta", {}) or {}).get("background_template", "burgundy_studio") or "burgundy_studio"
        media_type = (canonical.get("meta", {}) or {}).get("background_media_type") or ""
        skip_regen = template_id in {
            "ai_lyric_scene",
            "custom_video",
            "library_image",
            "library_video",
        } or bool((canonical.get("meta") or {}).get("ai_background"))
        if skip_regen:
            return None
        aspect_ratio = canonical.get("render", {}).get("aspect_ratio", "16:9")
        try:
            from app.services.background_generator import BackgroundGenerator
            from app.services.theme_catalog import get_theme
            w, h = BackgroundGenerator.get_dimensions(aspect_ratio)
            theme = get_theme(template_id) or {}
            is_video_theme = (theme.get("media_type") == "video") or (media_type == "video")
            if is_video_theme:
                bg_file = proj_dir / f"background_{template_id}.mp4"
                if not bg_file.exists() or bg_file.stat().st_size < 2000:
                    motion = (theme.get("motion") or "visualizer").lower()
                    BackgroundGenerator.generate_theme_video_loop(
                        pattern_type=template_id,
                        output_path=bg_file,
                        width=w,
                        height=h,
                        seconds=5.0 if motion == "visualizer" else 6.0,
                    )
            else:
                bg_file = proj_dir / f"background_{template_id}.webp"
                try:
                    BackgroundGenerator.generate_template_asset(
                        pattern_type=template_id,
                        output_path=bg_file,
                        width=w,
                        height=h,
                        fmt="WEBP"
                    )
                except Exception:
                    bg_file = proj_dir / f"background_{template_id}.png"
                    BackgroundGenerator.generate_template_asset(
                        pattern_type=template_id,
                        output_path=bg_file,
                        width=w,
                        height=h,
                        fmt="PNG"
                    )
            if bg_file.exists() and bg_file.stat().st_size > 0:
                _heal_project_media_path(project, kind, bg_file)
                return bg_file
        except Exception:
            pass

    return None

def _heal_project_media_path(project, kind: str, resolved_path: Path):
    """Auto-updates project media path in database if it differed."""
    try:
        from app.extensions import db
        resolved_str = str(resolved_path.resolve())
        changed = False
        if kind == "audio" and project.audio_path != resolved_str:
            project.audio_path = resolved_str
            changed = True
        elif kind == "video" and project.video_path != resolved_str:
            project.video_path = resolved_str
            changed = True
        if changed:
            canonical = project.get_canonical_json()
            if kind == "audio":
                canonical.setdefault("media", {})["audio_path"] = resolved_str
            else:
                canonical.setdefault("media", {})["video_path"] = resolved_str
            project.set_canonical_json(canonical)
            db.session.commit()
    except Exception:
        pass

def resolve_rendered_video(project) -> Path | None:
    """
    Robustly locates the latest rendered MP4 video file for a project.
    Checks completed RenderJobs, MediaAsset output records, expected revision output,
    and scans output folder.
    """
    if not project:
        return None

    project_id = str(project.id)
    out_dir = get_project_output_dir(project_id)

    # 1. Query RenderJob with completed status and output_file_path
    try:
        from app.models import RenderJob
        from app.extensions import db
        job = (
            db.session.query(RenderJob)
            .filter(
                RenderJob.project_id == project_id,
                RenderJob.status == "completed",
                RenderJob.output_file_path.isnot(None),
                RenderJob.output_file_path != ""
            )
            .order_by(RenderJob.created_at.desc())
            .first()
        )
        if job and job.output_file_path:
            p = Path(job.output_file_path)
            if p.exists() and p.is_file() and p.stat().st_size > 0:
                return p
            cand = out_dir / p.name
            if cand.exists() and cand.is_file() and cand.stat().st_size > 0:
                job.output_file_path = str(cand.resolve())
                db.session.commit()
                return cand
    except Exception:
        pass

    # 2. Query MediaAsset of kind 'output'
    try:
        from app.models import MediaAsset
        from app.extensions import db
        asset = (
            db.session.query(MediaAsset)
            .filter_by(project_id=project_id, kind="output")
            .order_by(MediaAsset.created_at.desc())
            .first()
        )
        if asset:
            if asset.file_path:
                ap = Path(asset.file_path)
                if ap.exists() and ap.is_file() and ap.stat().st_size > 0:
                    return ap
            if asset.storage_key:
                cand = out_dir / asset.storage_key
                if cand.exists() and cand.is_file() and cand.stat().st_size > 0:
                    return cand
    except Exception:
        pass

    # 3. Check expected output filename for project revision
    expected = out_dir / f"lyricsync_{project.id}_rev{project.current_revision}.mp4"
    if expected.exists() and expected.is_file() and expected.stat().st_size > 0:
        return expected

    # 4. Scan out_dir for any valid MP4 video files, returning newest
    if out_dir.exists():
        mp4_files = [f for f in out_dir.glob("*.mp4") if f.is_file() and f.stat().st_size > 0]
        if mp4_files:
            mp4_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return mp4_files[0]

    return None

