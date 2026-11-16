cmake_minimum_required(VERSION 3.13)

# The badge is Pico-compatible: 12 MHz crystal, W25Q-series QSPI flash.
set(PICO_BOARD pico)
include(pico_sdk_import.cmake)

project(rev2_test C CXX ASM)
pico_sdk_init()

add_executable(rev2_test main.c vl53l4cd.c)
pico_generate_pio_header(rev2_test ${CMAKE_CURRENT_LIST_DIR}/ws2812.pio)
target_link_libraries(rev2_test pico_stdlib hardware_pio hardware_pwm hardware_i2c)

# GPIO0/1 drive LEDs, so stdio goes over USB rather than UART0
pico_enable_stdio_usb(rev2_test 1)
pico_enable_stdio_uart(rev2_test 0)
pico_add_extra_outputs(rev2_test)
