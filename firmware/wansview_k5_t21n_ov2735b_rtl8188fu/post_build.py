"""K5-only integration checks and fixups after Buildroot overlays are applied."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import sys

target = Path(sys.argv[1])
profile = Path(__file__).resolve().parent
version = "k5-v3-sd-recovery-20261012"

api = target / "var/www-portal/x/api.cgi"
text = (profile.parents[2] / "package/wifi/files/api.cgi").read_text()
for command in (
    'wlan configure "$wlan_ssid" "$wlan_secret" ap',
    'wlan configure "$wlan_ssid" "$wlan_secret"',
):
    # Match whole lines so the AP command cannot be patched as a STA command.
    line = "\t\t" + command + "\n"
    if text.count(line) != 1:
        raise RuntimeError("Portal save handler changed: " + command)
    text = text.replace(line, "\t\tif ! " + command + " >/dev/null 2>&1; then\n"
                        "\t\t\techo '{\"success\":false,\"error\":\"Invalid Wi-Fi settings\"}'\n"
                        "\t\t\treturn\n\t\tfi\n")
old = "\treboot -d 2 &"
if text.count(old) != 1:
    raise RuntimeError("Portal reboot handler changed")
text = text.replace(old, "\tk5-log portal.save.complete\n"
                    "\t(k5-reboot >/dev/null 2>&1) &")
api.write_text(text)

# Older Make output was accidentally included in some kernelrelease paths.
# Collect identical modules into the actual release path and regenerate depmod
# later in Buildroot's normal finalize stage. Preserve odd directories on the
# host; they must never consume space in the shipped SquashFS.
modules = target / "usr/lib/modules"
release = (target.parent / "build/linux-3.10.14/include/config/kernel.release").read_text().strip()
if "/" in release or "\n" in release or "make" in release:
    raise RuntimeError("Invalid kernel release")
canonical = modules / release
canonical.mkdir(parents=True, exist_ok=True)
for directory in list(modules.iterdir()):
    if directory == canonical:
        continue
    if "make[" not in directory.name:
        raise RuntimeError("Unexpected module release directory: " + directory.name)
    for module in directory.rglob("*.ko"):
        destination = canonical / "extra" / module.name
        destination.parent.mkdir(exist_ok=True)
        if destination.exists() and hashlib.sha256(destination.read_bytes()).digest() != hashlib.sha256(module.read_bytes()).digest():
            raise RuntimeError("Conflicting module payload: " + module.name)
        shutil.copy2(module, destination)
    trash = target.parent / "k5-malformed-module-paths"
    trash.mkdir(exist_ok=True)
    saved = trash / directory.name
    serial = 0
    while saved.exists():
        serial += 1
        saved = trash / (directory.name + "." + str(serial))
    shutil.move(directory, saved)

required = {"8188fu.ko", "jzmmc_v12.ko", "exfat.ko"}
found = {module.name for module in canonical.rglob("*.ko")}
if not required <= found:
    raise RuntimeError("Required modules missing: " + repr(required - found))
subprocess.run([str(target.parent / "host/sbin/depmod"), "-b", str(target), release], check=True)

# The obsolete late report exposes identifiers. Replace with the safe reporter.
(target / "etc/init.d/S95k5-boot-report").write_text("#!/bin/sh\nset -eu\n[ \"${1:-}\" = start ] || exit 0\nk5-log services.boot-complete\nk5-report\n")
(target / "etc/init.d/S95k5-boot-report").chmod(0o755)

for file in (profile / "overlay").rglob("*"):
    if file.is_file() and file.read_bytes().startswith(b"#!/bin/sh"):
        (target / file.relative_to(profile / "overlay")).chmod(0o755)

digest = hashlib.sha256()
for file in sorted(profile.rglob("*")):
    if file.is_file() and "__pycache__" not in str(file) and file.name != "k5-build-id":
        digest.update(str(file.relative_to(profile)).encode() + b"\0" + file.read_bytes())
revision = digest.hexdigest()
(target / "etc/k5-build-id").write_text(f"K5_BUILD_ID={version}\nK5_PROFILE_SHA256={revision}\n")
os_release = target / "usr/lib/os-release"
text = os_release.read_text()
lines = [f'BUILD_ID="{version}"' if line.startswith("BUILD_ID=") else line for line in text.splitlines()]
os_release.write_text("\n".join(lines) + "\n" + f'K5_PROFILE_SHA256="{revision}"\n')
print(f"K5_PROFILE_VERIFIED={revision}")
print(f"K5_BUILD_ID={version}")
