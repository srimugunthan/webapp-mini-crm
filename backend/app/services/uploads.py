"""Keep a copy of every CSV the user uploads in the data folder (decision 73).

Saving is best-effort: if the folder is read-only or missing a permission, the request still succeeds and the
problem is logged. Existing files are never overwritten (a timestamp and a counter keep names unique).
"""
import logging
import re
from datetime import datetime
from pathlib import Path

from .. import clock

log = logging.getLogger("crm")


def _safe_stem(filename: str | None) -> str:
    stem = Path(filename or "upload").name
    stem = re.sub(r"\.csv$", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._") or "upload"
    return stem[:80]


def save_upload(data_dir: Path, kind: str, filename: str | None, data: bytes) -> Path | None:
    """Write `<kind>-<YYYYMMDD-HHMMSS>-<original name>.csv` into data_dir. Returns the path, or None on failure."""
    try:
        data_dir = Path(data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.fromtimestamp(clock.now()).strftime("%Y%m%d-%H%M%S")
        base = f"{kind}-{stamp}-{_safe_stem(filename)}"
        path = data_dir / f"{base}.csv"
        n = 1
        while path.exists():
            n += 1
            path = data_dir / f"{base}-{n}.csv"
        path.write_bytes(data)
        return path
    except OSError as e:
        log.warning("could not save uploaded CSV to %s: %s", data_dir, e)
        return None
