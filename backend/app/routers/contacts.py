from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ..services import contacts as svc
from .deps import get_db

router = APIRouter(tags=["contacts"])


class MessagedBody(BaseModel):
    date: str | None = None  # YYYY-MM-DD, local noon


class BulkMessagedBody(BaseModel):
    ids: list[int]
    date: str | None = None


class NoteBody(BaseModel):
    body: str


@router.get("/api/contacts")
def list_contacts(q: str | None = None, company: str | None = None, position: str | None = None,
                  year: int | None = None, never_visited: bool = False, never_messaged: bool = False,
                  no_group: bool = False, group: str | None = None, sort: str = "name", order: str = "asc",
                  offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), conn=Depends(get_db)):
    return svc.list_contacts(conn, q=q, company=company, position=position, year=year,
                             never_visited=never_visited, never_messaged=never_messaged, no_group=no_group, group=group,
                             sort=sort, order=order, offset=offset, limit=limit)


@router.get("/api/contacts/ids")
def contact_ids(q: str | None = None, company: str | None = None, position: str | None = None,
                year: int | None = None, never_visited: bool = False, never_messaged: bool = False,
                no_group: bool = False, group: str | None = None, conn=Depends(get_db)):
    """Ids of every contact matching the filters (across all pages), for 'select all N matching'."""
    total, rows = svc.repo.list_contacts(conn, q=q, company=company, position=position, year=year,
                                         never_visited=never_visited, never_messaged=never_messaged,
                                         no_group=no_group, group=group, offset=0, limit=10_000_000)
    return {"ids": [r["id"] for r in rows], "total": total}


@router.get("/api/contacts/{contact_id}")
def get_contact(contact_id: int, conn=Depends(get_db)):
    return svc.detail(conn, contact_id)


@router.post("/api/contacts/messaged-bulk")
def messaged_bulk(body: BulkMessagedBody, conn=Depends(get_db)):
    return {"last_messaged_at": svc.mark_messaged(conn, body.ids, body.date)}


@router.post("/api/contacts/{contact_id}/messaged")
def messaged(contact_id: int, body: MessagedBody | None = None, conn=Depends(get_db)):
    return {"last_messaged_at": svc.mark_messaged(conn, [contact_id], body.date if body else None)}


@router.get("/api/contacts/{contact_id}/notes")
def get_notes(contact_id: int, conn=Depends(get_db)):
    return svc.notes(conn, contact_id)


@router.post("/api/contacts/{contact_id}/notes", status_code=201)
def post_note(contact_id: int, body: NoteBody, conn=Depends(get_db)):
    return svc.add_note(conn, contact_id, body.body)


@router.get("/go/{contact_id}")
def go(contact_id: int, request: Request, conn=Depends(get_db)):
    target = svc.visit(conn, contact_id, request.headers)
    return RedirectResponse(target, status_code=302)
