#!/bin/sh
HTTP_COOKIE=${HTTP_COOKIE:-}
HTTP_X_API_KEY=${HTTP_X_API_KEY:-}
HTTP_ACCEPT=${HTTP_ACCEPT:-}
QUERY_STRING=${QUERY_STRING:-}
. /var/www/x/auth.sh
require_auth
fail() {
 printf 'Status: %s\r\nContent-Type: application/json\r\nCache-Control: no-store\r\n\r\n{"error":"%s"}\n' "$1" "$2"
 exit 1
}
getmotion() {
 awk -v key="$1" '/^\[/ {section=$0} section=="[motion]" && $0 !~ /^[#;]/ {split($0,a,"="); gsub(/^[ \t]+|[ \t]+$/,"",a[1]); if(a[1]==key) {gsub(/^[ \t]+|[ \t]+$/,"",a[2]); print a[2]; exit}}' /etc/raptor.conf
}
case "${REQUEST_METHOD:-GET}" in
 GET)
  if [ "$QUERY_STRING" = snapshot ]; then
   user=$(raptorctl config get http username); pass=$(raptorctl config get http password)
   snap=$(mktemp /tmp/motion-snap.XXXXXX) || fail '500 Internal Server Error' 'Snapshot unavailable'
   trap 'rm -f "$snap"' EXIT
   curl -ksS --max-time 5 -u "$user:$pass" https://127.0.0.1:8443/snap.jpg -o "$snap" || fail '503 Service Unavailable' 'Snapshot unavailable'
   printf 'Content-Type: image/jpeg\r\nCache-Control: no-store\r\n\r\n'
   cat "$snap"; exit
  fi
  enabled=$(getmotion enabled); sens=$(getmotion sensitivity); mask=$(getmotion zone_mask)
  case "$enabled" in true|false) ;; *) enabled=false;; esac
  case "$sens" in 0|1|2|3|4) ;; *) sens=2;; esac
  case "$mask" in ''|*[!0-9]*) mask=65535;; esac
  live=$(raptorctl rvd ivs-status 2>/dev/null) || live='{"active":false,"motion":false}'
  printf 'Content-Type: application/json\r\nCache-Control: no-store\r\n\r\n'
  printf '{"enabled":%s,"sensitivity":%s,"mask":%s,"live":%s}\n' "$enabled" "$sens" "$mask" "$live"
  ;;
 POST)
  [ "${CONTENT_TYPE:-}" = application/x-thingino-motion-zones ] || fail '403 Forbidden' 'Invalid content type'
  case "${CONTENT_LENGTH:-}" in ''|*[!0-9]*) fail '400 Bad Request' 'Invalid length';; esac
  [ "$CONTENT_LENGTH" -le 32 ] || fail '400 Bad Request' 'Request too large'
  body=$(dd bs=1 count="$CONTENT_LENGTH" 2>/dev/null)
  case "$body" in *[!0-9\ ]*) fail '400 Bad Request' 'Invalid settings';; esac
  set -- $body
  [ "$#" -eq 3 ] || fail '400 Bad Request' 'Expected enable sensitivity mask'
  enabled=$1; sens=$2; mask=$3
  case "$enabled" in 0) enabled=false;; 1) enabled=true;; *) fail '400 Bad Request' 'Invalid enable setting';; esac
  case "$sens" in 0|1|2|3|4) ;; *) fail '400 Bad Request' 'Invalid sensitivity';; esac
  case "$mask" in ''|0*|*[!0-9]*) fail '400 Bad Request' 'Select at least one zone';; esac
  [ "${#mask}" -le 5 ] && [ "$mask" -le 65535 ] || fail '400 Bad Request' 'Invalid zone mask'
  exec 9>/tmp/motion-zones.lock
  flock -n 9 || fail '409 Conflict' 'A settings change is already running'
  [ -e /etc/raptor.conf.pre-zones-20261014 ] || cp -p /etc/raptor.conf /etc/raptor.conf.pre-zones-20261014
  tmp=$(mktemp /etc/raptor.conf.zones.XXXXXX) || fail '500 Internal Server Error' 'Cannot save'
  trap 'rm -f "$tmp"' EXIT
  awk '/^\[motion\]/{skip=1;next} /^\[/{skip=0} !skip{print}' /etc/raptor.conf > "$tmp" || fail '500 Internal Server Error' 'Cannot save'
  {
   printf '\n[motion]\nenabled = %s\nalgorithm = move\nsensitivity = %s\nzone_mask = %s\nskip_frames = 1\npoll_interval_ms = 250\ncooldown_sec = 10\nrecord = false\ngpio_pin = -1\n' "$enabled" "$sens" "$mask"
   count=0; i=0
   while [ "$i" -lt 16 ]; do
    if [ $((mask & (1 << i))) -ne 0 ]; then count=$((count+1)); fi
    i=$((i+1))
   done
   printf 'roi_count = %s\n' "$count"
   i=0; n=0
   while [ "$i" -lt 16 ]; do
    if [ $((mask & (1 << i))) -ne 0 ]; then
     x=$(( (i % 4)*160 )); y=$(( (i / 4)*90 ))
     printf 'roi%s = %s,%s,%s,%s\n' "$n" "$x" "$y" "$((x+159))" "$((y+89))"
     n=$((n+1))
    fi
    i=$((i+1))
   done
  } >> "$tmp"
  chmod 600 "$tmp" && mv "$tmp" /etc/raptor.conf || fail '500 Internal Server Error' 'Cannot save'
  trap - EXIT
  sync
  printf 'Content-Type: application/json\r\nCache-Control: no-store\r\n\r\n{"saved":true,"restarting":true}\n'
  (sleep 1; /etc/init.d/S31raptor restart) > /tmp/motion-zones-restart.log 2>&1 < /dev/null &
  ;;
 *) fail '405 Method Not Allowed' 'Unsupported method';;
esac
