"""Install a K5 post-build guard against stale per-package TLS snapshots."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/"thingino-firmware/configs/cameras/wansview_k5_t21n_ov2735b_rtl8188fu/post_build.py"
text=p.read_text()
marker="# K5 Raptor: restore authoritative rebuilt ELF files after cached-tree merge."
if marker in text: raise SystemExit("Cache guard already installed")
block="""
# K5 Raptor: restore authoritative rebuilt ELF files after cached-tree merge.
if (target / "usr/bin/rvd").exists():
    import os
    providers = {"mbedtls", "libcurl", "mbedtls-certgen", "thingino-agent",
                 "thingino-mosquitto-20x", "thingino-onvif", "thingino-uhttpd", "thingino-raptor"}
    replaced = 0
    strip = target.parent / "host/bin/mipsel-linux-strip"
    for listing in (target.parent / "build").glob("*/.files-list.txt"):
        for line in listing.read_text().splitlines():
            provider, relative = line.split(",", 1)
            if provider not in providers:
                continue
            source = target.parent / "per-package" / provider / "target" / relative
            if source.is_symlink() or not source.is_file():
                continue
            if source.read_bytes()[:4] != b"\\x7fELF":
                continue
            destination = target / relative
            temp = destination.with_name(destination.name + ".raptor-new")
            shutil.copy2(source, temp)
            subprocess.run([str(strip), "--strip-unneeded", str(temp)], check=True)
            os.replace(temp, destination)
            replaced += 1
    print(f"K5_RAPTOR_AUTHORITATIVE_ELF_FILES={replaced}")
"""
needle='digest = hashlib.sha256()'
assert text.count(needle)==1
p.write_text(text.replace(needle,block+"\n"+needle))
# Build only the rootfs, using the same pinned hardware/output.
s=(root/"scripts/build_raptor.py").read_text()
start=s.index('    for goal in ("br-mbedtls-reconfigure"')
end=s.index('print("RAPTOR_BUILD_COMPLETE"',start)
s=s[:start]+'''    subprocess.run(["make", "--no-print-directory", "br-rootfs-squashfs"], cwd=checkout, env=env, stdout=output, stderr=subprocess.STDOUT, check=True)
'''+s[end:]
(root/"scripts/build_raptor.py").write_text(s)
print("POST_BUILD_CACHE_GUARD_INSTALLED")
