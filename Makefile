PYTHON ?= python3

.PHONY: help verify test profile build package

help:
	@echo "make verify   - verify the current SD package and release archive"
	@echo "make test     - run 19 host tests; no camera access"
	@echo "make profile  - install the K5 source profile into the local checkout"
	@echo "make build    - rebuild kernel/rootfs on this host; no flashing"
	@echo "make package  - package built images as a disarmed SD installer"

verify:
	$(PYTHON) scripts/verify_dist.py

test:
	$(PYTHON) scripts/run_tests.py

profile:
	$(PYTHON) scripts/install_profile.py

build: profile
	$(PYTHON) scripts/build_firmware.py

package:
	$(PYTHON) src/k5-installer/build_v3_dist.py
	$(PYTHON) scripts/verify_dist.py
