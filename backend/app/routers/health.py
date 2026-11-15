from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..db import connect, list_migrations, schema_version

router = APIRouter(tags=["ops"])


@router.get("/api/health")
def health(request: Request):
    cfg = request.app.state.settings
    try:
        conn = connect(cfg.db_path)
        try:
            conn.execute("SELECT 1").fetchone()
            version = schema_version(conn)
        finally:
            conn.close()
        latest = max((n for n, _ in list_migrations(cfg.migrations_dir)), default=0)
        if version != latest:
            raise RuntimeError(f"schema version {version} != {latest}")
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=503)
    return {"status": "ok", "schema_version": version}
