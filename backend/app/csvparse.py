import csv
import io
from datetime import datetime

from .errors import AppError

CONTACT_COLUMNS = {
    "first name": "first_name",
    "last name": "last_name",
    "url": "url",
    "email address": "email",
    "company": "company",
    "position": "position",
    "connected on": "connected_on",
}


def decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise AppError(400, "File is not valid UTF-8 text. Is this the LinkedIn connections CSV?")


def read_rows(data: bytes, required: set[str], wanted: dict[str, str]):
    """Find the header row by column names (skips LinkedIn's notes preamble).

    Returns a list of (row_number, {field: value}) with 1-based file line numbers of the record start.
    """
    text = decode(data)
    reader = csv.reader(io.StringIO(text))
    header = None
    records = []
    for row in reader:
        lowered = [c.strip().lower() for c in row]
        if header is None:
            if required.issubset(set(lowered)):
                header = {name: i for i, name in enumerate(lowered) if name in wanted}
            continue
        if not any(c.strip() for c in row):
            continue
        values = {}
        for name, idx in header.items():
            values[wanted[name]] = row[idx].strip() if idx < len(row) else ""
        records.append((reader.line_num, values))
    if header is None:
        missing = ", ".join(sorted(required))
        raise AppError(400, f"Could not find a header row with the required columns: {missing}.")
    return records


def parse_connected_on(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in ("%d %b %Y", "%Y-%m-%d", "%m/%d/%Y", "%d %B %Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def parse_connections(data: bytes):
    return read_rows(data, {"first name", "url"}, CONTACT_COLUMNS)
