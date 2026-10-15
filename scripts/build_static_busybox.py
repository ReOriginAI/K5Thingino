"""Build a self-contained updater so rootfs replacement cannot break its tools."""
from pathlib import Path
import os, shutil, subprocess
root=Path(__file__).resolve().parents[1]
out=root/"thingino-firmware/output/stable/wansview_k5_t21n_ov2735b_rtl8188fu-3.10.14-uclibc"
src=next(p for p in (out/"build").glob("busybox-*") if (p/"Makefile").exists())
dest=root/"archive/raptor-20261014/static-busybox-source"
config=(src/".config").read_text()
config=config.replace("# CONFIG_STATIC is not set", "CONFIG_STATIC=y").replace("CONFIG_PIE=y", "# CONFIG_PIE is not set")
if not dest.exists(): shutil.copytree(src,dest,symlinks=True)
env=dict(os.environ)
tools=root/"tools/local-toolchain/usr"
env["PATH"]=str(tools/"bin")+os.pathsep+env["PATH"]
env["LD_LIBRARY_PATH"]=str(tools/"lib/x86_64-linux-gnu")
with (root/"docs/logs/raptor-static-tools-20261014.log").open("w") as log:
    subprocess.run(["make","distclean"],cwd=dest,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    (dest/".config").write_text(config)
    args=["make","CROSS_COMPILE="+str(out/"host/bin/mipsel-linux-"),"ARCH=mips","EXTRA_CFLAGS=-Os","-j16"]
    subprocess.run(args+["oldconfig"],cwd=dest,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
    subprocess.run(args,cwd=dest,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    elf=subprocess.check_output(["readelf","-l",str(dest/"busybox")],text=True)
    assert "INTERP" not in elf
    shutil.copy2(dest/"busybox",root/"archive/raptor-20261014/busybox-static")
print("STATIC_UPDATER_TOOLS_READY")
