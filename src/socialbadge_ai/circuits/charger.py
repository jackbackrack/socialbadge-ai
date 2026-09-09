"""
Battery-charger subcircuit — Microchip MCP73831T-2ACI/OT (4.2 V termination).

Per datasheet typical application (page 1):
- 4.7 uF X5R/X7R on VDD (input from VBUS)
- 4.7 uF X5R/X7R on VBAT (output to battery, required for loop stability even
  when battery is disconnected)
- 2 kΩ R_PROG to VSS  →  I_REG = 1000 V / 2 kΩ = 500 mA
- STAT pulled up to 3V3 through 1 kΩ in series with red LED; LED is on
  (STAT pin sinks) while charging, off when charge complete or no input.
"""

from jitx import Circuit, Net
from jitx.common import Power
from jitxlib.parts import Capacitor, Resistor

from ..components.power_linear_regulators.microchip_MCP73831T_2ACI_OT import MCP73831T_2ACI_OT
from ..components.diodes.kt_0603_red import KT_0603R


class Charger(Circuit):
    """Charge from VBUS into a single-cell Li-ion at 500 mA, with a status LED."""

    vbus = Power()       # input from USB (5 V nominal)
    vbat = Power()       # battery (positive = Vp, GND = Vn)
    v3v3 = Power()       # 3V3 supply for the indicator LED pull-up

    def __init__(self):
        self.GND = Net(name="GND")
        self.VBUS = Net(name="VBUS")
        self.VBAT = Net(name="VBAT")
        self.V3V3 = Net(name="3V3")
        self.STAT = Net(name="CHG_STAT")
        self.PROG = Net(name="CHG_PROG")

        self.u1 = MCP73831T_2ACI_OT()

        # Power connections
        self.GND += self.vbus.Vn + self.vbat.Vn + self.v3v3.Vn + self.u1.VSS
        self.VBUS += self.vbus.Vp + self.u1.VDD
        self.VBAT += self.vbat.Vp + self.u1.VBAT
        self.V3V3 += self.v3v3.Vp

        # Input/output bulk caps per datasheet
        self.c_vdd = Capacitor(capacitance=4.7e-6, rated_voltage=10.0, temperature_coefficient_code="X5R")
        self.c_vdd.insert(self.u1.VDD, self.u1.VSS, short_trace=True)

        self.c_vbat = Capacitor(capacitance=4.7e-6, rated_voltage=10.0, temperature_coefficient_code="X5R")
        self.c_vbat.insert(self.u1.VBAT, self.u1.VSS, short_trace=True)

        # PROG resistor sets charge current: I = 1000/R_prog = 500 mA at 2k
        self.r_prog = Resistor(resistance=2.0e3)
        self.r_prog.insert(self.u1.PROG, self.u1.VSS)

        # Charge status LED: 3V3 -> R_lim -> LED anode, LED cathode -> STAT
        # STAT pin is tri-state (sinks when charging) so LED lights when charging
        self.STAT += self.u1.STAT
        self.r_led = Resistor(resistance=1.0e3)
        self.led = KT_0603R()
        # Wire: V3V3 -> r_led -> LED anode; LED cathode -> STAT
        self.led_drive_nets = [
            self.r_led.p1 + self.v3v3.Vp,
            self.r_led.p2 + self.led.A,
            self.led.K + self.u1.STAT,
        ]


Device = Charger
