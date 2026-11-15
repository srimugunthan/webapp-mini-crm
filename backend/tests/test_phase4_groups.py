from tests.helpers import make_group, seed_contacts


def test_groups_crud_and_unique(client):
    g = client.post("/api/groups", json={"name": "Clients"})
    assert g.status_code == 201
    assert client.post("/api/groups", json={"name": "clients"}).status_code == 409
    assert client.post("/api/groups", json={"name": " "}).status_code == 422
    gid = g.json()["id"]
    assert client.patch(f"/api/groups/{gid}", json={"name": "Clients 2"}).json()["name"] == "Clients 2"
    other = make_group(client, "Other")
    assert client.patch(f"/api/groups/{other}", json={"name": "clients 2"}).status_code == 409
    lst = client.get("/api/groups").json()
    assert {x["name"]: x["member_count"] for x in lst} == {"Clients 2": 0, "Other": 0}


def test_add_members_idempotent_badges_and_filters(client):
    ids = seed_contacts(client, 4)
    gid = make_group(client)
    r = client.post(f"/api/groups/{gid}/members", json={"contact_ids": ids[:3]}).json()
    assert r == {"added": 3, "already_members": 0}
    r = client.post(f"/api/groups/{gid}/members", json={"contact_ids": ids[:4]}).json()
    assert r == {"added": 1, "already_members": 3}
    g2 = make_group(client, "G2")
    client.post(f"/api/groups/{g2}/members", json={"contact_ids": [ids[0]]})
    c = client.get(f"/api/contacts/{ids[0]}").json()
    assert sorted(g["name"] for g in c["groups"]) == ["G", "G2"]  # many groups per contact
    assert client.get("/api/contacts?no_group=true").json()["total"] == 0
    assert client.post(f"/api/groups/{gid}/members", json={"contact_ids": [9999]}).status_code == 404


def test_remove_member_keeps_contact_and_delete_group_cascades(client):
    ids = seed_contacts(client, 3)
    gid = make_group(client)
    client.post(f"/api/groups/{gid}/members", json={"contact_ids": ids})
    assert client.delete(f"/api/groups/{gid}/members/{ids[0]}").status_code == 204
    assert client.get(f"/api/contacts/{ids[0]}").status_code == 200
    assert client.get(f"/api/groups/{gid}").json()["member_count"] == 2
    assert client.delete(f"/api/groups/{gid}").status_code == 204
    assert client.get("/api/contacts").json()["total"] == 3
    assert client.get("/api/contacts?no_group=true").json()["total"] == 3
    assert client.get(f"/api/groups/{gid}").status_code == 404


def test_group_members_table_sort_filters(client, fake_now):
    ids = seed_contacts(client, 4)
    gid = make_group(client)
    client.post(f"/api/groups/{gid}/members", json={"contact_ids": ids})
    fake_now["t"] += 100 * 86400
    client.get(f"/go/{ids[0]}")  # visited now
    client.post(f"/api/contacts/{ids[1]}/messaged")
    m = client.get(f"/api/groups/{gid}/members").json()
    assert m["total"] == 4 and m["items"][0]["linkedin_url"].startswith("https://")
    nv = client.get(f"/api/groups/{gid}/members?not_visited_days=30").json()
    assert {i["contact_id"] for i in nv["items"]} == set(ids[1:])
    nm = client.get(f"/api/groups/{gid}/members?not_messaged_days=30").json()
    assert {i["contact_id"] for i in nm["items"]} == {ids[0], ids[2], ids[3]}
    desc = client.get(f"/api/groups/{gid}/members?sort=name&order=desc").json()["items"]
    assert [i["first_name"] for i in desc] == ["F3", "F2", "F1", "F0"]
    assert client.get(f"/api/groups/{gid}/members?q=F2").json()["total"] == 1


def _csv_upload(client, gid, text, apply):
    return client.post(f"/api/groups/{gid}/members/csv?apply={'true' if apply else 'false'}",
                       files={"file": ("m.csv", text.encode(), "text/csv")})


def test_add_members_from_csv_preview_then_apply(client):
    ids = seed_contacts(client, 5)
    gid = make_group(client)
    client.post(f"/api/groups/{gid}/members", json={"contact_ids": [ids[0]]})
    text = ("URL\nhttps://www.linkedin.com/in/p0\nhttps://linkedin.com/in/P1/\nhttps://www.linkedin.com/in/p2\n"
            "https://www.linkedin.com/in/p2\nhttps://www.linkedin.com/in/nobody\n")
    pv = _csv_upload(client, gid, text, False).json()
    assert (pv["to_add"], pv["already_members"], pv["not_found"], pv["applied"]) == (2, 1, 1, False)
    assert client.get(f"/api/groups/{gid}").json()["member_count"] == 1  # preview changes nothing
    ap = _csv_upload(client, gid, text, True).json()
    assert ap["added"] == 2 and ap["applied"] is True
    assert client.get(f"/api/groups/{gid}").json()["member_count"] == 3
    assert _csv_upload(client, gid, text, True).json()["added"] == 0  # idempotent
    assert client.get("/api/contacts").json()["total"] == 5  # never creates contacts


def test_add_members_from_csv_with_pipeline_starts_at_first_stage_and_rejects_bad_file(client):
    seed_contacts(client, 2)
    gid = make_group(client, "P", 1)
    _csv_upload(client, gid, "URL\nhttps://www.linkedin.com/in/p0\n", True)
    m = client.get(f"/api/groups/{gid}/members").json()["items"]
    assert m[0]["stage_name"] == "Connected"
    assert _csv_upload(client, gid, "a,b\n1,2\n", False).status_code == 400
    assert _csv_upload(client, 999, "URL\nx\n", False).status_code == 404
