import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from app.services.media_probe import get_ffmpeg_binary, MediaProbe

logger = logging.getLogger(__name__)

def escape_ass_path(path: Path) -> str:
    """
    Escapes a file path for use in the FFmpeg libass filter syntax on both Windows and POSIX.
    In FFmpeg filtergraph:
    - Backslashes must become forward slashes or be escaped
    - Colons (such as C:) must be escaped with a backslash: 'C\\:/...'
    - Single quotes must be escaped
    """
    s = str(path.resolve()).replace("\\", "/")
    # Escape colon for drive letter
    s = s.replace(":", "\\:")
    # Escape single quote
    s = s.replace("'", "\\'")
    return s

class FFmpegRenderer:
    def __init__(self, ffmpeg_bin: Optional[str] = None):
        self.ffmpeg_bin = ffmpeg_bin or get_ffmpeg_binary()

    def build_scale_crop_filter(self, aspect_ratio: str, target_width: int, target_height: int) -> str:
        """
        Build an FFmpeg scale and crop filter string to fit video into target dimensions without distortion.
        """
        return f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,crop={target_width}:{target_height}"

    def render(
        self,
        video_path: Path,
        audio_path: Path,
        ass_path: Path,
        output_path: Path,
        aspect_ratio: str = "16:9",
        audio_policy: str = "replace",
        video_policy: str = "loop",
        resolution: str = "1080",
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Path:
        """
        Renders synchronized lyric video using direct FFmpeg execution.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback(55, "Probing source media streams")

        v_probe = MediaProbe.probe(video_path)
        a_probe = MediaProbe.probe(audio_path)

        audio_dur = a_probe.get("duration", 0.0)
        video_dur = v_probe.get("duration", 0.0)

        # Dimension mapping
        base = {"720": 720, "1080": 1080, "2160": 2160}.get(str(resolution), 1080)
        if aspect_ratio == "9:16":
            width, height = round(base * 9 / 16), base
        elif aspect_ratio == "1:1":
            width, height = base, base
        elif aspect_ratio == "4:5":
            width, height = round(base * 4 / 5), base
        else:
            width, height = round(base * 16 / 9), base

        # Build video filter chain: scale/crop -> constant 30fps -> ASS burn-in
        ass_escaped = escape_ass_path(ass_path)
        scale_crop = self.build_scale_crop_filter(aspect_ratio, width, height)
        vf_filter = f"{scale_crop},fps=30,ass='{ass_escaped}'"

        cmd = [self.ffmpeg_bin, "-y"]

        # Duration policy & Looping
        # If video is shorter than audio and video_policy is 'loop', loop the video
        is_looping = video_policy == "loop" and video_dur > 0 and audio_dur > video_dur
        if is_looping:
            cmd.extend(["-stream_loop", "-1"])

        cmd.extend(["-i", str(video_path)])
        cmd.extend(["-i", str(audio_path)])

        # Video filter
        cmd.extend(["-vf", vf_filter])

        # Audio stream mapping: map audio track 1 (uploaded audio)
        if audio_policy == "replace" or not v_probe.get("has_audio"):
            cmd.extend(["-map", "0:v:0", "-map", "1:a:0"])
        else:
            # default to audio track 1
            cmd.extend(["-map", "0:v:0", "-map", "1:a:0"])

        # Codecs & Encoding settings with lockstep sync
        cmd.extend([
            "-c:v", "mpeg4",
            "-r", "30",
            "-q:v", "4",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-af", "aresample=async=1000:min_hard_comp=0.100000:first_pts=0",
            "-avoid_negative_ts", "make_zero",
            "-shortest",
        ])

        # Enforce exact duration if audio duration is known
        if audio_dur > 0:
            cmd.extend(["-t", str(audio_dur)])

        # Faststart for web streaming
        cmd.extend([
            "-movflags", "+faststart",
            str(output_path)
        ])

        if progress_callback:
            progress_callback(65, "Encoding video with FFmpeg libass")

        logger.info(f"Running FFmpeg render: {' '.join(cmd)}")

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if proc.returncode != 0:
            logger.error(f"FFmpeg error: {proc.stderr}")
            raise RuntimeError(f"FFmpeg render failed (exit code {proc.returncode}): {proc.stderr[-1000:]}")

        if progress_callback:
            progress_callback(95, "Validating rendered output")

        self.validate_output(output_path, expected_duration=audio_dur)

        if progress_callback:
            progress_callback(100, "Render completed successfully")

        return output_path

    def validate_output(self, output_path: Path, expected_duration: float = 0.0):
        """Validates that the rendered file exists, is non-empty, and has valid media streams."""
        if not output_path.exists():
            raise RuntimeError(f"Render output file was not created: {output_path}")

        size = output_path.stat().st_size
        if size == 0:
            raise RuntimeError("Rendered output file is 0 bytes")

        probe_info = MediaProbe.probe(output_path)
        if not probe_info.get("has_video"):
            raise RuntimeError("Rendered output file contains no video stream")

        logger.info(f"Render validated successfully: {output_path} ({size} bytes, duration {probe_info.get('duration')}s)")
