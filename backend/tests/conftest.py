import pytest
from fastapi.testclient import TestClient

from app import clock
from app.config import BACKEND_DIR, Settings
from app.main import create_app

FIX = BACKEND_DIR / "tests" / "fixtures"


@pytest.fixture
def settings(tmp_path):
    (tmp_path / "data").mkdir()
    return Settings(db_path=tmp_path / "db" / "crm.sqlite", data_dir=tmp_path / "data", static_dir=None)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings), follow_redirects=False) as c:
        yield c


@pytest.fixture
def fake_now(monkeypatch):
    state = {"t": 1_700_000_000}
    monkeypatch.setattr(clock, "now", lambda: state["t"])
    return state


def csv_fixture(name):
    return (FIX / name).read_bytes()


def do_import(client, data: bytes):
    r = client.post("/api/import", files={"file": ("Connections.csv", data, "text/csv")})
    return r


def make_csv(rows, preamble=True):
    lines = []
    if preamble:
        lines += ["Notes:", '"When exporting your connection data, you may notice that some of the email addresses are missing."', ""]
    lines.append("First Name,Last Name,URL,Email Address,Company,Position,Connected On")
    lines += rows
    return ("\n".join(lines) + "\n").encode()
