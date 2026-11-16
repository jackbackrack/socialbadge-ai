/*
 * Minimal VL53L4CD driver, ported from STMicroelectronics' VL53L4CD Ultra
 * Lite Driver as distributed in stm32duino/VL53L4CD (src/vl53l4cd_api.cpp,
 * V1.0.0, 29 November 2021). The default configuration table and the init,
 * timing, data-ready and result sequences are ST's; the I2C layer is the
 * Pico SDK's. Only continuous ranging is kept.
 *
 * COPYRIGHT(c) 2021 STMicroelectronics
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *   1. Redistributions of source code must retain the above copyright notice,
 *      this list of conditions and the following disclaimer.
 *   2. Redistributions in binary form must reproduce the above copyright
 *      notice, this list of conditions and the following disclaimer in the
 *      documentation and/or other materials provided with the distribution.
 *   3. Neither the name of STMicroelectronics nor the names of its
 *      contributors may be used to endorse or promote products derived from
 *      this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

#include "vl53l4cd.h"

#include "pico/stdlib.h"

#define REG_VHV_CONFIG_TIMEOUT_MACROP_LOOP_BOUND 0x0008
#define REG_GPIO_HV_MUX_CTRL 0x0030
#define REG_GPIO_TIO_HV_STATUS 0x0031
#define REG_RANGE_CONFIG_A 0x005E
#define REG_RANGE_CONFIG_B 0x0061
#define REG_INTERMEASUREMENT_MS 0x006C
#define REG_SYSTEM_INTERRUPT_CLEAR 0x0086
#define REG_SYSTEM_START 0x0087
#define REG_RESULT_RANGE_STATUS 0x0089
#define REG_RESULT_SPAD_NB 0x008C
#define REG_RESULT_SIGNAL_RATE 0x008E
#define REG_RESULT_AMBIENT_RATE 0x0090
#define REG_RESULT_SIGMA 0x0092
#define REG_RESULT_DISTANCE 0x0096
#define REG_FIRMWARE_SYSTEM_STATUS 0x00E5
#define REG_IDENTIFICATION_MODEL_ID 0x010F

#define I2C_TIMEOUT_US 10000

// Registers 0x2D..0x87, written by init (ST's VL53L4CD_DEFAULT_CONFIGURATION)
static const uint8_t DEFAULT_CONFIGURATION[] = {
    0x12, 0x00, 0x00, 0x11, 0x02, 0x00, 0x02, 0x08,  // 0x2d..0x34
    0x00, 0x08, 0x10, 0x01, 0x01, 0x00, 0x00, 0x00,  // 0x35..0x3c
    0x00, 0xff, 0x00, 0x0F, 0x00, 0x00, 0x00, 0x00,  // 0x3d..0x44
    0x00, 0x20, 0x0b, 0x00, 0x00, 0x02, 0x14, 0x21,  // 0x45..0x4c
    0x00, 0x00, 0x05, 0x00, 0x00, 0x00, 0x00, 0xc8,  // 0x4d..0x54
    0x00, 0x00, 0x38, 0xff, 0x01, 0x00, 0x08, 0x00,  // 0x55..0x5c
    0x00, 0x01, 0xcc, 0x07, 0x01, 0xf1, 0x05, 0x00,  // 0x5d..0x64
    0xa0, 0x00, 0x80, 0x08, 0x38, 0x00, 0x00, 0x00,  // 0x65..0x6c
    0x00, 0x0f, 0x89, 0x00, 0x00, 0x00, 0x00, 0x00,  // 0x6d..0x74
    0x00, 0x00, 0x01, 0x07, 0x05, 0x06, 0x06, 0x00,  // 0x75..0x7c
    0x00, 0x02, 0xc7, 0xff, 0x9B, 0x00, 0x00, 0x00,  // 0x7d..0x84
    0x01, 0x00, 0x00,                                // 0x85..0x87
};
_Static_assert(sizeof DEFAULT_CONFIGURATION == 0x87 - 0x2D + 1, "config covers 0x2D..0x87");

// Register indexes and values are big-endian on the wire.
static bool write_reg(i2c_inst_t *i2c, uint16_t reg, const uint8_t *data, size_t n) {
    uint8_t buf[2 + 4];
    buf[0] = reg >> 8;
    buf[1] = reg & 0xFF;
    for (size_t i = 0; i < n; i++) buf[2 + i] = data[i];
    return i2c_write_timeout_us(i2c, VL53L4CD_ADDR, buf, 2 + n, false, I2C_TIMEOUT_US) == (int)(2 + n);
}

static bool read_reg(i2c_inst_t *i2c, uint16_t reg, uint8_t *data, size_t n) {
    uint8_t idx[2] = {reg >> 8, reg & 0xFF};
    if (i2c_write_timeout_us(i2c, VL53L4CD_ADDR, idx, 2, true, I2C_TIMEOUT_US) != 2) return false;
    return i2c_read_timeout_us(i2c, VL53L4CD_ADDR, data, n, false, I2C_TIMEOUT_US) == (int)n;
}

static bool wr8(i2c_inst_t *i2c, uint16_t reg, uint8_t v) { return write_reg(i2c, reg, &v, 1); }

static bool wr16(i2c_inst_t *i2c, uint16_t reg, uint16_t v) {
    uint8_t b[2] = {v >> 8, v & 0xFF};
    return write_reg(i2c, reg, b, 2);
}

static bool wr32(i2c_inst_t *i2c, uint16_t reg, uint32_t v) {
    uint8_t b[4] = {v >> 24, v >> 16, v >> 8, v};
    return write_reg(i2c, reg, b, 4);
}

static bool rd8(i2c_inst_t *i2c, uint16_t reg, uint8_t *v) { return read_reg(i2c, reg, v, 1); }

static bool rd16(i2c_inst_t *i2c, uint16_t reg, uint16_t *v) {
    uint8_t b[2];
    if (!read_reg(i2c, reg, b, 2)) return false;
    *v = (uint16_t)(b[0] << 8 | b[1]);
    return true;
}

bool vl53l4cd_get_id(i2c_inst_t *i2c, uint16_t *id) { return rd16(i2c, REG_IDENTIFICATION_MODEL_ID, id); }

bool vl53l4cd_clear_interrupt(i2c_inst_t *i2c) { return wr8(i2c, REG_SYSTEM_INTERRUPT_CLEAR, 0x01); }

bool vl53l4cd_stop(i2c_inst_t *i2c) { return wr8(i2c, REG_SYSTEM_START, 0x00); }

bool vl53l4cd_data_ready(i2c_inst_t *i2c, bool *ready) {
    uint8_t mux, tio;
    if (!rd8(i2c, REG_GPIO_HV_MUX_CTRL, &mux) || !rd8(i2c, REG_GPIO_TIO_HV_STATUS, &tio)) return false;
    uint8_t int_pol = (mux & 0x10) ? 0 : 1;
    *ready = (tio & 1) == int_pol;
    return true;
}

static bool wait_data_ready(i2c_inst_t *i2c, uint32_t timeout_ms) {
    for (uint32_t i = 0; i < timeout_ms; i++) {
        bool ready;
        if (!vl53l4cd_data_ready(i2c, &ready)) return false;
        if (ready) return true;
        sleep_ms(1);
    }
    return false;
}

bool vl53l4cd_init(i2c_inst_t *i2c) {
    uint8_t st = 0;
    uint32_t i = 0;
    for (; i < 1000; i++) {  // boot: FIRMWARE_SYSTEM_STATUS reads 3
        if (rd8(i2c, REG_FIRMWARE_SYSTEM_STATUS, &st) && st == 0x3) break;
        sleep_ms(1);
    }
    if (i == 1000) return false;

    for (uint16_t a = 0x2D; a <= 0x87; a++)
        if (!wr8(i2c, a, DEFAULT_CONFIGURATION[a - 0x2D])) return false;

    // VHV: one measurement, then stop
    if (!wr8(i2c, REG_SYSTEM_START, 0x40)) return false;
    if (!wait_data_ready(i2c, 1000)) return false;
    if (!vl53l4cd_clear_interrupt(i2c) || !vl53l4cd_stop(i2c)) return false;
    if (!wr8(i2c, REG_VHV_CONFIG_TIMEOUT_MACROP_LOOP_BOUND, 0x09)) return false;
    if (!wr8(i2c, 0x0B, 0) || !wr16(i2c, 0x0024, 0x500)) return false;
    return vl53l4cd_set_timing(i2c, 50);
}

static uint16_t macrop(uint32_t budget_us, uint32_t macro_period_us, uint32_t mult) {
    uint32_t tmp = macro_period_us * mult;
    uint32_t ls = ((budget_us + ((tmp >> 6) >> 1)) / (tmp >> 6)) - 1;
    uint16_t ms = 0;
    while (ls & 0xFFFFFF00U) {
        ls >>= 1;
        ms++;
    }
    return (uint16_t)((ms << 8) + (ls & 0xFF));
}

bool vl53l4cd_set_timing(i2c_inst_t *i2c, uint32_t budget_ms) {
    uint16_t osc;
    if (budget_ms < 10 || budget_ms > 200) return false;
    if (!rd16(i2c, 0x0006, &osc) || osc == 0) return false;
    uint32_t macro_period_us = (uint32_t)(2304 * (0x40000000 / (uint32_t)osc)) >> 6;
    if (!wr32(i2c, REG_INTERMEASUREMENT_MS, 0)) return false;  // continuous
    uint32_t budget_us = (budget_ms * 1000 - 2500) << 12;
    return wr16(i2c, REG_RANGE_CONFIG_A, macrop(budget_us, macro_period_us, 16)) &&
           wr16(i2c, REG_RANGE_CONFIG_B, macrop(budget_us, macro_period_us, 12));
}

bool vl53l4cd_start(i2c_inst_t *i2c) {
    if (!wr8(i2c, REG_SYSTEM_START, 0x21)) return false;  // continuous mode
    if (!wait_data_ready(i2c, 1000)) return false;
    return vl53l4cd_clear_interrupt(i2c);
}

bool vl53l4cd_get_result(i2c_inst_t *i2c, vl53l4cd_result_t *r) {
    static const uint8_t status_rtn[24] = {255, 255, 255, 5,   2,   4,   1,   7,  3,  0,  255, 255,
                                           9,   13,  255, 255, 255, 255, 10,  6,  255, 255, 11, 12};
    uint8_t s;
    uint16_t v;
    if (!rd8(i2c, REG_RESULT_RANGE_STATUS, &s)) return false;
    s &= 0x1F;
    r->range_status = s < 24 ? status_rtn[s] : s;
    if (!rd16(i2c, REG_RESULT_SPAD_NB, &v)) return false;
    r->number_of_spad = v / 256;
    if (r->number_of_spad == 0) {
        r->range_status = 255;
        return true;
    }
    if (!rd16(i2c, REG_RESULT_SIGNAL_RATE, &v)) return false;
    r->signal_rate_kcps = v * 8;
    if (!rd16(i2c, REG_RESULT_AMBIENT_RATE, &v)) return false;
    r->ambient_rate_kcps = v * 8;
    if (!rd16(i2c, REG_RESULT_SIGMA, &v)) return false;
    r->sigma_mm = v / 4;
    if (!rd16(i2c, REG_RESULT_DISTANCE, &v)) return false;
    r->distance_mm = v;
    return true;
}
