// Rev 2 bring-up tests for the social badge: status LEDs, the front LED grid,
// the VL53L4CD distance sensor and the IR emitter/receiver.
//
// Driven over USB serial with one-key commands (see MENU). Each test prints
// what it did and ends with a line "== DONE <test>: PASS|FAIL|CHECK ==", so
// host.py can run it and collect the result; CHECK means the result is
// something to look at (LEDs) rather than something the board can measure.
//
// At power-up it runs the demo (distance sets the grid's hue and heartbeat
// rate) until a key arrives, so the badge demos on battery alone; host.py's
// first key stops it. BOOT_INTO_DEMO=0 starts at the menu instead.
//
// Pins (designs/badge_main.py):
//   GPIO0..2  status LEDs, active high
//   GPIO4/5   I2C0 SDA/SCL to the VL53L4CD (2.2 kOhm pull-ups on the board)
//   GPIO6     IR emitter, 38 kHz PWM (slice 3 A) into the BSS138 gate
//   GPIO7     IR receiver output, active low
//   GPIO8     VL53L4CD XSHUT (10 kOhm pull-up), GPIO9 its GPIO1 interrupt
//   GPIO10    LED grid power switch, high = VLED on
//   GPIO11    LED grid data (33 Ohm series), driven by PIO
//
// LED_DATA is held low whenever VLED is off: the WS2812s would otherwise be
// powered through their DIN protection diodes.

#include <math.h>
#include <stdio.h>

#include "hardware/clocks.h"
#include "hardware/i2c.h"
#include "hardware/pio.h"
#include "hardware/pwm.h"
#include "pico/bootrom.h"
#include "pico/stdlib.h"
#include "vl53l4cd.h"
#include "ws2812.pio.h"

#define PIN_TOF_SDA 4
#define PIN_TOF_SCL 5
#define PIN_IR_TX 6
#define PIN_IR_RX 7
#define PIN_TOF_XSHUT 8
#define PIN_TOF_INT 9
#define PIN_LED_EN 10
#define PIN_LED_DATA 11

static const uint STATUS_PINS[] = {0, 1, 2};
#define N_STATUS (sizeof STATUS_PINS / sizeof STATUS_PINS[0])

#define GRID_N 4
#define N_LEDS (GRID_N * GRID_N)
#define LEVEL 24  // of 255: dim, so the grid draws little from the charger on USB

#define IR_CARRIER_HZ 38000

// 1: power up straight into the distance/heartbeat demo (see test_demo);
// 0: wait at the test menu. Either way host.py's first key gets the menu.
#ifndef BOOT_INTO_DEMO
#define BOOT_INTO_DEMO 1
#endif

static const char MENU[] =
    "commands:\n"
    "  s  status LED chase (GPIO0..2)\n"
    "  g  LED grid: colours, index walk, rainbow\n"
    "  t  distance sensor (VL53L4CD): bus scan, ID, 3 s of ranging\n"
    "  i  IR loopback: 38 kHz bursts from the emitter, counted at the receiver\n"
    "  r  IR receive monitor, 10 s (point a TV remote at the badge)\n"
    "  d  demo: distance sets the hue (red near, blue far) and the heartbeat (fast near); any key stops\n"
    "  c  raw distance readings, one CSV line each, for calibrate.py; any key stops\n"
    "  a  all of s, g, t, i\n"
    "  b  reboot to BOOTSEL (for reflashing)\n";

static void done(const char *test, const char *result) { printf("== DONE %s: %s ==\n", test, result); }

// ---------------------------------------------------------------- status LEDs

static void test_status(void) {
    static const uint chase[] = {0, 1, 2, 1};
    printf("status LEDs: chasing GPIO0 -> 1 -> 2 -> 1, 3 passes\n");
    for (uint pass = 0; pass < 3; pass++) {
        for (uint s = 0; s < 4; s++) {
            for (uint i = 0; i < N_STATUS; i++) gpio_put(STATUS_PINS[i], i == chase[s]);
            sleep_ms(200);
        }
    }
    for (uint i = 0; i < N_STATUS; i++) gpio_put(STATUS_PINS[i], 0);
    done("status", "CHECK (each of the three LEDs lit in turn?)");
}

