"""Check the production startup PD2 sequence against register mocks."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from .hhkb_helpers import ROOT, function


class HybridPd2Test(unittest.TestCase):
    def test_startup_high_then_low_in_hybrid_init(self):
        platform = (ROOT / 'platforms/stm32l072/platform.c').read_text()
        hybrid = (ROOT / 'keyboards/hhkb/modules/hybrid/hybrid.c').read_text()
        code = r'''
#include <stdint.h>
#include <assert.h>
static struct {uint32_t IOPENR,APB2ENR;} rcc;
static struct gpio {uint32_t MODER,PUPDR,OTYPER,OSPEEDR,BSRR,BRR,AFR[2];} a,b,c,d;
#define KEEP_GPIO (void)a,(void)b
#define RCC (&rcc)
#define GPIOA (&a)
#define GPIOB (&b)
#define GPIOC (&c)
#define GPIOD (&d)
#define RCC_IOPENR_GPIOAEN 1U
#define RCC_IOPENR_GPIOBEN 2U
#define RCC_IOPENR_GPIOCEN 4U
#define RCC_IOPENR_GPIODEN 8U
'''
        code += function(platform, 'static void hhkb_hybrid_startup_pd2(')
        code += function(hybrid, 'void hhkb_hybrid_init(')
        code += r'''
int main(void){
 d.MODER=d.OTYPER=d.PUPDR=UINT32_MAX;
 KEEP_GPIO;
 hhkb_hybrid_startup_pd2();
 assert(rcc.IOPENR & RCC_IOPENR_GPIODEN);
 assert(d.BSRR==4 && !d.BRR);
 assert((d.MODER & (3U<<4))==(1U<<4));
 assert(!(d.OTYPER & 4U) && !(d.PUPDR & (3U<<4)));
 assert((d.OTYPER | 4U)==UINT32_MAX); // Other pin configuration preserved.
 hhkb_hybrid_init();
 assert(d.BRR==4);
 assert((d.MODER & (3U<<4))==(1U<<4) && !(d.OTYPER & 4U));
}
'''
        # No radio: the module must not reference SPI or the attention line.
        for banned in ('SPI1', 'spi_data', 'GPIOB->BSRR'):
            self.assertNotIn(banned, hybrid)
        with tempfile.TemporaryDirectory() as tmp:
            c = Path(tmp) / 'pd2.c'
            binary = Path(tmp) / 'pd2'
            c.write_text(code)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-Wsign-compare', str(c), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)
