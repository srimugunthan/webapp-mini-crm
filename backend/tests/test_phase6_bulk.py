import json

from tests.conftest import make_csv
from tests.helpers import make_group, seed_contacts


def _setup(client, n=6):
    ids = seed_contacts(client, n)
    gid = make_group(client, "G", 1)
    client.post(f"/api/groups/{gid}/members", json={"contact_ids": ids[:3]})
    stages = client.get(f"/api/groups/{gid}/stages").json()
    return gid, ids, stages


def url(i):
    return f"https://www.linkedin.com/in/p{i}"


def _csv(lines, header="URL"):
    return (header + "\n" + "\n".join(lines) + "\n").encode()


def _preview(client, gid, data, stage_id=None):
    form = {"stage_id": str(stage_id)} if stage_id else {}
    return client.post(f"/api/groups/{gid}/bulk-stage?preview=true", files={"file": ("b.csv", data, "text/csv")}, data=form)


def _apply(client, gid, token):
    return client.post(f"/api/groups/{gid}/bulk-stage", json={"token": token})


def test_preview_counts_categories_and_problems(client):
    gid, ids, st = _setup(client)
    reached = st[1]["id"]
    # p0 in group at Connected, p1 -> already at Reached out, p4 not in group, p9 no contact
    client.patch(f"/api/groups/{gid}/members/{ids[1]}", json={"stage_id": reached})
    data = _csv([url(0), url(1), url(4), url(9), "https://www.linkedin.com/in/P0/"])  # duplicate p0 collapses
    r = _preview(client, gid, data, reached)
    assert r.status_code == 200
    j = r.json()
    assert j["counts"] == {"move": 1, "no_change": 1, "add": 1, "not_found": 1, "unknown_stage": 0}
    assert [p["reason"] for p in j["problems"]] == ["URL not found in your contacts"]
    csv_text = client.get(f"/api/groups/{gid}/bulk-stage/{j['token']}/problems.csv").text
    assert "p9" in csv_text and "Reason" in csv_text
    # preview changed nothing
    assert client.get(f"/api/groups/{gid}/members").json()["total"] == 3


def test_stage_column_override_and_unknown(client):
    gid, ids, st = _setup(client)
    data = f"URL,Stage\n{url(0)},closed\n{url(1)},Nope\n{url(2)},\n".encode()
    j = _preview(client, gid, data, st[1]["id"]).json()
    assert j["counts"]["move"] == 2 and j["counts"]["unknown_stage"] == 1
    assert j["problems"][0]["reason"] == "Unknown stage name"
    assert _apply(client, gid, j["token"]).status_code == 200
    cur = {m["contact_id"]: m["stage_name"] for m in client.get(f"/api/groups/{gid}/members").json()["items"]}
    assert cur[ids[0]] == "Closed" and cur[ids[2]] == "Reached out" and cur[ids[1]] == "Connected"
    # no dropdown stage and no Stage column -> every row is a problem
    j = _preview(client, gid, _csv([url(0)])).json()
    assert j["counts"]["unknown_stage"] == 1


def test_apply_adds_moves_and_preserves_other_fields(client, fake_now):
    gid, ids, st = _setup(client)
    reached = st[1]["id"]
    client.post(f"/api/contacts/{ids[0]}/notes", json={"body": "keep me"})
    client.post(f"/api/contacts/{ids[0]}/messaged")
    client.patch(f"/api/groups/{gid}/members/{ids[0]}", json={"next_follow_up_at": 12345})
    client.patch(f"/api/groups/{gid}/members/{ids[1]}", json={"stage_id": reached})
    changed_at = {m["contact_id"]: m["stage_changed_at"] for m in client.get(f"/api/groups/{gid}/members").json()["items"]}
    fake_now["t"] += 1000
    j = _preview(client, gid, _csv([url(0), url(1), url(4)]), reached).json()
    r = _apply(client, gid, j["token"])
    assert r.json()["moved"] == 1 and r.json()["added"] == 1 and r.json()["unchanged"] == 1
    items = {m["contact_id"]: m for m in client.get(f"/api/groups/{gid}/members").json()["items"]}
    assert items[ids[0]]["stage_name"] == "Reached out" and items[ids[0]]["next_follow_up_at"] == 12345
    assert items[ids[1]]["stage_changed_at"] == changed_at[ids[1]]  # not reset
    assert items[ids[4]]["stage_name"] == "Reached out"
    c = client.get(f"/api/contacts/{ids[0]}").json()
    assert c["last_messaged_at"] and len(c["notes"]) == 1
    assert c["history"][0]["source"] == "bulk" and c["history"][0]["batch_id"]
    assert items[ids[2]]["stage_name"] == "Connected"  # not in CSV: untouched


