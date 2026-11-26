#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}====================================================${NC}"
echo -e "${BOLD}              DMK Comprehensive Test Suite          ${NC}"
echo -e "${BOLD}====================================================${NC}\n"

clang -std=c11 -Wall -Wextra -Werror -O2 -I "${SCRIPT_DIR}/dmk_core/include" \
    "${SCRIPT_DIR}/tests/test_ht_source_compat.c" -o /tmp/dmk-ht-source-compat
/tmp/dmk-ht-source-compat

clang -std=c11 -Wall -Wextra -Werror -O2 -I "${SCRIPT_DIR}/dmk_core/include" \
    "${SCRIPT_DIR}/tests/test_flash_journal.c" -o /tmp/dmk-flash-journal-test
/tmp/dmk-flash-journal-test

# Runtime integration tests can also run independently, with sanitizers.
bash "${SCRIPT_DIR}/tests/run_runtime_tests.sh"

# 1. C Core Unit Tests
echo -e "${BOLD}[1/2] Running Host-Based C Core Unit Tests...${NC}"
clang -Wall -Wextra -DMATRIX_REPORT_BATCH \
    -I "${SCRIPT_DIR}/tests" \
    -I "${SCRIPT_DIR}/tests/mocks" \
    -I "${SCRIPT_DIR}/dmk_core/include" \
    -I "${SCRIPT_DIR}/dmk_core/config" \
    -I "${SCRIPT_DIR}/dmk_core/features" \
    -I "${SCRIPT_DIR}/dmk_core/core" \
    -I "${SCRIPT_DIR}/dmk_core/drivers" \
    "${SCRIPT_DIR}/tests/test_core.c" -o "${SCRIPT_DIR}/tests/test_core"
"${SCRIPT_DIR}/tests/test_core"
rm -f "${SCRIPT_DIR}/tests/test_core"
clang -Wall -Wextra -I "${SCRIPT_DIR}/tests/mocks" \
    "${SCRIPT_DIR}/tests/test_memory_hooks.c" "${SCRIPT_DIR}/dmk_core/core/memory.c" \
    -o "${SCRIPT_DIR}/tests/test_memory_hooks"
"${SCRIPT_DIR}/tests/test_memory_hooks"
rm -f "${SCRIPT_DIR}/tests/test_memory_hooks"
clang -Wall -Wextra -I "${SCRIPT_DIR}/dmk_core/include" \
    "${SCRIPT_DIR}/tests/test_bounded_heap.c" -o "${SCRIPT_DIR}/tests/test_bounded_heap"
"${SCRIPT_DIR}/tests/test_bounded_heap"
rm -f "${SCRIPT_DIR}/tests/test_bounded_heap"
for heap_size in 3072 8192; do
    clang -Wall -Wextra -DconfigTOTAL_HEAP_SIZE="$heap_size" -I "${SCRIPT_DIR}/tests/heap_mocks" \
        "${SCRIPT_DIR}/tests/test_heap4_failure.c" "${SCRIPT_DIR}/dmk_core/core/memory.c" \
        "${SCRIPT_DIR}/lib/freertos/heap_4.c" -o "${SCRIPT_DIR}/tests/test_heap4_failure"
    "${SCRIPT_DIR}/tests/test_heap4_failure"
done
rm -f "${SCRIPT_DIR}/tests/test_heap4_failure"
clang -Wall -Wextra -I "${SCRIPT_DIR}/tests/mocks" -I "${SCRIPT_DIR}/dmk_core/include" \
    -I "${SCRIPT_DIR}/dmk_core/config" -I "${SCRIPT_DIR}/dmk_core/drivers" -I "${SCRIPT_DIR}/dmk_core/features" \
    "${SCRIPT_DIR}/tests/test_features.c" "${SCRIPT_DIR}/dmk_core/features/oneshot.c" \
    "${SCRIPT_DIR}/dmk_core/features/macros.c" -o "${SCRIPT_DIR}/tests/test_features"
"${SCRIPT_DIR}/tests/test_features"
rm -f "${SCRIPT_DIR}/tests/test_features"

clang -Wall -Wextra -Wno-unused-variable -DVIAL -DHHKB_GRAVE_ESCAPE=1 -DMCU_stm32l072 -DconfigTICK_RATE_HZ=1000 \
    -I "${SCRIPT_DIR}/keyboards/hhkb" -I "${SCRIPT_DIR}/platforms/stm32l072" \
    -I "${SCRIPT_DIR}/tests/mocks" -I "${SCRIPT_DIR}/dmk_core/include" \
    -I "${SCRIPT_DIR}/dmk_core/config" -I "${SCRIPT_DIR}/dmk_core/features" \
    -I "${SCRIPT_DIR}/dmk_core/drivers" -I "${SCRIPT_DIR}/dmk_core/core" \
    "${SCRIPT_DIR}/tests/test_vial_keycodes.c" "${SCRIPT_DIR}/dmk_core/features/vial.c" \
    -o "${SCRIPT_DIR}/tests/test_vial_keycodes"
"${SCRIPT_DIR}/tests/test_vial_keycodes"
rm -f "${SCRIPT_DIR}/tests/test_vial_keycodes"

