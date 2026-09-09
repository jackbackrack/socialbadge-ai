"""
Red 645nm LED 0603 2V 20mA

Auto-generated from KiCad footprint: easyeda2kicad:LED-SMD_L1.6-W0.8-R-RD
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
    """SMD pad (0.8 x 0.8 mm)."""
    shape = rectangle(0.8, 0.8)
    soldermask = Soldermask(rectangle(0.8, 0.8))
    paste = Paste(rectangle(0.8, 0.8))


# ======================================================================
# Landpattern
# ======================================================================
# NOTE: KiCad Y-axis is inverted vs JITX (KiCad Y+ = down, JITX Y+ = up)
# All Y coordinates are negated during conversion.
# Pads and the landpattern class are declared at module scope (not inside
# Component.__init__) because jitx 4.4 forbids creating new JITX classes
# during instantiation.

_pad_K = Pad1().at(-0.75, -0)
_pad_A = Pad1().at(0.75, -0)


@jitx.container.inline
class _Landpattern(Landpattern):
    name = "easyeda2kicad:LED-SMD_L1.6-W0.8-R-RD"
    p = {
        1: _pad_K,
        2: _pad_A,
    }
    reference_designator = Silkscreen(Text(">REF", 1, Anchor.W).at((0, 4)))
    value_label = Custom(Text(">VALUE", 1, Anchor.W).at((0, -4)), name="Fab")
    silkscreen = [
        Silkscreen(Polyline(0.25, [(0.2, 0.7), (1.47, 0.7)])),
        Silkscreen(Polyline(0.25, [(1.47, 0.7), (1.47, -0.7)])),
        Silkscreen(Polyline(0.25, [(1.47, -0.7), (0.2, -0.7)])),
        Silkscreen(Polyline(0.25, [(0.09, 0), (-0.12, 0)])),
        Silkscreen(Polyline(0.25, [(-0.3, 0.7), (-1.4, 0.7)])),
        Silkscreen(Polyline(0.25, [(-1.4, 0.7), (-1.7, 0.4)])),
        Silkscreen(Polyline(0.25, [(-1.7, 0.4), (-1.7, -0.4)])),
        Silkscreen(Polyline(0.25, [(-1.7, -0.4), (-1.4, -0.7)])),
        Silkscreen(Polyline(0.25, [(-1.4, -0.7), (-0.3, -0.7)])),
        Silkscreen(Polyline(0.25, [(0.09, 0.4), (0.09, -0.38)])),
        Silkscreen(ArcPolyline(0.1, [Arc((0.8, 0.4), 0.05, 0, -360)])),
    ]
    courtyard = Courtyard(rectangle(1.6, 0.8))


# ======================================================================
# Component
# ======================================================================

class KT_0603R(jitx.Component):
    "Red 645nm LED 0603 2V 20mA"

    mpn = "KT-0603R"
    manufacturer = "Hubei KENTO"
    reference_designator_prefix = "D"
    datasheet = "https://datasheet.lcsc.com/datasheet/pdf/011ec3e8cb1e825f6961d29bc4db4c7a.pdf"

    # --- Ports ---
    K = Port()  # Pad "K"
    A = Port()  # Pad "A"

    landpattern = _Landpattern

    # --- Symbol ---
    symbol = BoxSymbol(
        rows=Row(
            left=PinGroup(K, A),
        ),
    )

    def __init__(self):
        # --- Pad Mapping ---
        lp = self.landpattern
        self.pad_mapping = PadMapping({
            self.K: lp.p[1],
            self.A: lp.p[2],
        })


Device: type[KT_0603R] = KT_0603R
