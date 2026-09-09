"""
Power-path subcircuit — two SS14 Schottkys OR'ing VBUS and VBAT into SYS.

When USB is plugged in (VBUS = 5 V), VBUS-side diode forward-biases and battery diode
is reverse-biased: SYS = VBUS - V_F ≈ 4.6 V, battery does not source.
When USB is unplugged, only the battery diode conducts: SYS = VBAT - V_F ≈ 3.0-3.8 V.
"""

from jitx import Circuit, Net
from jitx.common import Power

from ..components.diodes.mdd_SS14 import SS14


class PowerPath(Circuit):
    """OR'es VBUS and VBAT into a common SYS rail via two Schottkys.

    No body of work needed downstream — connect SYS to the LDO input.
    """

    vbus = Power()   # USB 5 V input
    vbat = Power()   # battery input (3.0-4.2 V)
    sys = Power()    # OR'd output

    def __init__(self):
        self.GND = Net(name="GND")
        self.SYS = Net(name="SYS")

        self.d_usb = SS14()      # VBUS -> SYS
        self.d_bat = SS14()      # VBAT -> SYS

        self.GND += self.vbus.Vn + self.vbat.Vn + self.sys.Vn

        # Anodes on inputs, cathodes tied at SYS
        self.usb_in_net = [self.vbus.Vp + self.d_usb.A]
        self.bat_in_net = [self.vbat.Vp + self.d_bat.A]
        self.SYS += self.d_usb.K + self.d_bat.K + self.sys.Vp


Device = PowerPath
