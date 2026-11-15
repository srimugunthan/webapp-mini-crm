from .. import clock
from ..db import tx
from ..errors import AppError
from ..repositories import groups as grepo
from ..repositories import stages as repo


def _group(conn, gid):
    g = grepo.get(conn, gid)
    if not g:
        raise AppError(404, "Group not found")
    return g


def _stage(conn, sid):
    s = repo.get(conn, sid)
    if not s:
        raise AppError(404, "Stage not found")
    return s


def stage_dict(r):
    return {"id": r["id"], "group_id": r["group_id"], "name": r["name"], "position": r["position"],
            "is_final": bool(r["is_final"])}


def list_stages(conn, gid):
    _group(conn, gid)
    return [stage_dict(s) for s in repo.group_stages(conn, gid)]


def _name(n):
    n = (n or "").strip()
    if not n:
        raise AppError(422, "Stage name cannot be empty")
    return n


def add_stages(conn, gid, name=None, names=None, is_final=False):
    """Add one stage, or append a pasted list (existing names are skipped)."""
    _group(conn, gid)
    to_add = [(_name(name), is_final)] if name is not None else [(_name(n), False) for n in (names or []) if n.strip()]
    if not to_add:
        raise AppError(422, "Give a stage name or a list of names")
    with tx(conn):
        pos = len(repo.group_stages(conn, gid))
        for n, fin in to_add:
            if repo.find_by_name(conn, gid, n):
                if name is not None:
                    raise AppError(409, f"Stage '{n}' already exists in this group")
                continue
            repo.insert(conn, gid, n, pos, fin)
            pos += 1
    return list_stages(conn, gid)


def update_stage(conn, sid, name=None, is_final=None, position=None):
    s = _stage(conn, sid)
    gid = s["group_id"]
    with tx(conn):
        if name is not None:
            n = _name(name)
            clash = repo.find_by_name(conn, gid, n)
            if clash and clash["id"] != sid:
                raise AppError(409, f"Stage '{n}' already exists in this group")
            repo.update(conn, sid, n, s["is_final"] if is_final is None else is_final)
        elif is_final is not None:
            repo.update(conn, sid, s["name"], is_final)
        if position is not None:
            ids = [x["id"] for x in repo.group_stages(conn, gid) if x["id"] != sid]
            ids.insert(max(0, min(position, len(ids))), sid)
            for i, i_id in enumerate(ids):
                repo.set_position(conn, i_id, i)
    return list_stages(conn, gid)


def delete_stage(conn, sid, move_to=None, clear=False):
    s = _stage(conn, sid)
    gid = s["group_id"]
    members = repo.member_ids_in_stage(conn, sid)
    target = None
    if members:
        if move_to is None and not clear:
            raise AppError(409, {"message": "Stage has members: choose a stage to move them to, or clear their stage.",
                                 "member_count": len(members)})
        if move_to is not None:
            target = _stage(conn, move_to)
            if target["group_id"] != gid or target["id"] == sid:
                raise AppError(422, "Target stage must be another stage of the same group")
    now = clock.now()
    with tx(conn):
        for cid in members:
            repo.add_history(conn, gid, cid, s, target, now, note="stage deleted")
            grepo.set_member_stage(conn, gid, cid, target["id"] if target else None, now)
        repo.delete(conn, sid)
        for i, x in enumerate(repo.group_stages(conn, gid)):
            repo.set_position(conn, x["id"], i)
        grepo.bump_epoch(conn, gid)
    return list_stages(conn, gid)


def move_member(conn, gid, cid, stage_id, note=None, source="manual", batch_id=None):
    """Stage move: membership update and history row in one transaction (FR-43)."""
    member = grepo.get_member(conn, gid, cid)
    to = None
    if stage_id is not None:
        to = _stage(conn, stage_id)
        if to["group_id"] != gid:
            raise AppError(422, "Stage does not belong to this group")
    frm = repo.get(conn, member["stage_id"]) if member["stage_id"] else None
    if (frm["id"] if frm else None) == (to["id"] if to else None):
        return False
    now = clock.now()
    with tx(conn):
        grepo.set_member_stage(conn, gid, cid, to["id"] if to else None, now)
        repo.add_history(conn, gid, cid, frm, to, now, source, batch_id, (note or "").strip() or None)
    return True


# ---- templates
def list_templates(conn):
    return repo.list_templates(conn)


def _clean_stage_list(stages):
    out, seen = [], set()
    for s in stages:
        n = _name(s["name"])
        if n.lower() in seen:
            raise AppError(422, f"Duplicate stage name '{n}'")
        seen.add(n.lower())
        out.append({"name": n, "is_final": bool(s.get("is_final"))})
    return out


