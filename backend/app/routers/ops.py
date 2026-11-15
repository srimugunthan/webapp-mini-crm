import os
import tempfile
import time

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from fastapi.responses import FileResponse, Response

from ..db import backup_to, connect
from ..errors import AppError
from ..services import ops, restore as restore_svc
from .deps import get_db, settings

router = APIRouter(tags=["ops"])


@router.get("/api/export")
def export(group_id: int | None = None, ids: str | None = None, q: str | None = None, company: str | None = None,
           position: str | None = None, year: int | None = None, never_visited: bool = False,
           never_messaged: bool = False, no_group: bool = False, group: str | None = None, conn=Depends(get_db)):
    """All contacts, a group, an explicit selection (ids=1,2,3), or whatever the contacts filters match."""
    id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()] if ids is not None else None
    filters = {k: v for k, v in dict(q=q, company=company, position=position, year=year, never_visited=never_visited,
                                     never_messaged=never_messaged, no_group=no_group, group=group).items() if v}
    text, name = ops.export_csv(conn, group_id, id_list, filters if group_id is None else None)
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name)
    return Response(text, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{safe}.csv"'})


@router.get("/api/backup")
def backup(tasks: BackgroundTasks, cfg=Depends(settings)):
    fd, tmp = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    conn = connect(cfg.db_path)
    try:
        backup_to(conn, __import__("pathlib").Path(tmp))
    finally:
        conn.close()
    tasks.add_task(os.unlink, tmp)
    name = f"crm-backup-{time.strftime('%Y%m%d-%H%M%S')}.sqlite"
    return FileResponse(tmp, media_type="application/octet-stream", filename=name)


async def _read_db_upload(file: UploadFile, cfg) -> bytes:
    data = await file.read(cfg.max_restore_bytes + 1)
    if len(data) > cfg.max_restore_bytes:
        raise AppError(413, "That file is larger than 500 MB. Is it the right file?")
    return data


@router.post("/api/restore/preview")
async def restore_preview(file: UploadFile = File(...), cfg=Depends(settings)):
    """Validate an uploaded .sqlite backup and say what it contains. Changes nothing."""
    return restore_svc.inspect(await _read_db_upload(file, cfg), cfg.db_path.parent, cfg.migrations_dir)


@router.post("/api/restore")
async def restore_database(file: UploadFile = File(...), confirm: str | None = None, conn=Depends(get_db), cfg=Depends(settings)):
    """Replace the whole database with an uploaded backup. Needs confirm=RESTORE."""
    if confirm != restore_svc.RESTORE_PHRASE:
        raise AppError(400, f"Restoring replaces ALL current data. Confirm by sending confirm={restore_svc.RESTORE_PHRASE}.")
    return restore_svc.restore(conn, await _read_db_upload(file, cfg), cfg)
