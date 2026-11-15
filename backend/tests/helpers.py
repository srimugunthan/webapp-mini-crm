from tests.conftest import do_import, make_csv


def seed_contacts(client, n=6):
    rows = [f"F{i},L{i},https://www.linkedin.com/in/p{i},,Co,Role,01 Jan 2024" for i in range(n)]
    do_import(client, make_csv(rows))
    items = client.get("/api/contacts?limit=100").json()["items"]
    return [c["id"] for c in items]


def make_group(client, name="G", template_id=None):
    body = {"name": name}
    if template_id is not None:
        body["template_id"] = template_id
    return client.post("/api/groups", json=body).json()["id"]
