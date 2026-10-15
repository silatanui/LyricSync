import importlib
import sys


def test_default_database_uses_sqlite_without_explicit_db_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("MYSQL_HOST", raising=False)
    monkeypatch.delenv("MYSQL_PORT", raising=False)
    monkeypatch.delenv("MYSQL_USER", raising=False)
    monkeypatch.delenv("MYSQL_PASSWORD", raising=False)
    monkeypatch.delenv("MYSQL_DATABASE", raising=False)

    sys.modules.pop("config", None)
    config = importlib.import_module("config")
    importlib.reload(config)

    assert config.Config.SQLALCHEMY_DATABASE_URI.startswith("sqlite:///")
    assert "\\" not in config.Config.SQLALCHEMY_DATABASE_URI
    assert "lyricsync.db" in config.Config.SQLALCHEMY_DATABASE_URI
