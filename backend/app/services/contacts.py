from datetime import datetime

from .. import clock
from ..errors import AppError
from ..repositories import contacts as repo
from ..urlnorm import is_redirectable

PREFETCH_HEADERS = (("sec-purpose", "prefetch"), ("purpose", "prefetch"), ("x-moz", "prefetch"),
                    ("x-purpose", "preview"), ("sec-purpose", "prerender"))


def contact_dict(r, groups=None):
    d = {k: r[k] for k in r.keys()}
    if groups is not None:
        d["groups"] = groups
    return d


def list_contacts(conn, **kw):
    total, rows = repo.list_contacts(conn, **kw)
    groups = repo.groups_for(conn, [r["id"] for r in rows])
    return {"items": [contact_dict(r, groups[r["id"]]) for r in rows], "total": total,
            "offset": kw.get("offset", 0), "limit": kw.get("limit", 100)}


def require(conn, contact_id):
    r = repo.get(conn, contact_id)
    if not r:
        raise AppError(404, "Contact not found")
    return r


def detail(conn, contact_id):
    r = require(conn, contact_id)
    d = contact_dict(r, repo.groups_for(conn, [contact_id])[contact_id])
    d["memberships"] = [dict(m) for m in repo.memberships_for(conn, contact_id)]
    d["history"] = [dict(h) for h in repo.history_for(conn, contact_id)]
    d["notes"] = [dict(n) for n in repo.list_notes(conn, contact_id)]
    return d


def is_prefetch(headers) -> bool:
    low = {k.lower(): v.lower() for k, v in headers.items()}
    return any(h in low and val in low[h] for h, val in PREFETCH_HEADERS)


def visit(conn, contact_id, headers) -> str:
    r = require(conn, contact_id)
    if not is_redirectable(r["linkedin_url"]):
        raise AppError(400, "Stored URL is not an https linkedin.com address; refusing to redirect.")
    if not is_prefetch(headers):
        repo.touch_visit(conn, contact_id, clock.now())
    return r["linkedin_url"]


def local_noon(date_str: str) -> int:
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise AppError(422, "Date must be YYYY-MM-DD")
    return int(d.replace(hour=12).timestamp())


def mark_messaged(conn, ids, date_str=None):
    ts = local_noon(date_str) if date_str else clock.now()
    for i in ids:
        require(conn, i)
    repo.set_messaged(conn, ids, ts)
    return ts


def add_note(conn, contact_id, body):
    require(conn, contact_id)
    body = body.strip()
    if not body:
        raise AppError(422, "Note cannot be empty")
    return dict(repo.add_note(conn, contact_id, body, clock.now()))


def notes(conn, contact_id):
    require(conn, contact_id)
    return [dict(n) for n in repo.list_notes(conn, contact_id)]