// ------------------------------------------------------------------ LED grid

static PIO grid_pio = pio0;
static uint grid_sm;

static void grid_init(void) {
    uint offset = pio_add_program(grid_pio, &ws2812_program);
    grid_sm = pio_claim_unused_sm(grid_pio, true);
    pio_gpio_init(grid_pio, PIN_LED_DATA);
    pio_sm_set_consecutive_pindirs(grid_pio, grid_sm, PIN_LED_DATA, 1, true);
    pio_sm_config c = ws2812_program_get_default_config(offset);
    sm_config_set_sideset_pins(&c, PIN_LED_DATA);
    sm_config_set_out_shift(&c, false, true, 24);  // MSB first, autopull 24 bits
    sm_config_set_fifo_join(&c, PIO_FIFO_JOIN_TX);
    float cycles = ws2812_T1 + ws2812_T2 + ws2812_T3;
    sm_config_set_clkdiv(&c, clock_get_hz(clk_sys) / (800000.0f * cycles));
    pio_sm_init(grid_pio, grid_sm, offset, &c);
    pio_sm_set_enabled(grid_pio, grid_sm, true);
}

static uint32_t rgb(uint8_t r, uint8_t g, uint8_t b) { return (uint32_t)g << 16 | (uint32_t)r << 8 | b; }

// Send one frame (index 0 first) and wait out the latch (>= 280 us low).
static void grid_show(const uint32_t frame[N_LEDS]) {
    for (uint i = 0; i < N_LEDS; i++) pio_sm_put_blocking(grid_pio, grid_sm, frame[i] << 8u);
    while (!pio_sm_is_tx_fifo_empty(grid_pio, grid_sm)) tight_loop_contents();
    sleep_us(30 + 300);  // the last word shifting out, then the reset gap
}

static void grid_fill(uint32_t color) {
    uint32_t frame[N_LEDS];
    for (uint i = 0; i < N_LEDS; i++) frame[i] = color;
    grid_show(frame);
}

static void grid_power(bool on) {
    if (on) {
        gpio_put(PIN_LED_EN, 1);
        sleep_ms(20);
    } else {
        grid_fill(0);  // dark first, then cut the supply; the PIO keeps DATA low
        gpio_put(PIN_LED_EN, 0);
    }
}

// Chain index -> position, as front_leds.grid_transform lays the chain out:
// row 0 is the bottom row (nearest the sensors), even rows run right to left
// and odd rows left to right, seen from the front.
static void grid_position(uint i, uint *row, uint *col) {
    *row = i / GRID_N;
    uint c = i % GRID_N;
    *col = (*row % 2) ? c : GRID_N - 1 - c;
}

static uint32_t wheel(uint8_t pos) {  // 0..255 around the colour wheel, at LEVEL
    uint32_t r, g, b;
    if (pos < 85) {
        r = 255 - pos * 3, g = pos * 3, b = 0;
    } else if (pos < 170) {
        pos -= 85;
        r = 0, g = 255 - pos * 3, b = pos * 3;
    } else {
        pos -= 170;
        r = pos * 3, g = 0, b = 255 - pos * 3;
    }
    return rgb(r * LEVEL / 255, g * LEVEL / 255, b * LEVEL / 255);
}

