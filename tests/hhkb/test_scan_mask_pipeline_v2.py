"""Exercise the production pending processor with an arbitrary mask."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from .hhkb_helpers import ROOT, function


class ScanMaskPipelineV2(unittest.TestCase):
    def test_pending_transitions(self):
        source = (ROOT / "keyboards/hhkb/modules/ec/classic_matrix.c").read_text()
        processor = function(source, "bool scan_process_pending(")
        code = r'''
#include <assert.h>
#include <stdint.h>
#define MATRIX_COLS 15
#define MATRIX_ROWS 4
#define HHKB_RT_KEYMASK 1
#define HHKB_RT_ARBITRARY_SELECTION 1
#define HHKB_RT_DEADBAND 0
#include "scan_cache.h"
#include "scan_transition.h"
typedef uint16_t matrix_row_t;
typedef struct { uint16_t raw, travel; uint8_t col, row; bool valid, pressed; } scan_pending_t;
static rt_key_t s_rt_keys[MATRIX_COLS][MATRIX_ROWS];
static hhkb_scan_cache_t s_scan_cache;
static hhkb_scan_transition_t s_scan_transition[MATRIX_COLS][MATRIX_ROWS];
PROCESSOR
int main(void) {
    rt_cfg_t c = {.rt_enabled=true,.act_pm=500,.press_pm=50,.release_pm=100,.reset_pm=50};
    rt_cfg_t f = c; f.rt_enabled=false;
    rt_scan_cfg_t rt, classic;
    rt_prepare_scan(&rt,&c,0); rt_prepare_scan(&classic,&f,0);
    hhkb_rt_mask_t mask={{0}};
    matrix_row_t matrix[4]={0};
    scan_pending_t p={.col=14,.row=3,.valid=true,.raw=1600};
    rt_key_set_range(&s_rt_keys[14][3],1000,2000);
    hhkb_scan_cache_prepare(&s_scan_cache,s_rt_keys,&rt,&classic,&mask,1,1,1);
    assert(scan_process_pending(&p,&rt,&classic,&mask,matrix,1));
    assert(matrix[3] & (1u<<14));
    hhkb_rt_mask_set(&mask,59,1);
    hhkb_scan_cache_prepare(&s_scan_cache,s_rt_keys,&rt,&classic,&mask,2,1,1);
    assert(!scan_process_pending(&p,&rt,&classic,&mask,matrix,1));
    p.raw=UINT16_MAX;
    assert(!scan_process_pending(&p,&rt,&classic,&mask,matrix,1));
    assert(matrix[3] & (1u<<14));
    p.raw=1050;
    assert(scan_process_pending(&p,&rt,&classic,&mask,matrix,1));
    assert(!(matrix[3] & (1u<<14)));
    p.raw=1600;
    assert(scan_process_pending(&p,&rt,&classic,&mask,matrix,1));
    assert(matrix[3] & (1u<<14));
}
'''.replace("PROCESSOR", processor)
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            src = Path(tmp) / "pipeline.c"
            src.write_text(code)
            exe = Path(tmp) / "pipeline"
            subprocess.run([
                "clang", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2",
                "-I", str(ROOT / "keyboards/hhkb/modules/ec"),
                "-I", str(ROOT / "dmk_core/include"),
                "-DMATRIX_COLS=15", "-DMATRIX_ROWS=4", "-DHHKB_RT_KEYMASK=1",
                "-DHHKB_RT_ARBITRARY_SELECTION=1",
                str(src), str(ROOT / "keyboards/hhkb/modules/ec/rapid_trigger.c"),
                "-o", str(exe),
            ], check=True)
            subprocess.run([str(exe)], check=True)
