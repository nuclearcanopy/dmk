// SPDX-License-Identifier: MIT
// Modifications Copyright (C) 2026 nuclearcanopy, licensed AGPL-3.0-or-later.
// Reduced to the USB-wake-only battery STOP. Adapted from l3tnun's MIT-licensed hhkb_hybrid/power.c STOP wake sequence.
// The upstream copyright and license are in LICENSE.protocol.
#include "hybrid.h"
#include "stm32l072xx.h"

#define WAKE_EXTI_MASK (1UL << 13)
// Volatile RAM markers for SWD; these are not persisted across reset.
// 1: preparing, 3: before WFI, 4: woke.
volatile uint32_t hhkb_stop_stage;
volatile uint32_t hhkb_stop_wake_count;

#define LPTIM_ARR 500U // LSI / 128: about 1.7 seconds between watchdog refreshes.

// Wake only: the pending EXTI line ends WFI even with PRIMASK set.
void EXTI4_15_IRQHandler(void) { EXTI->PR = 1UL << 13; }
void LPTIM1_IRQHandler(void) { LPTIM1->ICR = LPTIM_ICR_ARRMCF; }

static void prepare_wake_sources(void) {
    RCC->APB2ENR |= RCC_APB2ENR_SYSCFGEN;
    SYSCFG->EXTICR[3] = (SYSCFG->EXTICR[3] & ~SYSCFG_EXTICR4_EXTI13) |
                         SYSCFG_EXTICR4_EXTI13_PC;
    // Terminal path owns EXTI: do not inherit unrelated bootloader sources.
    EXTI->FTSR = WAKE_EXTI_MASK;
    EXTI->RTSR = WAKE_EXTI_MASK;
    EXTI->IMR = WAKE_EXTI_MASK;
    EXTI->EMR = 0;

    RCC->CSR |= RCC_CSR_LSION;
    while (!(RCC->CSR & RCC_CSR_LSIRDY)) {}
    RCC->APB1ENR |= RCC_APB1ENR_LPTIM1EN | RCC_APB1ENR_PWREN;
    RCC->CCIPR = (RCC->CCIPR & ~RCC_CCIPR_LPTIM1SEL) |
                 RCC_CCIPR_LPTIM1SEL_0;
    LPTIM1->CR = 0;
    LPTIM1->CFGR = 7UL << LPTIM_CFGR_PRESC_Pos;
    LPTIM1->IER = LPTIM_IER_ARRMIE;
    LPTIM1->CR = LPTIM_CR_ENABLE;
    LPTIM1->ICR = LPTIM_ICR_ARROKCF;
    LPTIM1->ARR = LPTIM_ARR;
    while (!(LPTIM1->ISR & LPTIM_ISR_ARROK)) {}
    LPTIM1->CR |= LPTIM_CR_CNTSTRT;

    NVIC->ICER[0] = 0xFFFFFFFFUL;
    NVIC->ICPR[0] = 0xFFFFFFFFUL;
    NVIC_EnableIRQ(EXTI4_15_IRQn);
    NVIC_EnableIRQ(LPTIM1_IRQn);
}

static void stop_once(void) {
    EXTI->PR = WAKE_EXTI_MASK;
    LPTIM1->ICR = LPTIM_ICR_ARRMCF;
    NVIC->ICPR[0] = 0xFFFFFFFFUL;
    PWR->CR |= PWR_CR_CWUF;
    PWR->CR = (PWR->CR & ~PWR_CR_PDDS) | PWR_CR_LPSDSR;
    SCB->SCR |= SCB_SCR_SLEEPDEEP_Msk;
    hhkb_stop_stage = 3;
    __DSB();
    __WFI();
    hhkb_stop_stage = 4;
    ++hhkb_stop_wake_count;
    SCB->SCR &= ~SCB_SCR_SLEEPDEEP_Msk;
}

// Battery-only terminal state: wake solely on USB power (PC13), which resets.
void hhkb_hybrid_enter_stop(void) {
    hhkb_stop_stage = 1;
    hhkb_stop_wake_count = 0;
    TIM2->DIER = 0;
    TIM2->CR1 &= ~TIM_CR1_CEN;
    if (ADC1->CR & ADC_CR_ADEN) {
        ADC1->CR |= ADC_CR_ADDIS;
        while (ADC1->CR & ADC_CR_ADEN) {}
    }
    ADC1->CR &= ~ADC_CR_ADVREGEN;
    GPIOC->BRR = (1UL << 14) | (1UL << 7) | (1UL << 8);
    GPIOA->BRR = (1UL << 8) | (1UL << 9);
    // Remove drive from all rows and mux address lines.
    GPIOB->BRR = 0xFC07UL;
    GPIOC->BRR = 1UL << 6;

    __disable_irq();
    SysTick->CTRL = 0;
    // A pending RTOS exception must not keep the terminal WFI loop awake.
    SCB->ICSR = SCB_ICSR_PENDSTCLR_Msk | SCB_ICSR_PENDSVCLR_Msk;
    prepare_wake_sources();
    // Preserve an attached debug session, but do not inherit low-power debug
    // clock retention when no debugger is attached.
    // CMSIS M0+ omits CoreDebug; DHCSR.C_DEBUGEN is architectural bit 0.
    if (!(*(volatile const uint32_t *)0xE000EDF0UL & 1U))
        DBGMCU->CR &= ~(DBGMCU_CR_DBG_SLEEP | DBGMCU_CR_DBG_STOP | DBGMCU_CR_DBG_STANDBY);
    // USB is unavailable on this battery-only terminal path. Shut down the
    // transceiver before its clock; merely disabling its IRQ is insufficient.
    RCC->APB1ENR |= RCC_APB1ENR_USBEN;
    USB->BCDR &= ~USB_BCDR_DPPU;
    USB->CNTR = USB_CNTR_FRES | USB_CNTR_PDWN;
    RCC->APB1ENR &= ~(RCC_APB1ENR_USBEN | RCC_APB1ENR_CRSEN);
    RCC->CRRCR &= ~RCC_CRRCR_HSI48ON;
    SYSCFG->CFGR3 &= ~(SYSCFG_CFGR3_ENREF_HSI48 |
                          SYSCFG_CFGR3_ENBUF_VREFINT_ADC |
                          SYSCFG_CFGR3_ENBUF_SENSOR_ADC);
    // No code after this point needs the PLL or the 32 MHz system clock.
    RCC->CR |= RCC_CR_HSION;
    while (!(RCC->CR & RCC_CR_HSIRDY)) {}
    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_HSI;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_HSI) {}
    RCC->CR &= ~(RCC_CR_PLLON | RCC_CR_MSION);

    for (;;) {
        IWDG->KR = 0xAAAA;
        if (!(GPIOC->IDR & (1UL << 13))) NVIC_SystemReset();
        stop_once();
    }
}
