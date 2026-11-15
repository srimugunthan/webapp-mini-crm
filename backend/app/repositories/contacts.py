SORTS = {
    "name": "first_name COLLATE NOCASE {o}, last_name COLLATE NOCASE {o}",
    "company": "company COLLATE NOCASE {o}",
    "position": "position COLLATE NOCASE {o}",
    "connected_on": "connected_on {o}",
    "last_visited_at": "last_visited_at {o}",
    "last_messaged_at": "last_messaged_at {o}",
}


def like(term: str) -> str:
    esc = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{esc}%"


def find_by_url(conn, url):
    return conn.execute("SELECT * FROM contacts WHERE linkedin_url = ?", (url,)).fetchone()


def get(conn, contact_id):
    return conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()


def insert(conn, f, now):
    cur = conn.execute(
        "INSERT INTO contacts (first_name, last_name, company, position, linkedin_url, email, connected_on,"
        " created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (f["first_name"], f["last_name"], f["company"], f["position"], f["linkedin_url"], f["email"],
         f["connected_on"], now, now),
    )
    return cur.lastrowid


def update_import_fields(conn, contact_id, f, now):
    conn.execute(
        "UPDATE contacts SET first_name=?, last_name=?, company=?, position=?, email=?, connected_on=?,"
        " updated_at=? WHERE id=?",
        (f["first_name"], f["last_name"], f["company"], f["position"], f["email"], f["connected_on"], now, contact_id),
    )


def list_contacts(conn, q=None, company=None, position=None, year=None, never_visited=False,
                  never_messaged=False, no_group=False, group=None, ids=None, sort="name", order="asc", offset=0, limit=100):
    where, args = [], []
    from .. import search  # boolean search (decision 79)
    for text, field in ((q, "any"), (company, "company"), (position, "position"), (group, "group")):
        built = search.build(text, field)
        if built:
            where.append(built[0])
            args += built[1]
    if year:
        where.append("connected_on LIKE ?")
        args.append(f"{int(year):04d}-%")
    if never_visited:
        where.append("last_visited_at IS NULL")
    if never_messaged:
        where.append("last_messaged_at IS NULL")
    if no_group:
        where.append("NOT EXISTS (SELECT 1 FROM group_members gm WHERE gm.contact_id = contacts.id)")
    if ids is not None:
        where.append("id IN (%s)" % (",".join("?" * len(ids)) or "NULL"))
        args += list(ids)
    w = (" WHERE " + " AND ".join(where)) if where else ""
    o = "DESC" if order == "desc" else "ASC"
    order_sql = SORTS.get(sort, SORTS["name"]).format(o=o) + ", id ASC"
    total = conn.execute(f"SELECT COUNT(*) FROM contacts{w}", args).fetchone()[0]
    rows = conn.execute(f"SELECT * FROM contacts{w} ORDER BY {order_sql} LIMIT ? OFFSET ?",
                        args + [limit, offset]).fetchall()
    return total, rows


def groups_for(conn, ids):
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    out = {i: [] for i in ids}
    for r in conn.execute(
        f"SELECT gm.contact_id, g.id, g.name FROM group_members gm JOIN groups g ON g.id = gm.group_id"
        f" WHERE gm.contact_id IN ({marks}) ORDER BY g.name", list(ids)):
        out[r["contact_id"]].append({"id": r["id"], "name": r["name"]})
    return out


def touch_visit(conn, contact_id, ts):
    conn.execute("UPDATE contacts SET last_visited_at=? WHERE id=?", (ts, contact_id))


def set_messaged(conn, ids, ts):
    conn.executemany("UPDATE contacts SET last_messaged_at=? WHERE id=?", [(ts, i) for i in ids])


def list_notes(conn, contact_id):
    return conn.execute("SELECT * FROM notes WHERE contact_id=? ORDER BY created_at DESC, id DESC",
                        (contact_id,)).fetchall()


def add_note(conn, contact_id, body, now):
    cur = conn.execute("INSERT INTO notes (contact_id, body, created_at) VALUES (?,?,?)", (contact_id, body, now))
    return conn.execute("SELECT * FROM notes WHERE id=?", (cur.lastrowid,)).fetchone()


def memberships_for(conn, contact_id):
    return conn.execute(
        "SELECT g.id AS group_id, g.name AS group_name, s.name AS stage_name, gm.stage_changed_at,"
        " gm.next_follow_up_at FROM group_members gm JOIN groups g ON g.id = gm.group_id"
        " LEFT JOIN stages s ON s.id = gm.stage_id WHERE gm.contact_id=? ORDER BY g.name", (contact_id,)).fetchall()


def history_for(conn, contact_id):
    return conn.execute(
        "SELECT h.*, g.name AS group_name FROM stage_history h JOIN groups g ON g.id = h.group_id"
        " WHERE h.contact_id=? ORDER BY h.changed_at DESC, h.id DESC", (contact_id,)).fetchall()


def all_for_export(conn):
    return conn.execute("SELECT * FROM contacts ORDER BY last_name COLLATE NOCASE, first_name COLLATE NOCASE").fetchall()
