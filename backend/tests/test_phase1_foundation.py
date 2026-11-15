import sqlite3
from pathlib import Path

import pytest

from app.db import connect, migrate
from app.main import create_app
from fastapi.testclient import TestClient


def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_health_fails_when_db_unavailable(settings):
    app = create_app(settings)
    with TestClient(app) as c:
        settings.db_path.unlink()
        for ext in ("-wal", "-shm"):
            Path(str(settings.db_path) + ext).unlink(missing_ok=True)
        settings.db_path.mkdir()  # a directory where the file should be -> unreadable
        assert c.get("/api/health").status_code == 503


def test_pragmas(settings):
    create_app(settings)
    conn = connect(settings.db_path)
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_migrations_apply_and_set_version(settings):
    create_app(settings)
    conn = connect(settings.db_path)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 7


def _mig_dir(tmp_path, files):
    d = tmp_path / "mig"
    d.mkdir()
    for name, sql in files.items():
        (d / name).write_text(sql)
    return d


def test_backup_before_pending_migration_and_keep_last_5(tmp_path):
    db = tmp_path / "db" / "crm.sqlite"
    files = {"001_a.sql": "CREATE TABLE a (x);"}
    d = _mig_dir(tmp_path, files)
    backups = tmp_path / "db" / "backups"
    assert migrate(db, d, backups) == 1
    assert not backups.exists()  # fresh DB: nothing to back up
    for n in range(2, 10):
        (d / f"{n:03d}_m.sql").write_text(f"CREATE TABLE t{n} (x);")
        migrate(db, d, backups)
    assert len(list(backups.glob("pre-migration-*.sqlite"))) == 5


def test_failing_migration_rolls_back_and_raises(tmp_path):
    db = tmp_path / "db" / "crm.sqlite"
    d = _mig_dir(tmp_path, {"001_a.sql": "CREATE TABLE a (x);",
                            "002_bad.sql": "CREATE TABLE b (x); INSERT INTO nope VALUES (1);"})
    with pytest.raises(sqlite3.Error):
        migrate(db, d, tmp_path / "bk")
    conn = connect(db)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
    assert conn.execute("SELECT name FROM sqlite_master WHERE name='b'").fetchone() is None


def test_spa_fallback(settings, tmp_path):
    static = tmp_path / "dist"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<html>app</html>")
    (static / "assets" / "a.js").write_text("1")
    settings.static_dir = static
    with TestClient(create_app(settings)) as c:
        assert "app" in c.get("/groups/3").text
        assert c.get("/assets/a.js").text == "1"
        assert c.get("/api/nope").status_code == 404
