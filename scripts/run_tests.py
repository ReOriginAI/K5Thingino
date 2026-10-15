"""Run the host test suites and retain their latest full logs."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    logs = ROOT / "docs/logs"
    logs.mkdir(parents=True, exist_ok=True)
    for suite, name in (("test_k5_v3.py", "v3-runtime-tests-final.log"),
                        ("test_k5_flash_v3.py", "v3-installer-tests.log")):
        log = logs / name
        with log.open("w") as output:
            result = subprocess.run([sys.executable, str(ROOT / "tests" / suite)], cwd=ROOT,
                                    stdout=output, stderr=subprocess.STDOUT)
        print(log.read_text(), end="", flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
