/*
 * K5 factory-Linux SD installer: STATIC MIPS executable.
 * Built specifically for original 16MiB Wansview K5 MTD map.
 * No SPI writes before full preflight and per-partition SD backups succeed.
 * Writes ONLY the factory OS partitions mtd1 and mtd2.
 *
 * EXPERIMENTAL: flash on a powered camera with no UART recovery is risky.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <mtd/mtd-user.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <unistd.h>

#ifndef EXPECT_KERNEL_SIZE
#error EXPECT_KERNEL_SIZE must be set by package maker
#endif
#ifndef EXPECT_ROOT_SIZE
#error EXPECT_ROOT_SIZE must be set by package maker
#endif
#ifndef EXPECT_KERNEL_CRC32
#error EXPECT_KERNEL_CRC32 must be set by package maker
#endif
#ifndef EXPECT_ROOT_CRC32
#error EXPECT_ROOT_CRC32 must be set by package maker
#endif

#define KERNEL_CAP 0x280000u
#define ROOT_CAP   0x8e0000u
#define ERASE_SIZE 0x8000u
#define SDROOT "/mnt/mmc"
#define PKG "/mnt/mmc/k5-installer"
#define BUFSIZE 32768u
static char buf[BUFSIZE];
static FILE *logfile;
static int modified_flash=0;
static int rolling_back=0;
static void rollback_factory(void);
static uint32_t live_crc(const char *p, uint32_t count);


static void note(const char *fmt, ...) {
    va_list ap;
    va_start(ap,fmt);
    vfprintf(stdout,fmt,ap);
    va_end(ap);
    fflush(stdout);
    if (logfile) {
        va_start(ap,fmt);
        vfprintf(logfile,fmt,ap);
        va_end(ap);
        fflush(logfile);
        fsync(fileno(logfile));
    }
}
static void die(const char *why) {
    int original_errno=errno;
    note("ABORT: %s (errno=%d: %s)\n",why,original_errno,strerror(original_errno));
    if(modified_flash && !rolling_back) rollback_factory();
    exit(1);
}
static uint32_t crc32_update(uint32_t crc, const unsigned char *p, size_t n) {
    while(n--) {
        crc ^= *p++;
        for(int i=0;i<8;i++) crc=(crc>>1) ^ (0xedb88320u & -(crc & 1u));
    }
    return crc;
}
static uint32_t crc_fd(int fd, size_t len) {
    uint32_t crc=0xffffffffu;
    size_t done=0;
    while(done<len) {
        size_t want=len-done;
        if(want>BUFSIZE) want=BUFSIZE;
        ssize_t n=read(fd,buf,want);
        if(n<=0) die("Cannot read entire firmware image");
        crc=crc32_update(crc,(const unsigned char*)buf,(size_t)n);
        done+=(size_t)n;
    }
    return ~crc;
}
static void verify_image(const char *p, uint32_t expected_size, uint32_t expected_crc, int uimage) {
    struct stat st;
    int fd=open(p,O_RDONLY);
    if(fd<0 || fstat(fd,&st)<0) die("Firmware image missing");
    if(!S_ISREG(st.st_mode) || (uint64_t)st.st_size!=expected_size) die("Unexpected firmware image size");
    if(expected_size==0 || expected_size>(uimage?KERNEL_CAP:(6144u*1024u))) die("Image exceeds stock partition");
    uint32_t magic=0;
    unsigned char m[4];
    if(read(fd,m,4)!=4) die("Image header unreadable");
    magic=((uint32_t)m[0]<<24)|((uint32_t)m[1]<<16)|((uint32_t)m[2]<<8)|m[3];
    if(magic!=(uimage?0x27051956u:0x68737173u)) {
       /* Squashfs magic is little-endian 'hsqs', bytes 68 73 71 73. */
       if(!( !uimage && m[0]=='h' && m[1]=='s' && m[2]=='q' && m[3]=='s'))
           die("Unrecognized firmware image header");
    }
    if(lseek(fd,0,SEEK_SET)<0) die("Image seek failed");
    uint32_t crc=crc_fd(fd,expected_size);
    close(fd);
    if(crc!=expected_crc) die("Image checksum mismatch");
    note("PASS image %s, size %u, crc32 %08x\n",p,expected_size,crc);
}
static const struct {uint32_t size; const char *name;} parts[8]={
    {0x040000u,"boot"}, {0x280000u,"kernel"}, {0x8e0000u,"root"},
    {0x050000u,"syscfg"}, {0x050000u,"sysbak"}, {0x170000u,"minikernel"},
    {0x240000u,"minirootfs"},{0x010000u,"upgrade"}
};
static void verify_mtd(void) {
    FILE *f=fopen("/proc/mtd","r");
    if(!f) die("Cannot open /proc/mtd");
    char line[256]; int found=0,idx; unsigned size,erase;char name[100];
    while(fgets(line,sizeof(line),f)) {
        if(sscanf(line,"mtd%d: %x %x \"%99[^\"]\"",&idx,&size,&erase,name)==4) {
            if(idx!=found || idx>=8 || size!=parts[idx].size ||
               erase!=ERASE_SIZE || strcmp(name,parts[idx].name)) {
                fclose(f);
                die("MTD layout differs from verified factory K5 layout");
            }
            found++;
        }
    }
    fclose(f);
    if(found!=8) die("MTD partition count mismatch");
    f=fopen("/proc/cmdline","r");
    if(!f) die("Cannot open /proc/cmdline");
    char cmd[4096]={0};
    if(!fgets(cmd,sizeof(cmd),f)) die("Cannot read kernel command line");
    fclose(f);
    if(!strstr(cmd,"root=/dev/mtdblock2") ||
       !strstr(cmd,"mtdparts=jz_sfc:256k(boot),2560k(kernel),9088k(root)") ||
       !strstr(cmd,"init=/linuxrc")) {
        die("Not running the original factory Linux command line");
    }
    note("PASS factory partition map, command line and erase size\n");
}
static void verify_arm(void) {
    char marker[96]={0};
    char path[PATH_MAX];
    snprintf(path,sizeof(path),"%s/INSTALL_NOW",PKG);
    int fd=open(path,O_RDONLY);
    if(fd<0) die("Explicit INSTALL_NOW marker absent");
    ssize_t n=read(fd,marker,sizeof(marker)-1);
    close(fd);
    if(n<0 || strncmp(marker,"I_ACCEPT_BRICK_RISK",19)!=0 ||
       !(marker[19]=='\n'||marker[19]=='\r'||marker[19]==0))
        die("INSTALL_NOW marker content incorrect");
    note("Explicit risk acceptance marker verified\n");
}
static uint32_t live_crc(const char *p, uint32_t count) {
    int f=open(p,O_RDONLY);
    if(f<0) die("Cannot read current factory flash");
    uint32_t r=crc_fd(f,count);
    if(close(f)<0) die("Cannot close current factory flash");
    return r;
}
static void verify_pristine_factory(void) {
    /* These CRC32 values are from the device's OWN verified original backup. */
    uint32_t kern=live_crc("/dev/mtd1",KERNEL_CAP);
    uint32_t root=live_crc("/dev/mtd2",ROOT_CAP);
    note("CURRENT factory flash: mtd1=%08x (expected a8a87785), mtd2=%08x (expected d18d5787)\n",kern,root);
    if(kern!=0xa8a87785u || root!=0xd18d5787u)
        die("Factory kernel or root not exactly restored; refusing another flash");
    note("PASS original kernel and factory root both verified before any writes\n");
}
static void backup_all(void) {
    char path[PATH_MAX],dev[32];
    snprintf(path,sizeof(path),"%s/backup",PKG);
    if(mkdir(path,0700)<0 && errno!=EEXIST) die("Cannot create SD backup folder");
    struct statvfs sv;
    if(statvfs(SDROOT,&sv)<0 || ((uint64_t)sv.f_bavail*sv.f_frsize)<(19u*1024u*1024u))
        die("Insufficient SD free space for automatic safety backup (19MiB minimum)");
    for(int i=0;i<8;i++) {
        snprintf(dev,sizeof(dev),"/dev/mtd%d",i);
        snprintf(path,sizeof(path),PKG"/backup/mtd%d.bin",i);
        int in=open(dev,O_RDONLY);
        if(in<0) die("Unable to read existing flash for backup");
        int out=open(path,O_WRONLY|O_CREAT|O_EXCL,0600);
        if(out<0) die("Backup file already exists or cannot be created; refusing overwrite");
        uint32_t remain=parts[i].size, crc=0xffffffffu;
        while(remain) {
            unsigned want=remain<BUFSIZE?remain:BUFSIZE;
            ssize_t got=read(in,buf,want);
            if(got<=0) die("Flash read failed during backup");
            crc=crc32_update(crc,(unsigned char*)buf,(size_t)got);
            size_t off=0;
            while(off<(size_t)got) {
                ssize_t wr=write(out,buf+off,(size_t)got-off);
                if(wr<=0) die("SD write failed during flash backup");
                off+=(size_t)wr;
            }
            remain-=(uint32_t)got;
        }
        if(fsync(out)<0) die("SD backup flush failed");
        close(in); close(out);
        int saved=open(path,O_RDONLY);
        if(saved<0) die("Cannot reopen SD backup for verification");
        uint32_t saved_crc=crc_fd(saved,parts[i].size);
        close(saved);
        if(saved_crc!=(~crc)) die("Backup SD readback CRC32 mismatch");
        note("BACKUP mtd%d (%s): %u bytes, verified CRC32=%08x\n",i,parts[i].name,parts[i].size,saved_crc);
    }
    note("PASS 16MiB original NOR backup created on microSD\n");
}
static void flash_partition(int i,const char *image,uint32_t size,uint32_t crc_expected) {
    char dev[32];
    snprintf(dev,sizeof(dev),"/dev/mtd%d",i);
    int fd=open(dev,O_RDWR|O_SYNC);
    int input=open(image,O_RDONLY);
    if(fd<0 || input<0) die("Cannot open target MTD or firmware image");
    struct mtd_info_user info;
    if(ioctl(fd,MEMGETINFO,&info)<0 ||
       info.size!=parts[i].size || info.erasesize!=ERASE_SIZE ||
       info.type!=MTD_NORFLASH) die("MTD_INFO mismatch: writing refused");
    modified_flash=1; /* Any later failure attempts rollback from the SD backup. */
    note("%s mtd%d start; erasing %u bytes\n",rolling_back?"ROLLBACK":"FLASH",i,info.size);
    for(uint32_t off=0;off<info.size;off+=ERASE_SIZE) {
        struct erase_info_user e={.start=off,.length=ERASE_SIZE};
        if(ioctl(fd,MEMERASE,&e)<0) die("SPI NOR erase failed");
    }
    if(lseek(fd,0,SEEK_SET)<0) die("MTD seek failed after erase");
    uint32_t left=size;
    while(left) {
        unsigned count=left>BUFSIZE?BUFSIZE:left;
        ssize_t n=read(input,buf,count);
        if(n<=0) die("Cannot read firmware image during flash");
        size_t done=0;
        while(done<(size_t)n) {
            ssize_t wr=write(fd,buf+done,(size_t)n-done);
            if(wr<=0) die("SPI NOR program failed");
            done+=(size_t)wr;
        }
        left-=(uint32_t)n;
    }
    /* Stock jz_sfc MTD character device reports EINVAL on fsync().
       Do NOT call fsync(fd): writing and re-opening for readback are used. */
    if(close(fd)<0) die("Cannot close programmed MTD device");
    sync();
    int rd=open(dev,O_RDONLY);
    if(rd<0) die("Cannot reopen MTD device for independent readback");
    uint32_t crc=crc_fd(rd,size);
    if(crc!=crc_expected) die("SPI NOR readback CRC32 differs from original payload");
    /* Confirm all unused portion is erased to FF, critical for Thingino data area. */
    uint32_t rest=parts[i].size-size;
    while(rest) {
        unsigned wanted=rest>BUFSIZE?BUFSIZE:rest;
        ssize_t got=read(rd,buf,wanted);
        if(got<=0) die("Cannot read erased partition tail");
        for(ssize_t j=0;j<got;j++) if((unsigned char)buf[j]!=0xffu) die("Erased NOR tail contains unexpected data");
        rest-=(uint32_t)got;
    }
    if(close(rd)<0) die("Cannot close flash readback handle");
    if(close(input)<0) die("Cannot close image input");
    note("PASS mtd%d fresh-open readback CRC32=%08x and erased tail verified\n",i,crc);
}
/* Roll back BOTH original kernel and root, because a failed root write
   cannot be paired with either kernel. Original factory Linux is still in RAM. */
