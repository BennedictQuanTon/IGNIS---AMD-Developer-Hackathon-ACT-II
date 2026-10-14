"""Download MaintIE (MIT) at a pinned commit into the gitignored data/ folder and verify its hashes."""

import hashlib
import sys
import urllib.request
from pathlib import Path

COMMIT = "825e7710e4129598da997276a38b3cb40b200bc2"
BASE_URL = f"https://raw.githubusercontent.com/nlp-tlp/maintie/{COMMIT}"
FILES = {
    "data/gold_release.json": "ef811cf4ffd0c90e6a13b1369e24e9d1d08f9a294d873ab4fb1a580096d7d6e0",
    "data/scheme.json": "0352bd240953829105d3017caf72dbf008e9c2ceee201add1ade22d818b582c0",
    "LICENSE.md": None,
}
TARGET_DIRECTORY = Path("data/maintie")


def main() -> int:
    TARGET_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for remote_path, expected_hash in FILES.items():
        with urllib.request.urlopen(f"{BASE_URL}/{remote_path}", timeout=60) as response:
            data = response.read()
        actual_hash = hashlib.sha256(data).hexdigest()
        if expected_hash and actual_hash != expected_hash:
            print(f"hash mismatch for {remote_path}: {actual_hash}", file=sys.stderr)
            return 1
        target = TARGET_DIRECTORY / Path(remote_path).name
        target.write_bytes(data)
        print(f"saved {target} ({len(data)} bytes, sha256 {actual_hash[:12]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