static void test_grid(void) {
    static const struct {
        const char *name;
        uint8_t r, g, b;
    } colours[] = {
        {"red", LEVEL, 0, 0}, {"green", 0, LEVEL, 0}, {"blue", 0, 0, LEVEL}, {"white", LEVEL, LEVEL, LEVEL}};

    printf("LED grid: VLED on (GPIO10 high)\n");
    grid_power(true);
    for (uint k = 0; k < 4; k++) {
        printf("  all %s\n", colours[k].name);
        grid_fill(rgb(colours[k].r, colours[k].g, colours[k].b));
        sleep_ms(800);
    }

    printf("  index walk (row 0 = bottom, nearest the sensors; col 0 = left, seen from the front)\n");
    uint32_t frame[N_LEDS];
    for (uint i = 0; i < N_LEDS; i++) {
        uint row, col;
        grid_position(i, &row, &col);
        for (uint j = 0; j < N_LEDS; j++) frame[j] = j == i ? rgb(LEVEL, LEVEL, LEVEL) : 0;
        grid_show(frame);
        printf("    LED %2u: row %u, col %u\n", i, row, col);
        sleep_ms(350);
    }

    printf("  rainbow, 4 s\n");
    for (uint t = 0; t < 200; t++) {
        for (uint i = 0; i < N_LEDS; i++) frame[i] = wheel((uint8_t)(i * 256 / N_LEDS + t * 4));
        grid_show(frame);
        sleep_ms(20);
    }

    grid_power(false);
    printf("LED grid: off, VLED off (GPIO10 low), DATA held low\n");
    done("grid", "CHECK (16 LEDs each red/green/blue/white? walk in chain order?)");
}

// ----------------------------------------------------------- distance sensor

static void test_tof(void) {
    bool pass = true;

    printf("distance sensor: XSHUT low 10 ms, then high\n");
    gpio_put(PIN_TOF_XSHUT, 0);
    sleep_ms(10);
    gpio_put(PIN_TOF_XSHUT, 1);
    sleep_ms(5);

    printf("  I2C0 scan:");
    uint found = 0;
    for (uint8_t a = 0x08; a < 0x78; a++) {
        uint8_t b;
        if (i2c_read_timeout_us(i2c0, a, &b, 1, false, 2000) == 1) {
            printf(" 0x%02x", a);
            found++;
        }
    }
    printf(found ? "\n" : " nothing (SDA/SCL, pull-ups, 3V3 or XSHUT?)\n");

    uint16_t id = 0;
    if (!vl53l4cd_get_id(i2c0, &id)) {
        printf("  model ID: no answer at 0x%02x\n", VL53L4CD_ADDR);
        done("tof", "FAIL");
        return;
    }
    printf("  model ID: 0x%04x (expect 0x%04x)\n", id, VL53L4CD_MODEL_ID);
    if (id != VL53L4CD_MODEL_ID) pass = false;

    if (!vl53l4cd_init(i2c0) || !vl53l4cd_start(i2c0)) {
        printf("  init / start ranging failed\n");
        vl53l4cd_stop(i2c0);
        done("tof", "FAIL");
        return;
    }

    // Each sample waits for the interrupt pin (active low, open drain with a
    // 10 kOhm pull-up) before reading over I2C, so a dead GPIO1 line shows up.
    printf("  ranging, 50 ms budget; wave a hand over the front of the badge\n");
    uint int_seen = 0, valid = 0, n = 60;
    for (uint k = 0; k < n; k++) {
        absolute_time_t until = make_timeout_time_ms(200);
        bool irq = false;
        while (!time_reached(until))
            if (!gpio_get(PIN_TOF_INT)) {
                irq = true;
                break;
            }
        bool ready = irq;
        if (!irq) vl53l4cd_data_ready(i2c0, &ready);
        vl53l4cd_result_t r;
        if (ready && vl53l4cd_get_result(i2c0, &r)) {
            int_seen += irq;
            valid += r.range_status == 0;
            if (k % 3 == 0)
                printf("    %4u mm  status %3u  signal %5u kcps  ambient %5u kcps  sigma %3u mm%s\n", r.distance_mm,
                       r.range_status, r.signal_rate_kcps, r.ambient_rate_kcps, r.sigma_mm,
                       irq ? "" : "  (no INT)");
        } else {
            printf("    no data\n");
        }
        vl53l4cd_clear_interrupt(i2c0);
    }
    vl53l4cd_stop(i2c0);
    printf("  %u/%u samples valid (status 0); interrupt pin seen on %u\n", valid, n, int_seen);
    if (valid == 0) printf("  no valid range: nothing within ~1.3 m in front of the sensor?\n");
    if (int_seen == 0) {
        printf("  GPIO1 interrupt never went low (GPIO9 line?)\n");
        pass = false;
    }
    done("tof", pass && valid > 0 ? "PASS" : "FAIL");
}

