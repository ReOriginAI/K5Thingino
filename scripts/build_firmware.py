"""Rebuild only the K5 kernel and root filesystem on the development host."""
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CAMERA = "wansview_k5_t21n_ov2735b_rtl8188fu"


def main():
    checkout = ROOT / "thingino-firmware"
    if not (checkout / "buildroot/Makefile").exists():
        raise SystemExit("Prepare the pinned Thingino/Buildroot checkout first; see docs/development.md")
    env = dict(os.environ, CAMERA=CAMERA, WORKFLOW="1")
    local_tools = ROOT / "tools/local-toolchain/usr"
    if local_tools.exists():
        env["PATH"] = str(local_tools / "bin") + os.pathsep + env.get("PATH", "")
        libs = str(local_tools / "lib/x86_64-linux-gnu")
        env["LD_LIBRARY_PATH"] = libs + (os.pathsep + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    logs = ROOT / "docs/logs"
    logs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    log = logs / f"firmware-build-{stamp}.log"
    with log.open("w") as output:
        for goal in ("force-config", "br-linux-reconfigure", "br-rootfs-squashfs"):
            print(f"Building {goal}; full output: {log.relative_to(ROOT)}", flush=True)
            subprocess.run(["make", "--no-print-directory", goal], cwd=checkout,
                           env=env, stdout=output, stderr=subprocess.STDOUT, check=True)
    print("Kernel/rootfs built. Run make test, then make package. No camera accessed.")


if __name__ == "__main__":
    main()
