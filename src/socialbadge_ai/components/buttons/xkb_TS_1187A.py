"""
SPST tactile switch SMD 5.1x5.1mm

Auto-generated from KiCad footprint: easyeda2kicad:SW-SMD_4P-L5.1-W5.1-P3.70-LS6.5-TL_H1.5
"""

import jitx
from jitx import PadMapping
from jitx.feature import Courtyard, Custom, Cutout, Paste, Silkscreen, Soldermask
from jitx.landpattern import Landpattern, Pad
from jitx.net import Port
from jitx.shapes.composites import rectangle
from jitx.shapes.primitive import Arc, ArcPolyline, Polyline, Text
from jitx.anchor import Anchor
from jitxlib.symbols.box import BoxSymbol, PinGroup, Row, Column


# ======================================================================
# Pad shape definitions
# ======================================================================

class Pad1(Pad):
    """SMD pad (1 x 0.75 mm)."""
    shape = rectangle(1, 0.75)
    soldermask = Soldermask(rectangle(1, 0.75))
    paste = Paste(rectangle(1, 0.75))


# ======================================================================
# Landpattern
# ======================================================================
# NOTE: KiCad Y-axis is inverted vs JITX (KiCad Y+ = down, JITX Y+ = up)
# All Y coordinates are negated during conversion.
# Pads and the landpattern class are declared at module scope (not inside
# Component.__init__) because jitx 4.4 forbids creating new JITX classes
# during instantiation.

_pad_A = Pad1().at(-3, 1.85)
_pad_B = Pad1().at(3, 1.85)
_pad_C = Pad1().at(-3, -1.85)
_pad_D = Pad1().at(3, -1.85)


@jitx.container.inline
class _Landpattern(Landpattern):
    name = "easyeda2kicad:SW-SMD_4P-L5.1-W5.1-P3.70-LS6.5-TL_H1.5"
    p = {
        1: _pad_A,
        2: _pad_B,
        3: _pad_C,
        4: _pad_D,
    }
    reference_designator = Silkscreen(Text(">REF", 1, Anchor.W).at((0, 5.85)))
    value_label = Custom(Text(">VALUE", 1, Anchor.W).at((0, -5.85)), name="Fab")
    silkscreen = [
        Silkscreen(Polyline(0.25, [(-1, 1.8), (0.9, 1.8)])),
        Silkscreen(Polyline(0.25, [(0.9, 1.8), (1.8, 0.9)])),
        Silkscreen(Polyline(0.25, [(1.8, 0.9), (1.8, -0.9)])),
        Silkscreen(Polyline(0.25, [(1.8, -0.9), (0.8, -1.9)])),
        Silkscreen(Polyline(0.25, [(0.8, -1.9), (-0.9, -1.9)])),
        Silkscreen(Polyline(0.25, [(-0.9, -1.9), (-1.8, -1)])),
        Silkscreen(Polyline(0.25, [(-1.8, -1), (-1.8, 1)])),
        Silkscreen(Polyline(0.25, [(-1.8, 1), (-1, 1.8)])),
        Silkscreen(Polyline(0.25, [(1.28, 2.55), (2.17, 1.66)])),
        Silkscreen(Polyline(0.25, [(2.55, 1.17), (2.55, -1.17)])),
        Silkscreen(Polyline(0.25, [(2.17, -1.66), (1.28, -2.55)])),
        Silkscreen(Polyline(0.25, [(-2.55, 1.17), (-2.55, -1.17)])),
        Silkscreen(Polyline(0.25, [(-2.17, -1.66), (-1.28, -2.55)])),
        Silkscreen(Polyline(0.25, [(-1.28, 2.55), (-2.17, 1.66)])),
        Silkscreen(Polyline(0.25, [(-1.28, -2.55), (1.28, -2.55)])),
        Silkscreen(Polyline(0.25, [(-1.28, 2.55), (1.28, 2.55)])),
        Silkscreen(ArcPolyline(0.06, [Arc((-3.25, 2.55), 0.03, 0, -360)])),
        Silkscreen(ArcPolyline(0.25, [Arc((0, -0), 1.28, 0, -360)])),
    ]
    courtyard = Courtyard(rectangle(5.1, 5.1))


# ======================================================================
# Component
# ======================================================================

class TS_1187A_B_A_B(jitx.Component):
    "SPST tactile switch SMD 5.1x5.1mm"

    mpn = "TS-1187A-B-A-B"
    manufacturer = "XKB Connection"
    reference_designator_prefix = "SW"
    datasheet = "https://datasheet.lcsc.com/datasheet/pdf/56c8799ae5193945a16a1ffbe378246a.pdf"

    # --- Ports ---
    A = Port()  # Pad "A"
    B = Port()  # Pad "B"
    C = Port()  # Pad "C"
    D = Port()  # Pad "D"

    landpattern = _Landpattern

    # --- Symbol ---
    symbol = BoxSymbol(
        rows=Row(
            left=PinGroup(A, B, C, D),
        ),
    )

    def __init__(self):
        # --- Pad Mapping ---
        lp = self.landpattern
        self.pad_mapping = PadMapping({
            self.A: lp.p[1],
            self.B: lp.p[2],
            self.C: lp.p[3],
            self.D: lp.p[4],
        })


Device: type[TS_1187A_B_A_B] = TS_1187A_B_A_B
