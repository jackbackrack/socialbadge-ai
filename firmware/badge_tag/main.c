// Badge tag: badges find each other over IR and collect each other's colours.
//
// Each badge has an ID 1..16 (set over USB, kept in flash). ID k owns LED k
// of the grid -- read like text, top left = 1, bottom right = 16 -- and the
// hue (k - 1) * 22.5 degrees at full saturation.
//
//   - Its own LED is the brightest, pulsing once a second in its own colour.
//   - Every 300..700 ms (random, so two badges don't keep colliding) it sends
//     its ID as an NEC infrared frame: address BADGE_MAGIC, command = ID.
//   - While it hears another badge j, LED j blinks fast and bright in colour j
//     (so j's owner sees they're being called), and the other 14 LEDs count
//     down: all lit dimly in colour j, going out one by one.
//   - Heard for TAG_FREEZE_S without a gap longer than TAG_GAP_MS, LED j is
//     frozen: the grid flashes colour j three times, then LED j pulses slowly
//     and dimly while badge j is still here, and stays dim and steady once
//     it's gone. Frozen LEDs live only in RAM: power off (or reset) and only
//     the badge's own LED is left.
//
// "Close enough" is set by the IR power (the carrier's duty cycle; the LED
// current itself is fixed by its 47 Ohm resistor): turned down so that
// another badge is only heard within about 1 m. Tune it with `power`.
//
// USB serial commands, one per line (tag.py sends them):
//   id <1..16>     set this badge's ID
//   power <1..50>  IR carrier duty, percent (range)
//   clear          forget the frozen LEDs
//   status         ID, power, frozen set, badges heard now
//   selftest       send 10 frames and decode them on this badge's own receiver
//   boot           reboot to BOOTSEL for reflashing
// and it prints "EVT ..." lines as badges come, go and freeze.
//
// Pins (designs/badge_main.py): GPIO6 IR emitter (PWM slice 3 A), GPIO7 IR
// receiver (active low), GPIO10 LED grid power, GPIO11 grid data (PIO).

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "hardware/clocks.h"
#include "hardware/flash.h"
#include "hardware/gpio.h"
#include "hardware/pio.h"
#include "hardware/pwm.h"
#include "hardware/sync.h"
#include "pico/bootrom.h"
#include "pico/rand.h"
#include "pico/stdlib.h"
#include "ws2812.pio.h"

#define PIN_IR_TX 6
#define PIN_IR_RX 7
#define PIN_LED_EN 10
#define PIN_LED_DATA 11

#define N_IDS 16
#define GRID_N 4
#define VALUE 100                // of 255: LED brightness, kept under the 500 mA charger on USB

#define BADGE_MAGIC 0xB4         // NEC address byte: tells badge frames from TV remotes
#define TX_MIN_MS 300            // gap between frames, randomised in this range
#define TX_MAX_MS 700
#define TX_BLANK_US 3000         // receiver ignored this long after our own frame ends
#define POWER_DEFAULT 33         // IR carrier duty, percent; tune for ~1 m with `power`
#define POWER_MAX 50

#define TAG_HEARD_MS 1500        // "hearing" a badge: a frame within this long
#define TAG_GAP_MS 3000          // a longer silence restarts the freeze count
#define TAG_FREEZE_S 10          // heard this long without such a gap: frozen

// ------------------------------------------------------------------ storage
//
// One flash sector at the end of the 2 MB the Pico board config assumes (the
// badge's W25Q128 is 16 MB, so this is well clear of the program).

#define STORE_OFFSET (PICO_FLASH_SIZE_BYTES - FLASH_SECTOR_SIZE)
#define STORE_MAGIC 0x54414731u  // "TAG1"

typedef struct {
    uint32_t magic;
    uint8_t id;        // 0 = not set
    uint8_t power;     // percent
    uint16_t spare;    // was the frozen set, now kept in RAM only; written as 0
    uint32_t check;
} store_t;

