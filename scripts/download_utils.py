from __future__ import annotations

import hashlib
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class DownloadResult:
    bytes_written: int
    sha256: str


def validate_https_url(url: str, *, allowed_hosts: set[str] | None = None) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Downloads require an absolute HTTPS URL")
    if allowed_hosts is not None and parsed.hostname not in allowed_hosts:
        raise ValueError(f"Download host is not allow-listed: {parsed.hostname}")
    return url


def download_https(
    url: str,
    destination: Path,
    *,
    user_agent: str,
    allowed_hosts: set[str] | None = None,
    timeout_s: float = 60.0,
) -> DownloadResult:
    """Download one allow-listed HTTPS resource using verified platform TLS defaults."""
    validated_url = validate_https_url(url, allowed_hosts=allowed_hosts)
    request = urllib.request.Request(validated_url, headers={"User-Agent": user_agent})
    digest = hashlib.sha256()
    bytes_written = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    # B310 is safe here because both the requested URL and the post-redirect URL are validated.
    with urllib.request.urlopen(request, timeout=timeout_s) as response:  # nosec B310
        final_url = response.geturl()
        validate_https_url(final_url, allowed_hosts=allowed_hosts)
        with destination.open("wb") as handle:
            while chunk := response.read(1024 * 1024):
                handle.write(chunk)
                digest.update(chunk)
                bytes_written += len(chunk)
    return DownloadResult(bytes_written=bytes_written, sha256=digest.hexdigest())
