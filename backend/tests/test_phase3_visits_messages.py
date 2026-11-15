import datetime

from tests.conftest import do_import, make_csv


def _contact(client, url="https://www.linkedin.com/in/asha"):
    do_import(client, make_csv([f"Asha,Rao,{url},,X,CTO,02 Nov 2024"]))
    return client.get("/api/contacts").json()["items"][0]["id"]


def test_go_updates_timestamp_and_redirects(client, fake_now):
    cid = _contact(client)
    r = client.get(f"/go/{cid}")
    assert r.status_code == 302 and r.headers["location"] == "https://www.linkedin.com/in/asha"
    assert client.get(f"/api/contacts/{cid}").json()["last_visited_at"] == fake_now["t"]


def test_go_prefetch_does_not_count(client):
    cid = _contact(client)
    for h in ({"Sec-Purpose": "prefetch"}, {"Purpose": "prefetch"}, {"X-Moz": "prefetch"}, {"Sec-Purpose": "prefetch;prerender"}):
        r = client.get(f"/go/{cid}", headers=h)
        assert r.status_code == 302
    assert client.get(f"/api/contacts/{cid}").json()["last_visited_at"] is None


def test_go_refuses_other_hosts(client, settings):
    cid = _contact(client, "https://evil.example.com/in/asha")
    r = client.get(f"/go/{cid}")
    assert r.status_code == 400
    assert client.get(f"/api/contacts/{cid}").json()["last_visited_at"] is None
    assert client.get("/go/9999").status_code == 404


def test_mark_messaged_now_and_date(client, fake_now):
    cid = _contact(client)
    client.post(f"/api/contacts/{cid}/messaged")
    assert client.get(f"/api/contacts/{cid}").json()["last_messaged_at"] == fake_now["t"]
    r = client.post(f"/api/contacts/{cid}/messaged", json={"date": "2024-10-01"})
    expected = int(datetime.datetime(2024, 10, 1, 12).timestamp())
    assert r.json()["last_messaged_at"] == expected
    assert client.post(f"/api/contacts/{cid}/messaged", json={"date": "nope"}).status_code == 422
    assert client.post("/api/contacts/999/messaged").status_code == 404


def test_visits_pending_endpoint_is_gone_and_bulk_messaged_still_works(client, fake_now):
    cid = _contact(client)
    assert client.get("/api/visits/pending").status_code == 404
    r = client.post("/api/contacts/messaged-bulk", json={"ids": [cid]})
    assert r.json()["last_messaged_at"] == fake_now["t"]
    assert client.get(f"/api/contacts/{cid}").json()["last_messaged_at"] == fake_now["t"]


def test_notes(client, fake_now):
    cid = _contact(client)
    assert client.get(f"/api/contacts/{cid}/notes").json() == []
    client.post(f"/api/contacts/{cid}/notes", json={"body": "met at conf"})
    fake_now["t"] += 5
    client.post(f"/api/contacts/{cid}/notes", json={"body": "follow up"})
    notes = client.get(f"/api/contacts/{cid}/notes").json()
    assert [n["body"] for n in notes] == ["follow up", "met at conf"] and notes[0]["created_at"] > notes[1]["created_at"]
    assert client.post(f"/api/contacts/{cid}/notes", json={"body": "  "}).status_code == 422
    # survives re-import
    do_import(client, make_csv(["Asha,Rao,https://www.linkedin.com/in/asha,,NewCo,CEO,02 Nov 2024"]))
    assert len(client.get(f"/api/contacts/{cid}").json()["notes"]) == 2