def test_token_single_use_and_expiry(client, fake_now):
    gid, ids, st = _setup(client)
    j = _preview(client, gid, _csv([url(0)]), st[1]["id"]).json()
    assert _apply(client, gid, j["token"]).status_code == 200
    assert _apply(client, gid, j["token"]).status_code == 410
    j = _preview(client, gid, _csv([url(1)]), st[1]["id"]).json()
    fake_now["t"] += 31 * 60
    assert _apply(client, gid, j["token"]).status_code == 410
    assert _apply(client, gid, "bogus").status_code == 410


def test_stale_preview_aborts_everything(client):
    gid, ids, st = _setup(client)
    j = _preview(client, gid, _csv([url(0), url(1)]), st[1]["id"]).json()
    assert j["counts"]["move"] == 2
    client.patch(f"/api/groups/{gid}/members/{ids[0]}", json={"stage_id": st[1]["id"]})  # data changed
    r = _apply(client, gid, j["token"])
    assert r.status_code == 409 and "preview again" in r.json()["detail"]
    cur = {m["contact_id"]: m["stage_name"] for m in client.get(f"/api/groups/{gid}/members").json()["items"]}
    assert cur[ids[1]] == "Connected"  # nothing applied
    assert _apply(client, gid, j["token"]).status_code == 410  # token consumed


def test_apply_is_atomic(client, monkeypatch):
    gid, ids, st = _setup(client)
    j = _preview(client, gid, _csv([url(0), url(1), url(4)]), st[1]["id"]).json()
    from app.repositories import stages as srepo
    real, n = srepo.add_history, {"n": 0}

    def flaky(*a, **k):
        n["n"] += 1
        if n["n"] == 2:
            raise RuntimeError("boom")
        return real(*a, **k)
    monkeypatch.setattr(srepo, "add_history", flaky)
    import pytest
    with pytest.raises(RuntimeError):
        _apply(client, gid, j["token"])
    monkeypatch.undo()
    items = client.get(f"/api/groups/{gid}/members").json()
    assert items["total"] == 3 and {m["stage_name"] for m in items["items"]} == {"Connected"}
    assert client.get(f"/api/contacts/{ids[0]}").json()["history"] == []


def test_disabled_for_group_without_pipeline(client):
    ids = seed_contacts(client, 2)
    gid = make_group(client, "NoPipe")
    r = _preview(client, gid, _csv([url(0)]))
    assert r.status_code == 400


def test_undo_restores_and_removes_added(client):
    gid, ids, st = _setup(client)
    reached = st[1]["id"]
    j = _preview(client, gid, _csv([url(0), url(4)]), reached).json()
    _apply(client, gid, j["token"])
    assert client.get(f"/api/groups/{gid}/members").json()["total"] == 4
    r = client.post(f"/api/groups/{gid}/bulk-stage/undo")
    assert r.json() == {"restored": 1, "removed": 1}
    items = {m["contact_id"]: m["stage_name"] for m in client.get(f"/api/groups/{gid}/members").json()["items"]}
    assert ids[4] not in items and items[ids[0]] == "Connected"
    assert client.post(f"/api/groups/{gid}/bulk-stage/undo").status_code == 404  # already undone


def test_undo_refused_after_pipeline_change(client):
    gid, ids, st = _setup(client)
    j = _preview(client, gid, _csv([url(0)]), st[1]["id"]).json()
    _apply(client, gid, j["token"])
    t = client.post("/api/pipelines", json={"name": "T2", "stages": [{"name": "Connected"}, {"name": "Z"}]}).json()["id"]
    client.post(f"/api/groups/{gid}/pipeline", json={"template_id": t, "preview": False,
                                                    "mapping": {str(s["id"]): "Z" for s in st[1:]}})
    r = client.post(f"/api/groups/{gid}/bulk-stage/undo")
    assert r.status_code == 409 and "pipeline" in r.json()["detail"]


def test_preview_1000_rows_fast(client):
    import time
    ids = seed_contacts(client, 1000)
    gid = make_group(client, "Big", 1)
    st = client.get(f"/api/groups/{gid}/stages").json()
    data = _csv([url(i) for i in range(1000)])
    t = time.perf_counter()
    j = _preview(client, gid, data, st[1]["id"]).json()
    dt = time.perf_counter() - t
    print(f"\nPERF bulk_preview_1000={dt:.2f}s")
    assert j["counts"]["add"] == 1000 and dt < 3
