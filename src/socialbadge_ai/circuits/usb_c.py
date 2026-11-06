"""
USB-C interface — TYPE-C-31-M-12 receptacle wired as a USB 2.0 device.

Sink (UFP) advertisement: 5.1 kΩ pull-down on each CC pin to GND. This tells the
host we'll accept 5 V at the default 500 mA. The CC resistors must be on the
device-side and pulled to GND (not to VBUS).

D+/D- from both sides of the connector are merged (Type-C connectors have dual
rows for orientation flip; for USB 2.0 we tie A6/B6 (D+) and A7/B7 (D-) together
just past the connector). The RP2040's 27 Ω series resistors are in
RP2040Support, at its USB pins.

Shield/EH mounting tabs are tied directly to GND.

ESD protection (as on eink-placard), all at the connector pins:
- USBLC6-2SC6 on D+/D-, routed *through* the part: connector on pins 3/1,
  27 Ω resistors on pins 4/6, so the clamp sits between the connector and
  everything else. Its VBUS pin is on VBUS, decoupled with 100 nF.
- PESD5V0S1BL (bidirectional, 5 V) from each CC pin to GND.
- No TVS on VBUS: the MCP73831's VDD abs max is 7 V and a 6 V SMF TVS clamps
  at ~10 V, so it would not protect it; the USBLC6's VBUS clamp and the bulk
  caps are what VBUS gets.
"""

from jitx import Circuit, Net
from jitx.common import Power
from jitx.net import DiffPair, ShortTrace
from jitx.units import F, ohm
from jitxlib.parts import Capacitor, Resistor

from ..components.connectors.hroparts_TYPE_C_31_M_12 import TYPE_C_31_M_12
from ..components.protection.nexperia_PESD5V0S1BL import PESD5V0S1BL
from ..components.protection.st_USBLC6_2SC6 import USBLC6_2SC6

class USB_C(Circuit):
    """USB-C sink + USB 2.0 data interface to the MCU.

    Exposes VBUS, GND, and the D+/D- `data` pair for the MCU.
    """

    vbus = Power()      # output: VBUS rail to the rest of the board
    data = DiffPair()   # D+ (p) / D- (n) to the MCU, from the ESD array

    def __init__(self):
        self.GND = Net(name="GND")
        self.VBUS = Net(name="VBUS")
        self.USB_DP = Net(name="USB_DP")
        self.USB_DN = Net(name="USB_DN")
        # D+/D- between the ESD array's MCU-side pins and the MCU's 27 Ω resistors
        self.USB_DP_ESD = Net(name="USB_DP_ESD")
        self.USB_DN_ESD = Net(name="USB_DN_ESD")

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

        # D+/D- from both rows of the connector, through the ESD array
        # (flow-through: connector side on IO2[0]/IO1[0], pins 3/1; MCU side on
        # IO2[1]/IO1[1], pins 4/6) to the MCU. On the back the array's D- / D+
        # pins are left / right, as are the RP2040's.
        self.esd = USBLC6_2SC6()
        self.USB_DP += self.j1.DP1 + self.j1.DP2 + self.esd.IO2[0]
        self.USB_DN += self.j1.DN1 + self.j1.DN2 + self.esd.IO1[0]
        self.USB_DP_ESD += self.esd.IO2[1] + self.data.p
        self.USB_DN_ESD += self.esd.IO1[1] + self.data.n
        self.GND += self.esd.GND
        self.st_esd_at_vbus = ShortTrace(self.j1.VBUS[0], self.esd.VBUS)
        self.c_esd_vbus = Capacitor(capacitance=100e-9 * F)
        self.c_esd_vbus_nets = [ShortTrace(self.esd.VBUS, self.c_esd_vbus.p1), self.c_esd_vbus.p2 + self.GND]

        # CC ESD diodes, each at its connector pin
        self.esd_cc1 = PESD5V0S1BL()
        self.esd_cc2 = PESD5V0S1BL()
        self.st_esd_cc1_at_cc1 = ShortTrace(self.j1.CC1, self.esd_cc1.p1)
        self.st_esd_cc2_at_cc2 = ShortTrace(self.j1.CC2, self.esd_cc2.p1)
        self.GND += self.esd_cc1.p2 + self.esd_cc2.p2

        # Sink CC pull-downs: 5.1 kΩ on each CC pin to GND (Type-C UFP, default current)
        self.r_cc1 = Resistor(resistance=5.1e3 * ohm)
        self.r_cc1_nets = [self.r_cc1.p1 + self.j1.CC1, self.r_cc1.p2 + self.GND]

        self.r_cc2 = Resistor(resistance=5.1e3 * ohm)
        self.r_cc2_nets = [self.r_cc2.p1 + self.j1.CC2, self.r_cc2.p2 + self.GND]

        # SBU1/SBU2 unused for USB 2.0 — leave floating (no connect)
        # Two unnamed-by-LCSC alignment posts (j1.NC[0], j1.NC[1]) — leave floating


Device = USB_C
