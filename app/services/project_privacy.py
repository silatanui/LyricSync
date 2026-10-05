"""Project visibility helpers — private by default, public only when opted in."""
from __future__ import annotations

from typing import Any

from flask_login import current_user

from app.models.project import Project


def normalize_is_public(value: Any) -> bool:
    """
    Strict public flag parsing.
    Only True / 1 / "true" / "1" / "yes" / "public" count as public.
    Everything else (including missing, "false", "0", None) is private.
    """
    if value is True or value is False:
        return bool(value)
    if isinstance(value, (int, float)):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "public", "on"}
    return False


def project_is_public(project_or_canonical: Project | dict | None) -> bool:
    """Return True only when the owner explicitly published the project."""
    if project_or_canonical is None:
        return False
    if isinstance(project_or_canonical, dict):
        meta = project_or_canonical.get("meta") or {}
    else:
        meta = (project_or_canonical.get_canonical_json() or {}).get("meta") or {}
    return normalize_is_public(meta.get("is_public"))


def ensure_private_meta(canonical: dict) -> dict:
    """Guarantee meta.is_public exists and defaults to False."""
    meta = canonical.setdefault("meta", {})
    if "is_public" not in meta:
        meta["is_public"] = False
    else:
        meta["is_public"] = normalize_is_public(meta.get("is_public"))
    return canonical


def user_owns_project(user, project: Project | None) -> bool:
    if not project or not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_admin", False):
        return True
    return bool(project.user_id and project.user_id == getattr(user, "id", None))


def user_can_access_project(user, project: Project | None) -> bool:
    """
    Private projects: owner or admin only.
    Public projects: anyone may view the published surface / media.
    """
    if not project:
        return False
    if project_is_public(project):
        return True
    return user_owns_project(user, project)


def user_can_edit_project(user, project: Project | None) -> bool:
    """Editing always requires ownership (or admin), even if the project is public."""
    return user_owns_project(user, project)


def visible_projects_query(query, user=None):
    """
    Scope a Project query to what the current viewer should see in their studio list.
    - Admin: all projects
    - Signed-in user: only their own projects
    - Anonymous: empty
    """
    from sqlalchemy import false

    u = user if user is not None else current_user
    if not getattr(u, "is_authenticated", False):
        return query.filter(false())
    if getattr(u, "is_admin", False):
        return query
    return query.filter(Project.user_id == u.id)
