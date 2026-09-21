from pathlib import Path
from app.services.ffmpeg import escape_ass_path, FFmpegRenderer
from app.services.subtitles import SubtitleGenerator
from app.services.media_probe import MediaProbe

def test_escape_ass_path():
    p = Path("C:/projects/test.ass")
    escaped = escape_ass_path(p)
    assert "\\" not in escaped or "\\:" in escaped
    assert ":" not in escaped or "\\:" in escaped

def test_scale_crop_filter():
    renderer = FFmpegRenderer()
    vf = renderer.build_scale_crop_filter("16:9", 1920, 1080)
    assert "scale=1920:1080" in vf
    assert "crop=1920:1080" in vf

    vf_vert = renderer.build_scale_crop_filter("9:16", 1080, 1920)
    assert "scale=1080:1920" in vf_vert

def test_ffmpeg_render_end_to_end(test_media_dir, tmp_path):
    audio_path = test_media_dir["audio"]
    video_path = test_media_dir["video"]

    # Generate small ASS subtitle
    canonical = {
        "media": {"width": 640, "height": 360},
        "style": {
            "mode": "karaoke",
            "font": "Arial",
            "font_size": 24,
            "primary_color": "#FFFFFF",
            "highlight_color": "#FFE66D",
            "position": "bottom"
        },
        "lyrics": [
            {
                "id": 1,
                "text": "Sine wave tone",
                "start": 0.5,
                "end": 2.5,
                "words": [
                    {"text": "Sine", "start": 0.5, "end": 1.0},
                    {"text": "wave", "start": 1.1, "end": 1.8},
                    {"text": "tone", "start": 1.9, "end": 2.5},
                ]
            }
        ]
    }
    ass_path = tmp_path / "test.ass"
    SubtitleGenerator.generate_ass(canonical, ass_path)

    output_path = tmp_path / "rendered_output.mp4"
    renderer = FFmpegRenderer()

    # Render with looping enabled (video is 2s, audio is 3s)
    final_mp4 = renderer.render(
        video_path=video_path,
        audio_path=audio_path,
        ass_path=ass_path,
        output_path=output_path,
        aspect_ratio="16:9",
        video_policy="loop",
        audio_policy="replace"
    )

    assert final_mp4.exists()
    assert final_mp4.stat().st_size > 0

    # Probe output to ensure video and audio streams exist
    probe = MediaProbe.probe(final_mp4)
    assert probe["has_video"] is True
    assert probe["has_audio"] is True
    assert probe["duration"] >= 2.5
