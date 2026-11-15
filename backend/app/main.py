import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, settings_from_env
from .db import migrate
from .errors import AppError
from .routers import contacts, health, imports

log = logging.getLogger("crm")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or settings_from_env()
    migrate(settings.db_path, settings.migrations_dir, settings.backup_dir)
    app = FastAPI(title="LinkedIn Mini CRM")
    app.state.settings = settings

    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError):
        if exc.status >= 500:
            log.error("request failed: %s", exc.detail)
        return JSONResponse({"detail": exc.detail}, status_code=exc.status)

    for module in (health, imports, contacts):
        app.include_router(module.router)
    _extra_routers(app)

    static = settings.static_dir
    if static and Path(static).is_dir():
        index = Path(static) / "index.html"
        if (Path(static) / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=Path(static) / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):
            if full_path.startswith(("api/", "go/")):
                return JSONResponse({"detail": "Not found"}, status_code=404)
            candidate = Path(static) / full_path
            if full_path and candidate.is_file() and Path(static) in candidate.resolve().parents:
                return FileResponse(candidate)
            return FileResponse(index)

    return app


def _extra_routers(app: FastAPI):
    """Routers added by later phases register themselves here when present."""
    import importlib
    for name in ("groups", "pipelines", "bulk", "ops"):
        try:
            mod = importlib.import_module(f".routers.{name}", __package__)
        except ModuleNotFoundError as e:
            if e.name and e.name.endswith(f"routers.{name}"):
                continue
            raise
        app.include_router(mod.router)


def run():  # pragma: no cover
    app = create_app()
    return app
