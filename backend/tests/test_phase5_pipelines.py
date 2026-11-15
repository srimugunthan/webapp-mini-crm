from tests.helpers import make_group, seed_contacts

STARTER = 1


def _group_with_stages(client, names="A,B,C", members=3):
    ids = seed_contacts(client, members)
    gid = make_group(client)
    client.post(f"/api/groups/{gid}/stages", json={"names": names.split(",")})
    client.post(f"/api/groups/{gid}/members", json={"contact_ids": ids})
    stages = client.get(f"/api/groups/{gid}/stages").json()
    return gid, ids, stages


def test_stage_editor_crud_reorder_final(client):
    gid = make_group(client)
    assert client.post(f"/api/groups/{gid}/stages", json={"name": "One"}).status_code == 201
    r = client.post(f"/api/groups/{gid}/stages", json={"name": "Two", "is_final": True}).json()
    assert [s["name"] for s in r] == ["One", "Two"]
    assert client.post(f"/api/groups/{gid}/stages", json={"name": "one"}).status_code == 409  # unique, case-insens
    r = client.post(f"/api/groups/{gid}/stages", json={"names": ["Two", "Three", " Four "]}).json()
    assert [s["name"] for s in r] == ["One", "Two", "Three", "Four"]  # pasted list skips existing
    sid = r[3]["id"]
    r = client.patch(f"/api/stages/{sid}", json={"position": 0}).json()
    assert [s["name"] for s in r] == ["Four", "One", "Two", "Three"]
    r = client.patch(f"/api/stages/{sid}", json={"name": "Zero", "is_final": True}).json()
    assert r[0]["name"] == "Zero" and r[0]["is_final"] and r[2]["is_final"]  # several finals
    assert client.patch(f"/api/stages/{sid}", json={"name": "two"}).status_code == 409


def test_delete_stage_with_members_requires_choice(client):
    gid, ids, stages = _group_with_stages(client)
    a, b = stages[0]["id"], stages[1]["id"]
    assert all(m["stage_name"] == "A" for m in client.get(f"/api/groups/{gid}/members").json()["items"])
    r = client.delete(f"/api/stages/{a}")
    assert r.status_code == 409 and r.json()["detail"]["member_count"] == 3
    assert client.delete(f"/api/stages/{a}?move_to={a}").status_code == 422
    r = client.delete(f"/api/stages/{a}?move_to={b}")
    assert r.status_code == 200 and [s["name"] for s in r.json()] == ["B", "C"]
    assert {m["stage_name"] for m in client.get(f"/api/groups/{gid}/members").json()["items"]} == {"B"}
    # clearing
    assert client.delete(f"/api/stages/{b}?clear=true").status_code == 200
    assert {m["stage_id"] for m in client.get(f"/api/groups/{gid}/members").json()["items"]} == {None}
    h = client.get(f"/api/contacts/{ids[0]}").json()["history"]
    assert [x["to_stage_name"] for x in h] == [None, "B"] and h[1]["from_stage_name"] == "A"


def test_templates_starter_seed_and_create_group_copy(client):
    t = client.get("/api/pipelines").json()
    assert t[0]["name"] == "Starter" and [s["name"] for s in t[0]["stages"]] == [
        "Connected", "Reached out", "In conversation", "Closed"] and t[0]["stages"][3]["is_final"]
    gid = make_group(client, "WithPipe", STARTER)
    assert [s["name"] for s in client.get(f"/api/groups/{gid}/stages").json()] == [
        "Connected", "Reached out", "In conversation", "Closed"]
    none = make_group(client, "NoPipe")
    assert client.get(f"/api/groups/{none}/stages").json() == []
    # independence: editing group stage does not touch the template, deleting template does not touch group
    sid = client.get(f"/api/groups/{gid}/stages").json()[0]["id"]
    client.patch(f"/api/stages/{sid}", json={"name": "Renamed"})
    assert client.get("/api/pipelines").json()[0]["stages"][0]["name"] == "Connected"
    assert client.delete(f"/api/pipelines/{STARTER}").status_code == 204
    assert len(client.get(f"/api/groups/{gid}/stages").json()) == 4


def test_template_crud(client):
    r = client.post("/api/pipelines", json={"name": "Mine", "stages": [{"name": "x"}, {"name": "y", "is_final": True}]})
    assert r.status_code == 201
    tid = r.json()["id"]
    assert client.post("/api/pipelines", json={"name": "mine", "stages": [{"name": "x"}]}).status_code == 409
    assert client.post("/api/pipelines", json={"name": "Dup", "stages": [{"name": "x"}, {"name": "X"}]}).status_code == 422
    assert client.patch(f"/api/pipelines/{tid}", json={"name": "Renamed"}).json()["name"] == "Renamed"
    assert client.delete(f"/api/pipelines/{tid}").status_code == 204
    assert client.delete(f"/api/pipelines/{tid}").status_code == 404


