import time

from app.db import connect
from tests.conftest import csv_fixture, do_import, make_csv


def test_import_new_contacts_fixture(client):
    r = do_import(client, csv_fixture("Connections.csv"))
    assert r.status_code == 200
    s = r.json()
    assert s["new"] == 4 and s["updated"] == 0 and s["errors"] == []
    assert len(s["skipped"]) == 1 and s["skipped"][0]["name"] == "Ravi Kumar"
    items = client.get("/api/contacts").json()["items"]
    names = {(i["first_name"], i["company"]) for i in items}
    assert ("李", "北京公司") in names and ("Ünal", "Acme") in names
    priya = next(i for i in items if i["first_name"] == "Priya")
    assert priya["position"] == "VP, Engineering"
    assert priya["linkedin_url"] == "https://www.linkedin.com/in/priya-nair"
    assert priya["connected_on"] == "2023-10-28"
    unal = next(i for i in items if i["first_name"] == "Ünal")
    assert unal["position"] == 'Dir "Ops"'


def test_bom_file(client):
    assert do_import(client, csv_fixture("bom.csv")).json()["new"] == 4


def test_missing_columns_changes_nothing(client):
    r = do_import(client, csv_fixture("bad_columns.csv"))
    assert r.status_code == 400
    assert client.get("/api/contacts").json()["total"] == 0


def test_optional_columns_missing_ok(client):
    data = b"First Name,Last Name,URL\nA,B,https://linkedin.com/in/ab\n"
    assert do_import(client, data).json()["new"] == 1


def test_size_cap(client, settings):
    big = b"x" * (25 * 1024 * 1024 + 10)
    r = do_import(client, big)
    assert r.status_code == 413


def test_error_rolls_back_everything(client, monkeypatch):
    from app.repositories import contacts as repo
    calls = {"n": 0}
    real = repo.insert

    def flaky(conn, f, now):
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("boom")
        return real(conn, f, now)

    monkeypatch.setattr(repo, "insert", flaky)
    r = do_import(client, csv_fixture("Connections.csv"))
    assert r.status_code == 500 and "nothing was changed" in r.json()["detail"]
    assert client.get("/api/contacts").json()["total"] == 0


def test_reimport_updates_and_preserves(client, settings):
    do_import(client, csv_fixture("Connections.csv"))
    cid = client.get("/api/contacts?q=Asha").json()["items"][0]["id"]
    client.get(f"/go/{cid}")
    client.post(f"/api/contacts/{cid}/messaged")
    data = make_csv(["Asha,Rao,https://linkedin.com/in/asha-rao,new@x.com,NewCo,CEO,02 Nov 2024"])
    s = do_import(client, data).json()
    assert s["new"] == 0 and s["updated"] == 1
    c = client.get(f"/api/contacts/{cid}").json()
    assert c["company"] == "NewCo" and c["email"] == "new@x.com"
    assert c["last_visited_at"] and c["last_messaged_at"]
    assert client.get("/api/contacts").json()["total"] == 4  # others kept (FR-11)


def test_folder_import_endpoint_is_gone(client):
    assert client.post("/api/import/folder").status_code in (404, 405)


def test_uploaded_csv_is_saved_in_data_folder(client, settings, fake_now):
    original = csv_fixture("Connections.csv")
    assert do_import(client, original).status_code == 200
    saved = sorted(settings.data_dir.glob("*.csv"))
    assert len(saved) == 1 and saved[0].name.startswith("import-") and saved[0].name.endswith("-Connections.csv")
    assert saved[0].read_bytes() == original
    # a second upload of the same file at the same second never overwrites the first
    do_import(client, original)
    assert len(list(settings.data_dir.glob("*.csv"))) == 2


def test_rejected_upload_is_still_kept_and_unsafe_names_are_sanitised(client, settings):
    r = client.post("/api/import", files={"file": ("../../evil name!.CSV", b"a,b\n1,2\n", "text/csv")})
    assert r.status_code == 400  # not a connections file; nothing imported
    (saved,) = list(settings.data_dir.glob("*.csv"))
    assert saved.parent == settings.data_dir and saved.name.endswith("-evil_name.csv") and ".." not in saved.name


def test_import_still_works_when_data_folder_is_not_writable(client, settings):
    import shutil
    shutil.rmtree(settings.data_dir)
    settings.data_dir.write_text("a file, not a folder")  # mkdir/write will fail
    r = do_import(client, csv_fixture("Connections.csv"))
    assert r.status_code == 200 and r.json()["new"] == 4


