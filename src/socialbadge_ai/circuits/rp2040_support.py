"""
RP2040 support subcircuit — RP2040 MCU with QSPI flash, crystal, BOOTSEL/RESET buttons.

Follows the RP2040 datasheet "Minimal Design Example" (Chapter 2.9):
- 100 nF decoupling on every IOVDD pin (×6), ADC_AVDD, USB_VDD, VREG_VIN, both DVDD pins
- 1 µF bulk on VREG_VIN and VREG_VOUT (VREG_VOUT also feeds both DVDD pins)
- 12 MHz crystal between XIN/XOUT with two 27 pF load caps to GND
  (CL = 20 pF on YXC X322512MSB4SI → 2*(CL - C_stray) ≈ 33 pF; 27 pF is a closer E-series choice)
- RUN: 10 kΩ pull-up to 3V3 + 100 nF debounce + reset button to GND
- BOOTSEL: 1 kΩ in series between flash /CS and pushbutton to GND (Pico-style)
- TESTEN: hard-tied to GND
- W25Q128 QSPI flash: /CS, IO0..IO3, CLK wired to the RP2040 QSPI pins; 100 nF on VCC

External interface:
- v3v3 (Power)    — 3V3 supply
- usb_dp, usb_dn  — to USB-C interface (post-27 Ω series resistors)
- swclk, swd      — to debug header / test pads
- gpio[0..29]     — passthrough for board-level connections
"""

from jitx import Circuit, Net
from jitx.common import Power
from jitx.net import Port
from jitxlib.parts import Capacitor, Resistor

from ..components.mcus.raspberry_pi_RP2040 import RP2040
from ..components.memory.winbond_W25Q128JVSIQ import W25Q128JVSIQ
from ..components.crystals.yxc_X322512MSB4SI import X322512MSB4SI
from ..components.buttons.xkb_TS_1187A import TS_1187A_B_A_B


