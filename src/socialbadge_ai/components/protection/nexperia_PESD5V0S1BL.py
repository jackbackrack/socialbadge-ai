"""Nexperia PESD5V0S1BL -- 5 V bidirectional ESD protection diode, DFN1006-2 (SOD882).

Sources
- Data sheet "PESD5V0S1BA; PESD5V0S1BB; PESD5V0S1BL Low capacitance
  bidirectional ESD protection diodes", Rev. 04, 20 August 2009 (Nexperia
  reissue), saved as ``datasheets/PESD5V0S1BL.pdf``
  (https://assets.nexperia.com/documents/data-sheet/PESD5V0S1BA_BB_BL.pdf).
  - Table 3 "Pinning", p.2: SOD882 pin 1 = cathode 1, pin 2 = cathode 2
    (bidirectional, two back-to-back diodes -- no polarity).
  - Table 6 / Table 9, p.3 and p.5: VRWM 5 V, IRM 5 / 100 nA typ/max at 5 V,
    V(BR) 5.5 / 9.5 V min/max at 1 mA, V(CL)R 10 V at 1 A and 14 V at 12 A
    (8/20 us), PPP 130 W, IPP 12 A, IEC 61000-4-2 30 kV contact; Cd 35 / 45 pF
    typ/max at 0 V (Table 2, p.1).
  - Figure captioned "Package outline SOD882" (Fig. 11, p.11).
- Nexperia package information "SOD882 plastic, leadless ultra small package;
  2 terminals; 0.65 mm pitch", 20 May 2022, saved as
  ``datasheets/SOD882_package.pdf``
  (https://assets.nexperia.com/documents/package-information/SOD882.pdf):
  - Fig. 1 "Package outline DFN1006-2 (SOD882)", p.2: E 0.95..1.02 (length),
    D 0.55..0.62 (width), A 0.46..0.50, e1 0.65, L 0.22..0.30, b 0.47..0.55.
  - Fig. 2 "Reflow soldering footprint for DFN1006-2 (SOD882)", p.3: solder
    lands 0.4 x 0.7 mm on 0.7 mm centres, solder resist 0.5 x 0.8 mm, solder
    paste 0.3 x 0.6 mm, R0.05 corners, occupied area 1.3 x 0.9 mm.

Footprint: built from Nexperia Fig. 2 (the manufacturer's reflow footprint).
The IPC "small outline no-lead" generator was evaluated and rejected: it puts
a 0.3 mm toe fillet outside terminals that sit 0.03-0.04 mm inside the body
edge, giving 0.97 mm pad centres instead of Nexperia's 0.70 mm.

Channel evidence: LCSC C84374 (PESD5V0S1BL,315; ``datasheets/lcsc/C84374.txt``,
132k stock), pinout ``datasheets/lcsc/C84374_pinout.txt`` (pins 1, 2).
EasyEDA footprint (``datasheets/lcsc/C84374.kicad_mod``, cross-check only):
0.30 x 0.60 mm pads on 0.64 mm centres -- smaller than Nexperia's lands.

No-field facts: no polarity mark (bidirectional; the marking bar of note 2
applies to unidirectional SOD882 parts only). Per-line capacitance 35-45 pF.
"""

from jitx import PadMapping
from jitx.circuit import Circuit
from jitx.component import Component
from jitx.container import inline
from jitx.landpattern import Landpattern
from jitx.net import Port
from jitx.sample import SampleDesign
from jitx.shapes.composites import rectangle
from jitxlib.jlcpcb import LCSCPart
from jitxlib.landpatterns.pads import SMDPad
from jitxlib.symbols.box import BoxSymbol, PinGroup, Row

from .landpattern_helpers import courtyard_around, rect_at, silkscreen_outline

# Nexperia SOD882 reflow footprint (package information Fig. 2), mm.
LAND_X = 0.4  # along the part axis
LAND_Y = 0.7  # across
LAND_PITCH = 0.7
PASTE_X = 0.3
PASTE_Y = 0.6
# SOD882 outline (Fig. 1): body length E max, width D max.
BODY_L = 1.02
BODY_W = 0.62
# Silkscreen line distance beyond the land edge: clears soldermask
# registration + silk-to-mask spacing + half line width (labelled layout
# choice, not a vendor value).
SILK_OFFSET = 0.35


class SOD882Landpattern(Landpattern):
    """Nexperia reflow footprint for DFN1006-2 (SOD882), pins 1 (-x) / 2 (+x)."""

    def __init__(self) -> None:
        h = LAND_PITCH / 2
        self.p = {
            n: SMDPad(rectangle(LAND_X, LAND_Y), paste=rectangle(PASTE_X, PASTE_Y)).at(
                x, 0.0
            )
            for n, x in ((1, -h), (2, h))
        }
        pads = list(self.p.values())
        # Two body-length lines above and below the part, placed outside the
        # lands' soldermask keep-away (the lands fill the body, so lines on the
        # body edge would be clipped away entirely).
        bx, sy = BODY_L / 2, LAND_Y / 2 + SILK_OFFSET
        self.outline = silkscreen_outline(
            [[(-bx, sy), (bx, sy)], [(-bx, -sy), (bx, -sy)]], pads
        )
        self.courtyard = courtyard_around([rect_at(BODY_L, BODY_W, 0.0, 0.0)], pads)


class PESD5V0S1BL(Component):
    """Nexperia PESD5V0S1BL 5 V bidirectional ESD diode, 35 pF, SOD882."""

    mpn = "PESD5V0S1BL,315"
    lcsc = LCSCPart("C84374", footprint="DFN1006-2")  # JLCPCB assembly
    manufacturer = "Nexperia"
    reference_designator_prefix = "D"
    datasheet = "https://assets.nexperia.com/documents/data-sheet/PESD5V0S1BA_BB_BL.pdf"

    p1 = Port()  # pin 1 -- cathode 1
    p2 = Port()  # pin 2 -- cathode 2

    landpattern = SOD882Landpattern()
    symbol = BoxSymbol(rows=Row(left=PinGroup(p1), right=PinGroup(p2)))

    def __init__(self) -> None:
        lp = self.landpattern
        self.mappings = [PadMapping({self.p1: lp.p[1], self.p2: lp.p[2]})]


Device: type[PESD5V0S1BL] = PESD5V0S1BL


class TestDesign(SampleDesign):
    @inline
    class circuit(Circuit):
        dut = PESD5V0S1BL()
