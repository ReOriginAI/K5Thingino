# Wansview K5 project instructions

Workspace: `/home/ubuntu/projects/k5project`. Updated 2026-10-12.

## Current state

The user reported **"yes it works now"** after receiving the V3 SD package. Treat V3 as user-reported working on the original unit. Do not assume every Wi-Fi mode, Reset, cold boot, SD filesystem or video check was separately tested. The exact earlier lockout cause is still unproven.

Working payload identity and the scoped user report are in `docs/hardware-validation.json` and `dist/k5-installer/manifest.json`. V3 kernel: 1,516,106 bytes, CRC32 `afaa648c`; rootfs: 5,464,064 bytes, CRC32 `b51dfa34`. Cleanup changed documentation/paths only; the kernel, rootfs, installer binary and maintained firmware profile were preserved.

## Safety and privacy

- Never flash, upload or otherwise write camera NOR unless the user explicitly requests that action. Host preparation is allowed.
- Preserve all factory backups and recovery archives. Never overwrite the bootloader, factory syscfg/sysbak or mini-recovery partitions. Never use `ub_boot.bin`.
- Prefer SD-only work. The user does not want UART/disassembly.
- Remove power before inserting/removing SD cards. Allow flash operations to finish.
- Never install the failed original installer or repeat V2 as a fix. The original failed ZIP remains in `quarantine/FAILED-THINGINO-INSTALLER-DO-NOT-USE.zip`; superseded V2 packages were deleted.
- Never treat flash `SUCCESS` or a boot report as proof of Wi-Fi/video functionality.
- The **old** image's 20-second Reset mapping may erase the kernel. Do not recommend that action on old firmware. V3 uses Wi-Fi-only long Reset and a data-only full reset.
- Backups, recovery binaries, `uenv.txt`, raw session/diagnostic logs and `PRIVATE-*` files can contain credentials/MACs. Do not publish them or remove their ignore rules.

## Source and workflow

- `firmware/wansview_k5_t21n_ov2735b_rtl8188fu/` is the maintained, standalone profile. Keep its exact working content unless performing requested firmware development.
- `src/k5-installer/` contains the active V3 installer/packager.
- `thingino-firmware/` is the existing upstream checkout and build cache. Its `AGENTS.md` applies to edits there, including the Thingino development skill. Do not move the checkout/build output: Buildroot uses absolute paths.
- `make profile` copies the maintained profile into that checkout, preserving an existing changed profile before replacement. `make build` operates on the host only.
- `make test` runs 12 recovery/runtime tests and 7 regular-file MTD simulations. It needs the private original backup, prepared target binaries, host GCC/BusyBox and QEMU. Full logs are kept under `docs/logs/`.
- `make verify` checks the actual distribution and ZIP. `make package` starts disarmed, validates built images and passing tests, and preserves existing output in `archive/releases/` before replacement.
- Hardware validation applies only to matching kernel/rootfs/installer SHA-256 hashes. Never carry the user's success report onto different rebuilt payloads.
- The user explicitly requested pruning on 2026-10-12. Superseded packages, session history, unused tools and download caches were deleted. Preserve current working artifacts, maintained source, required build dependencies, all factory backups and recovery archives, and the quarantined failed installer. Test runs retain only their latest full logs.

## Hardware and recovery

Camera: K3C board, T21N, OV2735B, RTL8188FU, about 64 MiB RAM, 16 MiB SPI NOR. Do not substitute MT7601U profiles.

The factory kernel starts at 0x040000, size 0x280000. Factory root starts at 0x2c0000, size 0x8e0000. V3 divides only that root region into 6 MiB SquashFS and 2,944 KiB data. Original non-OS physical offsets are preserved; MTD indices after root change in Thingino.

The proven factory restoration uses **both** original `ub_kernel.bin` and `ub_rootfs.bin` on a separate FAT32 card. Restoring only the kernel after Thingino is insufficient. The preserved combined archive is `recovery/k5-uboot-FACTORY-KERNEL-AND-ROOT-RECOVERY-UNTESTED.zip`; its filename is historical, and the user confirmed the two-file recovery worked. See `recovery/README.md`.

Original backup: `backups/k5-factory-backup.zip`, SHA-256 `80818c697e08dd9b9e90a2830ef8a4364d20a3ef8ab629d5d5c45849ddf9953e`. Reconstructed image: `backups/wansview-k5-stock-fullflash-16MiB.bin`, SHA-256 `8bce987662b47bccdd0326fdbaae3943bbfd43ed37e345d2b168771f586f1030`. The original root-level duplicate is preserved under `backups/copies/`.

V2 independently verified its flash writes and reached the open portal, but saving either client Wi-Fi or a protected hotspot reproduced the steady-red lockout twice. No post-save kernel log established the cause. The user then reported V3 working; the current report takes precedence over the earlier camera state. See `docs/validation.md` for retained evidence.
