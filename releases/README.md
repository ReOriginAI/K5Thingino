# Generated release

The current SD installer archive is `k5-thingino-v3-sdcard.zip`; its extracted contents are in `../dist/`.

V3 was reported working on the original camera on 2026-10-12. The hardware report applies to the exact kernel/rootfs/installer hashes in `../docs/hardware-validation.json`. Individual feature checks were not separately documented.

Run `make verify` to check the archive against the SD distribution. Run `make package` after a successful host build/test cycle to generate a new disarmed package. Older output is preserved in the excluded `archive/releases/` directory.

Generated ZIPs are excluded from source control. Publish a release artifact separately if distributing it; do not include private factory backups, recovery archives or raw diagnostics.
