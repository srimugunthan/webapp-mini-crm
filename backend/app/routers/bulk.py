from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse

from ..errors import AppError
from ..services import bulk, uploads
from .deps import get_db, settings

router = APIRouter(tags=["bulk"])


@router.post("/api/groups/{gid}/bulk-stage")
async def bulk_stage(gid: int, request: Request, preview: bool = False, conn=Depends(get_db), cfg=Depends(settings)):
    if preview:
        form = await request.form()
        upload = form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise AppError(422, "Attach a CSV file")
        data = await upload.read(cfg.max_upload_bytes + 1)
        if len(data) > cfg.max_upload_bytes:
            raise AppError(413, "File is larger than 25 MB.")
        uploads.save_upload(cfg.data_dir, "bulk-stage", getattr(upload, "filename", None), data)
        raw = form.get("stage_id")
        return bulk.preview(conn, gid, data, int(raw) if raw not in (None, "") else None)
    body = await request.json()
    if not isinstance(body, dict) or not body.get("token"):
        raise AppError(422, "token is required")
    return bulk.apply(conn, gid, body["token"])


@router.get("/api/groups/{gid}/bulk-stage/{token}/problems.csv")
def problems(gid: int, token: str, conn=Depends(get_db)):
    return PlainTextResponse(bulk.problems_csv(conn, gid, token), media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="problem-rows.csv"'})


@router.post("/api/groups/{gid}/bulk-stage/undo")
def undo(gid: int, conn=Depends(get_db)):
    return bulk.undo(conn, gid)
