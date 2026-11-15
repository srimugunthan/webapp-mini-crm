"""CLI: `python -m app.cli backup [DEST]` writes a consistent single-file backup using SQLite's backup API."""
import sys
import time
from pathlib import Path

from .config import settings_from_env
from .db import backup_to, connect


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] != "backup":
        print("usage: python -m app.cli backup [DEST_FILE]", file=sys.stderr)
        return 2
    cfg = settings_from_env()
    if not cfg.db_path.exists():
        print(f"Database not found at {cfg.db_path}", file=sys.stderr)
        return 1
    dest = Path(argv[1]) if len(argv) > 1 else cfg.backup_dir / f"manual-{time.strftime('%Y%m%d-%H%M%S')}.sqlite"
    conn = connect(cfg.db_path)
    try:
        backup_to(conn, dest)
    finally:
        conn.close()
    print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
