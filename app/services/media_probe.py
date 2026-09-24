import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from config import Config

def get_ffmpeg_binary() -> str:
    if Config.FFMPEG_BINARY and Path(Config.FFMPEG_BINARY).exists():
        return Config.FFMPEG_BINARY
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    return "ffmpeg"

def get_ffprobe_binary() -> Optional[str]:
    if Config.FFPROBE_BINARY and Path(Config.FFPROBE_BINARY).exists():
        return Config.FFPROBE_BINARY
    found = shutil.which("ffprobe")
    if found:
        return found
    return None

class MediaProbe:
    @staticmethod
    def probe(file_path: Path) -> Dict[str, Any]:
        """
        Probe media metadata (duration, width, height, fps, audio/video presence)
        using ffprobe if available, or ffmpeg fallback.
        """
        ffprobe = get_ffprobe_binary()
        if ffprobe:
            try:
                cmd = [
                    ffprobe,
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    str(file_path)
                ]
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=True
                )
                data = json.loads(proc.stdout)
                return MediaProbe._parse_ffprobe_json(data)
            except Exception:
                pass

        # Fallback to ffmpeg -i
        return MediaProbe._probe_with_ffmpeg(file_path)

    @staticmethod
    def _parse_ffprobe_json(data: Dict[str, Any]) -> Dict[str, Any]:
        streams = data.get("streams", [])
        fmt = data.get("format", {})
        
        has_video = False
        has_audio = False
        width = 1920
        height = 1080
        fps = 30.0
        duration = float(fmt.get("duration", 0.0))

        for s in streams:
            codec_type = s.get("codec_type")
            if codec_type == "video" and not has_video:
                has_video = True
                width = int(s.get("width", 1920))
                height = int(s.get("height", 1080))
                # Parse r_frame_rate e.g. "30/1" or "29.97"
                r_fps = s.get("r_frame_rate", "30/1")
                if "/" in r_fps:
                    num, den = r_fps.split("/")
                    fps = round(float(num) / float(den), 2) if float(den) > 0 else 30.0
                else:
                    fps = round(float(r_fps), 2)
                if duration == 0.0 and "duration" in s:
                    duration = float(s["duration"])
            elif codec_type == "audio":
                has_audio = True
                if duration == 0.0 and "duration" in s:
                    duration = float(s["duration"])

        return {
            "has_video": has_video,
            "has_audio": has_audio,
            "duration": round(duration, 3),
            "width": width,
            "height": height,
            "fps": fps,
        }

    @staticmethod
    def _probe_with_ffmpeg(file_path: Path) -> Dict[str, Any]:
        ffmpeg = get_ffmpeg_binary()
        cmd = [ffmpeg, "-i", str(file_path)]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        text = proc.stderr

        duration = 0.0
        dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", text)
        if dur_match:
            h, m, s = dur_match.groups()
            duration = int(h) * 3600 + int(m) * 60 + float(s)

        has_video = "Video:" in text
        has_audio = "Audio:" in text
        width = 1920
        height = 1080
        fps = 30.0

        if has_video:
            res_match = re.search(r"(\d{3,4})x(\d{3,4})", text)
            if res_match:
                width = int(res_match.group(1))
                height = int(res_match.group(2))
            fps_match = re.search(r"(\d+(?:\.\d+)?)\s*fps", text)
            if fps_match:
                fps = float(fps_match.group(1))

        return {
            "has_video": has_video,
            "has_audio": has_audio,
            "duration": round(duration, 3),
            "width": width,
            "height": height,
            "fps": fps,
        }
