from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from download_utils import validate_https_url


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
