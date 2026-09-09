"""
Diodes Incorporated AP2112K-3.3TRG1 — 600 mA CMOS LDO with enable

Fixed 3.3 V output, 250 mV typical dropout at 600 mA, EN pin for shutdown.
SOT-25 (= SOT-23-5) package.

Pinout (from datasheet Pin Description table, page 2):
  Pin 1: VIN
  Pin 2: GND
  Pin 3: EN   (tie to VIN to keep always-on)
  Pin 4: NC
  Pin 5: VOUT
"""

import jitx
from jitx.net import Port
from jitx.toleranced import Toleranced
from jitxlib.landpatterns.generators.sot import SOT23_5, SOTLeadProfile
from jitxlib.landpatterns.ipc import DensityLevel
from jitxlib.landpatterns.package import RectanglePackage
from jitxlib.symbols.box import BoxSymbol, PinGroup, Row, Column


class AP2112K_33TRG1(jitx.Component):
    mpn = "AP2112K-3.3TRG1"
    manufacturer = "Diodes Incorporated"
    reference_designator_prefix = "U"
    datasheet = "https://datasheet.lcsc.com/datasheet/pdf/5b29baebdc4332b382a530ff21092301.pdf"

    VIN = Port()         # Pin 1
    GND = Port()         # Pin 2
    EN = Port()          # Pin 3
    NC = Port().no_connect()  # Pin 4
    VOUT = Port()        # Pin 5

    landpattern = (
        SOT23_5()
        .lead_profile(
            SOTLeadProfile(
                span=Toleranced.min_max(2.60, 3.00),
            )
        )
        .package_body(
            RectanglePackage(
                width=Toleranced.min_max(1.50, 1.70),
                length=Toleranced.min_max(2.80, 3.04),
                height=Toleranced.min_max(1.00, 1.30),
            )
        )
        .density_level(DensityLevel.B)
    )

    symbol = BoxSymbol(
        rows=Row(
            left=PinGroup(VIN, EN),
            right=PinGroup(VOUT, NC),
        ),
        columns=Column(
            down=PinGroup(GND),
        ),
    )


Device: type[AP2112K_33TRG1] = AP2112K_33TRG1
