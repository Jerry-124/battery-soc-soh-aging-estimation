from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from download_utils import download_https, validate_https_url


def test_validate_https_url_accepts_allowlisted_https() -> None:
    url = "https://web.calce.umd.edu/batteries/data/example.zip"

    assert validate_https_url(url, allowed_hosts={"web.calce.umd.edu"}) == url


def test_validate_https_url_rejects_non_https_schemes() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        validate_https_url("file:///tmp/example.zip")


def test_validate_https_url_rejects_unexpected_host() -> None:
    with pytest.raises(ValueError, match="allow-listed"):
        validate_https_url(
            "https://example.com/data.zip",
            allowed_hosts={"web.calce.umd.edu"},
        )


def test_download_rejects_redirect_to_unexpected_host(monkeypatch, tmp_path: Path) -> None:
    class RedirectedResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def geturl(self) -> str:
            return "https://example.com/redirected.zip"

        def read(self, _size: int) -> bytes:
            return b""

    monkeypatch.setattr(
        "download_utils.urllib.request.urlopen",
        lambda request, timeout: RedirectedResponse(),
    )
    destination = tmp_path / "dataset.zip"

    with pytest.raises(ValueError, match="allow-listed"):
        download_https(
            "https://web.calce.umd.edu/batteries/data/example.zip",
            destination,
            user_agent="test-agent",
            allowed_hosts={"web.calce.umd.edu"},
        )

    assert not destination.exists()
