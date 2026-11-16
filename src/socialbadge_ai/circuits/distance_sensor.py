"""
Distance sensor — ST VL53L4CD time-of-flight proximity sensor on I²C.

The VL53L4CD (1–1300 mm) replaced the VL53L0X, out of stock at JLCPCB on
2026-11-05: same LGA12 footprint and pins, different driver.

Per the datasheet application schematic (DS13812 Figure 3):
- AVDD and AVDDVCSEL both to the supply (3V3; AVDD range 2.6–3.5 V), with
  100 nF and 4.7 µF placed close to AVDDVCSEL / AVSSVCSEL.
- All ground pins (AVSSVCSEL, GND, GND2, GND3, GND4) to GND.
- SDA/SCL pull-ups: 2.2 kΩ, within DS13812 Table 3's 1.2–3.6 kΩ for 400 kHz.
  These are the bus's only pull-ups.
- XSHUT (active-low shutdown) and GPIO1 (open-drain interrupt): 10 kΩ
  pull-ups. XSHUT must always be driven, so the pull-up holds it high when
  the RP2040 pin floats.
- DNC left unconnected.
"""

from jitx import Circuit, Net
from jitx.common import Power
from jitx.net import Port, ShortTrace
from jitx.units import F, V, ohm
from jitxlib.parts import Capacitor, Resistor

from ..components.sensors.st_VL53L4CD import VL53L4CDV0DH_1


class DistanceSensor(Circuit):
    """VL53L4CD with decoupling, I²C pull-ups, and XSHUT/GPIO1 pull-ups."""

    v3v3 = Power()
    sda = Port()
    scl = Port()
    xshut = Port()  # RP2040 GPIO, low = sensor in hardware standby
    gpio1 = Port()  # open-drain interrupt to an RP2040 GPIO

    def __init__(self):
        self.GND = Net(name="GND")
        self.V3V3 = Net(name="3V3")
        self.GND += self.v3v3.Vn
        self.V3V3 += self.v3v3.Vp

        # Front-side parts are fixed in this circuit's frame (the sensor at the
        # origin); the pull-ups are free, for layout to put on the back.
        self.u1 = VL53L4CDV0DH_1().at(0.0, 0.0)
        self.V3V3 += self.u1.AVDD + self.u1.AVDDVCSEL
        self.GND += self.u1.AVSSVCSEL + self.u1.GND + self.u1.GND2 + self.u1.GND3 + self.u1.GND4

        # next to AVDDVCSEL (pad 1.6, -0.8) and AVSSVCSEL (0.8, -0.8)
        self.c_hf = Capacitor(capacitance=100e-9 * F).at(1.2, -2.3, rotate=90.0)
        self.c_bulk = Capacitor(
            capacitance=4.7e-6 * F, rated_voltage_dc=10.0 * V, temperature_coefficient_code="X5R"
        ).at(3.3, 0.0)
        self.decouple_nets = [
            ShortTrace(self.c_hf.p1, self.u1.AVDDVCSEL),
            ShortTrace(self.c_hf.p2, self.u1.AVSSVCSEL),
            ShortTrace(self.c_bulk.p1, self.u1.AVDDVCSEL),
            self.c_bulk.p2 + self.GND,
        ]

        self.bus_nets = [
            self.sda + self.u1.SDA,
            self.scl + self.u1.SCL,
            self.xshut + self.u1.XSHUT,
            self.gpio1 + self.u1.GPIO1,
        ]
        self.r_sda = Resistor(resistance=2.2e3 * ohm)
        self.r_scl = Resistor(resistance=2.2e3 * ohm)
        self.r_xshut = Resistor(resistance=10e3 * ohm)
        self.r_gpio1 = Resistor(resistance=10e3 * ohm)
        self.pullup_nets = [
            self.r_sda.p1 + self.u1.SDA,
            self.r_scl.p1 + self.u1.SCL,
            self.r_xshut.p1 + self.u1.XSHUT,
            self.r_gpio1.p1 + self.u1.GPIO1,
        ]
        self.V3V3 += self.r_sda.p2 + self.r_scl.p2 + self.r_xshut.p2 + self.r_gpio1.p2


Device = DistanceSensor