static store_t store;

// Badges collected (bit k-1 = ID k). Deliberately RAM only, never saved:
// the collection starts empty at every power-up.
static uint16_t frozen;

static uint32_t store_check(const store_t *s) {
    return s->magic ^ ((uint32_t)s->id << 24 | (uint32_t)s->power << 16 | s->spare) ^ 0x5A5A5A5Au;
}

static void store_load(void) {
    const store_t *f = (const store_t *)(XIP_BASE + STORE_OFFSET);
    if (f->magic == STORE_MAGIC && f->check == store_check(f) && f->id <= N_IDS && f->power >= 1 &&
        f->power <= POWER_MAX) {
        store = *f;
    } else {
        store = (store_t){.magic = STORE_MAGIC, .id = 0, .power = POWER_DEFAULT, .spare = 0};
    }
}

static void store_save(void) {
    store.spare = 0;
    store.check = store_check(&store);
    static uint8_t page[FLASH_PAGE_SIZE];
    memset(page, 0xFF, sizeof page);
    memcpy(page, &store, sizeof store);
    uint32_t irq = save_and_disable_interrupts();  // nothing may run from flash meanwhile
    flash_range_erase(STORE_OFFSET, FLASH_SECTOR_SIZE);
    flash_range_program(STORE_OFFSET, page, FLASH_PAGE_SIZE);
    restore_interrupts(irq);
}

// ------------------------------------------------------------------ LED grid

static PIO grid_pio = pio0;
static uint grid_sm;

static void grid_init(void) {
    gpio_init(PIN_LED_EN);
    gpio_set_dir(PIN_LED_EN, GPIO_OUT);
    gpio_put(PIN_LED_EN, 0);
    uint offset = pio_add_program(grid_pio, &ws2812_program);
    grid_sm = pio_claim_unused_sm(grid_pio, true);
    pio_gpio_init(grid_pio, PIN_LED_DATA);  // idles low while VLED is off
    pio_sm_set_consecutive_pindirs(grid_pio, grid_sm, PIN_LED_DATA, 1, true);
    pio_sm_config c = ws2812_program_get_default_config(offset);
    sm_config_set_sideset_pins(&c, PIN_LED_DATA);
    sm_config_set_out_shift(&c, false, true, 24);
    sm_config_set_fifo_join(&c, PIO_FIFO_JOIN_TX);
    float cycles = ws2812_T1 + ws2812_T2 + ws2812_T3;
    sm_config_set_clkdiv(&c, clock_get_hz(clk_sys) / (800000.0f * cycles));
    pio_sm_init(grid_pio, grid_sm, offset, &c);
    pio_sm_set_enabled(grid_pio, grid_sm, true);
    gpio_put(PIN_LED_EN, 1);
    sleep_ms(20);
}

static uint32_t rgb(uint8_t r, uint8_t g, uint8_t b) { return (uint32_t)g << 16 | (uint32_t)r << 8 | b; }

static void grid_show(const uint32_t frame[N_IDS]) {
    for (uint i = 0; i < N_IDS; i++) pio_sm_put_blocking(grid_pio, grid_sm, frame[i] << 8u);
    while (!pio_sm_is_tx_fifo_empty(grid_pio, grid_sm)) tight_loop_contents();
    sleep_us(30 + 300);
}

