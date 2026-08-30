from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path

from download_utils import download_https

ROOT = Path(__file__).resolve().parents[1]
CALCE_HOSTS = {"web.calce.umd.edu"}
FILES = {
    "ocv": (
        "https://web.calce.umd.edu/batteries/data/SP1_25C_IC_OCV_12_2_2015.zip",
        "4f2e5ccbf6891c0f038f015cc8e5915c1d7b381e9673b61a81402d15d2739689",
    ),
    "dst": (
        "https://web.calce.umd.edu/batteries/data/SP2_25C_DST.zip",
        "3d3a90a67574c336eca9d097a5f139aaad70e7fa3106078079da9cd11d1b3661",
    ),
    "fuds": (
        "https://web.calce.umd.edu/batteries/data/SP2_25C_FUDS.zip",
        "e2ce8e4626c4263cb8758c9488cec66d31c04a9d11465c14e668428cead1e053",
    ),
    "capacity": (
        "https://web.calce.umd.edu/batteries/data/SP2_Initial_capacity_10_16_2015.zip",
        "d18f9a958e2dabcaef9999bb42e8043ea5092b5d0c557966d92e4ad675d95c9d",
    ),
}


def _verify_archive(path: Path, expected_sha256: str) -> None:
    actual_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual_sha256 != expected_sha256:
        raise RuntimeError(f"SHA-256 mismatch for {path.name}: {actual_sha256}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download official CALCE INR18650-20R validation data")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "raw" / "calce")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for label, (url, expected_sha256) in FILES.items():
        archive = args.output / f"{label}.zip"
        if not archive.exists():
            print(f"Downloading {label}: {url}")
            download_https(
                url,
                archive,
                user_agent="battery-soc-soh-aging-estimation/1.0",
                allowed_hosts=CALCE_HOSTS,
            )
        _verify_archive(archive, expected_sha256)
        destination = args.output / label
        destination.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(destination)
        print(f"Ready: {destination} (SHA-256 verified)")


if __name__ == "__main__":
    main()