// ----------------------------------------------------------------------- IR

static uint ir_slice, ir_chan;
static uint16_t ir_on_level;

static void ir_init(void) {
    gpio_set_function(PIN_IR_TX, GPIO_FUNC_PWM);
    ir_slice = pwm_gpio_to_slice_num(PIN_IR_TX);
    ir_chan = pwm_gpio_to_channel(PIN_IR_TX);
    uint32_t wrap = clock_get_hz(clk_sys) / IR_CARRIER_HZ - 1;
    pwm_set_wrap(ir_slice, wrap);
    ir_on_level = (uint16_t)((wrap + 1) / 3);  // 33% duty
    pwm_set_chan_level(ir_slice, ir_chan, 0);  // emitter off
    pwm_set_enabled(ir_slice, true);
}

static void ir_carrier(bool on) { pwm_set_chan_level(ir_slice, ir_chan, on ? ir_on_level : 0); }

// Count the receiver going low within a window.
static uint ir_count_lows(uint32_t window_us) {
    uint lows = 0;
    bool prev = gpio_get(PIN_IR_RX);
    uint64_t end = time_us_64() + window_us;
    while (time_us_64() < end) {
        bool now = gpio_get(PIN_IR_RX);
        if (prev && !now) lows++;
        prev = now;
    }
    return lows;
}

// Bursts the receiver should accept: 600 us of carrier (23 cycles, past the
// ~10-cycle minimum), then a 2.4 ms gap so its AGC doesn't treat them as noise.
static uint ir_bursts(uint n) {
    uint seen = 0;
    for (uint k = 0; k < n; k++) {
        ir_carrier(true);
        uint lows = ir_count_lows(600);
        ir_carrier(false);
        lows += ir_count_lows(400);  // output lags the burst by up to ~300 us
        seen += lows > 0;
        sleep_us(2000);
    }
    return seen;
}

static void test_ir(void) {
    const uint n = 40;
    printf("IR: receiver idles %s (expect high)\n", gpio_get(PIN_IR_RX) ? "high" : "LOW");
    uint noise = ir_count_lows(300000);
    printf("  emitter off, 300 ms: %u pulses at the receiver (expect 0)\n", noise);

    uint direct = ir_bursts(n);
    printf("  %u bursts as is: receiver saw %u\n", n, direct);
    printf("  now hold a hand or white card 3-10 cm over the front; next bursts in 3 s\n");
    sleep_ms(3000);
    uint reflected = ir_bursts(n);
    printf("  %u bursts with a reflector: receiver saw %u\n", n, reflected);

    bool idle_ok = gpio_get(PIN_IR_RX);
    bool pass = idle_ok && noise == 0 && (direct >= n * 3 / 4 || reflected >= n * 3 / 4);
    if (!pass && idle_ok && noise == 0 && reflected == 0 && direct == 0)
        printf("  nothing received: emitter not lighting (D23 orientation, Q3, GPIO6?) or receiver deaf\n");
    done("ir", pass ? "PASS" : "FAIL");
}

static void test_ir_monitor(void) {
    printf("IR monitor, 10 s: point a remote at the badge and press a button\n");
    uint64_t end = time_us_64() + 10000000, edge = time_us_64();
    bool prev = gpio_get(PIN_IR_RX);
    uint marks = 0, printed = 0;
    while (time_us_64() < end) {
        bool now = gpio_get(PIN_IR_RX);
        if (now != prev) {
            uint64_t t = time_us_64();
            if (!now) marks++;
            if (printed < 64) {  // first frame's durations: mark (low) / space (high)
                printf("%s%llu", now ? " m" : " s", (unsigned long long)(t - edge));
                if (++printed % 16 == 0) printf("\n");
            }
            edge = t;
            prev = now;
        }
    }
    printf("\n  %u marks in 10 s\n", marks);
    done("ir_monitor", marks ? "PASS" : "CHECK (no IR seen)");
}

