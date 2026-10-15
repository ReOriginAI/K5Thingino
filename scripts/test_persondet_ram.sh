#!/bin/sh
# Run only from camera /tmp, automatically restore the known working streamer.
sleep 1
/etc/init.d/S31raptor stop
sleep 2
LD_LIBRARY_PATH=/tmp/k5-persondet/lib /tmp/k5-persondet/rvd -f -c /tmp/k5-persondet/raptor.conf > /tmp/k5-persondet/rvd.log 2>&1 &
sleep 12
free > /tmp/k5-persondet/memory.txt
pidof rvd > /tmp/k5-persondet/rvd.pid
LD_LIBRARY_PATH=/tmp/k5-persondet/lib /tmp/k5-persondet/rmd -f -c /tmp/k5-persondet/raptor.conf > /tmp/k5-persondet/rmd.log 2>&1 &
sleep 60
/etc/init.d/S31raptor stop
sleep 2
/etc/init.d/S31raptor start
echo RESTORED_BASELINE
