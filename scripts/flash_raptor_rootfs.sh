#!/tmp/raptor-upgrade/busybox sh
# One-time K5 rootfs update. All commands run from static tools in RAM.
set -eu
trap '' HUP INT TERM
b=/tmp/raptor-upgrade/busybox
cd /tmp/raptor-upgrade
old=90444ef51f31387c76b0ae22e02e506084f1551cb286e8f6516a0635ebb8d9b2
new=9bf59021c3a43e9d06b9121a819ae818648b313f133860e0add357a97c1cf623
check_hash() {
    actual=$("$b" sha256sum "$1")
    [ "${actual%% *}" = "$2" ]
}
check_flash() {
    actual=$("$b" dd if=/dev/mtd2ro bs=4096 count="$1" 2>/dev/null | "$b" sha256sum)
    [ "${actual%% *}" = "$2" ]
}
check_hash old-rootfs.bin "$old"
check_hash new-rootfs.squashfs "$new"
check_hash busybox f415784c1a0d3c01c97d71dc9e9ac79edd530fbc660bb981d1b8d08763e3dc6c
[ "$("$b" stat -c %s old-rootfs.bin)" -eq 6291456 ]
[ "$("$b" stat -c %s new-rootfs.squashfs)" -eq 5033984 ]
"$b" grep -q '^mtd2: 00600000 00010000 "rootfs"$' /proc/mtd
"$b" grep -q '^IMAGE_ID=wansview_k5_t21n_ov2735b_rtl8188fu$' /etc/os-release
check_flash 1536 "$old"
echo PRECHECK_PASS
for service in S31prudynt S10daynightd S60uhttpd S96onvif_discovery S97onvif_notify S95thingino-agent S91mqttsub S93ha S95recordmgr S98recorder; do
    [ ! -x "/etc/init.d/$service" ] || "$b" timeout 8 "/etc/init.d/$service" stop || true
done
"$b" killall watchdog || true
"$b" sleep 1
"$b" watchdog -T 60 -t 5 -F /dev/watchdog &
wdpid=$!
"$b" sleep 1
"$b" kill -0 "$wdpid"
"$b" sync
echo FLASHING_ROOTFS_ONLY
if "$b" flashcp -v new-rootfs.squashfs /dev/mtd2 && check_flash 1229 "$new"; then
    echo RAPTOR_ROOTFS_VERIFIED
else
    echo RESTORING_PREVIOUS_ROOTFS
    if "$b" flashcp -v old-rootfs.bin /dev/mtd2 && check_flash 1536 "$old"; then
        "$b" mv /etc/raptor.conf /etc/raptor.conf.failed-upgrade
        echo ROLLBACK_VERIFIED
    else
        echo ROLLBACK_FAILED
        exit 1
    fi
fi
"$b" sync
echo REBOOTING
"$b" reboot -f
"$b" sleep 5
[ ! -w /proc/jz/reset/reset ] || echo wdt >/proc/jz/reset/reset
