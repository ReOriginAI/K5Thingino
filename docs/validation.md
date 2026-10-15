# Validation

## Camera result

On 2026-10-12, after receiving the V3 distribution, the user reported **"yes it works now"**. This is a successful result for the original camera. There was no separate report identifying each tested Wi-Fi mode, video stream, Reset action, SD filesystem or cold-boot condition. The precise cause of the previous lockout remains unproven.

The report and exact kernel/rootfs/installer hashes are recorded in [hardware-validation.json](hardware-validation.json). Rebuilt images with different hashes do not inherit that result.

## Host checks

All 19 tests passed: 12 runtime/recovery tests and seven installer simulations. Coverage includes protected-AP configuration, escaped SSIDs and derived PSKs, invalid-input rejection, Wi-Fi-only reset, retained credentials, forced portal, successful WPA/DHCP state, missing DHCP, failed or hung launch, an independent guard during a blocked control command, and bounded shutdown.

Installer simulations check read-only mode, arm gating, wrong-map/image/factory rejection, backup collision protection, backups of all eight partitions, writing only the original OS partitions, erased tails, and recovery of both original OS partitions after an injected root-program failure. They use regular files, not camera flash.

The actual MIPS PSK binary was checked under QEMU. Source shell syntax was checked with MIPS BusyBox; shellcheck and shfmt passed. Artifact validation checks kernel options, uImage header/payload CRC and decompression, the embedded MTD command line, partition sizes, exact K5 overlays in the shipped SquashFS, module paths/dependencies, static MIPS installer, SD checksums and ZIP integrity.

Run `make test` and `make verify` to repeat the current checks. Full local logs are retained under `docs/logs/` and excluded from source control.

## Cleanup preservation

The working kernel, rootfs, installer binary and camera profile were preserved byte for byte during repository cleanup. Factory backups and all rescue archives were also preserved and checked against their earlier bytes. The current V3 distribution and ZIP remain under `dist/` and `releases/`; superseded copies were deleted at the user's request.

The historical V2 flash readbacks succeeded, but the old firmware locked up after portal configuration on two installations. Superseded V2 packages and old session diagnostics were pruned. The failed original installer remains quarantined and must never be installed.
