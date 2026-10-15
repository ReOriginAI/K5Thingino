# Hardware and flash layout

The original unit is a Wansview K5/K3C with an Ingenic T21N, OV2735B image sensor, RTL8188FU-family Wi-Fi, about 64 MiB RAM and 16 MiB SPI NOR. Published K5 targets using MT7601U are different revisions.

Factory U-Boot is 2013.07, dated 2019-08-26. Stock Linux is `3.10.14__isvp_turkey_1.0__`, built 2021-04-01. The factory NOR erase size is `0x8000`.

## Factory partitions

| MTD | Label | Offset | Size |
| --- | --- | --- | --- |
| 0 | boot | `0x000000` | `0x040000` |
| 1 | kernel | `0x040000` | `0x280000` |
| 2 | root | `0x2c0000` | `0x8e0000` |
| 3 | syscfg | `0xba0000` | `0x050000` |
| 4 | sysbak | `0xbf0000` | `0x050000` |
| 5 | minikernel | `0xc40000` | `0x170000` |
| 6 | minirootfs | `0xdb0000` | `0x240000` |
| 7 | upgrade | `0xff0000` | `0x010000` |

The installer uses the factory map and writes only partitions 1 and 2. It checks factory kernel CRC32 `a8a87785` and root CRC32 `d18d5787` before any write.

## Thingino layout

The stock bootloader and kernel offset are retained. The original root area is divided into 6 MiB SquashFS at `0x2c0000` and 2,944 KiB JFFS2 data at `0x8c0000`. Data ends at `0xba0000`; all following factory partitions keep their original physical offsets. The forced kernel command line is recorded in the release manifest.

Thingino therefore uses `mtd1` for the kernel, `mtd2` for rootfs and `mtd3` for data. Indices for the later factory partitions shift by one. Generic helpers must not assume that `mtd1` is U-Boot ENV.

## GPIOs

| Function | GPIO |
| --- | --- |
| Reset button | 50 |
| SD card detect | 52 |
| Speaker | 63, active low |
| Red LED | 72, active low |
| Blue LED | 73, active low |
| IR LED | 49 |
| IR cut | 79 / 80 |

LED observations alone do not establish boot or Wi-Fi state. SD reports and actual network/video behavior provide separate evidence.
