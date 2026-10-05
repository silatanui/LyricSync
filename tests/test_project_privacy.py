from app.extensions import db
from app.models import Project, User
from app.services.project_privacy import (
    normalize_is_public,
    project_is_public,
    user_can_access_project,
    user_can_edit_project,
    visible_projects_query,
)


def test_normalize_is_public_defaults_private():
    assert normalize_is_public(None) is False
    assert normalize_is_public(False) is False
    assert normalize_is_public("false") is False
    assert normalize_is_public("0") is False
    assert normalize_is_public("") is False
    assert normalize_is_public(True) is True
    assert normalize_is_public("true") is True
    assert normalize_is_public(1) is True


def test_new_project_is_private_and_owned(client, app, test_media_dir):
    with app.app_context():
        user = User(email="owner@example.com", display_name="Owner", email_verified=True)
        user.set_password("Secret123!")
        db.session.add(user)
        db.session.commit()

        login = client.post("/api/auth/login", json={
            "email": "owner@example.com",
            "password": "Secret123!",
        })
        assert login.status_code == 200

        with open(test_media_dir["audio"], "rb") as audio:
            res = client.post(
                "/api/projects",
                data={
                    "audio": (audio, "song.wav"),
                    "name": "Private Song",
                    "template": "burgundy_studio",
                    "aspect_ratio": "16:9",
                },
                content_type="multipart/form-data",
            )
        assert res.status_code in (200, 201)
        body = res.get_json()
        assert body["success"] is True
        project_id = body["project"]["id"]

        project = db.session.get(Project, project_id)
        assert project.user_id == user.id
        assert project_is_public(project) is False

        # Another user must not see it in the dashboard API
        client.get("/logout")
        stranger = User(email="stranger@example.com", display_name="Stranger", email_verified=True)
        stranger.set_password("Secret123!")
        db.session.add(stranger)
        db.session.commit()
        client.post("/api/auth/login", json={
            "email": "stranger@example.com",
            "password": "Secret123!",
        })
        listed = client.get("/api/projects").get_json()
        assert all(p["id"] != project_id for p in listed["projects"])

        denied = client.get(f"/api/projects/{project_id}")
        assert denied.status_code == 403


def test_public_opt_in_only(client, app):
    with app.app_context():
        user = User(email="publisher@example.com", display_name="Publisher", email_verified=True)
        user.set_password("Secret123!")
        db.session.add(user)
        db.session.commit()

        project = Project(name="Shelf Song", user_id=user.id, status="ready")
        canonical = project.get_canonical_json()
        canonical["meta"]["is_public"] = False
        project.set_canonical_json(canonical)
        db.session.add(project)
        db.session.commit()
        pid = project.id

        client.post("/api/auth/login", json={
            "email": "publisher@example.com",
            "password": "Secret123!",
        })
        assert client.get(f"/public/project/{pid}").status_code == 404

        updated = client.put(f"/api/projects/{pid}", json={"name": "Shelf Song", "is_public": True})
        assert updated.status_code == 200
        assert updated.get_json()["is_public"] is True
        assert client.get(f"/public/project/{pid}").status_code == 200

        home = client.get("/")
        assert home.status_code == 200
        assert "Shelf Song" in home.get_data(as_text=True)


def test_visible_query_scopes_by_owner(app):
    with app.app_context():
        a = User(email="a@example.com", display_name="A", email_verified=True)
        b = User(email="b@example.com", display_name="B", email_verified=True)
        a.set_password("Secret123!")
        b.set_password("Secret123!")
        db.session.add_all([a, b])
        db.session.commit()
        db.session.add_all([
            Project(name="A1", user_id=a.id),
            Project(name="B1", user_id=b.id),
        ])
        db.session.commit()

        scoped = visible_projects_query(db.session.query(Project), user=a).all()
        assert [p.name for p in scoped] == ["A1"]
        assert user_can_edit_project(a, scoped[0]) is True
        assert user_can_access_project(b, scoped[0]) is False
