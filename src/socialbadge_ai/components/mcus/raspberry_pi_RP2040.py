"""
Raspberry Pi RP2040 Dual ARM Cortex-M0+ Microcontroller

QFN-56 package, 7x7mm, 0.4mm pitch with reduced 3.2x3.2mm ePad.

Pin map and dimensions sourced from RP2040 datasheet
(https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf):
- Pin list: section 5.5.2.2 (Tables 615-621), pages 612-614
- Recommended PCB footprint: section 5.1.2 (Figure 167), page 608
"""

import jitx
from jitx import PadMapping
from jitx.net import Port
from jitx.toleranced import Toleranced
from jitx.shapes.composites import rectangle
from jitxlib.landpatterns.generators.qfn import QFN, QFNLead
from jitxlib.landpatterns.leads import LeadProfile
from jitxlib.landpatterns.package import RectanglePackage
from jitxlib.landpatterns.ipc import DensityLevel
from jitxlib.symbols.box import BoxSymbol, PinGroup, Row, Column


class RP2040(jitx.Component):
    """RP2040 microcontroller — dual Cortex-M0+ at 133 MHz, 264 KB SRAM,
    30 GPIO (4 ADC-capable), QSPI external flash interface, USB 1.1."""

    mpn = "RP2040"
    manufacturer = "Raspberry Pi"
    reference_designator_prefix = "U"
    datasheet = "https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf"

    # Power supplies
    IOVDD = [Port() for _ in range(6)]    # pins 1, 10, 22, 33, 42, 49
    DVDD = [Port() for _ in range(2)]     # pins 23, 50
    USB_VDD = Port()                       # pin 48
    ADC_AVDD = Port()                      # pin 43
    VREG_VIN = Port()                      # pin 44
    VREG_VOUT = Port()                     # pin 45
    GND = Port()                           # central ePad (pin 57)

    # 30 GPIOs; GPIO26-29 also serve as ADC0-3 (alt function on same pin)
    GPIO = [Port() for _ in range(30)]

    # Crystal oscillator
    XIN = Port()                           # pin 20
    XOUT = Port()                          # pin 21

    # Serial wire debug
    SWCLK = Port()                         # pin 24
    SWD = Port()                           # pin 25

    # Control / test
    RUN = Port()                           # pin 26
    TESTEN = Port()                        # pin 19, tie to GND

    # USB
    USB_DM = Port()                        # pin 46
    USB_DP = Port()                        # pin 47

    # QSPI flash interface
    QSPI_SD3 = Port()                      # pin 51
    QSPI_SCLK = Port()                     # pin 52
    QSPI_SD0 = Port()                      # pin 53
    QSPI_SD2 = Port()                      # pin 54
    QSPI_SD1 = Port()                      # pin 55
    QSPI_CSn = Port()                      # pin 56

    # QFN-56, 7x7mm body, 0.4mm pitch, reduced 3.2x3.2mm ePad
    landpattern = (
        QFN(num_leads=56)
        .lead_profile(
            LeadProfile(
                span=Toleranced.exact(7.0),
                pitch=0.4,
                type=QFNLead(
                    length=Toleranced.min_max(0.3, 0.5),
                    width=Toleranced.min_typ_max(0.13, 0.18, 0.23),
                ),
            ),
        )
        .package_body(
            RectanglePackage(
                width=Toleranced.exact(7.0),
                length=Toleranced.exact(7.0),
                height=Toleranced.min_max(0.8, 0.9),
            )
        )
        .thermal_pad(rectangle(3.2, 3.2))
        .density_level(DensityLevel.C)
    )

    symbol = BoxSymbol(
        rows=Row(
            left=PinGroup(
                QSPI_CSn, QSPI_SCLK,
                QSPI_SD0, QSPI_SD1, QSPI_SD2, QSPI_SD3,
                XIN, XOUT,
                SWCLK, SWD,
                RUN, TESTEN,
                USB_DM, USB_DP,
            ),
            right=PinGroup(*GPIO),
        ),
        columns=Column(
            up=PinGroup(*IOVDD, *DVDD, USB_VDD, ADC_AVDD, VREG_VIN, VREG_VOUT),
            down=PinGroup(GND),
        ),
    )

    def __init__(self):
        lp = self.landpattern
        self.mappings = [PadMapping({
            self.IOVDD[0]: [lp.p[1]],
            self.GPIO[0]: [lp.p[2]],
            self.GPIO[1]: [lp.p[3]],
            self.GPIO[2]: [lp.p[4]],
            self.GPIO[3]: [lp.p[5]],
            self.GPIO[4]: [lp.p[6]],
            self.GPIO[5]: [lp.p[7]],
            self.GPIO[6]: [lp.p[8]],
            self.GPIO[7]: [lp.p[9]],
            self.IOVDD[1]: [lp.p[10]],
            self.GPIO[8]: [lp.p[11]],
            self.GPIO[9]: [lp.p[12]],
            self.GPIO[10]: [lp.p[13]],
            self.GPIO[11]: [lp.p[14]],
            self.GPIO[12]: [lp.p[15]],
            self.GPIO[13]: [lp.p[16]],
            self.GPIO[14]: [lp.p[17]],
            self.GPIO[15]: [lp.p[18]],
            self.TESTEN: [lp.p[19]],
            self.XIN: [lp.p[20]],
            self.XOUT: [lp.p[21]],
            self.IOVDD[2]: [lp.p[22]],
            self.DVDD[0]: [lp.p[23]],
            self.SWCLK: [lp.p[24]],
            self.SWD: [lp.p[25]],
            self.RUN: [lp.p[26]],
            self.GPIO[16]: [lp.p[27]],
            self.GPIO[17]: [lp.p[28]],
            self.GPIO[18]: [lp.p[29]],
            self.GPIO[19]: [lp.p[30]],
            self.GPIO[20]: [lp.p[31]],
            self.GPIO[21]: [lp.p[32]],
            self.IOVDD[3]: [lp.p[33]],
            self.GPIO[22]: [lp.p[34]],
            self.GPIO[23]: [lp.p[35]],
            self.GPIO[24]: [lp.p[36]],
            self.GPIO[25]: [lp.p[37]],
            self.GPIO[26]: [lp.p[38]],
            self.GPIO[27]: [lp.p[39]],
            self.GPIO[28]: [lp.p[40]],
            self.GPIO[29]: [lp.p[41]],
            self.IOVDD[4]: [lp.p[42]],
            self.ADC_AVDD: [lp.p[43]],
            self.VREG_VIN: [lp.p[44]],
            self.VREG_VOUT: [lp.p[45]],
            self.USB_DM: [lp.p[46]],
            self.USB_DP: [lp.p[47]],
            self.USB_VDD: [lp.p[48]],
            self.IOVDD[5]: [lp.p[49]],
            self.DVDD[1]: [lp.p[50]],
            self.QSPI_SD3: [lp.p[51]],
            self.QSPI_SCLK: [lp.p[52]],
            self.QSPI_SD0: [lp.p[53]],
            self.QSPI_SD2: [lp.p[54]],
            self.QSPI_SD1: [lp.p[55]],
            self.QSPI_CSn: [lp.p[56]],
            self.GND: [lp.thermal_pads[0]],
        })]


Device: type[RP2040] = RP2040
