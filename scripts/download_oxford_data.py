from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from download_utils import download_https

ROOT = Path(__file__).resolve().parents[1]
URL = "https://ora.ox.ac.uk/objects/uuid:03ba4b01-cfed-46d3-9b1a-7d4a7bdf6fac/files/m5ac36a1e2073852e4f1f7dee647909a7"
SHA256 = "a8f0b928f4ea77d7ba98b97194b78cc77336f2338fee8b57573d043f0cf26781"
OXFORD_HOSTS = {"ora.ox.ac.uk"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Oxford Battery Degradation Dataset 1")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "raw" / "oxford" / "Oxford_Battery_Degradation_Dataset_1.mat",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not args.output.exists():
        download_https(
            URL,
            args.output,
            user_agent="battery-soc-soh-aging-estimation/1.0",
            allowed_hosts=OXFORD_HOSTS,
        )
    with args.output.open("rb") as handle:
        actual = hashlib.file_digest(handle, "sha256").hexdigest()
    if actual != SHA256:
        raise RuntimeError(f"SHA-256 mismatch: {actual}")
    print(f"Ready: {args.output} ({args.output.stat().st_size} bytes, SHA-256 verified)")


if __name__ == "__main__":
    main()
