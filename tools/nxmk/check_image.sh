#!/usr/bin/env bash
# Size/vector gates for the HHKB L072 Bank 2 image. Usage: check_image.sh [build-dir]
set -euo pipefail
D="${1:-build/hhkb-script}"; N=nxmk_hhkb_stm32l072
BIN="$D/$N.bin"; ELF="$D/$N"
sz=$(stat -c %s "$BIN")
read -r _ text data bss _ < <(arm-none-eabi-size "$ELF" | tail -1 | awk '{print "x",$1,$2,$3}')
sp=$(od -An -tx4 -N4 "$BIN" | tr -d ' ')
rv=$(od -An -tx4 -j4 -N4 "$BIN" | tr -d ' ')
echo "BIN=$sz text=$text data=$data bss=$bss SP=0x$sp reset=0x$rv"
fail=0
(( sz <= 65536 )) || { echo "FAIL: BIN > 65536"; fail=1; }
(( data + bss <= 20480 )) || { echo "FAIL: data+bss > 20480"; fail=1; }
(( (0x$sp >> 16) == 0x2000 && 0x$sp % 8 == 0 )) || { echo "FAIL: SP"; fail=1; }
(( (0x$rv & 1) == 1 && (0x$rv >> 16) == 0x0801 )) || { echo "FAIL: reset vector"; fail=1; }
exit $fail
