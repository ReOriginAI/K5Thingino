#!/usr/bin/env python3
"""Reconstruct a verified 16 MiB factory flash backup from the user's ZIP.

READ-ONLY to any camera hardware. Reads ZIP and writes one local output file.
No use of mtd, flashcp, flash_erase, or external network services.
"""
import hashlib
import os
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parents[1] / "backups"
SOURCE = HERE / "k5-factory-backup.zip"
DEST = HERE / "wansview-k5-stock-fullflash-16MiB.bin"
SOURCE_SHA256 = "80818c697e08dd9b9e90a2830ef8a4364d20a3ef8ab629d5d5c45849ddf9953e"
DEST_SHA256 = "8bce987662b47bccdd0326fdbaae3943bbfd43ed37e345d2b168771f586f1030"
EXPECTED_SIZES = [
    0x040000, 0x280000, 0x8e0000, 0x050000,
    0x050000, 0x170000, 0x240000, 0x010000,
]

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(1024 * 1024)
            if not block:
                return h.hexdigest()
            h.update(block)

def main():
    if not SOURCE.is_file():
        raise SystemExit("Missing: " + str(SOURCE) + "\nCopy your original user-uploaded ZIP into backups/ first.")
    actual = sha256_file(SOURCE)
    if actual != SOURCE_SHA256:
        raise SystemExit("Source ZIP SHA256 mismatch. Refusing to reconstruct: " + actual)
    if DEST.exists():
        if sha256_file(DEST) == DEST_SHA256:
            print("Already complete and verified:", DEST)
            return
        raise SystemExit("Output file exists but does not match expected hash; not overwriting.")
    tmp = HERE / ".fullflash.partial"
    if tmp.exists():
        raise SystemExit("Refusing to overwrite stale temp file: " + str(tmp))
    h = hashlib.sha256()
    count = 0
    try:
        with zipfile.ZipFile(SOURCE, "r") as z:
            bad = z.testzip()
            if bad:
                raise ValueError("ZIP corruption: " + bad)
            with tmp.open("xb") as target:
                os.chmod(tmp, 0o600)
                for i, expected in enumerate(EXPECTED_SIZES):
                    name = f"k5-factory-backup/mtd{i}.bin"
                    info = z.getinfo(name)
                    if info.file_size != expected:
                        raise ValueError(f"{name}: expected {expected} bytes, got {info.file_size}")
                    actual_size = 0
                    with z.open(name) as source:
                        while True:
                            block = source.read(1024 * 1024)
                            if not block:
                                break
                            target.write(block)
                            h.update(block)
                            actual_size += len(block)
                    if actual_size != expected:
                        raise ValueError(f"Short partition {name}: {actual_size} bytes")
                    count += actual_size
        if count != 16_777_216 or h.hexdigest() != DEST_SHA256:
            raise ValueError(f"Reconstruction digest/size mismatch: {count} bytes, {h.hexdigest()}")
        tmp.rename(DEST)
        print(f"VERIFIED full flash: {DEST} ({count} bytes)\nSHA256: {DEST_SHA256}")
    except Exception:
        tmp.unlink(missing_ok=True)
        raise

if __name__ == "__main__":
    main()
