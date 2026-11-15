from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel

from ..errors import AppError
from ..services import groups as svc
from ..services import pipelines, uploads
from .deps import get_db, settings

router = APIRouter(tags=["groups"])


class GroupCreate(BaseModel):
    name: str
    template_id: int | None = None


class GroupRename(BaseModel):
    name: str


class MembersAdd(BaseModel):
    contact_ids: list[int]


class MemberPatch(BaseModel):
    stage_id: int | None = None
    next_follow_up_at: int | None = None
    note: str | None = None


class StageCreate(BaseModel):
    name: str | None = None
    names: list[str] | None = None
    is_final: bool = False


class StagePatch(BaseModel):
    name: str | None = None
    is_final: bool | None = None
    position: int | None = None


class ApplyPipeline(BaseModel):
    template_id: int
    preview: bool = True
    mapping: dict[str, str] | None = None


@router.get("/api/groups")
def list_groups(conn=Depends(get_db)):
    return svc.list_groups(conn)


@router.post("/api/groups", status_code=201)
def create_group(body: GroupCreate, conn=Depends(get_db)):
    return svc.create(conn, body.name, body.template_id)


@router.get("/api/groups/{gid}")
def get_group(gid: int, conn=Depends(get_db)):
    return svc.group_dict(svc.require(conn, gid))


@router.patch("/api/groups/{gid}")
def rename_group(gid: int, body: GroupRename, conn=Depends(get_db)):
    return svc.rename(conn, gid, body.name)


@router.delete("/api/groups/{gid}", status_code=204)
def delete_group(gid: int, conn=Depends(get_db)):
    svc.delete(conn, gid)


@router.get("/api/groups/{gid}/members")
def list_members(gid: int, stage: str | None = None, q: str | None = None, not_visited_days: int | None = None,
                 not_messaged_days: int | None = None, overdue: bool = False, hide_final: bool = False,
                 sort: str = "name", order: str = "asc", all: bool = False,
                 offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), conn=Depends(get_db)):
    return svc.list_members(conn, gid, stage=stage, q=q, not_visited_days=not_visited_days,
                            not_messaged_days=not_messaged_days, overdue=overdue, hide_final=hide_final,
                            sort=sort, order=order, all=all, offset=offset, limit=limit)


@router.post("/api/groups/{gid}/members")
def add_members(gid: int, body: MembersAdd, conn=Depends(get_db)):
    return svc.add_members(conn, gid, body.contact_ids)


@router.post("/api/groups/{gid}/members/csv")
async def add_members_csv(gid: int, file: UploadFile = File(...), apply: bool = False, conn=Depends(get_db),
                          cfg=Depends(settings)):
    """Add people from a CSV (URL column). apply=false previews; apply=true adds them."""
    data = await file.read(cfg.max_upload_bytes + 1)
    if len(data) > cfg.max_upload_bytes:
        raise AppError(413, "File is larger than 25 MB. Is this the right file?")
    if apply:  # keep one copy per upload: the preview and the confirm send the same file
        uploads.save_upload(cfg.data_dir, "group-members", file.filename, data)
    return svc.add_from_csv(conn, gid, data, apply)


@router.delete("/api/groups/{gid}/members/{cid}", status_code=204)
def remove_member(gid: int, cid: int, conn=Depends(get_db)):
    svc.remove_member(conn, gid, cid)


@router.patch("/api/groups/{gid}/members/{cid}")
def patch_member(gid: int, cid: int, body: MemberPatch, conn=Depends(get_db)):
    return svc.update_member(conn, gid, cid, {k: getattr(body, k) for k in body.model_fields_set})


@router.get("/api/groups/{gid}/stage-counts")
def stage_counts(gid: int, conn=Depends(get_db)):
    return svc.stage_counts(conn, gid)


@router.get("/api/groups/{gid}/stages")
def list_stages(gid: int, conn=Depends(get_db)):
    return pipelines.list_stages(conn, gid)


@router.post("/api/groups/{gid}/stages", status_code=201)
def add_stages(gid: int, body: StageCreate, conn=Depends(get_db)):
    return pipelines.add_stages(conn, gid, body.name, body.names, body.is_final)


@router.patch("/api/stages/{sid}")
def patch_stage(sid: int, body: StagePatch, conn=Depends(get_db)):
    return pipelines.update_stage(conn, sid, body.name, body.is_final, body.position)


@router.delete("/api/stages/{sid}")
def delete_stage(sid: int, move_to: int | None = None, clear: bool = False, conn=Depends(get_db)):
    return pipelines.delete_stage(conn, sid, move_to, clear)


@router.post("/api/groups/{gid}/pipeline")
def apply_pipeline(gid: int, body: ApplyPipeline, conn=Depends(get_db)):
    return pipelines.apply_template(conn, gid, body.template_id, body.preview, body.mapping)


@router.delete("/api/groups/{gid}/pipeline")
def remove_pipeline(gid: int, confirm: bool = False, conn=Depends(get_db)):
    return pipelines.remove_pipeline(conn, gid, confirm)