def test_other_csv_uploads_are_saved_too(client, settings):
    from tests.helpers import make_group, seed_contacts
    seed_contacts(client, 2)
    gid = make_group(client, "G", 1)
    client.post(f"/api/groups/{gid}/members/csv?apply=true", files={"file": ("people.csv", b"URL\nhttps://www.linkedin.com/in/p0\n", "text/csv")})
    stage = client.get(f"/api/groups/{gid}/stages").json()[0]["id"]
    client.post(f"/api/groups/{gid}/bulk-stage?preview=true", files={"file": ("b.csv", b"URL\nhttps://www.linkedin.com/in/p0\n", "text/csv")}, data={"stage_id": str(stage)})
    kinds = sorted(p.name.split("-")[0] + "-" + p.name.split("-")[1] for p in settings.data_dir.glob("*.csv"))
    assert any(n.startswith("group") for n in kinds) and any(n.startswith("bulk") for n in kinds)


def _seed(client, n=30):
    rows = [f"F{i:03d},L{(n - i):03d},https://www.linkedin.com/in/p{i},,Co{i % 3},Role{i % 2},0{1 + i % 9} Jan {2018 + i % 4}"
            for i in range(n)]
    do_import(client, make_csv(rows))


def test_list_paging_and_sort(client):
    _seed(client, 30)
    p1 = client.get("/api/contacts?limit=10&offset=0").json()
    assert p1["total"] == 30 and len(p1["items"]) == 10
    p3 = client.get("/api/contacts?limit=10&offset=20").json()
    assert len(p3["items"]) == 10
    asc = client.get("/api/contacts?sort=company&order=asc&limit=100").json()["items"]
    assert [i["company"] for i in asc] == sorted(i["company"] for i in asc)
    desc = client.get("/api/contacts?sort=name&order=desc&limit=3").json()["items"]
    assert desc[0]["first_name"] == "F029"


def test_search_and_filters(client):
    _seed(client, 30)
    assert client.get("/api/contacts?q=f005").json()["total"] == 1
    assert client.get("/api/contacts?q=Co1").json()["total"] == 10
    assert client.get("/api/contacts?company=co2&position=role1").json()["total"] == 5
    year = client.get("/api/contacts?year=2018").json()["total"]
    assert year == len([i for i in range(30) if 2018 + i % 4 == 2018])
    assert client.get("/api/contacts?never_visited=true").json()["total"] == 30
    cid = client.get("/api/contacts?q=f001").json()["items"][0]["id"]
    client.get(f"/go/{cid}")
    client.post(f"/api/contacts/{cid}/messaged")
    assert client.get("/api/contacts?never_visited=true").json()["total"] == 29
    assert client.get("/api/contacts?never_messaged=true").json()["total"] == 29
    assert client.get("/api/contacts?no_group=true").json()["total"] == 30
    assert client.get("/api/contacts?q=%25").json()["total"] == 0  # LIKE wildcard is escaped


def test_perf_10k(client, settings):
    rows = [f"First{i},Last{i},https://www.linkedin.com/in/user{i},u{i}@x.com,Company{i % 500},Position {i % 50},0{1 + i % 9} Feb {2015 + i % 9}"
            for i in range(10000)]
    data = make_csv(rows)
    t = time.perf_counter()
    assert do_import(client, data).json()["new"] == 10000
    import_s = time.perf_counter() - t
    t = time.perf_counter()
    client.get("/api/contacts?sort=last_visited_at&limit=100")
    client.get("/api/contacts?q=Company42&limit=100")
    client.get("/api/contacts?offset=9900&limit=100&sort=company")
    list_s = (time.perf_counter() - t) / 3
    print(f"\nPERF import_10k={import_s:.2f}s list_avg={list_s:.3f}s")
    assert import_s < 10 and list_s < 1


# ---- add vs fresh import
def _fresh(client, data, confirm="RESET"):
    q = "?mode=fresh" + (f"&confirm={confirm}" if confirm else "")
    return client.post(f"/api/import{q}", files={"file": ("Connections.csv", data, "text/csv")})


def _populate(client):
    from tests.helpers import make_group
    do_import(client, csv_fixture("Connections.csv"))
    ids = [c["id"] for c in client.get("/api/contacts").json()["items"]]
    gid = make_group(client, "Keep?", 1)
    client.post(f"/api/groups/{gid}/members", json={"contact_ids": ids[:2]})
    client.post(f"/api/contacts/{ids[0]}/notes", json={"body": "note"})
    client.post("/api/pipelines", json={"name": "Custom", "stages": [{"name": "x"}, {"name": "y"}]})
    client.patch("/api/pipelines/1", json={"name": "Renamed starter"})
    return ids, gid


