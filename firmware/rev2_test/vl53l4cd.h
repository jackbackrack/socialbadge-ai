// Minimal VL53L4CD driver: the parts of ST's Ultra Lite Driver (ULD) the
// bring-up test needs -- sensor ID, init, continuous ranging, results.
// Ported from STMicroelectronics' VL53L4CD ULD as distributed in the
// stm32duino/VL53L4CD library (BSD-3-Clause; see vl53l4cd.c).

#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "hardware/i2c.h"

#define VL53L4CD_ADDR 0x29         // 7-bit (the datasheet's 0x52 is 8-bit)
#define VL53L4CD_MODEL_ID 0xEBAA   // IDENTIFICATION_MODEL_ID, 16-bit at 0x010F

typedef struct {
    uint8_t range_status;  // 0 = valid; ST's ULD status codes otherwise
    uint16_t distance_mm;
    uint16_t sigma_mm;
    uint16_t signal_rate_kcps;
    uint16_t ambient_rate_kcps;
    uint16_t number_of_spad;
} vl53l4cd_result_t;

// Every call returns false on an I2C error or timeout.
bool vl53l4cd_get_id(i2c_inst_t *i2c, uint16_t *id);
bool vl53l4cd_init(i2c_inst_t *i2c);  // boot wait, default config, VHV
bool vl53l4cd_set_timing(i2c_inst_t *i2c, uint32_t budget_ms);  // continuous mode, 10..200 ms
bool vl53l4cd_start(i2c_inst_t *i2c);
bool vl53l4cd_stop(i2c_inst_t *i2c);
bool vl53l4cd_data_ready(i2c_inst_t *i2c, bool *ready);
bool vl53l4cd_get_result(i2c_inst_t *i2c, vl53l4cd_result_t *r);
bool vl53l4cd_clear_interrupt(i2c_inst_t *i2c);
