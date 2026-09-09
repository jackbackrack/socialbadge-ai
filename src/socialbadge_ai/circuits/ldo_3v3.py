"""
3.3 V LDO subcircuit — Diodes AP2112K-3.3 with input/output decoupling.

Always-enabled: EN tied to VIN. Per AP2112 datasheet figure 2: 1 uF X5R/X7R on each
of input and output is stable across the operating range.
"""

from jitx import Circuit, Net
from jitx.common import Power
from jitxlib.parts import Capacitor

from ..components.power_linear_regulators.diodes_AP2112K_33TRG1 import AP2112K_33TRG1


class LDO_3V3(Circuit):
    """Steps SYS rail (3.0-5.5 V) down to a regulated 3.3 V output, 600 mA capable."""

    vin = Power()    # input — connect to SYS rail
    vout = Power()   # output — 3.3 V

    def __init__(self):
        self.GND = Net(name="GND")
        self.VIN = Net(name="VIN_LDO")
        self.V3V3 = Net(name="3V3")

        self.u1 = AP2112K_33TRG1()

        self.GND += self.vin.Vn + self.vout.Vn + self.u1.GND
        self.VIN += self.vin.Vp + self.u1.VIN + self.u1.EN  # EN tied to VIN
        self.V3V3 += self.vout.Vp + self.u1.VOUT

        self.c_in = Capacitor(capacitance=1.0e-6, rated_voltage=10.0, temperature_coefficient_code="X5R")
        self.c_in.insert(self.u1.VIN, self.u1.GND, short_trace=True)

        self.c_out = Capacitor(capacitance=1.0e-6, rated_voltage=10.0, temperature_coefficient_code="X5R")
        self.c_out.insert(self.u1.VOUT, self.u1.GND, short_trace=True)


Device = LDO_3V3