// Hue 0..359 at full saturation, value 0..255.
static uint32_t hsv(uint hue, uint8_t value) {
    hue %= 360;
    uint sector = hue / 60, f = (hue % 60) * 255 / 60;
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

static uint id_hue(uint id) { return (id - 1) * 360 / N_IDS; }

// ID 1..16 -> chain index. IDs read like text from the front (top left = 1);
// the chain starts bottom right and snakes up (front_leds.grid_transform):
// grid row 0 is the bottom, even rows run right to left, odd rows left to right.
static uint id_led(uint id) {
    uint row_from_top = (id - 1) / GRID_N, col = (id - 1) % GRID_N;
    uint row = GRID_N - 1 - row_from_top;
    uint c = (row % 2) ? col : GRID_N - 1 - col;
    return row * GRID_N + c;
}

// ----------------------------------------------------------------- IR send
//
// NEC: 9 ms mark, 4.5 ms space, then 32 bits LSB first (address, ~address,
// command, ~command), each a 562 us mark and a 562 us (0) or 1687 us (1)
// space, then a closing 562 us mark. A hardware alarm steps through the
// durations, switching the 38 kHz carrier on for marks.

#define NEC_N (2 + 64 + 1)
static uint16_t tx_dur[NEC_N];
static volatile uint tx_step;
static volatile bool tx_busy;
static volatile uint64_t tx_end_us;
static uint ir_slice, ir_chan;
static uint32_t ir_wrap;

static void ir_carrier(bool on) {
    pwm_set_chan_level(ir_slice, ir_chan, on ? (uint16_t)((ir_wrap + 1) * store.power / 100) : 0);
}

static int64_t tx_alarm(alarm_id_t id, void *user) {
    (void)id, (void)user;
    uint next = ++tx_step;
    if (next >= NEC_N) {
        ir_carrier(false);
        tx_end_us = time_us_64();
        tx_busy = false;
        return 0;
    }
    ir_carrier(next % 2 == 0);  // even steps are marks
    return -(int64_t)tx_dur[next];  // relative to when this step was due, so timing doesn't drift
}

static void ir_send(uint8_t address, uint8_t command) {
    uint32_t bits = address | (uint32_t)(uint8_t)~address << 8 | (uint32_t)command << 16 |
                    (uint32_t)(uint8_t)~command << 24;
    uint n = 0;
    tx_dur[n++] = 9000;
    tx_dur[n++] = 4500;
    for (uint b = 0; b < 32; b++) {
        tx_dur[n++] = 562;
        tx_dur[n++] = (bits >> b) & 1 ? 1687 : 562;
    }
    tx_dur[n++] = 562;
    tx_busy = true;
    tx_step = 0;
    ir_carrier(true);
    add_alarm_in_us(tx_dur[0], tx_alarm, NULL, true);
}

static void ir_init(void) {
    gpio_set_function(PIN_IR_TX, GPIO_FUNC_PWM);
    ir_slice = pwm_gpio_to_slice_num(PIN_IR_TX);
    ir_chan = pwm_gpio_to_channel(PIN_IR_TX);
    ir_wrap = clock_get_hz(clk_sys) / 38000 - 1;
    pwm_set_wrap(ir_slice, ir_wrap);
    pwm_set_chan_level(ir_slice, ir_chan, 0);
    pwm_set_enabled(ir_slice, true);
}

// -------------------------------------------------------------- IR receive
//
// The receiver's edges are timestamped in an interrupt and decoded in the
// main loop. Its output is low during a mark. Edges are dropped while we're
// sending and just after (a badge hears its own frames), except in selftest.

#define EDGES 256
static volatile uint64_t edge_t[EDGES];
static volatile bool edge_level[EDGES];
static volatile uint edge_head;
static uint edge_tail;
static volatile bool rx_hear_self;

static void rx_irq(uint gpio, uint32_t events) {
    (void)events;
    if (gpio != PIN_IR_RX) return;
    uint64_t now = time_us_64();
    if (!rx_hear_self && (tx_busy || now - tx_end_us < TX_BLANK_US)) return;
    uint h = edge_head;
    edge_t[h % EDGES] = now;
    edge_level[h % EDGES] = gpio_get(PIN_IR_RX);
    edge_head = h + 1;
}

typedef enum { NEC_IDLE, NEC_LEAD_SPACE, NEC_BIT_MARK, NEC_BIT_SPACE, NEC_STOP } nec_state_t;
static nec_state_t nec_state;
static uint32_t nec_bits;
static uint nec_n;
static uint64_t last_edge_t;

static bool within(uint32_t d, uint32_t nominal) { return d > nominal * 3 / 4 && d < nominal * 5 / 4; }

// Feed one mark or space; returns true with *frame set when a frame completes.
static bool nec_feed(bool mark, uint32_t d, uint32_t *frame) {
    switch (nec_state) {
        case NEC_IDLE:
            if (mark && within(d, 9000)) nec_state = NEC_LEAD_SPACE;
            break;
        case NEC_LEAD_SPACE:
            nec_state = !mark && within(d, 4500) ? NEC_BIT_MARK : NEC_IDLE;
            nec_bits = 0, nec_n = 0;
            break;
        case NEC_BIT_MARK:
            nec_state = mark && d > 300 && d < 900 ? NEC_BIT_SPACE : NEC_IDLE;
            break;
        case NEC_BIT_SPACE:
            if (!mark && d > 300 && d < 900) {
                nec_n++;
            } else if (!mark && d > 1300 && d < 2100) {
                nec_bits |= 1u << nec_n++;
            } else {
                nec_state = NEC_IDLE;
                break;
            }
            nec_state = nec_n == 32 ? NEC_STOP : NEC_BIT_MARK;
            break;
        case NEC_STOP:
            nec_state = NEC_IDLE;
            if (mark && d > 300 && d < 900) {
                *frame = nec_bits;
                return true;
            }
            break;
    }
    if (nec_state == NEC_IDLE && mark && within(d, 9000)) nec_state = NEC_LEAD_SPACE;  // resync on a leader
    return false;
}

// Next badge ID heard (1..16), or 0 if none is waiting.
static uint rx_poll(void) {
    while (edge_tail != edge_head) {
        uint i = edge_tail++ % EDGES;
        uint64_t t = edge_t[i];
        bool level = edge_level[i];
        uint32_t d = (uint32_t)(t - last_edge_t);
        last_edge_t = t;
        // a rising edge ends a mark (output low), a falling edge ends a space
        uint32_t frame;
        if (nec_feed(level, d, &frame)) {
            uint8_t a = frame, na = frame >> 8, c = frame >> 16, nc = frame >> 24;
            if (a == BADGE_MAGIC && (uint8_t)~a == na && (uint8_t)~c == nc && c >= 1 && c <= N_IDS) return c;
        }
    }
    return 0;
}

// --------------------------------------------------------------- presence

static uint64_t heard_first[N_IDS + 1], heard_last[N_IDS + 1];  // us; 0 = never
static uint32_t heard_frames[N_IDS + 1];
static uint freeze_id;          // the badge most recently frozen, for the "got it" flash
static uint64_t freeze_at;

static bool hearing(uint id, uint64_t now) { return heard_last[id] && now - heard_last[id] < TAG_HEARD_MS * 1000ull; }

static void on_heard(uint id, uint64_t now) {
    if (id == store.id) return;  // our own frame, reflected back
    if (!heard_last[id] || now - heard_last[id] > TAG_GAP_MS * 1000ull) {
        heard_first[id] = now;
        heard_frames[id] = 0;
        printf("EVT heard %u\n", id);
    }
    heard_last[id] = now;
    heard_frames[id]++;
    uint16_t bit = 1u << (id - 1);
    if (!(frozen & bit) && now - heard_first[id] >= TAG_FREEZE_S * 1000000ull) {
        frozen |= bit;
        freeze_id = id, freeze_at = now;
        printf("EVT frozen %u\n", id);
    }
}

static void check_gone(uint64_t now) {
    for (uint id = 1; id <= N_IDS; id++)
        if (heard_last[id] && heard_first[id] && now - heard_last[id] > TAG_GAP_MS * 1000ull) {
            printf("EVT gone %u (heard %lu frames over %llu s)\n", id, (unsigned long)heard_frames[id],
                   (unsigned long long)((heard_last[id] - heard_first[id]) / 1000000));
            heard_first[id] = 0;
        }
}

// ------------------------------------------------------------------ display

#define FLASH_US 1500000   // "got it" flash at the moment of freezing: the grid blinks 3 times
#define COUNTDOWN_VALUE 40  // countdown LEDs, dimmer than the badge's own blinking LED
// Three kinds of LED have to read apart at a glance:
#define OWN_VALUE 200       // ours: brightest, pulsing at OWN_PULSE_S
#define OWN_PULSE_S 1.0f
#define CALL_VALUE 200      // a badge heard and not yet collected: bright, blinking at CALL_HZ,
#define CALL_HZ 6           //   so its owner sees their colour flickering "come here"
#define GOT_VALUE 35        // collected: dim and steady (slowly pulsing while that badge is here)

static void render(uint64_t now) {
    uint32_t frame[N_IDS] = {0};
    float t = (float)(now % 60000000ull) / 1e6f;
    if (store.id == 0) {  // no ID yet: a dim white dot chasing round, so it's clearly waiting
        frame[(now / 150000) % N_IDS] = rgb(12, 12, 12);
        grid_show(frame);
        return;
    }
    if (freeze_id && now - freeze_at < FLASH_US) {  // just frozen: the whole grid flashes their colour
        bool on = ((now - freeze_at) / 250000) % 2 == 0;
        for (uint i = 0; i < N_IDS; i++) frame[i] = on ? hsv(id_hue(freeze_id), VALUE) : 0;
        grid_show(frame);
        return;
    }

    // The badge whose freeze countdown is furthest along, if any is running.
    uint counting = 0;
    for (uint id = 1; id <= N_IDS; id++)
        if (id != store.id && hearing(id, now) && heard_first[id] && !(frozen & (1u << (id - 1))) &&
            (!counting || heard_first[id] < heard_first[counting]))
            counting = id;

    bool blink_on = (now / (500000 / CALL_HZ)) % 2 == 0;                          // fast: calling
    float slow = 0.3f + 0.7f * (0.5f - 0.5f * cosf(2.0f * (float)M_PI * t / 2.0f));  // 2 s: frozen and here
    for (uint id = 1; id <= N_IDS; id++) {
        bool got = frozen & (1u << (id - 1));
        uint32_t c = 0;
        if (hearing(id, now) && !got)
            c = blink_on ? hsv(id_hue(id), CALL_VALUE) : 0;
        else if (hearing(id, now) && got)
            c = hsv(id_hue(id), (uint8_t)(GOT_VALUE * slow));
        else if (got)
            c = hsv(id_hue(id), GOT_VALUE);
        frame[id_led(id)] = c;
    }

    // Countdown: every LED but ours and theirs starts lit in their colour and
    // they go out one by one, last ID first, over TAG_FREEZE_S.
    if (counting) {
        uint others[N_IDS], n = 0;
        for (uint id = 1; id <= N_IDS; id++)
            if (id != store.id && id != counting) others[n++] = id;
        float left = 1.0f - (float)(now - heard_first[counting]) / (TAG_FREEZE_S * 1e6f);
        uint lit = left <= 0 ? 0 : (uint)ceilf(left * n);
        for (uint k = 0; k < n; k++) frame[id_led(others[k])] = k < lit ? hsv(id_hue(counting), COUNTDOWN_VALUE) : 0;
    }

    // our own LED: the brightest, pulsing once a second, so it reads apart
    // from the dim steady collected ones and the fast-blinking callers
    float breath = 0.15f + 0.85f * (0.5f - 0.5f * cosf(2.0f * (float)M_PI * t / OWN_PULSE_S));
    frame[id_led(store.id)] = hsv(id_hue(store.id), (uint8_t)(OWN_VALUE * breath * breath));
    grid_show(frame);
}

// ----------------------------------------------------------------- commands

static void print_status(uint64_t now) {
    printf("STATUS id %u power %u%% frozen", store.id, store.power);
    for (uint id = 1; id <= N_IDS; id++)
        if (frozen & (1u << (id - 1))) printf(" %u", id);
    printf(" | hearing");
    for (uint id = 1; id <= N_IDS; id++)
        if (hearing(id, now))
            printf(" %u(%llus)", id, (unsigned long long)((now - heard_first[id]) / 1000000));
    printf("\n");
}

static void selftest(void) {
    if (store.id == 0) {
        printf("ERR set an id first\n");
        return;
    }
    uint got = 0;
    rx_hear_self = true;
    for (uint k = 0; k < 10; k++) {
        ir_send(BADGE_MAGIC, store.id);
        while (tx_busy) tight_loop_contents();
        sleep_ms(5);
        uint id;
        while ((id = rx_poll()) != 0) got += id == store.id;
        sleep_ms(50);
    }
    rx_hear_self = false;
    printf("OK selftest: decoded %u/10 of our own frames at power %u%%\n", got, store.power);
}

static void command(char *line, uint64_t now) {
    char *arg = strchr(line, ' ');
    if (arg) *arg++ = 0;
    int n = arg ? atoi(arg) : 0;
    if (!strcmp(line, "id")) {
        if (n < 1 || n > N_IDS) {
            printf("ERR id is 1..16\n");
            return;
        }
        store.id = (uint8_t)n;
        store_save();
        printf("OK id %u (hue %u)\n", store.id, id_hue(store.id));
    } else if (!strcmp(line, "power")) {
        if (n < 1 || n > POWER_MAX) {
            printf("ERR power is 1..%u\n", POWER_MAX);
            return;
        }
        store.power = (uint8_t)n;
        store_save();
        printf("OK power %u%%\n", store.power);
    } else if (!strcmp(line, "clear")) {
        frozen = 0;
        printf("OK cleared\n");
    } else if (!strcmp(line, "status")) {
        print_status(now);
    } else if (!strcmp(line, "selftest")) {
        selftest();
    } else if (!strcmp(line, "boot")) {
        printf("OK rebooting to BOOTSEL\n");
        sleep_ms(100);
        reset_usb_boot(0, 0);
    } else if (line[0]) {
        printf("ERR commands: id <1..16>, power <1..%u>, clear, status, selftest, boot\n", POWER_MAX);
    }
}

// --------------------------------------------------------------------- main

int main(void) {
    stdio_init_all();
    store_load();
    grid_init();
    ir_init();
    gpio_init(PIN_IR_RX);
    gpio_set_dir(PIN_IR_RX, GPIO_IN);
    gpio_pull_up(PIN_IR_RX);
    gpio_set_irq_enabled_with_callback(PIN_IR_RX, GPIO_IRQ_EDGE_FALL | GPIO_IRQ_EDGE_RISE, true, rx_irq);

    char line[32];
    uint len = 0;
    uint64_t next_tx = time_us_64() + 500000, next_frame = 0;
    for (;;) {
        uint64_t now = time_us_64();

        uint id;
        while ((id = rx_poll()) != 0) on_heard(id, now);
        check_gone(now);

        if (store.id && !tx_busy && now >= next_tx) {
            ir_send(BADGE_MAGIC, store.id);
            next_tx = now + 1000ull * (TX_MIN_MS + get_rand_32() % (TX_MAX_MS - TX_MIN_MS + 1));
        }

        if (now >= next_frame) {
            render(now);
            next_frame = now + 20000;
        }

        int c = getchar_timeout_us(0);
        if (c >= 0) {
            if (c == '\n' || c == '\r') {
                line[len] = 0;
                command(line, now);
                len = 0;
            } else if (len < sizeof line - 1) {
                line[len++] = (char)c;
            }
        }
    }
}
