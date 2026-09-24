import io
import json
import pytest
from app.tasks.transcription_tasks import run_transcription_pipeline

def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"

def test_project_crud_and_canonical_flow(client, test_media_dir, app):
    audio_file = test_media_dir["audio"]
    video_file = test_media_dir["video"]

    # 1. Create project with multipart upload
    with open(audio_file, "rb") as a_f, open(video_file, "rb") as v_f:
        data = {
            "name": "Integration Test Song",
            "audio": (a_f, "test_audio.wav"),
            "video": (v_f, "test_video.mp4"),
        }
        res = client.post("/api/projects", data=data, content_type="multipart/form-data")

    assert res.status_code == 201
    json_data = res.get_json()
    assert json_data["success"] is True
    project_id = json_data["project"]["id"]
    assert project_id.startswith("proj_")

    # 2. List projects
    res = client.get("/api/projects")
    assert res.status_code == 200
    projects = res.get_json()["projects"]
    assert any(p["id"] == project_id for p in projects)

    # 3. Get project
    res = client.get(f"/api/projects/{project_id}")
    assert res.status_code == 200
    p_data = res.get_json()
    assert p_data["project"]["name"] == "Integration Test Song"
    canonical = p_data["canonical"]
    assert canonical["project_id"] == project_id

    # 4. Update project metadata
    res = client.put(f"/api/projects/{project_id}", json={"name": "Renamed Integration Song"})
    assert res.status_code == 200
    assert res.get_json()["project"]["name"] == "Renamed Integration Song"

    # 5. Transcribe (run pipeline directly in test context)
    run_transcription_pipeline(app, project_id)

    # 6. Get canonical lyrics
    res = client.get(f"/api/projects/{project_id}/lyrics")
    assert res.status_code == 200
    lyrics_data = res.get_json()
    assert lyrics_data["success"] is True
    assert len(lyrics_data["lyrics"]) > 0
    first_line = lyrics_data["lyrics"][0]
    assert "words" in first_line
    assert len(first_line["words"]) > 0

    # 7. Save edited revision
    edited_lyrics = lyrics_data["lyrics"]
    edited_lyrics[0]["text"] = "Customized opening line"
    res = client.put(
        f"/api/projects/{project_id}/lyrics",
        json={"lyrics": edited_lyrics}
    )
    assert res.status_code == 200
    assert res.get_json()["revision"] == 2

    # 8. Update style
    res = client.put(
        f"/api/projects/{project_id}/style",
        json={
            "style": {"font": "Impact", "font_size": 60, "highlight_color": "#FF0000"},
            "render": {"aspect_ratio": "9:16"}
        }
    )
    assert res.status_code == 200
    style_res = res.get_json()
    assert style_res["style"]["font"] == "Impact"
    assert style_res["render"]["aspect_ratio"] == "9:16"

    # 9. Delete project
    res = client.delete(f"/api/projects/{project_id}")
    assert res.status_code == 200
    res = client.get(f"/api/projects/{project_id}")
    assert res.status_code == 404

def test_project_creation_without_name_auto_generates_title(client, test_media_dir):
    audio_file = test_media_dir["audio"]
    video_file = test_media_dir["video"]

    # Post without "name" field
    with open(audio_file, "rb") as a_f, open(video_file, "rb") as v_f:
        data = {
            "audio": (a_f, "Midnight_Acoustic_Demo.wav"),
            "video": (v_f, "test_video.mp4"),
        }
        res = client.post("/api/projects", data=data, content_type="multipart/form-data")

    assert res.status_code == 201
    json_data = res.get_json()
    assert json_data["success"] is True
    assert json_data["project"]["name"] == "Midnight Acoustic Demo"

def test_stream_media_with_fallback_path(client, test_media_dir):
    audio_file = test_media_dir["audio"]
    video_file = test_media_dir["video"]

    with open(audio_file, "rb") as a_f, open(video_file, "rb") as v_f:
        data = {
            "name": "Streaming Path Test",
            "audio": (a_f, "test_audio.wav"),
            "video": (v_f, "test_video.mp4"),
        }
        res = client.post("/api/projects", data=data, content_type="multipart/form-data")

    assert res.status_code == 201
    project_id = res.get_json()["project"]["id"]

    # Stream audio
    res_audio = client.get(f"/api/projects/{project_id}/media/audio")
    assert res_audio.status_code == 200
    assert "audio/" in res_audio.headers.get("Content-Type", "")

    # Stream video
    res_video = client.get(f"/api/projects/{project_id}/media/video")
    assert res_video.status_code == 200
    assert "video/" in res_video.headers.get("Content-Type", "")

def test_download_rendered_project(client, test_media_dir, app):
    from app.models import Project, RenderJob
    from app.utils.files import get_project_output_dir
    from app.extensions import db

    audio_file = test_media_dir["audio"]
    video_file = test_media_dir["video"]

    with open(audio_file, "rb") as a_f, open(video_file, "rb") as v_f:
        data = {
            "name": "Download Test Song!",
            "audio": (a_f, "test_audio.wav"),
            "video": (v_f, "test_video.mp4"),
        }
        res = client.post("/api/projects", data=data, content_type="multipart/form-data")

    assert res.status_code == 201
    project_id = res.get_json()["project"]["id"]

    # Create dummy rendered output file
    with app.app_context():
        p = db.session.get(Project, project_id)
        out_dir = get_project_output_dir(project_id)
        out_file = out_dir / f"lyricsync_{project_id}_rev1.mp4"
        out_file.write_bytes(b"dummy mp4 video bytes")

        job = RenderJob(
            project_id=project_id,
            status="completed",
            output_file_path=str(out_file),
            progress=100
        )
        db.session.add(job)
        db.session.commit()

    # Test download endpoint
    res_dl = client.get(f"/api/projects/{project_id}/download")
    assert res_dl.status_code == 200
    assert res_dl.headers.get("Content-Type") == "video/mp4"
    assert "attachment" in res_dl.headers.get("Content-Disposition", "")
    assert "Download_Test_Song_lyrics.mp4" in res_dl.headers.get("Content-Disposition", "")

