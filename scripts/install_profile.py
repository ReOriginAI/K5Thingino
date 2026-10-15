"""Install the maintained source profile into a local Thingino checkout."""
import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
CAMERA = "wansview_k5_t21n_ov2735b_rtl8188fu"


def fingerprints(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in directory.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", nargs="?", type=Path, default=ROOT / "thingino-firmware")
    args = parser.parse_args()
    checkout = args.checkout.resolve()
    if not (checkout / "configs/cameras").is_dir():
        parser.error(f"Not a Thingino source checkout: {checkout}")
    source = ROOT / "firmware" / CAMERA
    destination = checkout / "configs/cameras" / CAMERA
    if destination.exists():
        if fingerprints(source) == fingerprints(destination):
            print("K5 source profile is already installed and matches.")
            return
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        saved = ROOT / "archive/profile-snapshots" / stamp / CAMERA
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(destination, saved)
        print(f"Previous profile preserved in {saved.relative_to(ROOT)}")
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__"))
    print(f"Installed source profile in {destination}. No camera accessed.")


if __name__ == "__main__":
    main()
