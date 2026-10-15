# Factory recovery for the original K5

This directory contains private recovery material for the original camera. Its binary contents are excluded from source control.

The user confirmed successful factory recovery using **both** original `ub_kernel.bin` and `ub_rootfs.bin`. The preserved archive is `k5-uboot-FACTORY-KERNEL-AND-ROOT-RECOVERY-UNTESTED.zip`. Its filename reflects an earlier status; the combined restoration was subsequently demonstrated on this unit.

## Procedure

1. Use a separate empty FAT32 SD card.
2. Extract only `ub_kernel.bin` and `ub_rootfs.bin` from that archive to the card's root.
3. Disconnect camera power before inserting the card.
4. Power on and allow five minutes for the updater to finish.
5. Disconnect power before removing the card; boot with no SD and confirm factory firmware works.

Never include `ub_boot.bin`, `facDiag`, Thingino images or installer files on the recovery card. Kernel-only restoration is insufficient after a full Thingino installation.

`legacy/` preserves older kernel-only rescue archives and packages for historical reference. Do not use them as the current combined factory-recovery procedure. The complete original flash backups remain in `../backups/`.

This recovery was demonstrated with the preserved original U-Boot on this exact unit. It does not establish recovery for another revision or damaged flash/bootloader.
