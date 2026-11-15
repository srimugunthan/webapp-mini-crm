from .. import clock
from ..db import tx
from ..errors import AppError
from ..repositories import contacts as crepo
from ..repositories import groups as repo
from ..repositories import stages as srepo
from . import pipelines


def group_dict(r):
    return {k: r[k] for k in r.keys()}


def require(conn, gid):
    g = repo.get(conn, gid)
    if not g:
        raise AppError(404, "Group not found")
    return g


def _clean_name(name):
    name = (name or "").strip()
    if not name:
        raise AppError(422, "Group name cannot be empty")
    return name


def list_groups(conn):
    return [group_dict(r) for r in repo.list_groups(conn)]


def create(conn, name, template_id=None):
    name = _clean_name(name)
    if repo.name_taken(conn, name):
        raise AppError(409, f"A group named '{name}' already exists")
    template = None
    if template_id is not None:
        template = srepo.get_template(conn, template_id)
        if not template:
            raise AppError(404, "Pipeline template not found")
    with tx(conn):
        gid = repo.insert(conn, name, clock.now())
        if template:
            for i, s in enumerate(template["stages"]):  # copy-on-apply (ADR-004)
                srepo.insert(conn, gid, s["name"], i, s["is_final"])
    return group_dict(repo.get(conn, gid))


def rename(conn, gid, name):
    require(conn, gid)
    name = _clean_name(name)
    if repo.name_taken(conn, name, gid):
        raise AppError(409, f"A group named '{name}' already exists")
    repo.rename(conn, gid, name)
    return group_dict(repo.get(conn, gid))


def delete(conn, gid):
    require(conn, gid)
    repo.delete(conn, gid)


def add_members(conn, gid, contact_ids):
    require(conn, gid)
    stages = srepo.group_stages(conn, gid)
    first = stages[0]["id"] if stages else None
    now = clock.now()
    added = 0
    with tx(conn):
        for cid in dict.fromkeys(contact_ids):
            if not crepo.get(conn, cid):
                raise AppError(404, f"Contact {cid} not found")
            if repo.get_member(conn, gid, cid):
                continue
            repo.add_member(conn, gid, cid, first, now)
            added += 1
    return {"added": added, "already_members": len(set(contact_ids)) - added}


def add_from_csv(conn, gid, data: bytes, apply: bool):
    """Add people to a group from a CSV with a URL column (a LinkedIn export works as is).

    Matches contacts by normalized URL; never creates contacts. With apply=False it only reports what would happen.
    """
    from ..csvparse import read_rows
    from ..urlnorm import normalize_url

    require(conn, gid)
    rows = read_rows(data, {"url"}, {"url": "url"})
    to_add, already, problems, seen = [], 0, [], set()
    for line, v in rows:
        contact = crepo.find_by_url(conn, normalize_url(v.get("url"))) if normalize_url(v.get("url")) else None
        if not contact:
            problems.append({"row": line, "url": v.get("url", ""), "reason": "URL not found in your contacts"})
            continue
        if contact["id"] in seen:
            continue
        seen.add(contact["id"])
        if repo.get_member(conn, gid, contact["id"]):
            already += 1
        else:
            to_add.append(contact["id"])
    result = {"to_add": len(to_add), "already_members": already, "not_found": len(problems), "problems": problems,
              "applied": False, "added": 0}
    if apply and to_add:
        result["added"] = add_members(conn, gid, to_add)["added"]
    result["applied"] = apply
    return result


def remove_member(conn, gid, cid):
    require(conn, gid)
    if not repo.remove_member(conn, gid, cid):
        raise AppError(404, "Member not found")


def list_members(conn, gid, **kw):
    require(conn, gid)
    all_rows = kw.pop("all", False)
    if all_rows:
        kw["limit"], kw["offset"] = None, 0
    total, rows = repo.list_members(conn, gid, clock.now(), **kw)
    return {"items": [dict(r) for r in rows], "total": total}


def update_member(conn, gid, cid, fields: dict):
    require(conn, gid)
    if not repo.get_member(conn, gid, cid):
        raise AppError(404, "Member not found")
    if "stage_id" in fields:
        pipelines.move_member(conn, gid, cid, fields["stage_id"], fields.get("note"))
    if "next_follow_up_at" in fields:
        repo.set_follow_up(conn, gid, cid, fields["next_follow_up_at"])
    return {k: repo.get_member(conn, gid, cid)[k] for k in ("stage_id", "stage_changed_at", "next_follow_up_at")}


def stage_counts(conn, gid):
    require(conn, gid)
    return {"total": repo.count_members(conn, gid), "unstaged": repo.count_unstaged(conn, gid),
            "stages": [dict(r) for r in repo.stage_counts(conn, gid)]}
