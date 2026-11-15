from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..services import pipelines
from .deps import get_db

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


class TemplateStage(BaseModel):
    name: str
    is_final: bool = False


class TemplateCreate(BaseModel):
    name: str
    stages: list[TemplateStage] | None = None
    from_group_id: int | None = None


class TemplateRename(BaseModel):
    name: str


@router.get("")
def list_templates(conn=Depends(get_db)):
    return pipelines.list_templates(conn)


@router.post("", status_code=201)
def create_template(body: TemplateCreate, conn=Depends(get_db)):
    stages = [s.model_dump() for s in body.stages] if body.stages else None
    return pipelines.create_template(conn, body.name, stages, body.from_group_id)


@router.patch("/{tid}")
def rename_template(tid: int, body: TemplateRename, conn=Depends(get_db)):
    return pipelines.rename_template(conn, tid, body.name)


@router.delete("/{tid}", status_code=204)
def delete_template(tid: int, conn=Depends(get_db)):
    pipelines.delete_template(conn, tid)
