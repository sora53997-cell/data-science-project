"""Download the seasonal China tourist mobility network files from Figshare."""

from __future__ import annotations

import argparse
import hashlib
import time
from pathlib import Path

import requests


FILES = {
    "Edges_Travels_in_Autumn.csv": (60631016, "5d8df600ffbc7df8101d16172b100fe8"),
    "Edges_Travels_in_Spring.csv": (60631019, "c80f705b0aba407f72aef56df0a1ec35"),
    "Edges_Travels_in_Summer.csv": (60631022, "d79262584ef1a434c4e25515688d857c"),
    "Edges_Travels_in_Winter.csv": (60631025, "1ccddd3fa9cbc662f32602923e56fe24"),
    "Nodes_Travels_in_Autumn.csv": (60631028, "bbbfbc299a36f4b33b70598be0abf49c"),
    "Nodes_Travels_in_Spring.csv": (60631031, "ae82df67c343839c597bccc6e60ac27a"),
    "Nodes_Travels_in_Summer.csv": (60631034, "675879e707912c589b3f3af9f584e982"),
    "Nodes_Travels_in_Winter.csv": (60631037, "22587e25d0ca084e3c7616479344e9aa"),
}


def md5sum(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(file_id: int, destination: Path, attempts: int = 6) -> None:
    url = f"https://ndownloader.figshare.com/files/{file_id}"
    headers = {"User-Agent": "china-tourism-portfolio/1.0 (educational use)"}

    for attempt in range(1, attempts + 1):
        response = requests.get(url, headers=headers, timeout=180)
        if response.ok:
            destination.write_bytes(response.content)
            return
        if attempt == attempts:
            response.raise_for_status()
        wait_seconds = 15 * attempt if response.status_code == 403 else 5 * attempt
        print(f"Figshare returned {response.status_code}; retrying in {wait_seconds}s...")
        time.sleep(wait_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "raw",
        help="Directory for the downloaded CSV files.",
    )
    parser.add_argument("--force", action="store_true", help="Download files again.")
    parser.add_argument(
        "--delay",
        type=float,
        default=8.0,
        help="Pause between files to respect Figshare download limits.",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for name, (file_id, expected_md5) in FILES.items():
        destination = args.output_dir / name
        if destination.exists() and not args.force and md5sum(destination) == expected_md5:
            print(f"Verified existing file: {name}")
            continue

        print(f"Downloading {name}...")
        download_file(file_id, destination)
        actual_md5 = md5sum(destination)
        if actual_md5 != expected_md5:
            destination.unlink(missing_ok=True)
            raise ValueError(f"Checksum mismatch for {name}: {actual_md5}")
        print(f"Verified: {name}")
        time.sleep(args.delay)

    print("All seasonal files downloaded and verified.")


if __name__ == "__main__":
    main()
