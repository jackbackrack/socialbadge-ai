cmake_minimum_required(VERSION 3.13)

# The badge is Pico-compatible: 12 MHz crystal, W25Q-series QSPI flash.
set(PICO_BOARD pico)
include(pico_sdk_import.cmake)

project(badge_tag C CXX ASM)
pico_sdk_init()

add_executable(badge_tag main.c)
# the LED grid's WS2812 encoder, shared with the bring-up tests
pico_generate_pio_header(badge_tag ${CMAKE_CURRENT_LIST_DIR}/../rev2_test/ws2812.pio)
target_link_libraries(badge_tag pico_stdlib pico_rand hardware_pio hardware_pwm hardware_flash hardware_sync)

# GPIO0/1 drive LEDs, so stdio goes over USB rather than UART0
pico_enable_stdio_usb(badge_tag 1)
pico_enable_stdio_uart(badge_tag 0)
pico_add_extra_outputs(badge_tag)
