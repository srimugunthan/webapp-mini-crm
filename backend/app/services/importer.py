import time
from pathlib import Path

from .. import clock
from ..csvparse import parse_connections, parse_connected_on
from ..db import backup_to, tx
from ..errors import AppError
from ..repositories import contacts as repo
from ..repositories import groups as grepo
from ..repositories import stages as srepo
from ..urlnorm import normalize_url


FRESH_PHRASE = "RESET"


def stats(conn) -> dict:
    """What a fresh import would delete (shown in the confirmation)."""
    one = lambda sql: conn.execute(sql).fetchone()[0]  # noqa: E731
    return {"contacts": one("SELECT COUNT(*) FROM contacts"), "groups": one("SELECT COUNT(*) FROM groups"),
            "memberships": one("SELECT COUNT(*) FROM group_members"), "notes": one("SELECT COUNT(*) FROM notes"),
            "stage_history": one("SELECT COUNT(*) FROM stage_history"),
            "templates": one("SELECT COUNT(*) FROM pipeline_templates")}


def _backup_before_wipe(conn, backup_dir: Path, keep: int = 5) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(clock.now()))
    dest = Path(backup_dir) / f"pre-fresh-import-{stamp}.sqlite"
    n = 1
    while dest.exists():
        n += 1
        dest = Path(backup_dir) / f"pre-fresh-import-{stamp}-{n}.sqlite"
    backup_to(conn, dest)
    for old in sorted(Path(backup_dir).glob("pre-fresh-import-*.sqlite"), key=lambda p: p.stat().st_mtime)[:-keep]:
        old.unlink()
    return dest.name


STARTER_STAGES = [("Connected", 0), ("Reached out", 0), ("In conversation", 0), ("Closed", 1)]


def _wipe(conn):
    """Complete reset: delete all connections, groups and pipeline templates, then re-create the default Starter
    template exactly as a brand-new install has it (migration 006)."""
    conn.execute("DELETE FROM groups")              # cascades: members, stages, stage history, bulk staging and batches
    conn.execute("DELETE FROM contacts")            # cascades: notes, any remaining memberships/history
    conn.execute("DELETE FROM pipeline_templates")  # cascades: template stages
    conn.execute("INSERT INTO pipeline_templates (id, name) VALUES (1, 'Starter')")
    for pos, (name, final) in enumerate(STARTER_STAGES):
        conn.execute("INSERT INTO pipeline_template_stages (template_id, name, position, is_final) VALUES (1, ?, ?, ?)",
                     (name, pos, final))


def import_csv(conn, data: bytes, fresh: bool = False, backup_dir: Path | None = None, group: str | None = None) -> dict:
    """Import a connections CSV. All-or-nothing.

    fresh=False adds new people and updates existing ones by URL (nothing is deleted).
    fresh=True first deletes all contacts, groups, stages, notes, history and pipeline templates (re-seeding the default Starter) in the SAME transaction, so a failed
    import leaves the old data untouched. A backup of the database is written first.

    group (optional): every person in the file with a valid URL (new or already known) is also put in this group,
    which is created if it does not exist (case-insensitive match otherwise). A new group has no pipeline; members of
    an existing pipelined group start at its first stage. Group creation and membership are part of the same
    transaction, so a failed import creates nothing.
    """
    group = (group or "").strip() or None
    if group and len(group) > 100:
        raise AppError(422, "Group name is too long (100 characters at most).")
    records = parse_connections(data)  # raises AppError(400) before touching the DB
    now = clock.now()
    summary = {"new": 0, "updated": 0, "skipped": [], "errors": [], "fresh": fresh}
    if fresh:
        summary["deleted"] = stats(conn)
        summary["backup"] = _backup_before_wipe(conn, backup_dir) if backup_dir else None
    try:
        with tx(conn):
            if fresh:
                _wipe(conn)
            gid, first_stage = None, None
            if group:
                existing_group = grepo.find_by_name(conn, group)
                gid = existing_group["id"] if existing_group else grepo.insert(conn, group, now)
                stages = srepo.group_stages(conn, gid)
                first_stage = stages[0]["id"] if stages else None
                summary["group"] = {"id": gid, "name": existing_group["name"] if existing_group else group,
                                    "created": existing_group is None, "added": 0, "already_members": 0}
            for line, v in records:
                url = normalize_url(v.get("url"))
                if not url:
                    summary["skipped"].append({"row": line, "reason": "missing URL",
                                               "name": f"{v.get('first_name', '')} {v.get('last_name', '')}".strip()})
                    continue
                fields = {
                    "first_name": v.get("first_name", ""), "last_name": v.get("last_name", ""),
                    "company": v.get("company", ""), "position": v.get("position", ""),
                    "email": v.get("email", ""), "connected_on": parse_connected_on(v.get("connected_on", "")),
                    "linkedin_url": url,
                }
                existing = repo.find_by_url(conn, url)
                if existing:
                    repo.update_import_fields(conn, existing["id"], fields, now)
                    summary["updated"] += 1
                    cid = existing["id"]
                else:
                    cid = repo.insert(conn, fields, now)
                    summary["new"] += 1
                if gid is not None:
                    if grepo.get_member(conn, gid, cid):
                        summary["group"]["already_members"] += 1
                    else:
                        grepo.add_member(conn, gid, cid, first_stage, now)
                        summary["group"]["added"] += 1
    except AppError:
        raise
    except Exception as e:  # noqa: BLE001 - rolled back by tx(); report which row
        raise AppError(500, f"Import failed and nothing was changed: {e}")
    return summary