def test_stats_endpoint(client):
    _populate(client)
    s = client.get("/api/import/stats").json()
    assert s["contacts"] == 4 and s["groups"] == 1 and s["memberships"] == 2 and s["notes"] == 1
    assert s["templates"] == 2


def test_fresh_import_requires_the_typed_confirmation(client):
    ids, gid = _populate(client)
    assert _fresh(client, csv_fixture("Connections.csv"), confirm=None).status_code == 400
    assert _fresh(client, csv_fixture("Connections.csv"), confirm="yes").status_code == 400
    assert client.post("/api/import?mode=bogus", files={"file": ("a.csv", b"x", "text/csv")}).status_code == 422
    assert client.get("/api/contacts").json()["total"] == 4 and client.get("/api/groups").json()[0]["member_count"] == 2


def test_fresh_import_wipes_everything_then_loads_the_file(client, settings):
    ids, gid = _populate(client)
    new = make_csv(["Zed,One,https://www.linkedin.com/in/zed1,,NewCo,Eng,01 Jan 2025",
                    "Yan,Two,https://www.linkedin.com/in/yan2,,NewCo,Eng,02 Jan 2025"])
    r = _fresh(client, new)
    assert r.status_code == 200
    j = r.json()
    assert j["fresh"] is True and j["new"] == 2 and j["updated"] == 0
    assert j["deleted"]["contacts"] == 4 and j["deleted"]["groups"] == 1 and j["deleted"]["notes"] == 1
    assert client.get("/api/contacts").json()["total"] == 2
    assert client.get("/api/groups").json() == []
    assert client.get("/api/import/stats").json()["notes"] == 0
    assert client.get("/api/import/stats").json()["stage_history"] == 0
    # complete reset: custom/renamed templates are gone and the default Starter is back
    tpls = client.get("/api/pipelines").json()
    assert [t["name"] for t in tpls] == ["Starter"] and [s["name"] for s in tpls[0]["stages"]] == [
        "Connected", "Reached out", "In conversation", "Closed"] and tpls[0]["stages"][3]["is_final"]
    # a backup of the old database was written first and still holds the old data
    import sqlite3
    (bk,) = list((settings.db_path.parent / "backups").glob("pre-fresh-import-*.sqlite"))
    assert j["backup"] == bk.name
    assert sqlite3.connect(bk).execute("SELECT COUNT(*) FROM contacts").fetchone()[0] == 4
    # the uploaded file is kept in the data folder with its kind in the name
    assert any(p.name.startswith("import-fresh-") for p in settings.data_dir.glob("*.csv"))


def test_fresh_import_with_a_bad_file_changes_nothing(client):
    _populate(client)
    assert _fresh(client, b"Foo,Bar\n1,2\n").status_code == 400  # parse failure happens before the wipe
    assert client.get("/api/contacts").json()["total"] == 4


def test_fresh_import_failure_midway_rolls_the_wipe_back(client, monkeypatch):
    _populate(client)
    from app.repositories import contacts as repo
    real = repo.insert
    n = {"i": 0}

    def flaky(conn, f, now):
        n["i"] += 1
        if n["i"] == 2:
            raise RuntimeError("boom")
        return real(conn, f, now)
    monkeypatch.setattr(repo, "insert", flaky)
    r = _fresh(client, csv_fixture("Connections.csv"))
    assert r.status_code == 500
    monkeypatch.undo()
    assert client.get("/api/contacts").json()["total"] == 4 and client.get("/api/groups").json()[0]["member_count"] == 2
    assert sorted(t["name"] for t in client.get("/api/pipelines").json()) == ["Custom", "Renamed starter"]  # wipe rolled back too


def test_add_mode_is_the_default_and_keeps_everything(client, settings):
    ids, gid = _populate(client)
    s = client.post("/api/import", files={"file": ("Connections.csv", make_csv(["N,P,https://www.linkedin.com/in/np,,Co,E,01 Jan 2025"]), "text/csv")}).json()
    assert s["fresh"] is False and s["new"] == 1 and "deleted" not in s
    assert client.get("/api/contacts").json()["total"] == 5 and len(client.get("/api/groups").json()) == 1
    assert any(p.name.startswith("import-add-") for p in settings.data_dir.glob("*.csv"))


# ---- optional group name on import (decision 80)
def _import_to_group(client, rows, group=None, header=True):
    q = f"?group={group}" if group is not None else ""
    return client.post(f"/api/import{q}", files={"file": ("following.csv", make_csv(rows), "text/csv")})


