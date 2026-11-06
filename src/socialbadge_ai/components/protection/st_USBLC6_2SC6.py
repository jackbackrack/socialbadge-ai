"""ST USBLC6-2SC6 — 2-line USB ESD protection with VBUS clamp, SOT23-6L.

Copied from eink-placard (eink_placard/components/discretes.py, class
USBLC6_2SC6), which built the land pattern from ST DocID 11265 Rev 5.
"""

from jitx import PadMapping
from jitx.circuit import Circuit
from jitx.component import Component
from jitx.container import inline
from jitx.net import Port
from jitx.sample import SampleDesign
from jitx.toleranced import Toleranced
from jitxlib.jlcpcb import LCSCPart
from jitxlib.landpatterns.generators.sot import SOT23_6, SOTLead, SOTLeadProfile
from jitxlib.landpatterns.ipc import DensityLevel
from jitxlib.landpatterns.package import RectanglePackage
from jitxlib.symbols.box import BoxSymbol, Column, PinGroup, Row


class USBLC6_2SC6(Component):
    """ST USBLC6-2SC6, 2-line + VBUS low-capacitance ESD protection, SOT23-6L.

    Pinout: USBLC6-2 DocID 11265 Rev 5, Figure 1 "Functional diagram (top
    view)", p.1: 1 I/O1, 2 GND, 3 I/O2, 4 I/O2, 5 VBUS, 6 I/O1. Pins 1/6 and
    3/4 are the two ends of the same internal line (flow-through; see the
    D+in/D+out PSpice model, Figure 16, p.9) -- route the data line *through*
    the part: connector side on one pin, MCU side on the other. Both pins of
    each pair are modeled as separate ports (``IO1[0]`` = pin 1,
    ``IO1[1]`` = pin 6; ``IO2[0]`` = pin 3, ``IO2[1]`` = pin 4).
    Ratings (p.2): VRM 5.25 V (IRM 150 nA max), VBR 6 V min VBUS-GND,
    Ci/o-GND 3.5 pF max, VCL 17 V at 5 A 8/20 us. Figure 14 (p.8) / Figure 18
    (p.9): VBUS pin decoupled with 100 nF to GND. Package: Table 4
    "SOT23-6L dimensions", p.12; recommended footprint (cross-check)
    Figure 22, p.12: 0.60 x 1.20 mm pads, 2.30 mm inner / 3.50 mm outer.
    """

    mpn = "USBLC6-2SC6"
    lcsc = LCSCPart("C7519", footprint="SOT-23-6L")  # JLCPCB assembly
    manufacturer = "STMicroelectronics"
    reference_designator_prefix = "D"
    datasheet = "https://www.st.com/resource/en/datasheet/usblc6-2.pdf"

    IO1 = [Port(), Port()]  # pins 1, 6 -- I/O1 (same internal line)
    GND = Port()  # pin 2
    IO2 = [Port(), Port()]  # pins 3, 4 -- I/O2 (same internal line)
    VBUS = Port()  # pin 5

    # Table 4, p.12 (mm): H span 2.60..3.00, E body width 1.50..1.75,
    # D body length 2.80..3.05, A height 0.90..1.45, e 0.95, b 0.35..0.50,
    # L 0.10..0.60.
    landpattern = (
        SOT23_6()
        .lead_profile(
            SOTLeadProfile(
                span=Toleranced.min_max(2.60, 3.00),
                pitch=0.95,
                type=SOTLead(
                    length=Toleranced.min_max(0.10, 0.60),
                    width=Toleranced.min_max(0.35, 0.50),
                ),
            )
        )
        .package_body(
            RectanglePackage(
                width=Toleranced.min_max(1.50, 1.75),
                length=Toleranced.min_max(2.80, 3.05),
                height=Toleranced.min_max(0.90, 1.45),
            )
        )
        .density_level(DensityLevel.B)
    )

    symbol = BoxSymbol(
        rows=Row(
            left=PinGroup(IO1[0], IO2[0]),
            right=PinGroup(IO1[1], IO2[1]),
        ),
        columns=Column(
            up=PinGroup(VBUS),
            down=PinGroup(GND),
        ),
    )

    def __init__(self):
        lp = self.landpattern
        self.mappings = [
            PadMapping(
                {
                    self.IO1[0]: lp.p[1],
                    self.GND: lp.p[2],
                    self.IO2[0]: lp.p[3],
                    self.IO2[1]: lp.p[4],
                    self.VBUS: lp.p[5],
                    self.IO1[1]: lp.p[6],
                }
            ),
        ]


Device: type[USBLC6_2SC6] = USBLC6_2SC6


class TestDesign(SampleDesign):
    @inline
    class circuit(Circuit):
        dut = USBLC6_2SC6()
