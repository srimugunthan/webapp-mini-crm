"""LinkedIn URL normalization (ADR-005). One function shared by import, bulk matching and /go."""
from urllib.parse import urlsplit

CANONICAL_HOST = "www.linkedin.com"


def normalize_url(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    if "://" not in s:
        s = "https://" + s.lstrip("/")
    parts = urlsplit(s)
    host = (parts.hostname or "").lower()
    if not host:
        return None
    if host == "linkedin.com" or host == "www.linkedin.com":
        host = CANONICAL_HOST
    path = parts.path.lower().rstrip("/")
    return f"https://{host}{path}"


def is_redirectable(url: str) -> bool:
    """/go only redirects to https linkedin.com or www.linkedin.com."""
    parts = urlsplit(url)
    return parts.scheme == "https" and (parts.hostname or "").lower() in ("linkedin.com", "www.linkedin.com")
