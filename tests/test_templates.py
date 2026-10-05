import pytest
from pathlib import Path
from app.extensions import db
from app.models.project import Project
from app.services.background_generator import BackgroundGenerator

def test_available_templates():
    templates = BackgroundGenerator.get_templates()
    assert len(templates) >= 50
    template_ids = [t["id"] for t in templates]
    assert "burgundy_studio" in template_ids
    assert "deep_nebula" in template_ids
    assert "dream_fog" in template_ids
    assert "niteke_pulse" not in template_ids
    assert "calvary_sunrise" in template_ids
    assert "neon_equalizer" in template_ids
    assert "city_vespers" in template_ids
    video_themes = [t for t in templates if t.get("is_video")]
    assert len(video_themes) >= 8
    assert all(t.get("motion") in {"visualizer", "starfield", "waves", "grid", "pulse"} for t in video_themes)
    assert any(t.get("is_visualizer") for t in templates)
    assert any(t.get("is_photo") for t in templates)
    # Photo/cinematic plates are stills, not fake video.
    city = next(t for t in templates if t["id"] == "city_vespers")
    assert city.get("is_video") is False
    assert all("moods" in t for t in templates)

def test_generate_pattern_images():
    templates = [
        "burgundy_studio", "deep_nebula", "retrowave_sunset",
        "midnight_acoustic", "abstract_aurora", "minimal_dark",
        "city_vespers", "hillside_cross", "gospel_spectrum",
    ]
    for t_id in templates:
        img = BackgroundGenerator.generate_pattern_image(t_id, width=320, height=180)
        assert img.size == (320, 180)
        assert img.mode == "RGB"


def test_visualizer_loop_generates_mp4(tmp_path):
    out = tmp_path / "mercy_bars.mp4"
    BackgroundGenerator.generate_theme_video_loop(
        "mercy_bars",
        out,
        width=320,
        height=180,
        seconds=1.0,
    )
    assert out.exists()
    assert out.stat().st_size > 1000

def test_api_templates_list(client):
    res = client.get("/api/projects/templates")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["templates"]) >= 50
    assert "moods" in data

    worship = client.get("/api/projects/templates?mood=worship")
    assert worship.status_code == 200
    wdata = worship.get_json()
    assert wdata["success"] is True
    assert len(wdata["templates"]) >= 1
    assert all("worship" in (t.get("moods") or []) for t in wdata["templates"])

def test_api_switch_background(client, test_media_dir, app):
    audio_file = test_media_dir["audio"]

    proj = Project(
        id="test_tmpl_proj",
        name="Template Test Project",
        audio_path=str(audio_file),
        video_path=str(test_media_dir["video"]),
        audio_duration=3.0,
        video_duration=3.0
    )
    with app.app_context():
        db.session.add(proj)
        db.session.commit()

        res = client.post("/api/projects/test_tmpl_proj/background", json={"template": "burgundy_studio"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["template"] == "burgundy_studio"
        assert "video_url" in data
        assert data["is_image"] is True

        updated_proj = db.session.get(Project, "test_tmpl_proj")
        assert updated_proj.is_video_background is False
