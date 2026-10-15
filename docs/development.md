# Development

The maintained source consists of the K5 profile in `firmware/` and the V3 installer in `src/k5-installer/`. No host command below flashes or connects to a camera.

## Prepared workspace

The existing `thingino-firmware/` checkout and its Buildroot output stay in place so cached absolute build paths remain valid. The base source commit recorded in the working release is `b310438feb288cbba05c053860975cd2bfc7e1b5`. Local K5 changes are identified separately by the profile and installer source hashes in the manifest.

`tools/` holds MIPS little-endian QEMU, lint tools and the locally extracted toolchain dependencies. Unused processor emulators and package downloads have been removed. `scripts/build_firmware.py` supplies the relocated toolchain paths to the host build. The upstream checkout has its own development instructions in `thingino-firmware/AGENTS.md`.

The upstream `dl/` download cache was pruned. Extracted build sources and the prepared compiler remain available; clean builds or newly required packages must download their pinned dependencies again.

A fresh environment must prepare that source revision, its pinned submodules, upstream build patches/toolchain dependencies and normal Thingino host prerequisites. Follow the upstream setup instructions; do not replace the working baseline with an arbitrary newer target or full-flash image.

## Host commands

```sh
make profile
make build
make test
make package
make verify
```

`make profile` compares the maintained camera profile with the local checkout. If it needs replacement, it archives the previous profile rather than deleting it. `make build` runs configuration, kernel and SquashFS build stages sequentially and records the full output under `docs/logs/`.

`make test` runs the 12 runtime/recovery tests and seven installer simulations. Requirements: Python 3, native GCC and MTD headers, BusyBox, the prepared MIPS target binaries, QEMU, and the private original backup archive under `backups/`. The simulations operate on regular files and mocked MTD ioctls. Each run replaces the previous test logs with the latest complete results.

`make package` checks kernel options, the stock-compatible command line embedded in the actual LZMA uImage, image CRCs/sizes, the 6 MiB rootfs limit, a static MIPS installer, and passing host tests. It preserves previous distributions in `archive/releases/` and produces a disarmed `dist/` plus `releases/k5-thingino-v3-sdcard.zip`.

`make verify` checks complete SD-file checksum coverage, ZIP contents, activation markers, image metadata and the actual source overlays/modules inside the SquashFS. It does not require a camera.

## Release identity

The user's success report applies only to the exact payload hashes in `docs/hardware-validation.json`. The packager attaches that report only when kernel, rootfs and installer hashes all match. A new build with different bytes requires new camera validation even if its short version label is unchanged.

The repository cleanup did not rebuild or change the working camera binaries. Superseded V1/V2 packages and investigation scripts were deleted. The failed original installer remains under `quarantine/` for reference and must never be installed.

## Private factory backup

`python3 scripts/reconstruct_factory.py` verifies the private original archive and reconstructs the 16 MiB image locally when absent. It refuses to overwrite a mismatched existing image. Keep its input/output private and never use the full-flash image as a replacement for the two-file SD recovery procedure.
