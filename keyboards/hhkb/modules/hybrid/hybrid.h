#pragma once

#include <stdbool.h>
#include <stdint.h>

// nxmk: Hybrid board support WITHOUT the radio. The Nordic nRF52832 link
// (SPI slave, attention line, pairing, profiles, battery reporting) is not
// built. Only USB/battery source detection and the battery soft-OFF/STOP
// path remain.

void hhkb_hybrid_init(void);
bool hhkb_hybrid_on_battery(void);   // PC13 high: no USB power
bool hhkb_hybrid_powered(void);      // false once battery soft-OFF began
// Battery power has no output path, so any battery source forces soft-OFF.
void hhkb_hybrid_power_poll(void);
void hhkb_hybrid_off_service(void);  // USB insertion while OFF resets the MCU
void hhkb_hybrid_enter_stop(void);   // Never returns; USB wake resets the MCU


uint32_t hhkb_hybrid_indicator_wait_ms(uint32_t now_ms);
bool hhkb_hybrid_led_override(uint8_t index, uint32_t now_ms, bool *on);
void hhkb_hybrid_refresh_indicators(void);
