def group_stages(conn, gid):
    return conn.execute("SELECT * FROM stages WHERE group_id=? ORDER BY position", (gid,)).fetchall()


def get(conn, sid):
    return conn.execute("SELECT * FROM stages WHERE id=?", (sid,)).fetchone()


def find_by_name(conn, gid, name):
    return conn.execute("SELECT * FROM stages WHERE group_id=? AND name = ? COLLATE NOCASE", (gid, name)).fetchone()


def insert(conn, gid, name, position, is_final):
    return conn.execute("INSERT INTO stages (group_id, name, position, is_final) VALUES (?,?,?,?)",
                        (gid, name, position, 1 if is_final else 0)).lastrowid


def update(conn, sid, name, is_final):
    conn.execute("UPDATE stages SET name=?, is_final=? WHERE id=?", (name, 1 if is_final else 0, sid))


def set_position(conn, sid, pos):
    conn.execute("UPDATE stages SET position=? WHERE id=?", (pos, sid))


def delete(conn, sid):
    conn.execute("DELETE FROM stages WHERE id=?", (sid,))


def delete_group_stages(conn, gid):
    conn.execute("DELETE FROM stages WHERE group_id=?", (gid,))


def member_ids_in_stage(conn, sid):
    return [r[0] for r in conn.execute("SELECT contact_id FROM group_members WHERE stage_id=?", (sid,))]


def add_history(conn, gid, cid, from_stage, to_stage, now, source="manual", batch_id=None, note=None, added=0):
    conn.execute(
        "INSERT INTO stage_history (group_id, contact_id, from_stage_id, to_stage_id, from_stage_name,"
        " to_stage_name, changed_at, source, batch_id, added_to_group, note) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (gid, cid, from_stage["id"] if from_stage else None, to_stage["id"] if to_stage else None,
         from_stage["name"] if from_stage else None, to_stage["name"] if to_stage else None,
         now, source, batch_id, added, note))


# ---- templates
def list_templates(conn):
    out = []
    for t in conn.execute("SELECT * FROM pipeline_templates ORDER BY name COLLATE NOCASE"):
        stages = conn.execute("SELECT name, position, is_final FROM pipeline_template_stages WHERE template_id=?"
                              " ORDER BY position", (t["id"],)).fetchall()
        out.append({"id": t["id"], "name": t["name"], "stages": [dict(s) for s in stages]})
    return out


def get_template(conn, tid):
    for t in list_templates(conn):
        if t["id"] == tid:
            return t
    return None


def template_name_taken(conn, name, exclude=None):
    return conn.execute("SELECT 1 FROM pipeline_templates WHERE name = ? COLLATE NOCASE AND id IS NOT ?",
                        (name, exclude)).fetchone() is not None


def insert_template(conn, name, stages):
    tid = conn.execute("INSERT INTO pipeline_templates (name) VALUES (?)", (name,)).lastrowid
    for i, s in enumerate(stages):
        conn.execute("INSERT INTO pipeline_template_stages (template_id, name, position, is_final) VALUES (?,?,?,?)",
                     (tid, s["name"], i, 1 if s.get("is_final") else 0))
    return tid


def rename_template(conn, tid, name):
    conn.execute("UPDATE pipeline_templates SET name=? WHERE id=?", (name, tid))


def delete_template(conn, tid):
    conn.execute("DELETE FROM pipeline_templates WHERE id=?", (tid,))


# ---- bulk staging
def purge_staging(conn, cutoff):
    conn.execute("DELETE FROM bulk_staging WHERE created_at < ?", (cutoff,))


def save_staging(conn, token, gid, stage_id, rows_json, problems_json, counts_json, now):
    conn.execute("INSERT INTO bulk_staging (token, group_id, stage_id, rows_json, problems_json, counts_json,"
                 " created_at) VALUES (?,?,?,?,?,?,?)", (token, gid, stage_id, rows_json, problems_json, counts_json, now))


def get_staging(conn, token):
    return conn.execute("SELECT * FROM bulk_staging WHERE token=?", (token,)).fetchone()


def delete_staging(conn, token):
    conn.execute("DELETE FROM bulk_staging WHERE token=?", (token,))


def insert_batch(conn, batch_id, gid, epoch, now):
    conn.execute("INSERT INTO bulk_batches (batch_id, group_id, epoch, created_at) VALUES (?,?,?,?)",
                 (batch_id, gid, epoch, now))


def last_batch(conn, gid):
    return conn.execute("SELECT * FROM bulk_batches WHERE group_id=? AND undone_at IS NULL"
                        " ORDER BY created_at DESC, rowid DESC LIMIT 1", (gid,)).fetchone()


def mark_batch_undone(conn, batch_id, now):
    conn.execute("UPDATE bulk_batches SET undone_at=? WHERE batch_id=?", (now, batch_id))


def batch_history(conn, batch_id):
    return conn.execute("SELECT * FROM stage_history WHERE batch_id=? ORDER BY id", (batch_id,)).fetchall()
