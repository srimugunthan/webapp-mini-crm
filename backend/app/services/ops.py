import csv
import io

from ..errors import AppError
from ..repositories import contacts as crepo
from ..repositories import groups as grepo

BASE_COLS = ["First Name", "Last Name", "URL", "Email Address", "Company", "Position", "Connected On"]


def _iso(ts):
    if ts is None:
        return ""
    import datetime
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def export_csv(conn, group_id=None, ids=None, filters=None) -> tuple[str, str]:
    if group_id is not None:
        g = grepo.get(conn, group_id)
        if not g:
            raise AppError(404, "Group not found")
        rows, name = grepo.members_export(conn, group_id, ids), g["name"] + ("-selected" if ids is not None else "")
    else:
        if ids is not None or filters:
            _, rows = crepo.list_contacts(conn, ids=ids, sort="name", offset=0, limit=10_000_000, **(filters or {}))
            name = "selected-contacts" if ids is not None else "filtered-contacts"
        else:
            rows, name = crepo.all_for_export(conn), "all-contacts"
    out = io.StringIO()
    w = csv.writer(out)
    extra = ["Stage"] if group_id is not None else []
    w.writerow(BASE_COLS + ["Last Visited (UTC)", "Last Messaged (UTC)"] + extra)
    for r in rows:
        line = [r["first_name"], r["last_name"], r["linkedin_url"], r["email"], r["company"], r["position"],
                r["connected_on"] or "", _iso(r["last_visited_at"]), _iso(r["last_messaged_at"])]
        if group_id is not None:
            line.append(r["stage_name"] or "")
        w.writerow(line)
    return out.getvalue(), name
