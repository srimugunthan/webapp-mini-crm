from fastapi import APIRouter, Depends, File, UploadFile

from ..errors import AppError
from ..services import importer, uploads
from .deps import get_db, settings

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("")
async def upload(file: UploadFile = File(...), mode: str = "add", confirm: str | None = None,
                 group: str | None = None, conn=Depends(get_db), cfg=Depends(settings)):
    """mode=add: add to existing contacts (default). mode=fresh&confirm=RESET: replace everything.
    group (optional): also put everyone in the file into this group (created if missing)."""
    if mode not in ("add", "fresh"):
        raise AppError(422, "mode must be 'add' or 'fresh'")
    fresh = mode == "fresh"
    if fresh and confirm != importer.FRESH_PHRASE:
        raise AppError(400, f"A fresh import deletes all contacts, groups and notes. Confirm by sending confirm={importer.FRESH_PHRASE}.")
    data = await file.read(cfg.max_upload_bytes + 1)
    if len(data) > cfg.max_upload_bytes:
        raise AppError(413, "File is larger than 25 MB. Is this the right file?")
    uploads.save_upload(cfg.data_dir, "import-fresh" if fresh else "import-add", file.filename, data)
    return importer.import_csv(conn, data, fresh=fresh, backup_dir=cfg.backup_dir, group=group)


@router.get("/stats")
def stats(conn=Depends(get_db)):
    """Counts of what a fresh import would delete."""
    return importer.stats(conn)
