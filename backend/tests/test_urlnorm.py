import pytest

from app.urlnorm import is_redirectable, normalize_url

CANON = "https://www.linkedin.com/in/asha-rao"


@pytest.mark.parametrize("raw", [
    "https://www.linkedin.com/in/asha-rao/", "http://linkedin.com/in/asha-rao", "HTTPS://WWW.LinkedIn.com/in/Asha-Rao",
    "https://linkedin.com/in/asha-rao?trk=abc#frag", "linkedin.com/in/asha-rao/", "  https://www.linkedin.com/in/asha-rao  ",
])
def test_variants_collapse(raw):
    assert normalize_url(raw) == CANON


def test_empty():
    assert normalize_url("") is None and normalize_url("   ") is None and normalize_url(None) is None


def test_redirectable():
    assert is_redirectable("https://www.linkedin.com/in/x")
    assert is_redirectable("https://linkedin.com/in/x")
    assert not is_redirectable("http://www.linkedin.com/in/x")
    assert not is_redirectable("https://evil.com/in/x")
    assert not is_redirectable("https://linkedin.com.evil.com/in/x")