def test_save_group_stages_as_template(client):
    gid, _, stages = _group_with_stages(client, "P,Q,R", 0)
    client.patch(f"/api/stages/{stages[2]['id']}", json={"is_final": True})
    r = client.post("/api/pipelines", json={"name": "FromGroup", "from_group_id": gid}).json()
    assert [(s["name"], s["is_final"]) for s in r["stages"]] == [("P", 0), ("Q", 0), ("R", 1)]
    client.post(f"/api/groups/{gid}/stages", json={"name": "S"})
    saved = next(t for t in client.get("/api/pipelines").json() if t["name"] == "FromGroup")
    assert len(saved["stages"]) == 3
    empty = make_group(client, "E")
    assert client.post("/api/pipelines", json={"name": "Nope", "from_group_id": empty}).status_code == 422


def test_member_move_history_days_and_atomic(client, fake_now, monkeypatch):
    gid, ids, stages = _group_with_stages(client)
    a, b = stages[0]["id"], stages[1]["id"]
    fake_now["t"] += 3 * 86400 + 5
    r = client.patch(f"/api/groups/{gid}/members/{ids[0]}", json={"stage_id": b, "note": " called "})
    assert r.json()["stage_id"] == b and r.json()["stage_changed_at"] == fake_now["t"]
    rows = {m["contact_id"]: m for m in client.get(f"/api/groups/{gid}/members").json()["items"]}
    assert rows[ids[0]]["days_in_stage"] == 0 and rows[ids[1]]["days_in_stage"] == 3
    s = client.get(f"/api/groups/{gid}/members?sort=days_in_stage&order=desc").json()["items"]
    assert s[-1]["contact_id"] == ids[0]
    h = client.get(f"/api/contacts/{ids[0]}").json()["history"]
    assert h[0]["from_stage_name"] == "A" and h[0]["to_stage_name"] == "B" and h[0]["note"] == "called"
    assert h[0]["source"] == "manual"
    # same-stage move is a no-op (no history, time not reset)
    client.patch(f"/api/groups/{gid}/members/{ids[0]}", json={"stage_id": b})
    assert len(client.get(f"/api/contacts/{ids[0]}").json()["history"]) == 1
    # stage from another group is rejected
    other = make_group(client, "O")
    client.post(f"/api/groups/{other}/stages", json={"name": "Z"})
    z = client.get(f"/api/groups/{other}/stages").json()[0]["id"]
    assert client.patch(f"/api/groups/{gid}/members/{ids[0]}", json={"stage_id": z}).status_code == 422
    # atomic: history failure rolls back the stage change
    from app.repositories import stages as srepo

    def boom(*a, **k):
        raise RuntimeError("history down")
    monkeypatch.setattr(srepo, "add_history", boom)
    import pytest
    with pytest.raises(RuntimeError):
        client.patch(f"/api/groups/{gid}/members/{ids[1]}", json={"stage_id": b})
    monkeypatch.undo()
    cur = {m["contact_id"]: m for m in client.get(f"/api/groups/{gid}/members").json()["items"]}
    assert cur[ids[1]]["stage_id"] == a


def test_stage_counts_filter_and_clear(client):
    gid, ids, stages = _group_with_stages(client, "A,B,C", 4)
    b = stages[1]["id"]
    client.patch(f"/api/groups/{gid}/members/{ids[0]}", json={"stage_id": b})
    client.patch(f"/api/groups/{gid}/members/{ids[1]}", json={"stage_id": None})
    c = client.get(f"/api/groups/{gid}/stage-counts").json()
    assert c["total"] == 4 and c["unstaged"] == 1
    assert [(s["name"], s["count"]) for s in c["stages"]] == [("A", 2), ("B", 1), ("C", 0)]
    assert client.get(f"/api/groups/{gid}/members?stage={b}").json()["total"] == 1
    assert client.get(f"/api/groups/{gid}/members?stage=none").json()["total"] == 1


def test_hide_final(client):
    gid, ids, stages = _group_with_stages(client, "A,Done", 3)
    client.patch(f"/api/stages/{stages[1]['id']}", json={"is_final": True})
    client.patch(f"/api/groups/{gid}/members/{ids[0]}", json={"stage_id": stages[1]["id"]})
    assert client.get(f"/api/groups/{gid}/members").json()["total"] == 3
    assert client.get(f"/api/groups/{gid}/members?hide_final=true").json()["total"] == 2
    # explicit stage filter still shows final members
    assert client.get(f"/api/groups/{gid}/members?hide_final=true&stage={stages[1]['id']}").json()["total"] == 1