static void rollback_factory(void) {
    rolling_back=1;
    note("ROLLBACK START: trying to restore factory mtd2(root), then mtd1(kernel) from SD\n");
    flash_partition(2,PKG"/backup/mtd2.bin",ROOT_CAP,0xd18d5787u);
    flash_partition(1,PKG"/backup/mtd1.bin",KERNEL_CAP,0xa8a87785u);
    note("ROLLBACK_SUCCESS: factory root and kernel fully readback-verified; no automatic reboot\n");
    sync();
}
int main(int argc, char **argv) {
    int check_only=(argc==2 && strcmp(argv[1],"--check-only")==0);
    if(argc>2 || (argc==2 && !check_only)) {
        fprintf(stderr,"Usage: k5-flash-static [--check-only]\n");
        return 2;
    }
    signal(SIGTERM,SIG_IGN);
    signal(SIGHUP,SIG_IGN);
    logfile=fopen(check_only?PKG"/read-only-validation.log":PKG"/flash.log","a");
    if(!logfile) die("Cannot create install progress log on SD");
    setvbuf(logfile,NULL,_IONBF,0);
    note("\n=== K5 NOR INSTALLER V3 / %s ===\n",check_only?"READ-ONLY VERIFICATION":"ARMED FLASH WITH ROLLBACK");
    verify_mtd();
    verify_image(PKG"/uImage.t21",EXPECT_KERNEL_SIZE,EXPECT_KERNEL_CRC32,1);
    verify_image(PKG"/rootfs.squashfs.t21",EXPECT_ROOT_SIZE,EXPECT_ROOT_CRC32,0);
    verify_pristine_factory();
    if(check_only) {
        note("READ_ONLY_V3_PASS: original firmware, mtd map, and Thingino payloads verified; zero flash writes\n");
        return 0;
    }
    verify_arm();
    backup_all();
    note("All safeguards passed; flashing ONLY mtd1(kernel) and mtd2(root)\n");
    flash_partition(1,PKG"/uImage.t21",EXPECT_KERNEL_SIZE,EXPECT_KERNEL_CRC32);
    flash_partition(2,PKG"/rootfs.squashfs.t21",EXPECT_ROOT_SIZE,EXPECT_ROOT_CRC32);
    note("SUCCESS. Preserved bootloader, calibration, recovery. Rebooting.\n");
    sync();
    reboot(RB_AUTOBOOT);
    note("WARNING: reboot syscall failed; manually power cycle only after flash.log SUCCESS\n");
    return 0;
}