// --------------------------------------------------------------------- demo

#define DEMO_NEAR_MM 20    // hue DEMO_HUE_NEAR at or closer than this
#define DEMO_FAR_MM 1000   // hue DEMO_HUE_FAR at or beyond this, and with nothing in range
#define DEMO_BUDGET_MS 50  // sensor timing budget: longer reaches further, but updates less often
#define DEMO_MEDIAN 5      // readings in the median filter (odd)
#define DEMO_HUE_NEAR 0    // red
#define DEMO_HUE_FAR 240   // blue (360 would wrap back round to red)
#define DEMO_VALUE 100     // of 255: 16 LEDs at full hue draw >600 mA, past the 500 mA charger on USB
#define DEMO_BPM_NEAR 140  // heartbeat rate at DEMO_NEAR_MM...
#define DEMO_BPM_FAR 50    // ...easing down to this at DEMO_FAR_MM
#define DEMO_REST 0.35f    // brightness between beats, as a fraction of a beat's peak (before gamma)
#define DEMO_FRAME_MS 10

// One raised-cosine bump: 1 at centre, easing to 0 at centre +/- half_width.
static float bump(float x, float centre, float half_width) {
    float d = (x - centre) / half_width;
    return d <= -1.0f || d >= 1.0f ? 0.0f : 0.5f * (1.0f + cosf((float)M_PI * d));
}

// Heartbeat envelope over one beat period, phase 0..1: a strong "lub", a
// softer "dub" just after, then rest. 0..1.
static float heartbeat(float phase) {
    float lub = bump(phase, 0.10f, 0.10f), dub = 0.55f * bump(phase, 0.32f, 0.12f);
    return lub > dub ? lub : dub;
}

// Hue 0..359 degrees at full saturation, value 0..255.
static uint32_t hsv(uint hue, uint8_t value) {
    hue %= 360;
    uint sector = hue / 60, f = (hue % 60) * 255 / 60;  // position within the sector, 0..255
    uint8_t up = (uint8_t)(value * f / 255), down = (uint8_t)(value * (255 - f) / 255);
    switch (sector) {
        case 0: return rgb(value, up, 0);
        case 1: return rgb(down, value, 0);
        case 2: return rgb(0, value, up);
        case 3: return rgb(0, down, value);
        case 4: return rgb(up, 0, value);
        default: return rgb(value, 0, down);
    }
}

// Median of the last DEMO_MEDIAN readings: throws out a single bad reading
// (a spurious near value, a dropout) while following a real change within
// (DEMO_MEDIAN + 1) / 2 readings.
static uint16_t median_push(uint16_t window[DEMO_MEDIAN], uint *next, uint16_t value) {
    window[*next] = value;
    *next = (*next + 1) % DEMO_MEDIAN;
    uint16_t sorted[DEMO_MEDIAN];
    for (uint i = 0; i < DEMO_MEDIAN; i++) {  // insertion sort, 5 values
        uint16_t v = window[i];
        uint j = i;
        for (; j > 0 && sorted[j - 1] > v; j--) sorted[j] = sorted[j - 1];
        sorted[j] = v;
    }
    return sorted[DEMO_MEDIAN / 2];
}

