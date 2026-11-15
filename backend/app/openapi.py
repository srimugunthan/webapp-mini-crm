"""Print the OpenAPI schema (used by `npm run gen:api`). Does not touch the real database."""
import json
import tempfile
from pathlib import Path

from .config import Settings
from .main import create_app

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        app = create_app(Settings(db_path=Path(d) / "x.sqlite", data_dir=Path(d), static_dir=None))
        print(json.dumps(app.openapi()))
