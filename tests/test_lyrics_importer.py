import pytest
from app.services.lyrics_importer import LyricsImporter
from app import create_app
from app.extensions import db
from app.models import Project

def test_lyrics_importer_plain_text():
    text = """
    First line of the song
    Second line of the song
    Third line of the song
    Fourth line of the song
    """
    lines = LyricsImporter.import_lyrics(text, total_duration=20.0)
    assert len(lines) == 4
    for i, line in enumerate(lines):
        assert line["start"] < line["end"]
        assert len(line["words"]) > 0
        assert line["text"] in text
        # Word timestamps inside line
        for w in line["words"]:
            assert w["start"] >= line["start"] - 0.01
            assert w["end"] <= line["end"] + 0.01

def test_lyrics_importer_lrc_format():
    lrc = """
    [ti:Test Song]
    [ar:Test Artist]
    [00:02.50]Hello first verse
    [00:06.80]Here comes the chorus line
    [00:12.15]Ending of the song
    """
    assert LyricsImporter.is_lrc(lrc) is True
    lines = LyricsImporter.import_lyrics(lrc, total_duration=30.0)
    assert len(lines) == 3
    assert lines[0]["start"] == 2.5
    assert lines[0]["text"] == "Hello first verse"
    assert lines[1]["start"] == 6.8
    assert lines[1]["text"] == "Here comes the chorus line"
    assert lines[2]["start"] == 12.15
    assert lines[2]["text"] == "Ending of the song"

def test_lyrics_importer_empty_raises():
    with pytest.raises(ValueError):
        LyricsImporter.import_lyrics("   \n\n  ")

def test_api_custom_lyrics_endpoint(client, app):
    with app.app_context():
        # Create test project
        project = Project(
            id="test-custom-lyrics-proj",
            name="Test Custom Song",
            status="ready",
            audio_duration=60.0
        )
        db.session.add(project)
        db.session.commit()

        # Test POST /api/projects/<id>/lyrics/custom with JSON
        payload = {
            "lyrics_text": "First line here\nSecond line follows\nThird line ends"
        }
        res = client.post(f"/api/projects/{project.id}/lyrics/custom", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert len(data["lyrics"]) == 3
        assert data["revision"] > 0

        # Verify canonical was updated
        db.session.refresh(project)
        canonical = project.get_canonical_json()
        assert len(canonical["lyrics"]) == 3
        assert canonical["lyrics"][0]["text"] == "First line here"

        # Cleanup
        db.session.delete(project)
        db.session.commit()