if [[ -f "${SCRIPT_DIR}/keyboards/hhkb/modules/ec/rapid_trigger.c" ]]; then
    # HHKB host-only algorithm and EEPROM guard tests
    HHKB_TEST_DIR="${SCRIPT_DIR}/tests/hhkb"
    HHKB_MODULES_DIR="${SCRIPT_DIR}/keyboards/hhkb/modules"
    clang -std=c11 -Wall -Wextra -Werror -O2 -I "${HHKB_MODULES_DIR}/ec" -I "${SCRIPT_DIR}/dmk_core/include" \
        "${HHKB_MODULES_DIR}/ec/rapid_trigger.c" "${HHKB_TEST_DIR}/test_rapid_trigger.c" \
        -o "${HHKB_TEST_DIR}/test_rapid_trigger"
    "${HHKB_TEST_DIR}/test_rapid_trigger"
    rm -f "${HHKB_TEST_DIR}/test_rapid_trigger"
    clang -std=c11 -Wall -Wextra -Werror -O2 -I "${HHKB_MODULES_DIR}/ec" -I "${SCRIPT_DIR}/dmk_core/include" \
        "${HHKB_MODULES_DIR}/ec/rapid_trigger.c" "${HHKB_TEST_DIR}/test_rt_lockout.c" \
        -o "${HHKB_TEST_DIR}/test_rt_lockout"
    "${HHKB_TEST_DIR}/test_rt_lockout"
    rm -f "${HHKB_TEST_DIR}/test_rt_lockout"
    clang -std=c11 -Wall -Wextra -Werror -O2 -I "${HHKB_MODULES_DIR}/ec" -I "${SCRIPT_DIR}/dmk_core/include" \
        "${HHKB_MODULES_DIR}/ec/rapid_trigger.c" "${HHKB_TEST_DIR}/rapid_trigger_reference.c" \
        "${HHKB_TEST_DIR}/test_scan_processing.c" -o /tmp/dmk-scan-processing-test
    /tmp/dmk-scan-processing-test
    clang -std=c11 -Wall -Wextra -Werror -O2 -I "${SCRIPT_DIR}/tests/mocks" \
        -I "${SCRIPT_DIR}/dmk_core/include" "${SCRIPT_DIR}/dmk_core/features/ec_curve.c" \
        "${HHKB_TEST_DIR}/test_ec_curve.c" -o "${HHKB_TEST_DIR}/test_ec_curve"
    "${HHKB_TEST_DIR}/test_ec_curve"
    rm -f "${HHKB_TEST_DIR}/test_ec_curve"
    clang -std=c11 -Wall -Wextra -Werror -I "${HHKB_MODULES_DIR}/via_settings" \
        "${HHKB_TEST_DIR}/test_settings_storage_guard.c" -o "${HHKB_TEST_DIR}/test_settings_storage_guard"
    "${HHKB_TEST_DIR}/test_settings_storage_guard"
    rm -f "${HHKB_TEST_DIR}/test_settings_storage_guard"
    clang -std=c11 -Wall -Wextra -Werror -I "${HHKB_MODULES_DIR}/ec" \
        "${HHKB_TEST_DIR}/test_cal_request.c" -o "${HHKB_TEST_DIR}/test_cal_request"
    "${HHKB_TEST_DIR}/test_cal_request"
    rm -f "${HHKB_TEST_DIR}/test_cal_request"
    clang -std=c11 -Wall -Wextra -Werror -O2 -DSOF_LOCK_HOST_TEST -I "${HHKB_MODULES_DIR}/ec" \
        "${HHKB_TEST_DIR}/test_sof_lock.c" -o "${HHKB_TEST_DIR}/test_sof_lock"
    "${HHKB_TEST_DIR}/test_sof_lock"
    rm -f "${HHKB_TEST_DIR}/test_sof_lock"
    clang -std=c11 -Wall -Wextra -Werror -O2 -I "${HHKB_MODULES_DIR}/ec" \
        "${HHKB_TEST_DIR}/test_idle_scan.c" -o "${HHKB_TEST_DIR}/test_idle_scan"
    "${HHKB_TEST_DIR}/test_idle_scan"
    rm -f "${HHKB_TEST_DIR}/test_idle_scan"
    for hhkb_test in test_keymap_storage test_indicators_system; do
        clang -std=c11 -Wall -Wextra -Werror -I "${HHKB_TEST_DIR}/mocks" \
            "${HHKB_TEST_DIR}/${hhkb_test}.c" -o "${HHKB_TEST_DIR}/${hhkb_test}"
        "${HHKB_TEST_DIR}/${hhkb_test}"
        rm -f "${HHKB_TEST_DIR}/${hhkb_test}"
    done

else
    echo "HHKB sources absent; skipping HHKB firmware tests."
fi

# 2. Python Tool Tests
echo -e "${BOLD}[2/2] Running Python Tool Unit Tests...${NC}"
uv run python3 -m unittest discover -s "${SCRIPT_DIR}/tests" -p "test_*.py"

echo -e "\n${GREEN}${BOLD}🎉 All test suites completed successfully!${NC}\n"
