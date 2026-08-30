from __future__ import annotations

import argparse
from pathlib import Path

from download_utils import download_https

ROOT = Path(__file__).resolve().parents[1]
URL = "https://web.calce.umd.edu/batteries/data/CX2_3.zip"
EXPECTED_BYTES = 425_523_304
EXPECTED_SHA256 = "1a1d8c2aecba147c398ae9d6e1305a677dadba98b89accb65753ddbdfb51c330"
CALCE_HOSTS = {"web.calce.umd.edu"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and verify the official CALCE CX2-3 archive")
    parser.add_argument("--output", type=Path, default=ROOT / "data/raw/calce_cx2/CX2_3.complete.zip")
    args = parser.parse_args()
    temporary = args.output.with_suffix(args.output.suffix + ".part")
    result = download_https(
        URL,
        temporary,
        user_agent="battery-soc-soh-aging-estimation/1.0",
        allowed_hosts=CALCE_HOSTS,
    )
    if result.bytes_written != EXPECTED_BYTES or result.sha256 != EXPECTED_SHA256:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(
            f"Verification failed: bytes={result.bytes_written}, sha256={result.sha256}"
        )
    temporary.replace(args.output)
    print(
        f"Verified {args.output} "
        f"({result.bytes_written} bytes, SHA-256 {EXPECTED_SHA256})"
    )


if __name__ == "__main__":
    main()
