"""Verify rootfs bytes and preservation of all non-rootfs OS/recovery regions."""
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(__file__).resolve().parents[1]
socket=sys.argv[1]
base=["ssh","-S",socket,"-o","BatchMode=yes","root@192.168.1.54"]
parts=[0,1,4,5,6,7,8]
r=subprocess.run(base+["sha256sum "+" ".join("/dev/mtd"+str(n)+"ro" for n in parts)],text=True,capture_output=True,check=True,timeout=45)
for line in r.stdout.splitlines():
    sha,device=line.split()
    n=int(device.removeprefix("/dev/mtd").removesuffix("ro"))
    expected=hashlib.sha256((root/"backups/pre-raptor-20261014"/("mtd"+str(n)+".bin")).read_bytes()).hexdigest()
    assert sha==expected,device
meta=json.loads((root/"docs/logs/raptor-final-payload-20261014.json").read_text())
count=meta["size"]//4096
r=subprocess.run(base+[f"dd if=/dev/mtd2ro bs=4096 count={count} 2>/dev/null | sha256sum"],text=True,capture_output=True,check=True,timeout=20)
assert r.stdout.split()[0]==meta["sha256"]
print("FINAL_FLASH_HASH_PASS")
print("BOOTLOADER_KERNEL_FACTORY_CONFIG_AND_RECOVERY_UNCHANGED")
