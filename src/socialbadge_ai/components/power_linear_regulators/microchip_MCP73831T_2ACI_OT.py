"""
Microchip MCP73831T-2ACI/OT — Single-cell Li-ion / LiPo linear charge controller

4.2 V termination voltage, programmable charge current 15–500 mA via PROG resistor,
tri-state STAT pin for status indication. SOT-23-5 package.

Pinout (from datasheet table 3-1, page 11):
  Pin 1: STAT  — charge status output (tri-state)
  Pin 2: VSS   — ground
  Pin 3: VBAT  — battery output (drain of internal P-MOSFET)
  Pin 4: VDD   — input supply (3.75 V – 6 V)
  Pin 5: PROG  — current set resistor to VSS

Charge current I_REG = 1000 / R_PROG  (R in Ω, I in A).
R_PROG = 2 kΩ → 500 mA.
"""

import jitx
from jitx.net import Port
from jitx.toleranced import Toleranced
from jitxlib.landpatterns.generators.sot import SOT23_5, SOTLeadProfile, SOTLead
from jitxlib.landpatterns.ipc import DensityLevel
from jitxlib.landpatterns.package import RectanglePackage
from jitxlib.symbols.box import BoxSymbol, PinGroup, Row, Column


class MCP73831T_2ACI_OT(jitx.Component):
    mpn = "MCP73831T-2ACI/OT"
    manufacturer = "Microchip Technology"
    reference_designator_prefix = "U"
    datasheet = "https://datasheet.lcsc.com/datasheet/pdf/c7ec00710e742b7fb9393e620ae1332b.pdf"

    STAT = Port()   # Pin 1 — tri-state status output
    VSS = Port()    # Pin 2 — ground
    VBAT = Port()   # Pin 3 — battery output
    VDD = Port()    # Pin 4 — input supply
    PROG = Port()   # Pin 5 — current programming resistor

    # Standard JEDEC SOT-23-5 dimensions
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
            left=PinGroup(VDD, PROG),
            right=PinGroup(VBAT, STAT),
        ),
        columns=Column(
            down=PinGroup(VSS),
        ),
    )


Device: type[MCP73831T_2ACI_OT] = MCP73831T_2ACI_OT
