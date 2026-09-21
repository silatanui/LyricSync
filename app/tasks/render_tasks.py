import logging
from pathlib import Path
from app.extensions import db
from app.models import Project, RenderJob, MediaAsset
from app.services.subtitles import SubtitleGenerator
from app.services.ffmpeg import FFmpegRenderer
from app.utils.files import get_project_output_dir, calculate_checksum
from app.utils.ids import generate_asset_id

logger = logging.getLogger(__name__)

def run_render_pipeline(app, project_id: str, job_id: str):
    """
    Asynchronously builds subtitles, runs FFmpeg with libass, and generates the final MP4 video.
    """
    with app.app_context():
        project = db.session.get(Project, project_id)
        job = db.session.get(RenderJob, job_id)

        if not project or not job:
            logger.error(f"Render pipeline failed: Project {project_id} or Job {job_id} not found")
            return

        try:
            job.status = "rendering"
            job.progress = 55
            job.stage = "Generating stylized ASS subtitles"
            db.session.commit()

            canonical = project.get_canonical_json()
            out_dir = get_project_output_dir(project.id)

            # Generate ASS file
            ass_path = out_dir / f"lyrics_rev_{project.current_revision}.ass"
            SubtitleGenerator.generate_ass(canonical, ass_path)

            video_path = Path(project.video_path)
            if not video_path.is_absolute():
                video_path = (Path(app.root_path).parent / video_path).resolve()

            audio_path = Path(project.audio_path)
            if not audio_path.is_absolute():
                audio_path = (Path(app.root_path).parent / audio_path).resolve()

            output_mp4 = out_dir / f"lyricsync_{project.id}_rev{project.current_revision}.mp4"

            render_cfg = canonical.get("render", {})
            aspect_ratio = render_cfg.get("aspect_ratio", "16:9")
            audio_policy = render_cfg.get("audio_policy", "replace")
            video_policy = render_cfg.get("video_policy", "loop")
            resolution = render_cfg.get("resolution", "1080")

            def progress_cb(pct: int, msg: str):
                try:
                    job.progress = pct
                    job.stage = msg
                    db.session.commit()
                except Exception:
                    pass

            renderer = FFmpegRenderer()
            final_path = renderer.render(
                video_path=video_path,
                audio_path=audio_path,
                ass_path=ass_path,
                output_path=output_mp4,
                aspect_ratio=aspect_ratio,
                audio_policy=audio_policy,
                video_policy=video_policy,
                resolution=resolution,
                progress_callback=progress_cb
            )

            # Register output media asset
            checksum = calculate_checksum(final_path)
            size_bytes = final_path.stat().st_size
            asset = MediaAsset(
                id=generate_asset_id(),
                project_id=project.id,
                kind="output",
                storage_key=final_path.name,
                file_path=str(final_path),
                mime_type="video/mp4",
                size_bytes=size_bytes,
                duration=project.audio_duration,
                checksum=checksum,
            )
            db.session.add(asset)

            job.status = "completed"
            job.progress = 100
            job.stage = "Video ready for download"
            job.output_asset_id = asset.id
            job.output_file_path = str(final_path)
            db.session.commit()

            logger.info(f"Render job {job_id} completed successfully for project {project_id}")

        except Exception as e:
            logger.exception(f"Render job {job_id} failed: {e}")
            db.session.rollback()
            job.status = "failed"
            job.error_code = "RENDER_ERROR"
            job.error_message = str(e)
            job.stage = "Render failed"
            db.session.commit()
