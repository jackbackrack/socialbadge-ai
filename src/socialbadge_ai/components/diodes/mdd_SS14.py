"""
Schottky diode 40V 1A SMA

Auto-generated from KiCad footprint: easyeda2kicad:SMA_L4.2-W2.6-LS5.0-RD_1
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
    """SMD pad (1.52 x 1.68 mm)."""
    shape = rectangle(1.52, 1.68)
    soldermask = Soldermask(rectangle(1.52, 1.68))
    paste = Paste(rectangle(1.52, 1.68))


# ======================================================================
# Landpattern
# ======================================================================
# NOTE: KiCad Y-axis is inverted vs JITX (KiCad Y+ = down, JITX Y+ = up)
# All Y coordinates are negated during conversion.
# Pads and the landpattern class are declared at module scope (not inside
# Component.__init__) because jitx 4.4 forbids creating new JITX classes
# during instantiation.

_pad_A = Pad1().at(1.96, -0)
_pad_K = Pad1().at(-1.96, -0)


@jitx.container.inline
class _Landpattern(Landpattern):
    name = "easyeda2kicad:SMA_L4.2-W2.6-LS5.0-RD_1"
    p = {
        1: _pad_A,
        2: _pad_K,
    }
    reference_designator = Silkscreen(Text(">REF", 1, Anchor.W).at((0, 4)))
    value_label = Custom(Text(">VALUE", 1, Anchor.W).at((0, -4)), name="Fab")
    silkscreen = [
        Silkscreen(Polyline(0.25, [(-0.72, -0), (0.75, -0)])),
        Silkscreen(Polyline(0.25, [(-0.25, 0.5), (-0.25, -0.5)])),
        Silkscreen(Polyline(0.25, [(0.25, 0.5), (-0.25, -0)])),
        Silkscreen(Polyline(0.25, [(-0.25, -0), (0.25, -0.5)])),
        Silkscreen(Polyline(0.25, [(0.25, -0.5), (0.25, 0.5)])),
        Silkscreen(Polyline(0.25, [(2.1, -1.07), (2.1, -1.3)])),
        Silkscreen(Polyline(0.25, [(2.1, 1.3), (2.1, 1.07)])),
        Silkscreen(Polyline(0.25, [(-2.1, 1.3), (2.1, 1.3)])),
        Silkscreen(Polyline(0.25, [(-2.1, 1.07), (-2.1, 1.3)])),
        Silkscreen(Polyline(0.25, [(-2.1, -1.3), (-2.1, -1.07)])),
        Silkscreen(Polyline(0.25, [(2.1, -1.3), (-2.1, -1.3)])),
        Silkscreen(ArcPolyline(0.06, [Arc((-2.63, -1.3), 0.03, 0, -360)])),
    ]
    courtyard = Courtyard(rectangle(4.2, 2.6))


# ======================================================================
# Component
# ======================================================================

class SS14(jitx.Component):
    "Schottky diode 40V 1A SMA"

    mpn = "SS14"
    manufacturer = "MDD"
    reference_designator_prefix = "D"
    datasheet = "https://datasheet.lcsc.com/datasheet/pdf/9977bb85cd7e349115b7bcb7054cfa0d.pdf"

    # --- Ports ---
    A = Port()  # Pad "A"
    K = Port()  # Pad "K"

    landpattern = _Landpattern

    # --- Symbol ---
    symbol = BoxSymbol(
        rows=Row(
            left=PinGroup(A, K),
        ),
    )

    def __init__(self):
        # --- Pad Mapping ---
        lp = self.landpattern
        self.pad_mapping = PadMapping({
            self.A: lp.p[1],
            self.K: lp.p[2],
        })


Device: type[SS14] = SS14
