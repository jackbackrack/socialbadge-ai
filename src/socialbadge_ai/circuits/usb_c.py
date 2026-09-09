"""
USB-C interface — TYPE-C-31-M-12 receptacle wired as a USB 2.0 device.

Sink (UFP) advertisement: 5.1 kΩ pull-down on each CC pin to GND. This tells the
host we'll accept 5 V at the default 500 mA. The CC resistors must be on the
device-side and pulled to GND (not to VBUS).

D+/D- from both sides of the connector are merged (Type-C connectors have dual
rows for orientation flip; for USB 2.0 we tie A6/B6 (D+) and A7/B7 (D-) together
just past the connector). 27 Ω series resistors on each line satisfy the RP2040
datasheet requirement for USB termination.

Shield/EH mounting tabs are tied directly to GND.
"""

from jitx import Circuit, Net
from jitx.common import Power
from jitx.net import Port
from jitxlib.parts import Resistor

from ..components.connectors.hroparts_TYPE_C_31_M_12 import TYPE_C_31_M_12


class USB_C(Circuit):
    """USB-C sink + USB 2.0 data interface to the MCU.

    Exposes VBUS, GND, and a (DP, DN) pair for the host-side data lines.
    """

    vbus = Power()      # output: VBUS rail to the rest of the board
    DP = Port()         # connect to MCU USB_DP (after the 27 Ω resistor)
    DN = Port()         # connect to MCU USB_DM (after the 27 Ω resistor)

    def __init__(self):
        self.GND = Net(name="GND")
        self.VBUS = Net(name="VBUS")
        self.USB_DP = Net(name="USB_DP")
        self.USB_DN = Net(name="USB_DN")

        self.j1 = TYPE_C_31_M_12()

        # Power & shield
        self.VBUS += self.vbus.Vp + self.j1.VBUS[0] + self.j1.VBUS[1]
        self.GND += (
            self.vbus.Vn
            + self.j1.GND[0]
            + self.j1.GND[1]
            + self.j1.EH[0]
            + self.j1.EH[1]
            + self.j1.EH[2]
            + self.j1.EH[3]
        )

        # Merge D+/D- pairs from both rows of the connector
        self.USB_DP += self.j1.DP1 + self.j1.DP2
        self.USB_DN += self.j1.DN1 + self.j1.DN2

        # Sink CC pull-downs: 5.1 kΩ on each CC pin to GND (Type-C UFP, default current)
        self.r_cc1 = Resistor(resistance=5.1e3)
        self.r_cc1.insert(self.j1.CC1, self.GND)

        self.r_cc2 = Resistor(resistance=5.1e3)
        self.r_cc2.insert(self.j1.CC2, self.GND)

        # 27 Ω series resistors on USB data lines (RP2040 datasheet requirement)
        self.r_dp = Resistor(resistance=27.0)
        self.r_dp.insert(self.USB_DP, self.DP)

        self.r_dn = Resistor(resistance=27.0)
        self.r_dn.insert(self.USB_DN, self.DN)

        # SBU1/SBU2 unused for USB 2.0 — leave floating (no connect)
        # Two unnamed-by-LCSC alignment posts (j1.NC[0], j1.NC[1]) — leave floating


Device = USB_C