// Every reading as it comes, unfiltered, for calibrate.py:
//   RAW,<ms>,<distance_mm>,<status>,<signal_kcps>,<ambient_kcps>,<sigma_mm>,<spads>
// status 0 is a valid range; 255 means no target (no SPADs returned).
static void test_raw(void) {
    printf("raw distance readings, %u ms budget; any key stops\n", DEMO_BUDGET_MS);
    gpio_put(PIN_TOF_XSHUT, 0);
    sleep_ms(10);
    gpio_put(PIN_TOF_XSHUT, 1);
    sleep_ms(5);
    if (!vl53l4cd_init(i2c0) || !vl53l4cd_set_timing(i2c0, DEMO_BUDGET_MS) || !vl53l4cd_start(i2c0)) {
        printf("  distance sensor didn't start\n");
        done("raw", "FAIL");
        return;
    }
    uint64_t start = time_us_64();
    while (getchar_timeout_us(0) == PICO_ERROR_TIMEOUT) {
        bool ready = false;
        vl53l4cd_data_ready(i2c0, &ready);
        if (!ready) {
            sleep_ms(1);
            continue;
        }
        vl53l4cd_result_t r = {0};
        bool ok = vl53l4cd_get_result(i2c0, &r);
        vl53l4cd_clear_interrupt(i2c0);
        if (ok)
            printf("RAW,%llu,%u,%u,%u,%u,%u,%u\n", (unsigned long long)((time_us_64() - start) / 1000), r.distance_mm,
                   r.range_status, r.signal_rate_kcps, r.ambient_rate_kcps, r.sigma_mm, r.number_of_spad);
    }
    vl53l4cd_stop(i2c0);
    done("raw", "stopped");
}

static void test_demo(void) {
    printf("demo: %u mm = hue %u, %u bpm to %u mm = hue %u, %u bpm; any key stops\n", DEMO_NEAR_MM, DEMO_HUE_NEAR,
           DEMO_BPM_NEAR, DEMO_FAR_MM, DEMO_HUE_FAR, DEMO_BPM_FAR);
    gpio_put(PIN_TOF_XSHUT, 0);
    sleep_ms(10);
    gpio_put(PIN_TOF_XSHUT, 1);
    sleep_ms(5);
    if (!vl53l4cd_init(i2c0) || !vl53l4cd_set_timing(i2c0, DEMO_BUDGET_MS) || !vl53l4cd_start(i2c0)) {
        printf("  distance sensor didn't start\n");
        done("demo", "FAIL");
        return;
    }
    grid_power(true);

    // The grid is redrawn every frame for a smooth pulse; the sensor is read
    // whenever it has a sample (every DEMO_BUDGET_MS). Each reading goes
    // through a median filter, a reading that isn't valid or is past
    // DEMO_FAR_MM counting as DEMO_FAR_MM, so with nothing within range the
    // demo settles at the far end (blue, slow beat) rather than holding the
    // last near value. `far` (0 at DEMO_NEAR_MM, 1 at DEMO_FAR_MM) is then
    // smoothed, so the colour glides and the beat speeds up and slows down
    // gradually. The beat's phase is integrated rather than taken from the
    // clock, so a change of rate never jumps it mid-beat. `fade_in` brings
    // the grid up gently at the start.
    float far = 1.0f, fade_in = 0, phase = 0;
    uint16_t window[DEMO_MEDIAN], raw = DEMO_FAR_MM, filtered = DEMO_FAR_MM;
    uint next = 0;
    for (uint i = 0; i < DEMO_MEDIAN; i++) window[i] = DEMO_FAR_MM;
    uint64_t last = time_us_64(), last_print = 0;
    while (getchar_timeout_us(0) == PICO_ERROR_TIMEOUT) {
        bool ready = false;
        vl53l4cd_data_ready(i2c0, &ready);
        if (ready) {
            vl53l4cd_result_t r;
            bool valid = vl53l4cd_get_result(i2c0, &r) && r.range_status == 0;
            vl53l4cd_clear_interrupt(i2c0);
            raw = valid && r.distance_mm < DEMO_FAR_MM ? r.distance_mm : DEMO_FAR_MM;
            filtered = median_push(window, &next, raw);
            uint d = filtered < DEMO_NEAR_MM ? DEMO_NEAR_MM : filtered;
            float target = (float)(d - DEMO_NEAR_MM) / (DEMO_FAR_MM - DEMO_NEAR_MM);
            far += (target - far) * 0.35f;
        }
        fade_in += (1.0f - fade_in) * 0.03f;
        float hue = DEMO_HUE_NEAR + (DEMO_HUE_FAR - DEMO_HUE_NEAR) * far;
        float bpm = DEMO_BPM_NEAR + (DEMO_BPM_FAR - DEMO_BPM_NEAR) * far;

        uint64_t now = time_us_64();
        phase += (float)(now - last) * bpm / 60e6f;
        phase -= floorf(phase);
        last = now;
        float level = DEMO_REST + (1.0f - DEMO_REST) * heartbeat(phase);
        float value = DEMO_VALUE * powf(level, 2.2f) * fade_in;  // gamma, so the fades look even
        grid_fill(hsv((uint)(hue + 0.5f), (uint8_t)(value + 0.5f)));

        if (now - last_print > 250000) {
            last_print = now;
            if (filtered < DEMO_FAR_MM)
                printf("  %4u mm (raw %4u) -> hue %3u, %3u bpm\n", filtered, raw, (uint)(hue + 0.5f),
                       (uint)(bpm + 0.5f));
            else
                printf("  nothing within %u mm (raw %4u) -> hue %3u, %3u bpm\n", DEMO_FAR_MM, raw,
                       (uint)(hue + 0.5f), (uint)(bpm + 0.5f));
        }
        sleep_ms(DEMO_FRAME_MS);
    }
    vl53l4cd_stop(i2c0);
    grid_power(false);
    done("demo", "stopped");
}

