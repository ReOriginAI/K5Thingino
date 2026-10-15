WANSVIEW K5 - NEW THINGINO V3 SD PACKAGE
Build: k5-v3-sd-recovery-20261012

For this factory-restored T21N / OV2735B / RTL8188FU / 16 MiB K5 only.
The user reported this V3 release working on the original camera on
2026-10-12. Host checks also passed. Individual Wi-Fi, video, Reset and
SD checks were not separately documented. Newly rebuilt images require
new camera testing; the earlier failure's exact cause remains unproven.

START HERE - COPY THE CONTENTS OF dist, NOT THE dist FOLDER

1. Use an empty FAT32 SD card with at least 32 MiB free. Save any old SD
   files and backups on your computer first. Do not merge this package
   with an older installer, recovery card, run.sh, runonce.sh or uenv.txt.
2. Drag every file and folder INSIDE dist to the card's root. You should
   see facDiag and k5-installer directly on the card. Leave the file
   ARM-BY-RENAMING-TO-INSTALL_NOW.txt unchanged for the first boot.
3. With the camera powered OFF, insert the card. Power it on and allow
   five minutes. The first run checks compatibility and writes reports
   to the SD card only. It does not change camera firmware.
4. Remove power before removing the card. Read these two files:
     k5-installer/preflight-report.txt: must end with PREFLIGHT_ERRORS=0
     k5-installer/read-only-validation.log: must contain READ_ONLY_V3_PASS
   The card's facDiag should have become facDiag.probed. If either check
   failed or reports are missing, stop here and keep factory firmware.

INSTALL THE NEW BUILD AFTER BOTH CHECKS PASS

5. On that same checked card, make these TWO renames:
     facDiag.probed -> facDiag
     k5-installer/ARM-BY-RENAMING-TO-INSTALL_NOW.txt -> INSTALL_NOW
   Keep INSTALL_NOW inside k5-installer. This is the explicit install
   switch; copying this package without the rename cannot flash it.
6. With the camera powered OFF, insert the card and power on. Keep power
   stable and do not interrupt or remove the card. Allow at least five
   minutes for backup, flashing, readback verification and reboot.
7. Look for the open THINGINO-xxxx Wi-Fi network. Connect and open
   http://172.16.0.1 to configure it. If no network appears after five
   minutes, power off before removing the card and inspect flash.log.
8. Read k5-installer/flash.log. SUCCESS means the flash contents were
   verified. It does not prove that Wi-Fi or camera video works.
   The installer also creates k5-installer/backup/ with all eight
   original flash partitions. Keep these backups private and save them
   on your computer. Never reuse this flashed card unchanged to install
   again: existing backup files intentionally prevent overwriting them.

WI-FI SETUP AND RECOVERY

- Joining an existing network: use a 2.4 GHz WPA/WPA2 network. After
  saving, the camera should join your router; find its address in your
  router's client list.
- Creating a protected hotspot: look for the SSID YOU chose, then open
  http://100.64.1.1. It will not be named THINGINO-xxxx in this mode.
- If configured Wi-Fi fails, V3 attempts an automatic reboot back to the
  open THINGINO-xxxx portal. Allow up to five minutes. Saved Wi-Fi
  credentials are retained; saving new settings permits another attempt.
  This fallback depends on working kernel/watchdog hardware and still
  needs testing on this unit.
- To force the portal with SD, power off, rename the card's
  FORCE-PORTAL-BY-RENAMING-TO-FORCE_PORTAL.txt to FORCE_PORTAL, then boot
  with the card. This affects V3 runtime only and does not reinstall it.
  Remove or rename FORCE_PORTAL before trying a normal configured boot.
- In this NEW V3 build, holding Reset for five seconds and releasing
  resets Wi-Fi only and requests a reboot. Do not apply this instruction
  to the old failing firmware. V3 removes the kernel-erasing button action.

SD REPORTS AND REQUIRED CAMERA CHECKS

Keep the installation card inserted for the first V3 boot so FAT32
diagnostics can be checked before Wi-Fi configuration. Reports appear in
k5-logs/:
  init-latest.txt       Early boot, overlay mount, and pivot phases.
  events-latest.txt     Wi-Fi and shutdown progress, without credentials.
  runtime-latest.txt    Firmware ID, memory, flash layout and error counts.
  *-previous.txt       Previous boot's safe reports, when available.

Optional detailed debugging: rename
COLLECT-PRIVATE-LOGS-BY-RENAMING-TO-COLLECT_PRIVATE_LOGS.txt to
COLLECT_PRIVATE_LOGS before a V3 boot. This adds PRIVATE-*.txt files with
raw kernel and Wi-Fi output. They may contain SSIDs, MACs and secrets.
Do not share raw private logs, backups or Wi-Fi passwords publicly.

After installation, check the open portal, FAT32 reports, Wi-Fi client,
protected hotspot, Reset, a cold boot with no SD, and a live camera stream.
Actual SD mounting, watchdog fallback, reboot, Wi-Fi and video behavior
were not individually documented in the user's success report. exFAT is included
but only FAT32 should be used for this factory installer.

FACTORY RECOVERY IF NEEDED

The workspace's existing archive
recovery/k5-uboot-FACTORY-KERNEL-AND-ROOT-RECOVERY-UNTESTED.zip contains the TWO
original recovery images. Despite its historical filename, you previously
confirmed this combined recovery worked on this exact camera.

Use a separate empty FAT32 card with ONLY ub_kernel.bin and ub_rootfs.bin
at its root. Do not mix them with facDiag or this installer. Power off for
insertion, power on and allow five minutes, then remove power before
removing the card. Boot with no SD and confirm factory firmware works.
Never use ub_boot.bin. This package preserves the original U-Boot,
calibration/config backups and mini-recovery partitions.

Flash error rollback is best effort. It cannot guarantee recovery after
power loss or a firmware/runtime failure. All work preparing this package
was performed on the development host; no camera was accessed or flashed.
