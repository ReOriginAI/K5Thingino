"""Build the Raptor rootfs against the preserved K5 hardware baseline."""
from pathlib import Path
import os, shutil, subprocess
root = Path(__file__).resolve().parents[1]
checkout = root / "thingino-firmware"
out = checkout / "output/stable/wansview_k5_t21n_ov2735b_rtl8188fu-3.10.14-uclibc"
archive = root / "archive/raptor-20261014"
archive.mkdir(parents=True, exist_ok=True)
fragment = checkout / "user/wansview_k5_t21n_ov2735b_rtl8188fu/local.fragment"
fragment.parent.mkdir(parents=True, exist_ok=True)
fragment.write_text("""BR2_PACKAGE_THINGINO_STREAMER_RAPTOR=y
# BR2_PACKAGE_THINGINO_STREAMER_PRUDYNT is not set
# BR2_PACKAGE_PRUDYNT_T is not set
# BR2_PACKAGE_THINGINO_DAYNIGHTD is not set
# BR2_PACKAGE_THINGINO_RAPTOR_WEBTORRENT is not set
""")
env = dict(os.environ, CAMERA="wansview_k5_t21n_ov2735b_rtl8188fu", IP="192.168.1.54",
           WORKFLOW="1", THINGINO_OUTPUT_DIR=str(out))
tools = root / "tools/local-toolchain/usr"
env["PATH"] = str(tools / "bin") + os.pathsep + env.get("PATH", "")
env["LD_LIBRARY_PATH"] = str(tools / "lib/x86_64-linux-gnu") + (os.pathsep + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
log = root / "docs/logs/raptor-build-20261014.log"
with log.open("w") as output:
    subprocess.run(["make", "--no-print-directory", "force-config"], cwd=checkout, env=env, stdout=output, stderr=subprocess.STDOUT, check=True)
    target = out / "target"
    stale = ("usr/bin/prudynt", "etc/init.d/S31prudynt", "etc/init.d/S10daynightd")
    for relative in stale:
        file = target / relative
        if file.exists():
            saved = archive / "removed-target" / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file), str(saved))
    for goal in ("br-thingino-ustream-ssl-reconfigure", "br-thingino-raptor-reconfigure", "br-rootfs-squashfs"):
        subprocess.run(["make", "--no-print-directory", goal], cwd=checkout, env=env, stdout=output, stderr=subprocess.STDOUT, check=True)
print("RAPTOR_BUILD_COMPLETE", out / "images/rootfs.squashfs")
