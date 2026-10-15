"""Build a checked, disarmed SD package from the new K5 kernel and SquashFS."""
from datetime import datetime, timezone
import hashlib
import json
import lzma
from pathlib import Path
import shutil
import struct
import subprocess
from zipfile import ZIP_DEFLATED, ZipFile
import zlib

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT / "thingino-firmware"
CAMERA = "wansview_k5_t21n_ov2735b_rtl8188fu"
BUILD = REPO / "output/stable" / f"{CAMERA}-3.10.14-uclibc"
PROFILE = REPO / "configs/cameras" / CAMERA
SRC = Path(__file__).resolve().parent
DIST = ROOT / "dist"
CMDLINE = ('console=ttyS1,115200n8 mem=41M@0x0 rmem=23M@0x2900000 panic=2 '
           'init=/init rootfstype=squashfs root=/dev/mtdblock2 rw '
           'mtdparts=jz_sfc:256k(boot),2560k(kernel),6144k(rootfs),2944k(data),'
           '320k(syscfg),320k(sysbak),1472k(minikernel),2304k(minirootfs),64k(upgrade)')


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    config = (BUILD / "build/linux-3.10.14/.config").read_text()
    for option in ("CONFIG_CMDLINE_BOOL=y", "CONFIG_CMDLINE_OVERRIDE=y", "CONFIG_FAT_FS=y",
                   "CONFIG_VFAT_FS=y", "CONFIG_NLS_CODEPAGE_437=y", "CONFIG_NLS_ISO8859_1=y",
                   "CONFIG_NLS_UTF8=y", "CONFIG_WATCHDOG_NOWAYOUT=y", "CONFIG_JZ_WDT=y"):
        check(option + "\n" in config, "Kernel option missing: " + option)
    check(f'CONFIG_CMDLINE="{CMDLINE}"\n' in config, "Kernel command line changed")
    kernel = (BUILD / "images/uImage").read_bytes()
    rootfs = (BUILD / "images/rootfs.squashfs").read_bytes()
    check(len(kernel) <= 0x280000 and len(rootfs) <= 0x600000, "Image exceeds K5 partition")
    check(zlib.crc32(kernel) != 0x1ee18fc1 and zlib.crc32(rootfs) != 0x5b77b3f8,
          "Refusing to package either old failing firmware payload")
    head = struct.unpack(">7I4B32s", kernel[:64])
    header = bytearray(kernel[:64]); header[4:8] = b"\0" * 4
    check(head[0] == 0x27051956 and zlib.crc32(header) == head[1], "uImage header CRC invalid")
    check(head[3] == len(kernel) - 64 and zlib.crc32(kernel[64:]) == head[6], "uImage payload CRC invalid")
    check(head[4] == 0x80010000 and head[7:11] == (5, 5, 2, 3), "Not a Linux/MIPS/LZMA kernel for stock U-Boot")
    raw_kernel = lzma.decompress(kernel[64:], format=lzma.FORMAT_ALONE)
    check(CMDLINE.encode() in raw_kernel, "Forced command line missing from actual boot payload")
    check(rootfs[:4] == b"hsqs", "Invalid SquashFS magic")
    check((BUILD / "target/etc/k5-build-id").read_text().startswith("K5_BUILD_ID=k5-v3-"), "V3 build identity missing")
    for log, count in (("v3-runtime-tests-final.log", 12), ("v3-installer-tests.log", 7)):
        text = (ROOT / "docs/logs" / log).read_text()
        check(f"Ran {count} tests" in text and text.rstrip().endswith("OK"), "Host tests did not pass: " + log)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    preserved = ROOT / "archive/releases"
    preserved.mkdir(parents=True, exist_ok=True)
    if DIST.exists():
        DIST.rename(preserved / f"dist-preserved-{stamp}")
    package = DIST / "k5-installer"
    package.mkdir(parents=True)
    (package / "uImage.t21").write_bytes(kernel)
    (package / "rootfs.squashfs.t21").write_bytes(rootfs)
    shutil.copy2(SRC / "facDiag-v3", DIST / "facDiag")
    shutil.copy2(SRC / "README-V3.txt", DIST / "README-FIRST.txt")
    (package / "ARM-BY-RENAMING-TO-INSTALL_NOW.txt").write_text("I_ACCEPT_BRICK_RISK\n")
    (DIST / "FORCE-PORTAL-BY-RENAMING-TO-FORCE_PORTAL.txt").write_text("Rename to FORCE_PORTAL only to request V3 portal recovery.\n")
    (DIST / "COLLECT-PRIVATE-LOGS-BY-RENAMING-TO-COLLECT_PRIVATE_LOGS.txt").write_text("Optional private SD debugging. Never post raw PRIVATE logs without redaction.\n")
    preflight = (SRC / "preflight.sh").read_text()
    check("ROOT_BYTES\" -le 6291456" in preflight, "Preflight must limit rootfs to 6 MiB")
    (package / "preflight.sh").write_text(preflight)
    (package / "images.md5").write_text(
        f"{hashlib.md5(kernel).hexdigest()}  uImage.t21\n{hashlib.md5(rootfs).hexdigest()}  rootfs.squashfs.t21\n")
    flags = [f"-DEXPECT_KERNEL_SIZE={len(kernel)}u", f"-DEXPECT_ROOT_SIZE={len(rootfs)}u",
             f"-DEXPECT_KERNEL_CRC32=0x{zlib.crc32(kernel):08x}u", f"-DEXPECT_ROOT_CRC32=0x{zlib.crc32(rootfs):08x}u"]
    subprocess.run([str(BUILD / "host/bin/mipsel-linux-gcc"), "-std=gnu11", "-Os", "-static",
                    "-Wall", "-Wextra", "-Werror", *flags, str(SRC / "k5_flash_v3.c"),
                    "-o", str(package / "k5-flash-static")], check=True)
    elf = subprocess.check_output(["readelf", "-h", "-l", str(package / "k5-flash-static")], text=True)
    check("MIPS" in elf and "INTERP" not in elf, "Installer is not static MIPS")
    for file in (DIST / "facDiag", package / "preflight.sh", package / "k5-flash-static"):
        file.chmod(0o755)
    for file in (DIST / "facDiag", package / "preflight.sh"):
        file.read_bytes().decode("ascii")
        subprocess.run(["busybox", "sh", "-n", str(file)], check=True)

    commit = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    check(subprocess.check_output(["git", "-C", str(REPO), "cat-file", "-t", commit], text=True).strip() == "commit",
          "Base source commit is not valid")
    identity = dict(line.split("=", 1) for line in (BUILD / "target/etc/k5-build-id").read_text().splitlines())
    manifest = {
        "version": identity["K5_BUILD_ID"], "profile": CAMERA, "prepared_utc": stamp,
        "source_base_commit": commit, "source_tree_has_local_changes": True,
        "camera_profile_sha256": identity["K5_PROFILE_SHA256"],
        "installer_source_sha256": sha(SRC / "k5_flash_v3.c"),
        "installer_version": "v3-readonly-first", "arm_marker_bundled": False,
        "camera_hardware_tested": False, "original_runtime_root_cause_proven": False,
        "host_runtime_tests_passed": 12, "host_installer_simulation_tests_passed": 7,
        "kernel": {"bytes": len(kernel), "crc32": f"{zlib.crc32(kernel):08x}",
                   "sha256": sha(package / "uImage.t21"), "load_address": hex(head[4]), "entry_point": hex(head[5])},
        "rootfs": {"bytes": len(rootfs), "crc32": f"{zlib.crc32(rootfs):08x}",
                   "sha256": sha(package / "rootfs.squashfs.t21")},
        "kernel_command_line": CMDLINE,
        "flash_write_targets": ["factory mtd1 at 0x040000 (0x280000 bytes)", "factory mtd2 at 0x2c0000 (0x8e0000 bytes)"],
        "stock_bootloader_and_non_os_partitions_preserved": True,
        "all_eight_partitions_backed_up_before_writes": True,
        "independent_readback_and_erased_tail_check": True,
        "best_effort_factory_kernel_and_root_rollback": True,
        "runtime_changes": ["built-in FAT32 and charsets", "early SD phase logging", "correct module paths",
                            "asynchronous configured Wi-Fi", "persistent failed-attempt latch",
                            "independent 180-second startup guard", "RAM-only fallback portal",
                            "bounded shutdown with armed watchdog", "Wi-Fi-only long Reset",
                            "data-only firstboot", "disabled stock-layout ENV writes"],
    }
    # Hardware success applies only to exactly matching tested payloads.
    evidence = ROOT / "docs/hardware-validation.json"
    if evidence.exists():
        report = json.loads(evidence.read_text())
        if (report["kernel_sha256"] == manifest["kernel"]["sha256"] and
                report["rootfs_sha256"] == manifest["rootfs"]["sha256"] and
                report["installer_sha256"] == sha(package / "k5-flash-static")):
            manifest["camera_hardware_tested"] = True
            manifest["hardware_validation"] = report
    (package / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    files = sorted(file for file in DIST.rglob("*") if file.is_file())
    (DIST / "SHA256SUMS").write_text("".join(f"{sha(file)}  {file.relative_to(DIST)}\n" for file in files))
    check(not (package / "INSTALL_NOW").exists(), "Package accidentally armed")
    check(not any(file.name in ("ub_boot.bin", "ub_kernel.bin", "ub_rootfs.bin") for file in files), "Recovery files mixed with installer")
    releases = ROOT / "releases"
    releases.mkdir(exist_ok=True)
    archive = releases / "k5-thingino-v3-sdcard.zip"
    if archive.exists():
        archive.rename(preserved / f"k5-thingino-v3-sdcard-preserved-{stamp}.zip")
    with ZipFile(archive, "w", ZIP_DEFLATED, compresslevel=6) as zipfile:
        for file in sorted(DIST.rglob("*")):
            if file.is_file():
                zipfile.write(file, str(file.relative_to(DIST)))
    with ZipFile(archive) as zipfile:
        check(zipfile.testzip() is None, "ZIP integrity failure")
        check("k5-installer/INSTALL_NOW" not in zipfile.namelist(), "ZIP armed unexpectedly")
    print(json.dumps(manifest, indent=2))
    print(f"DIST={DIST}\nZIP={archive}\nZIP_SHA256={sha(archive)}")


if __name__ == "__main__":
    main()
