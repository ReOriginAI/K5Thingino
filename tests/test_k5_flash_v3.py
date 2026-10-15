"""Run the real installer algorithm against regular files and mocked MTD ioctls."""
from pathlib import Path
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile
import zlib

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "tools/test-work"
IMAGES = ROOT / "thingino-firmware/output/stable/wansview_k5_t21n_ov2735b_rtl8188fu-3.10.14-uclibc/images"
SIZES = [0x40000, 0x280000, 0x8e0000, 0x50000, 0x50000, 0x170000, 0x240000, 0x10000]
NAMES = ["boot", "kernel", "root", "syscfg", "sysbak", "minikernel", "minirootfs", "upgrade"]
SHIM = r'''
#define _GNU_SOURCE
#include <errno.h>
#include <limits.h>
#include <mtd/mtd-user.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>
ssize_t __real_write(int, const void *, size_t);
static const unsigned sizes[] = {0x40000,0x280000,0x8e0000,0x50000,0x50000,0x170000,0x240000,0x10000};
static int index_mtd(int fd) {
    char link[PATH_MAX], path[PATH_MAX];
    int n=snprintf(link,sizeof(link),"/proc/self/fd/%d",fd);
    if(n<0 || (size_t)n>=sizeof(link)) abort();
    ssize_t got=readlink(link,path,sizeof(path)-1);
    if(got<0) return -1;
    path[got]=0;
    char *p=strstr(path,"/dev/mtd");
    if(!p) return -1;
    char *end;
    long i=strtol(p+8,&end,10);
    return *end==0 && i>=0 && i<8 ? (int)i : -1;
}
static void event(const char *op,int i) {
    FILE *f=fopen(getenv("K5_SIM_EVENTS"),"a");
    if(!f) abort();
    fprintf(f,"%s mtd%d\n",op,i);
    if(fclose(f)) abort();
}
int __wrap_ioctl(int fd,unsigned long request,...) {
    va_list ap;
    va_start(ap,request);
    void *arg=va_arg(ap,void*);
    va_end(ap);
    int i=index_mtd(fd);
    if(i<0) {errno=ENOTTY; return -1;}
    if(request==MEMGETINFO) {
        struct mtd_info_user *info=arg;
        memset(info,0,sizeof(*info));
        info->type=MTD_NORFLASH; info->size=sizes[i]; info->erasesize=0x8000;
        return 0;
    }
    if(request==MEMERASE) {
        struct erase_info_user *erase=arg;
        unsigned char buf[0x8000];
        memset(buf,0xff,sizeof(buf));
        if(erase->length!=sizeof(buf) || erase->start+erase->length>sizes[i]) abort();
        event("ERASE",i);
        return pwrite(fd,buf,sizeof(buf),erase->start)==sizeof(buf) ? 0 : -1;
    }
    errno=ENOTTY; return -1;
}
ssize_t __wrap_write(int fd,const void *data,size_t length) {
    static int failed=0;
    int i=index_mtd(fd);
    if(i>=0) {
        event("WRITE",i);
        if(i==2 && getenv("K5_SIM_FAIL_ROOT") && !failed) {
            failed=1; errno=EIO; return -1;
        }
    }
    return __real_write(fd,data,length);
}
int __wrap_reboot(int command) {
    (void)command;
    event("REBOOT",-1);
    errno=EPERM; return -1;
}
'''


class InstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WORK.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix="v3-flash-sim-", dir=WORK)
        cls.device = Path(cls.temp.name)
        for directory in ("dev", "proc", "k5-installer"):
            (cls.device / directory).mkdir()
        with ZipFile(ROOT / "backups/k5-factory-backup.zip") as archive:
            cls.factory = [archive.read(f"k5-factory-backup/mtd{i}.bin") for i in range(8)]
        assert [len(data) for data in cls.factory] == SIZES
        assert zlib.crc32(cls.factory[1]) == 0xa8a87785
        assert zlib.crc32(cls.factory[2]) == 0xd18d5787
        cls.kernel = (IMAGES / "uImage").read_bytes()
        cls.rootfs = (IMAGES / "rootfs.squashfs").read_bytes()
        text = (ROOT / "src/k5-installer/k5_flash_v3.c").read_text()
        text = text.replace('"/mnt/mmc/k5-installer"', '"' + str(cls.device / "k5-installer") + '"')
        text = text.replace('"/mnt/mmc"', '"' + str(cls.device) + '"')
        text = text.replace('"/dev/mtd', '"' + str(cls.device) + '/dev/mtd')
        text = text.replace('"/proc/mtd"', '"' + str(cls.device / "proc/mtd") + '"')
        text = text.replace('"/proc/cmdline"', '"' + str(cls.device / "proc/cmdline") + '"')
        # Test paths are longer than real /dev/mtdN names; only the host
        # simulation needs larger pathname buffers.
        text = text.replace("dev[32]", "dev[PATH_MAX]")
        (cls.device / "installer.c").write_text(text)
        (cls.device / "shim.c").write_text(SHIM)
        flags = [f"-DEXPECT_KERNEL_SIZE={len(cls.kernel)}u", f"-DEXPECT_ROOT_SIZE={len(cls.rootfs)}u",
                 f"-DEXPECT_KERNEL_CRC32=0x{zlib.crc32(cls.kernel):08x}u",
                 f"-DEXPECT_ROOT_CRC32=0x{zlib.crc32(cls.rootfs):08x}u"]
        subprocess.run(["gcc", "-std=gnu11", "-Os", "-Wall", "-Wextra", "-Werror", *flags,
                        str(cls.device / "installer.c"), str(cls.device / "shim.c"),
                        "-Wl,--wrap=ioctl", "-Wl,--wrap=write", "-Wl,--wrap=reboot",
                        "-o", str(cls.device / "installer")], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.package = self.device / "k5-installer"
        if self.package.exists():
            shutil.rmtree(self.package)
        self.package.mkdir()
        for i, data in enumerate(self.factory):
            (self.device / f"dev/mtd{i}").write_bytes(data)
        (self.device / "proc/mtd").write_text("dev: size erasesize name\n" + "".join(
            f'mtd{i}: {size:08x} 00008000 "{name}"\n' for i, (size, name) in enumerate(zip(SIZES, NAMES))))
        (self.device / "proc/cmdline").write_text("root=/dev/mtdblock2 init=/linuxrc mtdparts=jz_sfc:256k(boot),2560k(kernel),9088k(root)\n")
        (self.package / "uImage.t21").write_bytes(self.kernel)
        (self.package / "rootfs.squashfs.t21").write_bytes(self.rootfs)
        self.events = self.device / "events"
        self.events.write_text("")

    def run_installer(self, *args, fail_root=False):
        env = dict(os.environ, K5_SIM_EVENTS=str(self.events))
        if fail_root:
            env["K5_SIM_FAIL_ROOT"] = "1"
        result = subprocess.run([str(self.device / "installer"), *args], env=env,
                                capture_output=True, text=True, timeout=30)
        return result

    def assert_factory_unchanged(self):
        for i, data in enumerate(self.factory):
            self.assertEqual(hashlib.sha256((self.device / f"dev/mtd{i}").read_bytes()).digest(),
                             hashlib.sha256(data).digest(), f"mtd{i} changed")

    def arm(self):
        (self.package / "INSTALL_NOW").write_text("I_ACCEPT_BRICK_RISK\n")

    def test_read_only_checks_never_erase_or_write(self):
        result = self.run_installer("--check-only")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("READ_ONLY_V3_PASS", result.stdout)
        self.assertEqual(self.events.read_text(), "")
        self.assertFalse((self.package / "backup").exists())
        self.assert_factory_unchanged()

    def test_missing_arm_marker_refuses_writes(self):
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("INSTALL_NOW marker absent", result.stdout)
        self.assertEqual(self.events.read_text(), "")
        self.assert_factory_unchanged()

    def test_modified_factory_refuses_writes(self):
        data = bytearray(self.factory[1]); data[100] ^= 1
        (self.device / "dev/mtd1").write_bytes(data)
        self.arm()
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Factory kernel or root not exactly restored", result.stdout)
        self.assertEqual(self.events.read_text(), "")

    def test_bad_image_and_bad_map_refuse_writes(self):
        data = bytearray(self.kernel); data[100] ^= 1
        (self.package / "uImage.t21").write_bytes(data)
        self.arm()
        self.assertNotEqual(self.run_installer().returncode, 0)
        self.assertEqual(self.events.read_text(), "")
        (self.package / "uImage.t21").write_bytes(self.kernel)
        (self.device / "proc/mtd").write_text('mtd0: 00040000 00008000 "env"\n')
        self.assertNotEqual(self.run_installer().returncode, 0)
        self.assertEqual(self.events.read_text(), "")
        self.assert_factory_unchanged()

    def test_backup_collision_refuses_writes(self):
        (self.package / "backup").mkdir()
        (self.package / "backup/mtd0.bin").write_bytes(b"preserve this backup")
        self.arm()
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.events.read_text(), "")
        self.assertEqual((self.package / "backup/mtd0.bin").read_bytes(), b"preserve this backup")
        self.assert_factory_unchanged()

    def test_success_backs_up_all_and_writes_only_os_with_erased_tails(self):
        self.arm()
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("SUCCESS.", result.stdout)
        for i in range(8):
            self.assertEqual((self.package / f"backup/mtd{i}.bin").read_bytes(), self.factory[i])
            actual = (self.device / f"dev/mtd{i}").read_bytes()
            payload = {1: self.kernel, 2: self.rootfs}.get(i)
            if payload is None:
                self.assertEqual(actual, self.factory[i])
            else:
                self.assertEqual(actual, payload + b"\xff" * (SIZES[i] - len(payload)))
        targets = set(re.findall(r"(?:ERASE|WRITE) mtd(\d+)", self.events.read_text()))
        self.assertEqual(targets, {"1", "2"})

    def test_root_program_failure_rolls_back_both_partitions(self):
        self.arm()
        result = self.run_installer(fail_root=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ROLLBACK_SUCCESS", result.stdout)
        self.assertNotIn("REBOOT", self.events.read_text())
        self.assert_factory_unchanged()


if __name__ == "__main__":
    unittest.main(verbosity=2)
