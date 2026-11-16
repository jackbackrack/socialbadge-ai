// Bring-up test for the social badge's three status LEDs.
//
// LEDs are active-high on GPIO0..2 (GPIO -> 330 ohm -> LED -> GND). This
// runs them as a back-and-forth chaser (A B C B A B C B ...), reporting each
// step over USB serial so a dead LED can be told apart from a dead program.

#include <stdio.h>

#include "pico/stdlib.h"

static const uint LED_PINS[] = {0, 1, 2};
#define N_LEDS (sizeof LED_PINS / sizeof LED_PINS[0])

// One full sweep A B C B: indices into LED_PINS
static const uint CHASE[] = {0, 1, 2, 1};
#define N_STEPS (sizeof CHASE / sizeof CHASE[0])

#define STEP_MS 200

int main(void) {
    stdio_init_all();
    for (uint i = 0; i < N_LEDS; i++) {
        gpio_init(LED_PINS[i]);
        gpio_set_dir(LED_PINS[i], GPIO_OUT);
    }

    for (uint pass = 0;; pass++) {
        for (uint s = 0; s < N_STEPS; s++) {
            uint lit = CHASE[s];
            for (uint i = 0; i < N_LEDS; i++) gpio_put(LED_PINS[i], i == lit);
            printf("pass %u: LED on GPIO%u\n", pass, LED_PINS[lit]);
            sleep_ms(STEP_MS);
        }
    }
}
