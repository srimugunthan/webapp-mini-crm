import sqlite3
from contextlib import contextmanager
from pathlib import Path


def connect(path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def tx(conn):
    """One explicit transaction: commit on success, roll back on any error."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def _statements(sql: str):
    buf = ""
    for line in sql.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            if buf.strip():
                yield buf
            buf = ""
    if buf.strip():
        yield buf


def list_migrations(directory: Path):
    items = []
    for p in sorted(Path(directory).glob("*.sql")):
        items.append((int(p.name.split("_", 1)[0]), p))
    return items


def backup_to(conn: sqlite3.Connection, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    out = sqlite3.connect(str(dest))
    try:
        conn.backup(out)
    finally:
        out.close()


def migrate(db_path: Path, migrations_dir: Path, backup_dir: Path, keep: int = 5) -> int:
    """Apply pending numbered migrations; back up first when the DB already has data."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        current = conn.execute("PRAGMA user_version").fetchone()[0]
        pending = [(n, p) for n, p in list_migrations(migrations_dir) if n > current]
        if not pending:
            return current
        if current > 0:
            stamp = __import__("time").strftime("%Y%m%d-%H%M%S")
            backup_to(conn, Path(backup_dir) / f"pre-migration-v{current}-{stamp}.sqlite")
            backups = sorted(Path(backup_dir).glob("pre-migration-*.sqlite"), key=lambda p: p.stat().st_mtime)
            for old in backups[:-keep]:
                old.unlink()
        for n, path in pending:
            with tx(conn):
                for stmt in _statements(path.read_text()):
                    conn.execute(stmt)
                conn.execute(f"PRAGMA user_version = {int(n)}")
            current = n
        return current
    finally:
        conn.close()


def schema_version(conn) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]