// --------------------------------------------------------------------- main

static void init_pins(void) {
    for (uint i = 0; i < N_STATUS; i++) {
        gpio_init(STATUS_PINS[i]);
        gpio_set_dir(STATUS_PINS[i], GPIO_OUT);
    }
    // grid power off, data low, before anything else drives the grid
    gpio_init(PIN_LED_EN);
    gpio_set_dir(PIN_LED_EN, GPIO_OUT);
    gpio_put(PIN_LED_EN, 0);
    gpio_init(PIN_LED_DATA);
    gpio_set_dir(PIN_LED_DATA, GPIO_OUT);
    gpio_put(PIN_LED_DATA, 0);
    grid_init();

    i2c_init(i2c0, 400000);
    gpio_set_function(PIN_TOF_SDA, GPIO_FUNC_I2C);
    gpio_set_function(PIN_TOF_SCL, GPIO_FUNC_I2C);
    gpio_init(PIN_TOF_XSHUT);
    gpio_set_dir(PIN_TOF_XSHUT, GPIO_OUT);
    gpio_put(PIN_TOF_XSHUT, 1);
    gpio_init(PIN_TOF_INT);
    gpio_set_dir(PIN_TOF_INT, GPIO_IN);

    ir_init();
    gpio_init(PIN_IR_RX);
    gpio_set_dir(PIN_IR_RX, GPIO_IN);
    gpio_pull_up(PIN_IR_RX);
}

int main(void) {
    stdio_init_all();
    init_pins();

#if BOOT_INTO_DEMO
    // Straight into the demo, on USB or battery alone; any key (host.py sends
    // one first) stops it and drops to the test menu.
    test_demo();
#else
    for (uint i = 0; i < 100 && !stdio_usb_connected(); i++) sleep_ms(100);
#endif
    printf("\nsocial badge rev 2 bring-up tests\n%s> ", MENU);

    for (;;) {
        int c = getchar_timeout_us(100000);
        if (c == PICO_ERROR_TIMEOUT || c == '\r' || c == '\n') continue;
        printf("%c\n", c);
        switch (c) {
            case 's': test_status(); break;
            case 'g': test_grid(); break;
            case 't': test_tof(); break;
            case 'i': test_ir(); break;
            case 'r': test_ir_monitor(); break;
            case 'd': test_demo(); break;
            case 'c': test_raw(); break;
            case 'a':
                test_status();
                test_grid();
                test_tof();
                test_ir();
                done("all", "see above");
                break;
            case 'b':
                printf("rebooting to BOOTSEL\n");
                sleep_ms(100);
                reset_usb_boot(0, 0);
                break;
            default: printf("%s", MENU);
        }
        printf("> ");
    }
}