class RP2040Support(Circuit):
    """Complete RP2040 + flash + crystal + reset/boot buttons support circuit."""

    v3v3 = Power()
    usb_dp = Port()
    usb_dn = Port()
    swclk = Port()
    swd = Port()
    gpio = [Port() for _ in range(30)]

    def __init__(self):
        self.GND = Net(name="GND")
        self.V3V3 = Net(name="3V3")
        self.VREG_VOUT = Net(name="1V1")

        self.mcu = RP2040()
        self.flash = W25Q128JVSIQ()
        self.xtal = X322512MSB4SI()
        self.sw_run = TS_1187A_B_A_B()    # RESET button
        self.sw_boot = TS_1187A_B_A_B()   # BOOTSEL button

        # --- Power & ground ---
        self.GND += (
            self.v3v3.Vn
            + self.mcu.GND
            + self.flash.GND
            + self.xtal.GND[0]
            + self.xtal.GND[1]
        )
        self.V3V3 += (
            self.v3v3.Vp
            + self.mcu.IOVDD[0]
            + self.mcu.IOVDD[1]
            + self.mcu.IOVDD[2]
            + self.mcu.IOVDD[3]
            + self.mcu.IOVDD[4]
            + self.mcu.IOVDD[5]
            + self.mcu.ADC_AVDD
            + self.mcu.USB_VDD
            + self.mcu.VREG_VIN
            + self.flash.VCC
        )
        # VREG_VOUT (1.1 V) feeds both DVDD pins
        self.VREG_VOUT += self.mcu.VREG_VOUT + self.mcu.DVDD[0] + self.mcu.DVDD[1]

        # --- Decoupling caps ---
        # 100 nF on every IOVDD pin
        self.c_iovdd = [
            Capacitor(capacitance=100e-9, rated_voltage=10.0, temperature_coefficient_code="X7R")
            for _ in range(6)
        ]
        for i, c in enumerate(self.c_iovdd):
            c.insert(self.mcu.IOVDD[i], self.mcu.GND, short_trace=True)

        # 100 nF on ADC_AVDD, USB_VDD
        self.c_adc_avdd = Capacitor(capacitance=100e-9, rated_voltage=10.0, temperature_coefficient_code="X7R")
        self.c_adc_avdd.insert(self.mcu.ADC_AVDD, self.mcu.GND, short_trace=True)

        self.c_usb_vdd = Capacitor(capacitance=100e-9, rated_voltage=10.0, temperature_coefficient_code="X7R")
        self.c_usb_vdd.insert(self.mcu.USB_VDD, self.mcu.GND, short_trace=True)

        # 1 uF bulk + 100 nF HF on VREG_VIN
        self.c_vreg_vin_bulk = Capacitor(capacitance=1.0e-6, rated_voltage=10.0, temperature_coefficient_code="X5R")
        self.c_vreg_vin_bulk.insert(self.mcu.VREG_VIN, self.mcu.GND, short_trace=True)
        self.c_vreg_vin_hf = Capacitor(capacitance=100e-9, rated_voltage=10.0, temperature_coefficient_code="X7R")
        self.c_vreg_vin_hf.insert(self.mcu.VREG_VIN, self.mcu.GND, short_trace=True)

        # 1 uF on VREG_VOUT (also feeds DVDD) + 100 nF per DVDD pin
        self.c_vreg_vout = Capacitor(capacitance=1.0e-6, rated_voltage=10.0, temperature_coefficient_code="X5R")
        self.c_vreg_vout.insert(self.mcu.VREG_VOUT, self.mcu.GND, short_trace=True)
        self.c_dvdd0 = Capacitor(capacitance=100e-9, rated_voltage=10.0, temperature_coefficient_code="X7R")
        self.c_dvdd0.insert(self.mcu.DVDD[0], self.mcu.GND, short_trace=True)
        self.c_dvdd1 = Capacitor(capacitance=100e-9, rated_voltage=10.0, temperature_coefficient_code="X7R")
        self.c_dvdd1.insert(self.mcu.DVDD[1], self.mcu.GND, short_trace=True)

        # 100 nF on flash VCC
        self.c_flash_vcc = Capacitor(capacitance=100e-9, rated_voltage=10.0, temperature_coefficient_code="X7R")
        self.c_flash_vcc.insert(self.flash.VCC, self.flash.GND, short_trace=True)

        # --- Crystal ---
        # Crystal between XIN/XOUT; load caps tuned for CL ≈ 20 pF (using 27 pF E-series)
        self.XIN = Net(name="XIN")
        self.XOUT = Net(name="XOUT")
        self.XIN += self.mcu.XIN + self.xtal.OSC1
        self.XOUT += self.mcu.XOUT + self.xtal.OSC2

        # Crystal load caps — NOT short_trace (placement is per the crystal datasheet)
        self.c_xin = Capacitor(capacitance=27e-12, rated_voltage=10.0, temperature_coefficient_code="C0G")
        self.c_xin.insert(self.mcu.XIN, self.mcu.GND)
        self.c_xout = Capacitor(capacitance=27e-12, rated_voltage=10.0, temperature_coefficient_code="C0G")
        self.c_xout.insert(self.mcu.XOUT, self.mcu.GND)

        # --- TESTEN tied to GND ---
        self.GND += self.mcu.TESTEN

        # --- QSPI flash to RP2040 ---
        # RP2040 pin -> W25Q128 pin: SD0->IO0(5), SD1->IO1(2), SD2->IO2(3), SD3->IO3(7), SCLK->CLK(6), CSn->CS(1)
        self.QSPI_SCLK = Net(name="QSPI_SCLK")
        self.QSPI_SD0 = Net(name="QSPI_SD0")
        self.QSPI_SD1 = Net(name="QSPI_SD1")
        self.QSPI_SD2 = Net(name="QSPI_SD2")
        self.QSPI_SD3 = Net(name="QSPI_SD3")
        self.QSPI_CSn = Net(name="QSPI_CSn")
        self.QSPI_SCLK += self.mcu.QSPI_SCLK + self.flash.CLK
        self.QSPI_SD0 += self.mcu.QSPI_SD0 + self.flash.DI
        self.QSPI_SD1 += self.mcu.QSPI_SD1 + self.flash.DO
        self.QSPI_SD2 += self.mcu.QSPI_SD2 + self.flash.WP_n
        self.QSPI_SD3 += self.mcu.QSPI_SD3 + self.flash.HOLD_n
        self.QSPI_CSn += self.mcu.QSPI_CSn + self.flash.CS_n

        # --- RUN (reset) ---
        # 10 kΩ pull-up to 3V3 + 100 nF debounce + RUN button to GND
        self.RUN = Net(name="RUN")
        self.RUN += self.mcu.RUN
        self.r_run_pu = Resistor(resistance=10e3)
        self.r_run_pu.insert(self.mcu.RUN, self.V3V3)
        self.c_run_debounce = Capacitor(capacitance=100e-9, rated_voltage=10.0, temperature_coefficient_code="X7R")
        self.c_run_debounce.insert(self.mcu.RUN, self.mcu.GND)

        # Reset button: TS-1187A pads A+B are one contact, C+D the other.
        # Wire one side to RUN, other side to GND.
        self.reset_btn_nets = [
            self.sw_run.A + self.sw_run.B + self.mcu.RUN,
            self.sw_run.C + self.sw_run.D + self.GND,
        ]

        # --- BOOTSEL ---
        # Pico-style: 1 kΩ between flash /CS and the button; button to GND.
        # During reset the resistor pulls /CS low when button is held.
        self.BOOTSEL_NODE = Net(name="BOOTSEL_NODE")
        self.r_bootsel = Resistor(resistance=1.0e3)
        self.r_bootsel.insert(self.flash.CS_n, self.BOOTSEL_NODE)
        self.bootsel_btn_nets = [
            self.sw_boot.A + self.sw_boot.B + self.BOOTSEL_NODE,
            self.sw_boot.C + self.sw_boot.D + self.GND,
        ]

        # --- External passthroughs ---
        self.usb_dp_net = [self.mcu.USB_DP + self.usb_dp]
        self.usb_dn_net = [self.mcu.USB_DM + self.usb_dn]
        self.swclk_net = [self.mcu.SWCLK + self.swclk]
        self.swd_net = [self.mcu.SWD + self.swd]
        self.gpio_passthrough = [self.mcu.GPIO[i] + self.gpio[i] for i in range(30)]


Device = RP2040Support
