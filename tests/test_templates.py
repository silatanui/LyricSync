import pytest
from pathlib import Path
from app.extensions import db
from app.models.project import Project
from app.services.background_generator import BackgroundGenerator

def test_available_templates():
    templates = BackgroundGenerator.get_templates()
    assert len(templates) >= 6
    template_ids = [t["id"] for t in templates]
    assert "burgundy_studio" in template_ids
    assert "deep_nebula" in template_ids
    assert "retrowave_sunset" in template_ids
    assert "midnight_acoustic" in template_ids
    assert "abstract_aurora" in template_ids
    assert "minimal_dark" in template_ids

def test_generate_pattern_images():
    templates = ["burgundy_studio", "deep_nebula", "retrowave_sunset", "midnight_acoustic", "abstract_aurora", "minimal_dark"]
    for t_id in templates:
        img = BackgroundGenerator.generate_pattern_image(t_id, width=320, height=180)
        assert img.size == (320, 180)
        assert img.mode == "RGB"

def test_api_templates_list(client):
    res = client.get("/api/projects/templates")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["templates"]) >= 6

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

        res = client.post("/api/projects/test_tmpl_proj/background", json={"template": "deep_nebula"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["template"] == "deep_nebula"
        assert "video_url" in data
