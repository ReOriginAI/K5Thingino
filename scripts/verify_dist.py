"""Verify the SD distribution and ZIP without connecting to a camera."""
import hashlib
import json
import lzma
from pathlib import Path
import struct
import subprocess
from zipfile import ZipFile
import zlib

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def check(condition, message):
    if not condition:
        raise SystemExit("FAIL: " + message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((DIST / "k5-installer/manifest.json").read_text())
    covered = set()
    for line in (DIST / "SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ", 1)
        path = DIST / name
        check(path.resolve().is_relative_to(DIST.resolve()), "Checksum path leaves dist")
        check(sha(path) == expected, "Checksum mismatch: " + name)
        covered.add(name)
    actual = {str(path.relative_to(DIST)) for path in DIST.rglob("*")
              if path.is_file() and path.name != "SHA256SUMS"}
    check(covered == actual, "Checksum coverage does not match SD contents")
    for name in ("k5-installer/INSTALL_NOW", "FORCE_PORTAL", "COLLECT_PRIVATE_LOGS"):
        check(not (DIST / name).exists(), "An activation marker is bundled: " + name)
    check(not any(path.name.startswith("ub_") for path in DIST.rglob("*")), "Recovery images mixed with installer")

    package = DIST / "k5-installer"
    for filename, key, limit in (("uImage.t21", "kernel", 0x280000),
                                 ("rootfs.squashfs.t21", "rootfs", 0x600000)):
        path = package / filename
        data = path.read_bytes()
        metadata = manifest[key]
        check(len(data) == metadata["bytes"] and len(data) <= limit, "Image size invalid: " + filename)
        check(sha(path) == metadata["sha256"], "Image SHA invalid: " + filename)
        check(f"{zlib.crc32(data):08x}" == metadata["crc32"], "Image CRC invalid: " + filename)

    kernel = (package / "uImage.t21").read_bytes()
    fields = struct.unpack(">7I4B32s", kernel[:64])
    header = bytearray(kernel[:64]); header[4:8] = b"\0" * 4
    check(fields[0] == 0x27051956 and zlib.crc32(header) == fields[1], "uImage header invalid")
    check(fields[3] == len(kernel) - 64 and zlib.crc32(kernel[64:]) == fields[6], "uImage payload invalid")
    check(fields[4] == 0x80010000 and fields[7:11] == (5, 5, 2, 3), "Wrong kernel architecture/load format")
    check(manifest["kernel_command_line"].encode() in lzma.decompress(kernel[64:], format=lzma.FORMAT_ALONE),
          "MTD command line missing from actual kernel")
    elf = subprocess.check_output(["readelf", "-h", "-l", str(package / "k5-flash-static")], text=True)
    check("MIPS" in elf and "INTERP" not in elf, "Installer is not static MIPS")

    squashfs = package / "rootfs.squashfs.t21"
    profile = ROOT / "firmware" / manifest["profile"]
    for file in (profile / "overlay").rglob("*"):
        if file.is_file():
            name = str(file.relative_to(profile / "overlay"))
            shipped = subprocess.check_output(["unsquashfs", "-cat", str(squashfs), name], stderr=subprocess.DEVNULL)
            check(shipped == file.read_bytes(), "Shipped overlay differs from maintained source: " + name)
    listing = subprocess.check_output(["unsquashfs", "-ll", str(squashfs)], text=True)
    check("make[" not in listing, "Malformed module path in SquashFS")
    for module in ("8188fu.ko", "jzmmc_v12.ko", "exfat.ko"):
        check(module in listing, "Missing module: " + module)

    archive = ROOT / "releases/k5-thingino-v3-sdcard.zip"
    with ZipFile(archive) as zipped:
        check(zipped.testzip() is None, "Corrupt release ZIP")
        files = actual | {"SHA256SUMS"}
        check(set(zipped.namelist()) == files, "Release ZIP differs from dist")
        for name in files:
            check(zipped.read(name) == (DIST / name).read_bytes(), "ZIP file differs: " + name)
    print(f"PASS: {manifest['version']}; checksums, kernel, source overlays, modules, static installer and ZIP")
    print("PASS: distribution starts disarmed; no recovery images included")
    print("Hardware status: " + manifest.get("hardware_validation", {}).get("status", "not recorded for these exact payloads"))


if __name__ == "__main__":
    main()
