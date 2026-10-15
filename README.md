# Wansview K5 Thingino SD installer

An SD-only Thingino port and factory-firmware installer for the Wansview K5 with a K3C board, Ingenic T21N, OV2735B sensor, RTL8188FU Wi-Fi and 16 MiB SPI NOR.

**Status:** the user reported V3 working on the original camera on 2026-10-12. The earlier post-configuration lockout is no longer reported with this build. This is one unit's success report; individual feature checks still depend on exact kernel/rootfs/installer hashes and the same hardware family.

## Install

IMPORTANT: You must do a clean flash first.

1. Insert a blank SD card into your computer and format it as FAT32.
2. Open the `cleanflash/` directory in this repository.
3. Drag and drop the files from `cleanflash/` to the root of the SD card.
4. Power off the camera, insert the SD card, and power the camera back on.
5. Let the clean flash complete before continuing. Do not remove power during the process.
6. After the clean flash finishes, power off the camera and remove the SD card.
7. Re-format the SD card to FAT32 again.
8. Open the `dist/` directory in this repository.
9. Drag and drop the files from `dist/` to the root of the freshly formatted SD card.
10. Insert the SD card, power the camera on, and wait for the update/installer to finish.

> Quick note: use `cleanflash/` first for the initial clean flash, then re-format and use `dist/` for the final SD-card image. Do not mix the two directories on the same card.

The prepared `dist/` directory contains the SD-card contents. Copy its **contents** to an empty FAT32 card. The package starts disarmed and runs a read-only compatibility check first.

Follow the [SD installation instructions](src/k5-installer/README-V3.txt) for validation and the two arming renames. The current ZIP is generated at `releases/k5-thingino-v3-sdcard.zip`.

This installer starts from the exact factory firmware checked for this unit. It verifies the factory partition map and image checksums, backs up all eight partitions, and writes only the original factory data required for the selected flow.

Insert and remove SD cards with power disconnected. Never include `ub_boot.bin` or mix factory-recovery images with the installer.

## What V3 changes

- Built-in FAT32 support and SD boot diagnostics.
- Configured Wi-Fi starts without blocking the other boot services.
- Failed Wi-Fi attempts can return to an open portal while retaining credentials.
- Bounded shutdown with the hardware watchdog kept armed.
- Long Reset presses reset Wi-Fi; full reset only erases the data overlay.
- Module paths and dependencies are checked; incompatible U-Boot ENV writes are disabled.

The initial portal is at `http://172.16.0.1`. A configured protected hotspot uses the chosen SSID and `http://100.64.1.1`.

## Repository layout

| Path | Contents |
| --- | --- |
| `firmware/` | Maintained K5 camera profile, kernel fragment and rootfs overlay |
| `src/k5-installer/` | Current C installer, factory SD hook and packager |
| `tests/` | Runtime/recovery and flash-simulation tests |
| `scripts/` | Profile installation, host build, verification and test runners |
| `docs/` | Hardware layout, development guide and validation evidence |
| `dist/` | Generated drag-and-drop SD contents |
| `releases/` | Generated current release ZIP |
| `recovery/` | Private, device-specific factory recovery archives |
| `backups/` | Private original factory images |
| `quarantine/` | Failed original installer retained for reference; never install it |
| `tools/`, `thingino-firmware/` | Local dependencies and the prepared upstream checkout/build cache |

Device backups, recovery binaries, quarantined files, logs, credentials, build caches and generated artifacts are excluded by `.gitignore`. Keep original factory data and raw `PRIVATE-*` diagnostics private. Never publish them or remove their ignore rules.

## Develop and verify

On the prepared development host:

```sh
make verify   # Verify SD checksums, image formats, source overlays and ZIP
make test     # Run all 19 host tests; no camera access
make profile  # Install or check the maintained K5 profile
make build    # Rebuild the kernel/rootfs locally
make package  # Create a disarmed SD package from the built images
```

See [development](docs/development.md), [hardware and flash layout](docs/hardware.md), [validation](docs/validation.md) and [factory recovery](recovery/README.md).

The cached upstream source comes from [Thingino](https://github.com/themactep/thingino-firmware). The K5 profile is specific to the RTL8188FU revision; the published MT7601U K5 profiles describe different hardware and are not interchangeable.
