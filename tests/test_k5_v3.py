"""Host tests for K5 recovery behavior. No camera or real MTD is accessed."""
import hashlib
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "firmware/wansview_k5_t21n_ov2735b_rtl8188fu"
OVERLAY = PROFILE / "overlay"
TARGET = ROOT / "thingino-firmware/output/stable/wansview_k5_t21n_ov2735b_rtl8188fu-3.10.14-uclibc/target"
QEMU = ROOT / "tools/host-tools/unpacked/usr/bin/qemu-mipsel-static"
WORK = ROOT / "tools/test-work"

MOCK = r'''#!/usr/bin/python3
import hashlib, os, pathlib, signal, sys, time
name=pathlib.Path(sys.argv[0]).name
root=pathlib.Path(os.environ['K5_TEST_ROOT'])
scenario=os.environ.get('K5_SCENARIO','client')
with (root/'calls').open('a') as f: f.write(name+' '+ ' '.join(sys.argv[1:])+'\n')
if name == 'wpa_cli':
    if scenario == 'control-hang':
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        (root/'control.pid').write_text(str(os.getpid()))
        time.sleep(15)
    if scenario in ('client','ap','no-dhcp'): print('wpa_state=COMPLETED\nmode='+('AP' if scenario=='ap' else 'station'))
    else: print('wpa_state=DISCONNECTED')
elif name == 'ip' and 'show' in sys.argv:
    if scenario == 'client': print('    inet 192.0.2.10/24 scope global wlan0')
elif name == 'wpa_supplicant':
    if scenario=='launch-fail': sys.exit(1)
    if scenario=='launch-hang': time.sleep(15)
elif name == 'wpa_passphrase':
    print('network={\n\tpsk='+hashlib.pbkdf2_hmac('sha1',sys.argv[2].encode(),sys.argv[1].encode(),4096,32).hex()+'\n}')
elif name == 'sleep': time.sleep(3 if sys.argv[1]=='180' else 0.01)
'''


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        WORK.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="v3-test-", dir=WORK)
        self.root = Path(self.temp.name)
        for name in ("etc", "run", "rom/etc", "proc", "sys/class/net/wlan0", "usr/sbin", "bin", "dev"):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        (self.root / "proc/mtd").write_text('mtd1: 00280000 00008000 "kernel"\nmtd3: 002e0000 00008000 "data"\n')
        (self.root / "sys/class/net/wlan0/address").write_text("02:00:00:00:aa:bb\n")
        (self.root / "rom/etc/wpa_supplicant.conf").write_text('network={\n ssid="THINGINO-"\n key_mgmt=NONE\n}\n')
        self.config = self.root / "etc/wpa_supplicant.conf"
        self.config.write_text('network={\n ssid="test-network"\n psk=' + "1" * 64 + '\n}\n')
        self.calls = self.root / "calls"
        self.calls.touch()
        for command in ("k5-log", "k5-report", "k5-reboot", "ip", "wpa_cli", "wpa_passphrase", "sleep", "sync", "play", "udhcpc", "udhcpd", "dnsd", "flash_eraseall", "reboot", "killall"):
            script = self.root / "bin" / command
            script.write_text(MOCK)
            script.chmod(0o755)
        wpa = self.root / "usr/sbin/wpa_supplicant"
        wpa.write_text(MOCK)
        wpa.chmod(0o755)
        self.env = dict(os.environ, K5_TEST_ROOT=str(self.root), PATH=str(self.root / "bin") + ":/usr/bin:/bin")
        self.processes = []

    def tearDown(self):
        for process in self.processes:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        pidfile = self.root / "control.pid"
        if pidfile.exists():
            try:
                os.kill(int(pidfile.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.temp.cleanup()

    def run_script(self, file, *args, scenario="client", input=None, timeout=20):
        text = (OVERLAY / file).read_text()
        text = re.sub(r"(?<![A-Za-z0-9_])(/(?:etc|run|rom|proc|sys|dev|usr/sbin)/)",
                      lambda match: str(self.root) + match.group(1), text)
        script = self.root / "script"
        script.write_text(text)
        script.chmod(0o755)
        env = dict(self.env, K5_SCENARIO=scenario)
        process = subprocess.Popen(["/bin/sh", str(script), *args], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   env=env, start_new_session=True)
        self.processes.append(process)
        stdout, stderr = process.communicate(input, timeout=timeout)
        return subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)

    def test_special_ssid_passphrase_and_atomic_rejection(self):
        ssid = 'Lab "camera"\\$(false)'
        password = "test passphrase"
        result = self.run_script("usr/sbin/wlan", "configure", ssid, password)
        self.assertEqual(result.returncode, 0, result.stderr)
        content = self.config.read_text()
        expected = hashlib.pbkdf2_hmac("sha1", password.encode(), ssid.encode(), 4096, 32).hex()
        self.assertIn("psk=" + expected, content)
        self.assertIn('ssid="Lab \\"camera\\"\\\\$(false)"', content)
        self.assertNotIn(password, content)
        result = self.run_script("usr/sbin/wlan", "configure", "bad\nnetwork", password)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.config.read_text(), content)
        result = self.run_script("usr/sbin/wlan", "configure", "a" * 33, password)
        self.assertNotEqual(result.returncode, 0)
        result = self.run_script("usr/sbin/wlan", "configure", "network", "short")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.config.read_text(), content)

    def test_protected_ap_and_derived_psk(self):
        result = self.run_script("usr/sbin/wlan", "configure", "test-ap", "a" * 64, "ap")
        self.assertEqual(result.returncode, 0, result.stderr)
        content = self.config.read_text()
        self.assertIn("mode=2", content)
        self.assertIn("key_mgmt=WPA-PSK", content)
        self.assertIn("pairwise=CCMP", content)
        self.assertIn("psk=" + "a" * 64, content)

    def test_reset_changes_wifi_only(self):
        (self.root / "etc/k5-wifi-attempt").touch()
        untouched = self.root / "etc/unrelated-settings"
        untouched.write_text("preserve\n")
        result = self.run_script("usr/sbin/wlan", "reset")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.config.read_bytes(), (self.root / "rom/etc/wpa_supplicant.conf").read_bytes())
        self.assertFalse((self.root / "etc/k5-wifi-attempt").exists())
        self.assertEqual(untouched.read_text(), "preserve\n")
        self.assertNotIn("flash_eraseall", self.calls.read_text())

    def test_stale_attempt_returns_portal_without_losing_credentials(self):
        before = self.config.read_bytes()
        (self.root / "etc/k5-wifi-attempt").touch()
        result = self.run_script("etc/init.d/S38wpa_supplicant", "start")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / "run/portal_mode").exists())
        self.assertIn("key_mgmt=NONE", (self.root / "run/k5-portal.conf").read_text())
        self.assertEqual(self.config.read_bytes(), before)

    def test_sd_force_portal(self):
        (self.root / "run/k5-force-portal").touch()
        result = self.run_script("etc/init.d/S38wpa_supplicant", "start")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / "run/portal_mode").exists())

    def test_successful_client_and_ap_clear_attempt(self):
        for mode in ("client", "ap"):
            with self.subTest(mode=mode):
                (self.root / "etc/k5-wifi-attempt").touch()
                result = self.run_script("etc/init.d/S38wpa_supplicant", "configured_worker", mode, scenario=mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse((self.root / "etc/k5-wifi-attempt").exists())
                self.assertTrue((self.root / "run/k5-wifi-ready").exists())

    def test_bad_password_missing_dhcp_and_hung_launch_keep_latch(self):
        for scenario in ("disconnected", "no-dhcp", "launch-fail", "launch-hang"):
            with self.subTest(scenario=scenario):
                (self.root / "etc/k5-wifi-attempt").touch()
                self.calls.write_text("")
                (self.root / "run/k5-wpa-start-failed").unlink(missing_ok=True)
                result = self.run_script("etc/init.d/S38wpa_supplicant", "configured_worker", "client", scenario=scenario)
                self.assertTrue((self.root / "etc/k5-wifi-attempt").exists())
                self.assertIn("k5-reboot ", self.calls.read_text())

    def test_firstboot_refuses_factory_or_wrong_size_map(self):
        for line in ('mtd1: 00280000 00008000 "kernel"\nmtd3: 00050000 00008000 "syscfg"\n',
                     'mtd3: 00050000 00008000 "data"\n'):
            (self.root / "proc/mtd").write_text(line)
            result = self.run_script("usr/sbin/firstboot", "-f")
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("flash_eraseall", self.calls.read_text())

    def test_blocked_control_command_does_not_prevent_independent_guard(self):
        (self.root / "etc/k5-wifi-attempt").touch()
        with self.assertRaises(subprocess.TimeoutExpired):
            self.run_script("etc/init.d/S38wpa_supplicant", "configured_worker", "client",
                            scenario="control-hang", timeout=5)
        self.assertIn("k5-reboot ", self.calls.read_text())
        self.assertTrue((self.root / "etc/k5-wifi-attempt").exists())

    def test_stuck_shutdown_service_is_bounded_and_watchdog_stops_first(self):
        directory = self.root / "etc/init.d"
        directory.mkdir(exist_ok=True)
        service = directory / "S98recorder"
        service.write_text("#!/bin/sh\n/bin/sleep 15\n")
        service.chmod(0o755)
        start = time.monotonic()
        result = self.run_script("etc/init.d/rcK", timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(time.monotonic() - start, 7)
        calls = self.calls.read_text()
        self.assertLess(calls.index("killall -9 watchdog"), calls.index("shutdown.S98recorder"))
        self.assertIn("reboot -f", calls)

    def test_firstboot_erases_only_reserved_data(self):
        result = self.run_script("usr/sbin/firstboot", "-f")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("flash_eraseall -j " + str(self.root / "dev/mtd3"), self.calls.read_text())
        self.assertNotIn("mtd1", self.calls.read_text())

    def test_actual_mips_psk_generation(self):
        ssid = 'Camera "test"\\room'
        password = "host-only-test-pass"
        output = subprocess.check_output([str(QEMU), "-L", str(TARGET),
                                          str(TARGET / "usr/sbin/wpa_passphrase"), ssid, password], text=True)
        psk = re.search(r"^\s*psk=([a-f0-9]{64})$", output, re.M).group(1)
        self.assertEqual(psk, hashlib.pbkdf2_hmac("sha1", password.encode(), ssid.encode(), 4096, 32).hex())


if __name__ == "__main__":
    unittest.main(verbosity=2)
