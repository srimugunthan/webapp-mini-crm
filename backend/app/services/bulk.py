import csv
import io
import json
import secrets
import uuid

from .. import clock
from ..csvparse import read_rows
from ..db import tx
from ..errors import AppError
from ..repositories import contacts as crepo
from ..repositories import groups as grepo
from ..repositories import stages as srepo
from ..urlnorm import normalize_url
from . import pipelines

TOKEN_TTL = 30 * 60
COUNT_KEYS = ("move", "no_change", "add", "not_found", "unknown_stage")


def _group_with_stages(conn, gid):
    g = grepo.get(conn, gid)
    if not g:
        raise AppError(404, "Group not found")
    if not g["stage_count"]:
        raise AppError(400, "This group has no pipeline, so Bulk set stage is not available.")
    return g


def _classify_target(conn, gid, contact_id, stage_id):
    m = grepo.get_member(conn, gid, contact_id)
    if m is None:
        return "add"
    return "no_change" if m["stage_id"] == stage_id else "move"


def preview(conn, gid, data: bytes, stage_id=None):
    _group_with_stages(conn, gid)
    default = None
    if stage_id is not None:
        default = srepo.get(conn, stage_id)
        if not default or default["group_id"] != gid:
            raise AppError(422, "Chosen stage does not belong to this group")
    rows = read_rows(data, {"url"}, {"url": "url", "stage": "stage"})
    counts = {k: 0 for k in COUNT_KEYS}
    staged, problems, seen = {}, [], {}
    for line, v in rows:
        url = normalize_url(v.get("url"))
        stage_name = v.get("stage", "")
        problem = lambda reason: problems.append({"row": line, "url": v.get("url", ""), "stage": stage_name, "reason": reason})  # noqa: E731
        contact = crepo.find_by_url(conn, url) if url else None
        if not contact:
            counts["not_found"] += 1
            problem("URL not found in your contacts")
            continue
        if stage_name:
            st = srepo.find_by_name(conn, gid, stage_name)
        else:
            st = default
        if not st:
            counts["unknown_stage"] += 1
            problem("Unknown stage name" if stage_name else "No stage given")
            continue
        staged[contact["id"]] = {"contact_id": contact["id"], "stage_id": st["id"], "row": line}  # last row wins
    for r in staged.values():
        kind = _classify_target(conn, gid, r["contact_id"], r["stage_id"])
        counts[kind] += 1
    now = clock.now()
    token = secrets.token_urlsafe(16)
    with tx(conn):
        srepo.purge_staging(conn, now - TOKEN_TTL)
        srepo.save_staging(conn, token, gid, stage_id, json.dumps(list(staged.values())), json.dumps(problems),
                           json.dumps(counts), now)
    return {"token": token, "counts": counts, "problems": problems, "expires_in": TOKEN_TTL}


def problems_csv(conn, gid, token) -> str:
    row = srepo.get_staging(conn, token)
    if not row or row["group_id"] != gid:
        raise AppError(404, "Preview not found or expired")
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Row", "URL", "Stage", "Reason"])
    for p in json.loads(row["problems_json"]):
        w.writerow([p["row"], p["url"], p["stage"], p["reason"]])
    return out.getvalue()


def apply(conn, gid, token):
    _group_with_stages(conn, gid)
    now = clock.now()
    row = srepo.get_staging(conn, token)
    if not row or row["group_id"] != gid:
        raise AppError(410, "This preview was not found, already used, or expired. Please preview again.")
    if row["created_at"] < now - TOKEN_TTL:
        srepo.delete_staging(conn, token)
        raise AppError(410, "This preview expired. Please preview again.")
    staged = json.loads(row["rows_json"])
    expected = json.loads(row["counts_json"])
    batch_id = str(uuid.uuid4())
    stale = False
    try:
        with tx(conn):
            actions = []
            fresh = {"move": 0, "no_change": 0, "add": 0}
            for r in staged:  # re-classify inside the apply transaction (D34)
                st = srepo.get(conn, r["stage_id"])
                if not st or st["group_id"] != gid or not crepo.get(conn, r["contact_id"]):
                    stale = True
                    break
                kind = _classify_target(conn, gid, r["contact_id"], r["stage_id"])
                fresh[kind] += 1
                actions.append((kind, r, st))
            if not stale and any(fresh[k] != expected[k] for k in fresh):
                stale = True
            if stale:
                raise _Stale()
            epoch = grepo.get(conn, gid)["pipeline_epoch"]
            srepo.insert_batch(conn, batch_id, gid, epoch, now)
            for kind, r, st in actions:
                if kind == "no_change":
                    continue  # stage_changed_at is not reset (FR-54)
                if kind == "add":
                    grepo.add_member(conn, gid, r["contact_id"], st["id"], now)
                    srepo.add_history(conn, gid, r["contact_id"], None, st, now, "bulk", batch_id, added=1)
                else:
                    m = grepo.get_member(conn, gid, r["contact_id"])
                    frm = srepo.get(conn, m["stage_id"]) if m["stage_id"] else None
                    grepo.set_member_stage(conn, gid, r["contact_id"], st["id"], now)
                    srepo.add_history(conn, gid, r["contact_id"], frm, st, now, "bulk", batch_id)
            srepo.delete_staging(conn, token)
    except _Stale:
        srepo.delete_staging(conn, token)
        raise AppError(409, "Your data changed since the preview. Please preview again.")
    return {"batch_id": batch_id, "moved": fresh["move"], "added": fresh["add"], "unchanged": fresh["no_change"]}


class _Stale(Exception):
    pass


def undo(conn, gid):
    g = grepo.get(conn, gid)
    if not g:
        raise AppError(404, "Group not found")
    batch = srepo.last_batch(conn, gid)
    if not batch:
        raise AppError(404, "There is no bulk change to undo.")
    if batch["epoch"] != g["pipeline_epoch"]:
        raise AppError(409, "Cannot undo: the group's pipeline was changed after this bulk update.")
    now = clock.now()
    restored = removed = 0
    with tx(conn):
        for h in srepo.batch_history(conn, batch["batch_id"]):
            cid = h["contact_id"]
            if not grepo.get_member(conn, gid, cid):
                continue
            if h["added_to_group"]:
                grepo.remove_member(conn, gid, cid)
                removed += 1
                continue
            frm = srepo.get(conn, h["from_stage_id"]) if h["from_stage_id"] else None
            to = srepo.get(conn, h["to_stage_id"]) if h["to_stage_id"] else None
            grepo.set_member_stage(conn, gid, cid, frm["id"] if frm else None, now)
            srepo.add_history(conn, gid, cid, to, frm, now, "manual", None, "bulk undo")
            restored += 1
        srepo.mark_batch_undone(conn, batch["batch_id"], now)
    return {"restored": restored, "removed": removed}