def test_apply_template_preview_and_apply(client):
    ids = seed_contacts(client, 4)
    gid = make_group(client)
    client.post(f"/api/groups/{gid}/members", json={"contact_ids": ids})  # no pipeline: null stages
    # stage-less -> first stage
    pv = client.post(f"/api/groups/{gid}/pipeline", json={"template_id": STARTER, "preview": True}).json()
    assert pv["no_stage_to_first"] == 4 and pv["first_stage"] == "Connected" and pv["unmatched"] == []
    assert client.get(f"/api/groups/{gid}/stages").json() == []  # preview changes nothing
    r = client.post(f"/api/groups/{gid}/pipeline", json={"template_id": STARTER, "preview": False})
    assert r.status_code == 200
    assert {m["stage_name"] for m in client.get(f"/api/groups/{gid}/members").json()["items"]} == {"Connected"}
    assert len(client.get(f"/api/contacts/{ids[0]}").json()["history"]) == 1
    # switching to a template with partly different names: same-name maps, others need a choice
    stages = client.get(f"/api/groups/{gid}/stages").json()
    client.patch(f"/api/groups/{gid}/members/{ids[0]}", json={"stage_id": stages[1]["id"]})  # Reached out
    client.patch(f"/api/groups/{gid}/members/{ids[1]}", json={"stage_id": stages[2]["id"]})  # In conversation
    t = client.post("/api/pipelines", json={"name": "Other", "stages": [
        {"name": "connected"}, {"name": "Talking"}, {"name": "Won", "is_final": True}]}).json()["id"]
    pv = client.post(f"/api/groups/{gid}/pipeline", json={"template_id": t, "preview": True}).json()
    assert {u["stage_name"] for u in pv["unmatched"]} == {"Reached out", "In conversation"}
    assert [m["stage_name"] for m in pv["mapped"]] == ["Connected"] and pv["mapped"][0]["count"] == 2
    r = client.post(f"/api/groups/{gid}/pipeline", json={"template_id": t, "preview": False})
    assert r.status_code == 422
    mapping = {str(u["stage_id"]): "Talking" for u in pv["unmatched"]}
    r = client.post(f"/api/groups/{gid}/pipeline", json={"template_id": t, "preview": False, "mapping": mapping})
    assert r.status_code == 200
    cur = {m["contact_id"]: m["stage_name"] for m in client.get(f"/api/groups/{gid}/members").json()["items"]}
    assert cur[ids[0]] == "Talking" and cur[ids[1]] == "Talking" and cur[ids[2]] == "connected"
    assert [s["name"] for s in client.get(f"/api/groups/{gid}/stages").json()] == ["connected", "Talking", "Won"]
    hist = client.get(f"/api/contacts/{ids[0]}").json()["history"]
    assert hist[0]["from_stage_name"] == "Reached out" and hist[0]["to_stage_name"] == "Talking"


def test_remove_pipeline_requires_confirmation_keeps_history(client):
    ids = seed_contacts(client, 3)
    gid = make_group(client, "G", STARTER)
    client.post(f"/api/groups/{gid}/members", json={"contact_ids": ids})
    r = client.delete(f"/api/groups/{gid}/pipeline")
    assert r.status_code == 409 and r.json()["detail"]["members_losing_stage"] == 3
    assert len(client.get(f"/api/groups/{gid}/stages").json()) == 4
    r = client.delete(f"/api/groups/{gid}/pipeline?confirm=true")
    assert r.json() == {"removed": True, "members_lost_stage": 3}
    assert client.get(f"/api/groups/{gid}/stages").json() == []
    assert {m["stage_id"] for m in client.get(f"/api/groups/{gid}/members").json()["items"]} == {None}
    h = client.get(f"/api/contacts/{ids[0]}").json()["history"]
    assert h[0]["from_stage_name"] == "Connected" and h[0]["to_stage_name"] is None


def test_follow_up_dates_per_membership_and_overdue(client, fake_now):
    ids = seed_contacts(client, 3)
    g1, g2 = make_group(client, "G1"), make_group(client, "G2")
    for g in (g1, g2):
        client.post(f"/api/groups/{g}/members", json={"contact_ids": ids[:2]})
    past, future = fake_now["t"] - 86400, fake_now["t"] + 86400
    client.patch(f"/api/groups/{g1}/members/{ids[0]}", json={"next_follow_up_at": past})
    client.patch(f"/api/groups/{g1}/members/{ids[1]}", json={"next_follow_up_at": future})
    client.patch(f"/api/groups/{g2}/members/{ids[0]}", json={"next_follow_up_at": future})
    od = client.get(f"/api/groups/{g1}/members?overdue=true").json()
    assert [m["contact_id"] for m in od["items"]] == [ids[0]]
    assert client.get(f"/api/groups/{g2}/members?overdue=true").json()["total"] == 0
    client.patch(f"/api/groups/{g1}/members/{ids[0]}", json={"next_follow_up_at": None})
    assert client.get(f"/api/groups/{g1}/members?overdue=true").json()["total"] == 0
