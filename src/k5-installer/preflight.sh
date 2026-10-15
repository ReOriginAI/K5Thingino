#!/bin/sh
# Wansview K5 (T21): NON-DESTRUCTIVE install compatibility probe
# Deliberately does not have erase or write operations.
SD="$1"
[ -n "$SD" ] || exit 1
P="$SD/k5-installer"
LOG="$P/preflight-report.txt"
: > "$LOG" || exit 1
exec > "$LOG" 2>&1
echo "Wansview K5 Thingino V3: READ ONLY preflight"
date 2>/dev/null || true
echo "--- kernel ---"
uname -a
echo "--- command line ---"
cat /proc/cmdline
echo "--- flash map ---"
cat /proc/mtd
echo "--- storage ---"
df -k "$SD" 2>/dev/null || true
echo "--- active modules ---"
cat /proc/modules 2>/dev/null | grep -Ei '8188|7601|jzmmc|jz_sfc' || true

ERRORS=0
check_mtd() {
    if grep -q "^$1: $2 00008000 \"$3\"$" /proc/mtd; then
        echo "PASS $1 ($3): expected partition layout"
    else
        echo "FAIL $1 ($3): partition differs from verified K5 stock image"
        ERRORS=$((ERRORS + 1))
    fi
}
check_mtd mtd0 00040000 boot
check_mtd mtd1 00280000 kernel
check_mtd mtd2 008e0000 root
check_mtd mtd3 00050000 syscfg
check_mtd mtd4 00050000 sysbak
check_mtd mtd5 00170000 minikernel
check_mtd mtd6 00240000 minirootfs
check_mtd mtd7 00010000 upgrade
if grep -q 'root=/dev/mtdblock2' /proc/cmdline; then
    echo "PASS: stock root=/dev/mtdblock2"
else
    echo "FAIL: unexpected root command line"
    ERRORS=$((ERRORS + 1))
fi
if grep -q 'mtdparts=jz_sfc:' /proc/cmdline; then
    echo "PASS: factory NOR driver partition command line"
else
    echo "FAIL: no factory jz_sfc partition arguments"
    ERRORS=$((ERRORS + 1))
fi
echo "--- candidate image files ---"
if [ -f "$P/uImage.t21" ] && [ -f "$P/rootfs.squashfs.t21" ]; then
    wc -c "$P/uImage.t21" "$P/rootfs.squashfs.t21"
    KERNEL_BYTES=$(wc -c < "$P/uImage.t21")
    ROOT_BYTES=$(wc -c < "$P/rootfs.squashfs.t21")
    if [ "$KERNEL_BYTES" -gt 0 ] && [ "$KERNEL_BYTES" -le 2621440 ]; then
        echo "PASS: kernel fits primary mtd1"
    else
        echo "FAIL: kernel exceeds stock mtd1"
        ERRORS=$((ERRORS + 1))
    fi
    if [ "$ROOT_BYTES" -gt 0 ] && [ "$ROOT_BYTES" -le 6291456 ]; then
        echo "PASS: SquashFS image fits primary mtd2"
    else
        echo "FAIL: rootfs exceeds stock mtd2"
        ERRORS=$((ERRORS + 1))
    fi
    if [ -f "$P/images.md5" ]; then
        echo "--- image checksum verification ---"
        (cd "$P" && md5sum -c images.md5) || ERRORS=$((ERRORS + 1))
    else
        echo "FAIL: images.md5 missing"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "INFO: no firmware images staged: diagnostics only"
fi
if [ -f "$P/INSTALL_NOW" ]; then
    echo "NOTICE: preflight never writes flash; the separately armed installer may run afterward"
fi
echo "PREFLIGHT_ERRORS=$ERRORS"
echo "No camera flash partitions have been written."
sync
exit "$ERRORS"
