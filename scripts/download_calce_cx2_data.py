from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
URL = "https://web.calce.umd.edu/batteries/data/CX2_3.zip"
EXPECTED_BYTES = 425_523_304
EXPECTED_SHA256 = "1a1d8c2aecba147c398ae9d6e1305a677dadba98b89accb65753ddbdfb51c330"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and verify the official CALCE CX2-3 archive")
    parser.add_argument("--output", type=Path, default=ROOT / "data/raw/calce_cx2/CX2_3.complete.zip")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".part")
    request = urllib.request.Request(URL, headers={"User-Agent": "battery-soc-soh-aging-estimation/1.0"})
    digest = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(request) as response, temporary.open("wb") as handle:
        while chunk := response.read(1024 * 1024):
            handle.write(chunk); digest.update(chunk); size += len(chunk)
    if size != EXPECTED_BYTES or digest.hexdigest() != EXPECTED_SHA256:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Verification failed: bytes={size}, sha256={digest.hexdigest()}")
    temporary.replace(args.output)
    print(f"Verified {args.output} ({size} bytes, SHA-256 {EXPECTED_SHA256})")


if __name__ == "__main__":
    main()
