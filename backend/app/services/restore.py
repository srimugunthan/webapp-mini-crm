"""Restore the whole database from an uploaded .sqlite file (decision 76).

Safety: the upload is validated in a temp file (SQLite header, integrity_check, made by this app, not from a newer
version); the current database is backed up first; the swap uses SQLite's backup API, which is atomic for the
destination, so a failure leaves the current data untouched. Older backups are upgraded by running migrations.
"""
import os
import sqlite3
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from .. import clock
from ..db import backup_to, connect, list_migrations, migrate
from ..errors import AppError

MAGIC = b"SQLite format 3\x00"
RESTORE_PHRASE = "RESTORE"
MIN_VERSION = 4  # groups exist from migration 004; older files are not a usable CRM database


def latest_version(migrations_dir) -> int:
    return max((n for n, _ in list_migrations(migrations_dir)), default=0)


@contextmanager
def _temp_copy(data: bytes, directory: Path):
    Path(directory).mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(suffix=".sqlite", dir=directory)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        yield Path(name)
    finally:
        for ext in ("", "-wal", "-shm", "-journal"):
            try:
                os.unlink(name + ext)
            except FileNotFoundError:
                pass


def inspect(data: bytes, workdir: Path, migrations_dir) -> dict:
    """Validate an uploaded database and describe it. Raises AppError(400) with a plain reason when unusable."""
    if not data.startswith(MAGIC):
        raise AppError(400, "This is not a SQLite database file. Choose a backup made by this app (Import → Download backup).")
    latest = latest_version(migrations_dir)
    with _temp_copy(data, workdir) as path:
        try:
            src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            try:
                if src.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise AppError(400, "The database file is damaged (integrity check failed).")
                tables = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not {"app_meta", "contacts", "groups", "group_members"} <= tables:
                    raise AppError(400, "This SQLite file was not made by LinkedIn Mini CRM.")
                made_by = src.execute("SELECT v FROM app_meta WHERE k='created_by'").fetchone()
                if not made_by or made_by[0] != "linkedin-mini-crm":
                    raise AppError(400, "This SQLite file was not made by LinkedIn Mini CRM.")
                version = src.execute("PRAGMA user_version").fetchone()[0]
                if version > latest:
                    raise AppError(400, f"This backup was made by a newer version of the app (schema {version}, this app knows {latest}). Update the app first.")
                if version < MIN_VERSION:
                    raise AppError(400, f"This backup is too old to restore (schema {version}).")
                count = lambda t: src.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] if t in tables else 0  # noqa: E731
                return {"schema_version": version, "app_schema_version": latest, "needs_upgrade": version < latest,
                        "contacts": count("contacts"), "groups": count("groups"), "memberships": count("group_members"),
                        "notes": count("notes"), "stage_history": count("stage_history"),
                        "templates": count("pipeline_templates")}
            finally:
                src.close()
        except sqlite3.DatabaseError as e:
            raise AppError(400, f"Could not read this file as a database: {e}")


def _safety_backup(conn, backup_dir: Path, keep: int = 5) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(clock.now()))
    dest = Path(backup_dir) / f"pre-restore-{stamp}.sqlite"
    n = 1
    while dest.exists():
        n += 1
        dest = Path(backup_dir) / f"pre-restore-{stamp}-{n}.sqlite"
    backup_to(conn, dest)
    for old in sorted(Path(backup_dir).glob("pre-restore-*.sqlite"), key=lambda p: p.stat().st_mtime)[:-keep]:
        old.unlink()
    return dest.name


def restore(conn, data: bytes, settings) -> dict:
    info = inspect(data, settings.db_path.parent, settings.migrations_dir)
    safety = _safety_backup(conn, settings.backup_dir)
    with _temp_copy(data, settings.db_path.parent) as path:
        src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            src.backup(conn)  # atomic for the destination: on failure the current database is unchanged
        except sqlite3.Error as e:
            raise AppError(500, f"Restore failed and your current data was kept: {e}")
        finally:
            src.close()
    conn.execute("PRAGMA journal_mode=WAL")
    final = migrate(settings.db_path, settings.migrations_dir, settings.backup_dir)  # upgrades an older backup
    return {"restored": True, "from_schema_version": info["schema_version"], "schema_version": final,
            "upgraded": info["needs_upgrade"], "safety_backup": safety, **{k: info[k] for k in ("contacts", "groups", "memberships", "notes")}}
