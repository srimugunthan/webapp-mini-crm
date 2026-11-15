import sqlite3

from tests.conftest import do_import, make_csv
from tests.helpers import make_group, seed_contacts


def _db_bytes(client):
    return client.get("/api/backup").content


def _restore(client, data, confirm="RESTORE"):
    q = f"?confirm={confirm}" if confirm else ""
    return client.post(f"/api/restore{q}", files={"file": ("backup.sqlite", data, "application/octet-stream")})


def _preview(client, data):
    return client.post("/api/restore/preview", files={"file": ("backup.sqlite", data, "application/octet-stream")})


def _state(client):
    return client.get("/api/contacts").json()["total"], [g["name"] for g in client.get("/api/groups").json()]


def test_restore_brings_back_the_backed_up_data(client, settings):
    ids = seed_contacts(client, 5)
    gid = make_group(client, "Original", 1)
    client.post(f"/api/groups/{gid}/members", json={"contact_ids": ids[:3]})
    client.post(f"/api/contacts/{ids[0]}/notes", json={"body": "keep"})
    backup = _db_bytes(client)
    # change things after the backup
    do_import(client, make_csv(["N,P,https://www.linkedin.com/in/np,,Co,E,01 Jan 2025"]))
    client.delete(f"/api/groups/{gid}")
    make_group(client, "Later")
    assert _state(client) == (6, ["Later"])
    r = _restore(client, backup)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["restored"] is True and j["contacts"] == 5 and j["groups"] == 1 and j["notes"] == 1 and j["upgraded"] is False
    assert _state(client) == (5, ["Original"])
    assert client.get(f"/api/groups/{gid}/members").json()["total"] == 3
    assert len(client.get(f"/api/contacts/{ids[0]}/notes").json()) == 1
    assert client.get("/api/health").json()["status"] == "ok"
    # a safety backup of the state before the restore was written, and holds the pre-restore data
    (bk,) = list((settings.db_path.parent / "backups").glob("pre-restore-*.sqlite"))
    assert j["safety_backup"] == bk.name
    assert sqlite3.connect(bk).execute("SELECT COUNT(*) FROM contacts").fetchone()[0] == 6
    # the app keeps working normally after the swap
    assert client.post(f"/api/groups", json={"name": "AfterRestore"}).status_code == 201


def test_confirmation_is_required(client):
    seed_contacts(client, 2)
    backup = _db_bytes(client)
    assert _restore(client, backup, confirm=None).status_code == 400
    assert _restore(client, backup, confirm="restore").status_code == 400
    assert not list((client.app.state.settings.db_path.parent / "backups").glob("pre-restore-*"))


def test_preview_describes_the_file_and_changes_nothing(client):
    seed_contacts(client, 4)
    backup = _db_bytes(client)
    do_import(client, make_csv(["N,P,https://www.linkedin.com/in/np,,Co,E,01 Jan 2025"]))
    pv = _preview(client, backup).json()
    assert pv["contacts"] == 4 and pv["needs_upgrade"] is False and pv["schema_version"] == pv["app_schema_version"]
    assert _state(client)[0] == 5


def test_rejects_files_that_are_not_a_valid_crm_backup(client, tmp_path):
    seed_contacts(client, 3)
    assert _restore(client, b"First Name,URL\n1,2\n").status_code == 400  # not sqlite
    other = tmp_path / "other.sqlite"
    c = sqlite3.connect(other); c.execute("CREATE TABLE t (x)"); c.commit(); c.close()
    r = _restore(client, other.read_bytes())
    assert r.status_code == 400 and "not made by LinkedIn Mini CRM" in r.json()["detail"]
    # truncated / corrupt database
    good = _db_bytes(client)
    assert _preview(client, good[: len(good) // 2]).status_code == 400
    assert _state(client)[0] == 3  # nothing changed by any rejected upload


def test_rejects_a_backup_from_a_newer_app_version(client, tmp_path):
    seed_contacts(client, 2)
    p = tmp_path / "newer.sqlite"
    p.write_bytes(_db_bytes(client))
    c = sqlite3.connect(p); c.execute("PRAGMA user_version = 999"); c.commit(); c.close()
    r = _restore(client, p.read_bytes())
    assert r.status_code == 400 and "newer version" in r.json()["detail"]
    assert _state(client)[0] == 2


def test_older_backup_is_restored_then_upgraded(client, tmp_path):
    seed_contacts(client, 3)
    p = tmp_path / "old.sqlite"
    p.write_bytes(_db_bytes(client))
    c = sqlite3.connect(p)
    c.executescript("DROP TABLE bulk_staging; DROP TABLE bulk_batches; PRAGMA user_version = 6;")
    c.commit(); c.close()
    assert _preview(client, p.read_bytes()).json()["needs_upgrade"] is True
    r = _restore(client, p.read_bytes())
    assert r.status_code == 200 and r.json()["upgraded"] is True and r.json()["schema_version"] == 7
    assert client.get("/api/health").json()["schema_version"] == 7
    gid = make_group(client, "G", 1)
    ids = [c["id"] for c in client.get("/api/contacts").json()["items"]]
    client.post(f"/api/groups/{gid}/members", json={"contact_ids": ids[:1]})
    st = client.get(f"/api/groups/{gid}/stages").json()[0]["id"]  # bulk tables exist again
    assert client.post(f"/api/groups/{gid}/bulk-stage?preview=true", files={"file": ("b.csv", b"URL\nhttps://www.linkedin.com/in/p0\n", "text/csv")}, data={"stage_id": str(st)}).status_code == 200
