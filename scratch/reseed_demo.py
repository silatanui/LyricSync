import sys
import os
import shutil
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(r"c:\Users\silat\Desktop\Projects\Lyric_studio")
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db
from app.models.project import Project
from app.models.lyric import LyricLine, LyricWord
from app.services.media_probe import MediaProbe, get_ffmpeg_binary
from app.services.background_generator import BackgroundGenerator
import subprocess

app = create_app()
with app.app_context():
    # 1. Ensure samples/vocal_song.mp3 exists
    vocal_mp3 = PROJECT_ROOT / "samples" / "vocal_song.mp3"
    if not vocal_mp3.exists():
        raise FileNotFoundError("vocal_song.mp3 not found in samples!")

    # 2. Also convert vocal_song.mp3 to sample_audio.wav to replace the sine beep in samples
    sample_wav = PROJECT_ROOT / "samples" / "sample_audio.wav"
    ffmpeg = get_ffmpeg_binary()
    subprocess.run([ffmpeg, "-y", "-i", str(vocal_mp3), "-c:a", "pcm_s16le", str(sample_wav)], check=True)
    print("Updated samples/sample_audio.wav with real vocal track.")

    # 3. Locate or create demo project
    demo_id = "proj_1a0bfea5480_56bc6c80"
    project = db.session.get(Project, demo_id)
    if not project:
        project = Project(id=demo_id, name="Midnight Stars - Studio Demo")
        db.session.add(project)

    project.name = "Midnight Stars - Vocal Demo"
    project.status = "ready"
    project.fps = 30.0
    project.width = 1920
    project.height = 1080
    project.audio_duration = 7.22
    project.video_duration = 7.22

    # Target folder
    proj_dir = PROJECT_ROOT / "data" / "media" / demo_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    master_audio_path = proj_dir / "master_audio.mp3"
    master_wav_path = proj_dir / "master_audio.wav"
    shutil.copyfile(vocal_mp3, master_audio_path)
    shutil.copyfile(sample_wav, master_wav_path)

    project.audio_path = str(master_audio_path.relative_to(PROJECT_ROOT) if master_audio_path.is_relative_to(PROJECT_ROOT) else master_audio_path)

    # 4. Generate 16:9 Burgundy Studio template video with vocal song muxed in
    bg_video_path = proj_dir / "background_video.mp4"
    BackgroundGenerator.generate_background_video(
        audio_path=master_audio_path,
        output_video_path=bg_video_path,
        duration=7.22,
        pattern_type="burgundy_studio"
    )
    project.video_path = str(bg_video_path.relative_to(PROJECT_ROOT) if bg_video_path.is_relative_to(PROJECT_ROOT) else bg_video_path)

    # 5. Build Canonical JSON with Whisper-transcribed lines & words
    canonical_lines = [
        {
            "id": f"{demo_id}_line_1",
            "line_index": 0,
            "text": "Welcome to LyricSync Studio",
            "start": 0.0,
            "end": 1.62,
            "words": [
                {"text": "Welcome", "start": 0.0, "end": 0.34},
                {"text": "to", "start": 0.34, "end": 0.58},
                {"text": "LyricSync", "start": 0.58, "end": 1.04},
                {"text": "Studio", "start": 1.04, "end": 1.62}
            ]
        },
        {
            "id": f"{demo_id}_line_2",
            "line_index": 1,
            "text": "Sing your heart out",
            "start": 2.18,
            "end": 2.94,
            "words": [
                {"text": "Sing", "start": 2.18, "end": 2.18},
                {"text": "your", "start": 2.18, "end": 2.38},
                {"text": "heart", "start": 2.38, "end": 2.60},
                {"text": "out", "start": 2.60, "end": 2.94}
            ]
        },
        {
            "id": f"{demo_id}_line_3",
            "line_index": 2,
            "text": "underneath the midnight stars",
            "start": 2.94,
            "end": 4.30,
            "words": [
                {"text": "underneath", "start": 2.94, "end": 3.22},
                {"text": "the", "start": 3.22, "end": 3.48},
                {"text": "midnight", "start": 3.48, "end": 3.82},
                {"text": "stars", "start": 3.82, "end": 4.30}
            ]
        },
        {
            "id": f"{demo_id}_line_4",
            "line_index": 3,
            "text": "feel the rhythm",
            "start": 4.98,
            "end": 5.54,
            "words": [
                {"text": "feel", "start": 4.98, "end": 5.02},
                {"text": "the", "start": 5.02, "end": 5.54},
                {"text": "rhythm", "start": 5.54, "end": 5.54}
            ]
        },
        {
            "id": f"{demo_id}_line_5",
            "line_index": 4,
            "text": "and let the music play",
            "start": 5.86,
            "end": 6.94,
            "words": [
                {"text": "and", "start": 5.86, "end": 6.00},
                {"text": "let", "start": 6.00, "end": 6.08},
                {"text": "the", "start": 6.08, "end": 6.30},
                {"text": "music", "start": 6.30, "end": 6.60},
                {"text": "play", "start": 6.60, "end": 6.94}
            ]
        }
    ]

    canonical_data = {
        "project_id": demo_id,
        "media": {
            "audio_path": project.audio_path,
            "video_path": project.video_path,
            "audio_duration": 7.22,
            "video_duration": 7.22,
            "fps": 30.0,
            "width": 1920,
            "height": 1080
        },
        "style": {
            "font": "Outfit",
            "fontSize": 32,
            "primaryColor": "#FFFFFF",
            "highlightColor": "#10B981",
            "position": "bottom",
            "mode": "karaoke",
            "aspectRatio": "16:9"
        },
        "meta": {
            "background_template": "burgundy_studio"
        },
        "lyrics": canonical_lines
    }

    project.set_canonical_json(canonical_data)

    # 6. Update database relational tables (LyricLine, LyricWord)
    LyricLine.query.filter_by(project_id=demo_id).delete()
    for l_data in canonical_lines:
        ll = LyricLine(
            id=l_data["id"],
            project_id=demo_id,
            line_index=l_data["line_index"],
            text=l_data["text"],
            start=l_data["start"],
            end=l_data["end"]
        )
        db.session.add(ll)
        for w_idx, w_data in enumerate(l_data["words"]):
            lw = LyricWord(
                id=f"{ll.id}_w_{w_idx}",
                line_id=ll.id,
                word_index=w_idx,
                text=w_data["text"],
                start=w_data["start"],
                end=w_data["end"]
            )
            db.session.add(lw)

    db.session.commit()
    print("Demo project successfully reseeded with real vocal song and 16:9 chalkboard video!")
