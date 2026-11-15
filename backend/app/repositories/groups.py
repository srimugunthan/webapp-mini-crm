from .contacts import like


def list_groups(conn):
    return conn.execute(
        "SELECT g.id, g.name, g.created_at,"
        " (SELECT COUNT(*) FROM group_members m WHERE m.group_id = g.id) AS member_count,"
        " (SELECT COUNT(*) FROM stages s WHERE s.group_id = g.id) AS stage_count"
        " FROM groups g ORDER BY g.name COLLATE NOCASE").fetchall()


def get(conn, gid):
    return conn.execute(
        "SELECT g.*, (SELECT COUNT(*) FROM group_members m WHERE m.group_id = g.id) AS member_count,"
        " (SELECT COUNT(*) FROM stages s WHERE s.group_id = g.id) AS stage_count FROM groups g WHERE g.id=?",
        (gid,)).fetchone()


def name_taken(conn, name, exclude_id=None):
    return conn.execute("SELECT 1 FROM groups WHERE name = ? COLLATE NOCASE AND id IS NOT ?",
                        (name, exclude_id)).fetchone() is not None


def find_by_name(conn, name):
    return conn.execute("SELECT * FROM groups WHERE name = ? COLLATE NOCASE", (name,)).fetchone()


def insert(conn, name, now):
    return conn.execute("INSERT INTO groups (name, created_at) VALUES (?,?)", (name, now)).lastrowid


def rename(conn, gid, name):
    conn.execute("UPDATE groups SET name=? WHERE id=?", (name, gid))


def delete(conn, gid):
    conn.execute("DELETE FROM groups WHERE id=?", (gid,))


def bump_epoch(conn, gid):
    conn.execute("UPDATE groups SET pipeline_epoch = pipeline_epoch + 1 WHERE id=?", (gid,))


def get_member(conn, gid, cid):
    return conn.execute("SELECT * FROM group_members WHERE group_id=? AND contact_id=?", (gid, cid)).fetchone()


def add_member(conn, gid, cid, stage_id, now):
    conn.execute("INSERT INTO group_members (group_id, contact_id, added_at, stage_id, stage_changed_at)"
                 " VALUES (?,?,?,?,?)", (gid, cid, now, stage_id, now if stage_id else None))


def remove_member(conn, gid, cid):
    return conn.execute("DELETE FROM group_members WHERE group_id=? AND contact_id=?", (gid, cid)).rowcount


def set_member_stage(conn, gid, cid, stage_id, now):
    conn.execute("UPDATE group_members SET stage_id=?, stage_changed_at=? WHERE group_id=? AND contact_id=?",
                 (stage_id, now if stage_id else None, gid, cid))


def set_follow_up(conn, gid, cid, ts):
    conn.execute("UPDATE group_members SET next_follow_up_at=? WHERE group_id=? AND contact_id=?", (ts, gid, cid))


MEMBER_SORTS = {
    "name": "c.first_name COLLATE NOCASE {o}, c.last_name COLLATE NOCASE {o}",
    "company": "c.company COLLATE NOCASE {o}",
    "position": "c.position COLLATE NOCASE {o}",
    "last_visited_at": "c.last_visited_at {o}",
    "last_messaged_at": "c.last_messaged_at {o}",
    "stage": "s.position {o}",
    "next_follow_up_at": "gm.next_follow_up_at {o}",
}


def list_members(conn, gid, now, stage=None, q=None, not_visited_days=None, not_messaged_days=None,
                 overdue=False, hide_final=False, sort="name", order="asc", offset=0, limit=100):
    where, args = ["gm.group_id = ?"], [gid]
    if stage == "none":
        where.append("gm.stage_id IS NULL")
    elif stage:
        where.append("gm.stage_id = ?")
        args.append(int(stage))
    elif hide_final:
        where.append("(s.id IS NULL OR s.is_final = 0)")
    if q:
        where.append("(c.first_name || ' ' || c.last_name LIKE ? ESCAPE '\\' OR c.company LIKE ? ESCAPE '\\'"
                     " OR c.position LIKE ? ESCAPE '\\')")
        args += [like(q)] * 3
    if not_visited_days is not None:
        where.append("(c.last_visited_at IS NULL OR c.last_visited_at < ?)")
        args.append(now - not_visited_days * 86400)
    if not_messaged_days is not None:
        where.append("(c.last_messaged_at IS NULL OR c.last_messaged_at < ?)")
        args.append(now - not_messaged_days * 86400)
    if overdue:
        where.append("gm.next_follow_up_at IS NOT NULL AND gm.next_follow_up_at < ?")
        args.append(now)
    base = (" FROM group_members gm JOIN contacts c ON c.id = gm.contact_id"
            " LEFT JOIN stages s ON s.id = gm.stage_id WHERE " + " AND ".join(where))
    if sort == "days_in_stage":
        # more days in stage == older stage_changed_at; stage-less members sort last
        o = "ASC" if order == "desc" else "DESC"
        order_sql = f"gm.stage_changed_at IS NULL, gm.stage_changed_at {o}"
    else:
        o = "DESC" if order == "desc" else "ASC"
        order_sql = MEMBER_SORTS.get(sort, MEMBER_SORTS["name"]).format(o=o)
    total = conn.execute("SELECT COUNT(*)" + base, args).fetchone()[0]
    sql = ("SELECT c.id AS contact_id, c.first_name, c.last_name, c.company, c.position, c.linkedin_url,"
           " c.last_visited_at, c.last_messaged_at, gm.stage_id, s.name AS stage_name, s.is_final AS stage_is_final,"
           " gm.stage_changed_at, gm.next_follow_up_at, gm.added_at,"
           " CASE WHEN gm.stage_changed_at IS NULL THEN NULL ELSE CAST((? - gm.stage_changed_at) / 86400 AS INTEGER) END"
           " AS days_in_stage" + base + f" ORDER BY {order_sql}, c.id")
    params = [now] + args
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params += [limit, offset]
    return total, conn.execute(sql, params).fetchall()


def stage_counts(conn, gid):
    return conn.execute(
        "SELECT s.id AS stage_id, s.name, s.is_final, COUNT(gm.contact_id) AS count FROM stages s"
        " LEFT JOIN group_members gm ON gm.stage_id = s.id AND gm.group_id = s.group_id"
        " WHERE s.group_id=? GROUP BY s.id ORDER BY s.position", (gid,)).fetchall()


def count_members(conn, gid):
    return conn.execute("SELECT COUNT(*) FROM group_members WHERE group_id=?", (gid,)).fetchone()[0]


def count_unstaged(conn, gid):
    return conn.execute("SELECT COUNT(*) FROM group_members WHERE group_id=? AND stage_id IS NULL", (gid,)).fetchone()[0]


def members_export(conn, gid, ids=None):
    sql = ("SELECT c.*, s.name AS stage_name FROM group_members gm JOIN contacts c ON c.id = gm.contact_id"
           " LEFT JOIN stages s ON s.id = gm.stage_id WHERE gm.group_id=?")
    args = [gid]
    if ids is not None:  # only members of this group that were ticked
        sql += " AND c.id IN (%s)" % (",".join("?" * len(ids)) or "NULL")
        args += list(ids)
    return conn.execute(sql + " ORDER BY c.last_name COLLATE NOCASE, c.first_name COLLATE NOCASE", args).fetchall()