def test_import_with_group_name_creates_group_and_adds_everyone(client):
    do_import(client, csv_fixture("Connections.csv"))  # 4 existing connections, no groups
    rows = ["Fay,Ito,https://www.linkedin.com/in/fay,,Zed,Writer,01 Jan 2025",
            "Gus,Lee,https://www.linkedin.com/in/gus,,Zed,Editor,01 Jan 2025"]
    r = _import_to_group(client, rows, group="Following")
    assert r.status_code == 200
    j = r.json()
    assert j["new"] == 2 and j["group"]["name"] == "Following" and j["group"]["created"] is True and j["group"]["added"] == 2
    # contacts page shows everyone: the 4 connections plus the 2 people followed
    assert client.get("/api/contacts").json()["total"] == 6
    g = client.get("/api/groups").json()
    assert [(x["name"], x["member_count"], x["stage_count"]) for x in g] == [("Following", 2, 0)]  # no pipeline
    members = client.get(f"/api/groups/{g[0]['id']}/members").json()["items"]
    assert sorted(m["first_name"] for m in members) == ["Fay", "Gus"]
    # the existing connections are NOT in the group
    assert client.get("/api/contacts?group=Following").json()["total"] == 2


def test_import_without_group_name_is_unchanged(client):
    r = _import_to_group(client, ["Hal,Ng,https://www.linkedin.com/in/hal,,Co,Eng,01 Jan 2025"])
    assert "group" not in r.json() and client.get("/api/groups").json() == []
    r = _import_to_group(client, ["Ivy,Oh,https://www.linkedin.com/in/ivy,,Co,Eng,01 Jan 2025"], group="   ")
    assert "group" not in r.json() and client.get("/api/groups").json() == []  # blank name = no group


def test_group_name_reuses_an_existing_group_case_insensitively_and_is_idempotent(client):
    rows = ["Fay,Ito,https://www.linkedin.com/in/fay,,Zed,Writer,01 Jan 2025"]
    _import_to_group(client, rows, group="Following")
    r = _import_to_group(client, rows + ["Gus,Lee,https://www.linkedin.com/in/gus,,Zed,Editor,01 Jan 2025"], group="following").json()
    assert r["group"]["created"] is False and r["group"]["name"] == "Following"
    assert r["group"]["added"] == 1 and r["group"]["already_members"] == 1 and r["updated"] == 1 and r["new"] == 1
    assert len(client.get("/api/groups").json()) == 1


def test_people_already_in_contacts_are_added_to_the_group_too_and_keep_their_data(client):
    do_import(client, csv_fixture("Connections.csv"))
    asha = client.get("/api/contacts?q=Asha").json()["items"][0]["id"]
    client.post(f"/api/contacts/{asha}/notes", json={"body": "keep"})
    r = _import_to_group(client, ["Asha,Rao,https://www.linkedin.com/in/asha-rao,,NewCo,CEO,02 Nov 2024"], group="Following").json()
    assert r["updated"] == 1 and r["new"] == 0 and r["group"]["added"] == 1
    c = client.get(f"/api/contacts/{asha}").json()
    assert c["company"] == "NewCo" and len(c["notes"]) == 1 and [g["name"] for g in c["groups"]] == ["Following"]


def test_existing_pipelined_group_puts_new_members_at_its_first_stage(client):
    from tests.helpers import make_group
    make_group(client, "Pipelined", 1)
    r = _import_to_group(client, ["Jo,Pu,https://www.linkedin.com/in/jo,,Co,Eng,01 Jan 2025"], group="pipelined").json()
    assert r["group"]["added"] == 1
    gid = r["group"]["id"]
    assert client.get(f"/api/groups/{gid}/members").json()["items"][0]["stage_name"] == "Connected"


def test_group_not_created_when_the_import_fails_and_name_is_validated(client, monkeypatch):
    from app.repositories import contacts as repo
    real, n = repo.insert, {"i": 0}

    def flaky(conn, f, now):
        n["i"] += 1
        if n["i"] == 2:
            raise RuntimeError("boom")
        return real(conn, f, now)
    monkeypatch.setattr(repo, "insert", flaky)
    rows = ["A,A,https://www.linkedin.com/in/a1,,Co,E,01 Jan 2025", "B,B,https://www.linkedin.com/in/b1,,Co,E,01 Jan 2025"]
    assert _import_to_group(client, rows, group="Ghost").status_code == 500
    monkeypatch.undo()
    assert client.get("/api/groups").json() == [] and client.get("/api/contacts").json()["total"] == 0
    assert _import_to_group(client, rows[:1], group="x" * 101).status_code == 422
    assert client.get("/api/contacts").json()["total"] == 0
    # a bad file does not create the group either
    assert client.post("/api/import?group=Nope", files={"file": ("a.csv", b"a,b\n1,2\n", "text/csv")}).status_code == 400
    assert client.get("/api/groups").json() == []
