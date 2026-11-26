// SPDX-License-Identifier: MIT
// nxmk: radio-free Hybrid support. The former Nordic SPI link (adapted from
// l3tnun's hhkb_hybrid nrf_spi.c / hhkb_hybrid.c; see LICENSE.protocol) has
// been removed. Only power-source detection and battery soft-OFF remain.
#include "hybrid.h"
#include "FreeRTOS.h"
#include "task.h"
#include "stm32l072xx.h"

static volatile bool powered = true;

void hhkb_hybrid_init(void) {
    RCC->IOPENR |= RCC_IOPENR_GPIOAEN | RCC_IOPENR_GPIOBEN |
                   RCC_IOPENR_GPIOCEN | RCC_IOPENR_GPIODEN;
    GPIOC->MODER &= ~(3UL << 26); // PC13: power-source input
    // Stock ends the startup-HIGH PD2 phase once the main loop is ready; the
    // scan wrapper keeps it LOW afterwards (see classic_matrix.c).
    GPIOD->OTYPER &= ~(1U << 2);
    GPIOD->BRR = 1U << 2;
    GPIOD->MODER = (GPIOD->MODER & ~(3UL << 4)) | (1UL << 4);
}

bool hhkb_hybrid_on_battery(void) { return (GPIOC->IDR & (1U << 13)) != 0; }
bool hhkb_hybrid_powered(void) { return powered; }

void hhkb_hybrid_power_poll(void) {
    if (powered && hhkb_hybrid_on_battery()) {
        powered = false;
        hhkb_hybrid_refresh_indicators();
    }
}

void hhkb_hybrid_off_service(void) {
    if (powered) return;
    IWDG->KR = 0xAAAA;
    if (!hhkb_hybrid_on_battery()) NVIC_SystemReset(); // USB inserted: clean restart.
}

uint32_t hhkb_hybrid_indicator_wait_ms(uint32_t now_ms) {
    (void)now_ms;
    return powered ? 250 : 50;
}

bool hhkb_hybrid_led_override(uint8_t index, uint32_t now_ms, bool *on) {
    (void)index;
    (void)now_ms;
    if (powered) return false;
    *on = false;
    return true;
}
