import csv
import io
import sqlite3

from tests.conftest import do_import
from tests.helpers import make_group, seed_contacts


def test_export_all_roundtrips_through_importer(client):
    ids = seed_contacts(client, 3)
    r = client.get("/api/export")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows) == 3 and rows[0]["URL"].startswith("https://www.linkedin.com/in/")
    # re-import the export: all URLs match -> updates only, nothing new
    s = do_import(client, r.content).json()
    assert s["new"] == 0 and s["updated"] == 3


def test_export_group_scope_and_stage(client):
    ids = seed_contacts(client, 4)
    gid = make_group(client, "My Group!", 1)
    client.post(f"/api/groups/{gid}/members", json={"contact_ids": ids[:2]})
    r = client.get(f"/api/export?group_id={gid}")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows) == 2 and {x["Stage"] for x in rows} == {"Connected"}
    assert "My_Group_.csv" in r.headers["content-disposition"]
    assert client.get("/api/export?group_id=999").status_code == 404


def test_backup_download_is_valid_sqlite(client, tmp_path):
    seed_contacts(client, 5)
    r = client.get("/api/backup")
    assert r.status_code == 200
    out = tmp_path / "b.sqlite"
    out.write_bytes(r.content)
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0] == 5
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_backup_cli(settings, client, tmp_path, monkeypatch):
    seed_contacts(client, 2)
    from app import cli
    monkeypatch.setenv("DB_PATH", str(settings.db_path))
    monkeypatch.setenv("DATA_DIR", str(settings.data_dir))
    dest = tmp_path / "cli.sqlite"
    assert cli.main(["backup", str(dest)]) == 0
    assert sqlite3.connect(dest).execute("SELECT COUNT(*) FROM contacts").fetchone()[0] == 2
    assert cli.main([]) == 2


def test_export_selected_ids_and_filtered(client):
    seed_contacts(client, 6)
    all_ids = client.get("/api/contacts/ids").json()
    assert all_ids["total"] == 6 and len(all_ids["ids"]) == 6
    pick = all_ids["ids"][:2]
    r = client.get(f"/api/export?ids={pick[0]},{pick[1]}")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows) == 2 and "selected-contacts.csv" in r.headers["content-disposition"]
    assert client.get("/api/export?ids=").text.count("\n") == 1  # empty selection -> header only
    do_import(client, __import__("tests.conftest", fromlist=["make_csv"]).make_csv(
        ["Z,Zed,https://www.linkedin.com/in/zed,,Sarvam AI,Eng,01 Jan 2024"]))
    r = client.get("/api/export?company=sarvam")
    assert len(list(csv.DictReader(io.StringIO(r.text)))) == 1 and "filtered-contacts" in r.headers["content-disposition"]
    assert client.get("/api/contacts/ids?company=sarvam").json()["total"] == 1


def test_export_group_with_selected_ids_only_includes_ticked_members(client):
    ids = seed_contacts(client, 4)
    gid = make_group(client, "Team", 1)
    client.post(f"/api/groups/{gid}/members", json={"contact_ids": ids[:3]})
    r = client.get(f"/api/export?group_id={gid}&ids={ids[0]},{ids[2]},{ids[3]}")  # ids[3] is not a member
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows) == 2 and {x["Stage"] for x in rows} == {"Connected"}
    assert "Team-selected.csv" in r.headers["content-disposition"]
    assert len(list(csv.DictReader(io.StringIO(client.get(f"/api/export?group_id={gid}").text)))) == 3
