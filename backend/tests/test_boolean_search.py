import pytest

from tests.conftest import do_import, make_csv
from tests.helpers import make_group

ROWS = [
    "Asha,Rao,https://www.linkedin.com/in/asha,,Google,Data Scientist,01 Jan 2024",
    "Ben,Kumar,https://www.linkedin.com/in/ben,,Google,Product Manager,01 Jan 2024",
    "Chen,Li,https://www.linkedin.com/in/chen,,Acme,Data Engineer,01 Jan 2024",
    "Dee,Nair,https://www.linkedin.com/in/dee,,Acme,Founder and CEO,01 Jan 2024",
    "Eli,Park,https://www.linkedin.com/in/eli,,Initech,Recruiter,01 Jan 2024",
]


@pytest.fixture
def world(client):
    do_import(client, make_csv(ROWS))
    ids = {c["first_name"]: c["id"] for c in client.get("/api/contacts?limit=100").json()["items"]}
    hr = make_group(client, "HR Leads")
    ml = make_group(client, "ML Team")
    hot = make_group(client, "Hot Prospects")
    for g, names in ((hr, ["Eli", "Dee"]), (ml, ["Asha", "Chen"]), (hot, ["Asha", "Dee", "Ben"])):
        client.post(f"/api/groups/{g}/members", json={"contact_ids": [ids[n] for n in names]})
    return client


def names(client, **params):
    from urllib.parse import urlencode
    r = client.get("/api/contacts?" + urlencode({"limit": 100, **params}))
    assert r.status_code == 200, r.text
    return sorted(c["first_name"] for c in r.json()["items"])


def test_group_box_single_term_is_contains_and_case_insensitive(world):
    assert names(world, group="ml") == ["Asha", "Chen"]
    assert names(world, group="HR Leads".lower()) == ["Dee", "Eli"]
    assert names(world, group='"HR Leads"') == ["Dee", "Eli"]
    assert names(world, group="nomatch") == []


def test_group_boolean_and_or_not(world):
    assert names(world, group="ML OR HR") == ["Asha", "Chen", "Dee", "Eli"]
    assert names(world, group="ML AND Hot") == ["Asha"]
    assert names(world, group="Hot AND NOT ML") == ["Ben", "Dee"]
    assert names(world, group="Hot -ML") == ["Ben", "Dee"]           # implicit AND with -term
    assert names(world, group="(ML OR HR) AND Hot") == ["Asha", "Dee"]
    assert names(world, group="NOT Hot") == ["Chen", "Eli"]           # also includes people in no group (none here besides these)


def test_not_group_includes_contacts_who_are_in_no_group(world):
    do_import(world, make_csv(["Fay,Ito,https://www.linkedin.com/in/fay,,Zed,Writer,01 Jan 2024"]))
    assert "Fay" in names(world, group="NOT Hot")


def test_main_search_boolean_over_name_company_position(world):
    assert names(world, q="data") == ["Asha", "Chen"]
    assert names(world, q="data AND google") == ["Asha"]
    assert names(world, q="google OR initech") == ["Asha", "Ben", "Eli"]
    assert names(world, q="data NOT google") == ["Chen"]
    assert names(world, q="data google") == ["Asha"]                  # implicit AND
    assert names(world, q="(google OR acme) AND NOT manager") == ["Asha", "Chen", "Dee"]
    assert names(world, q='"founder and ceo"') == ["Dee"]            # quoted phrase, lowercase 'and' is just a word
    assert names(world, q="founder and ceo") == ["Dee"]              # lowercase and is not an operator


def test_field_prefixes_and_combining_boxes(world):
    assert names(world, q="company:acme AND position:engineer") == ["Chen"]
    assert names(world, q="title:data AND name:rao") == ["Asha"]
    assert names(world, q="group:ml AND company:google") == ["Asha"]
    assert names(world, q="company:google", group="Hot") == ["Asha", "Ben"]   # boxes AND together
    assert names(world, company="google OR initech") == ["Asha", "Ben", "Eli"]
    assert names(world, position="data NOT scientist") == ["Chen"]
    assert names(world, q="http:something") == []                    # unknown field prefix stays a plain word


@pytest.mark.parametrize("bad", ["(data", "data)", "data AND", "OR data", "AND", '"unterminated', "NOT", "()", "data AND OR google"])
def test_bad_syntax_gives_a_clear_400_and_changes_nothing(world, bad):
    r = world.get("/api/contacts", params={"q": bad})
    assert r.status_code == 400 and "Search" in r.json()["detail"]


def test_limits(world):
    assert world.get("/api/contacts", params={"q": "a" * 301}).status_code == 400
    assert world.get("/api/contacts", params={"q": " OR ".join(["x"] * 31)}).status_code == 400
    assert world.get("/api/contacts", params={"q": " OR ".join(["x"] * 30)}).status_code == 200


def test_wildcards_and_quotes_are_literal_and_safe(world):
    assert names(world, q="%") == []
    assert names(world, q="_") == []
    assert world.get("/api/contacts", params={"q": "'; DROP TABLE contacts; --"}).status_code == 200
    assert world.get("/api/contacts").json()["total"] == 5


def test_ids_and_export_use_the_same_boolean_filters(world):
    assert world.get("/api/contacts/ids", params={"group": "ML AND Hot"}).json()["total"] == 1
    csvtext = world.get("/api/export", params={"group": "Hot AND NOT ML"}).text
    assert csvtext.count("\n") == 3 and "Ben" in csvtext and "Dee" in csvtext and "Asha" not in csvtext
    assert world.get("/api/export", params={"q": "(bad"}).status_code == 400
