cmake_minimum_required(VERSION 3.13)

# The badge is Pico-compatible: 12 MHz crystal, W25Q-series QSPI flash.
set(PICO_BOARD pico)
include(pico_sdk_import.cmake)

project(led_test C CXX ASM)
pico_sdk_init()

add_executable(led_test main.c)
target_link_libraries(led_test pico_stdlib)

# GPIO0/1 drive LEDs, so stdio goes over USB rather than UART0
pico_enable_stdio_usb(led_test 1)
pico_enable_stdio_uart(led_test 0)
pico_add_extra_outputs(led_test)
