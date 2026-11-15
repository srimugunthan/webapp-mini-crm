import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    db_path: Path
    data_dir: Path
    static_dir: Path | None
    migrations_dir: Path = BACKEND_DIR / "migrations"
    max_upload_bytes: int = 25 * 1024 * 1024
    max_restore_bytes: int = 500 * 1024 * 1024

    @property
    def backup_dir(self) -> Path:
        return self.db_path.parent / "backups"


def settings_from_env() -> Settings:
    static = os.environ.get("STATIC_DIR", str(BACKEND_DIR.parent / "frontend" / "dist"))
    return Settings(
        db_path=Path(os.environ.get("DB_PATH", BACKEND_DIR.parent / "db" / "crm.sqlite")),
        data_dir=Path(os.environ.get("DATA_DIR", BACKEND_DIR.parent / "data")),
        static_dir=Path(static) if static else None,
    )