def create_template(conn, name, stages=None, from_group_id=None):
    name = _name(name)
    if repo.template_name_taken(conn, name):
        raise AppError(409, f"A template named '{name}' already exists")
    if from_group_id is not None:
        _group(conn, from_group_id)
        stages = [{"name": s["name"], "is_final": bool(s["is_final"])} for s in repo.group_stages(conn, from_group_id)]
        if not stages:
            raise AppError(422, "That group has no stages to save")
    stages = _clean_stage_list(stages or [])
    if not stages:
        raise AppError(422, "A template needs at least one stage")
    with tx(conn):
        tid = repo.insert_template(conn, name, stages)
    return repo.get_template(conn, tid)


def rename_template(conn, tid, name):
    if not repo.get_template(conn, tid):
        raise AppError(404, "Template not found")
    name = _name(name)
    if repo.template_name_taken(conn, name, tid):
        raise AppError(409, f"A template named '{name}' already exists")
    repo.rename_template(conn, tid, name)
    return repo.get_template(conn, tid)


def delete_template(conn, tid):
    if not repo.get_template(conn, tid):
        raise AppError(404, "Template not found")
    repo.delete_template(conn, tid)


# ---- apply / remove pipeline on an existing group
def _plan_apply(conn, gid, template, mapping):
    t_names = {s["name"].lower(): s["name"] for s in template["stages"]}
    first = template["stages"][0]["name"]
    stage_rows = repo.group_stages(conn, gid)
    counts = {s["id"]: len(repo.member_ids_in_stage(conn, s["id"])) for s in stage_rows}
    mapped, unmatched = [], []
    for s in stage_rows:
        if not counts[s["id"]]:
            continue
        auto = t_names.get(s["name"].lower())
        choice = auto or (mapping or {}).get(str(s["id"]))
        entry = {"stage_id": s["id"], "stage_name": s["name"], "count": counts[s["id"]], "to": choice}
        if choice is not None and choice.lower() not in t_names:
            raise AppError(422, f"'{choice}' is not a stage of the template")
        (mapped if choice else unmatched).append(entry)
    no_stage = grepo.count_unstaged(conn, gid)
    return {"template_id": template["id"], "template_stages": [s["name"] for s in template["stages"]],
            "no_stage_to_first": no_stage, "first_stage": first, "mapped": mapped, "unmatched": unmatched}


def apply_template(conn, gid, template_id, preview=True, mapping=None):
    _group(conn, gid)
    template = repo.get_template(conn, template_id)
    if not template:
        raise AppError(404, "Template not found")
    plan = _plan_apply(conn, gid, template, mapping)
    if preview:
        return plan
    if plan["unmatched"]:
        raise AppError(422, {"message": "Choose a stage for every unmatched stage first.",
                             "unmatched": plan["unmatched"]})
    now = clock.now()
    old = {s["id"]: s for s in repo.group_stages(conn, gid)}
    members = conn.execute("SELECT contact_id, stage_id FROM group_members WHERE group_id=?", (gid,)).fetchall()
    with tx(conn):
        # detach members first, replace the group's stages with copies of the template's
        for m in members:
            grepo.set_member_stage(conn, gid, m["contact_id"], None, now)
        repo.delete_group_stages(conn, gid)
        new = {}
        for i, s in enumerate(template["stages"]):
            sid = repo.insert(conn, gid, s["name"], i, s["is_final"])
            new[s["name"].lower()] = repo.get(conn, sid)
        by_old = {e["stage_id"]: new[e["to"].lower()] for e in plan["mapped"]}
        first = new[template["stages"][0]["name"].lower()]
        for m in members:
            frm = old.get(m["stage_id"])
            to = by_old[m["stage_id"]] if frm else first
            grepo.set_member_stage(conn, gid, m["contact_id"], to["id"], now)
            repo.add_history(conn, gid, m["contact_id"], frm, to, now, note="pipeline applied")
        grepo.bump_epoch(conn, gid)
    return {"applied": True, **{k: plan[k] for k in ("no_stage_to_first", "first_stage")}}


def remove_pipeline(conn, gid, confirm=False):
    _group(conn, gid)
    staged = conn.execute("SELECT COUNT(*) FROM group_members WHERE group_id=? AND stage_id IS NOT NULL",
                          (gid,)).fetchone()[0]
    if not confirm:
        raise AppError(409, {"message": f"{staged} members will lose their stage. Confirm to continue.",
                             "members_losing_stage": staged})
    now = clock.now()
    old = {s["id"]: s for s in repo.group_stages(conn, gid)}
    members = conn.execute("SELECT contact_id, stage_id FROM group_members WHERE group_id=? AND stage_id IS NOT NULL",
                           (gid,)).fetchall()
    with tx(conn):
        for m in members:
            repo.add_history(conn, gid, m["contact_id"], old[m["stage_id"]], None, now, note="pipeline removed")
            grepo.set_member_stage(conn, gid, m["contact_id"], None, now)
        repo.delete_group_stages(conn, gid)
        grepo.bump_epoch(conn, gid)
    return {"removed": True, "members_lost_stage": staged}
