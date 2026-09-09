"""
12 MHz crystal, 20pF CL, SMD3225-4P

Auto-generated from KiCad footprint: easyeda2kicad:CRYSTAL-SMD_4P-L3.2-W2.5-BL
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
    """SMD pad (1.4 x 1.2 mm)."""
    shape = rectangle(1.4, 1.2)
    soldermask = Soldermask(rectangle(1.4, 1.2))
    paste = Paste(rectangle(1.4, 1.2))


# ======================================================================
# Landpattern
# ======================================================================
# NOTE: KiCad Y-axis is inverted vs JITX (KiCad Y+ = down, JITX Y+ = up)
# All Y coordinates are negated during conversion.
# Pads and the landpattern class are declared at module scope (not inside
# Component.__init__) because jitx 4.4 forbids creating new JITX classes
# during instantiation.

_pad_OSC1 = Pad1().at(-1.1, -0.85)
_pad_GND_0 = Pad1().at(1.1, -0.85)
_pad_GND_1 = Pad1().at(-1.1, 0.85)
_pad_OSC2 = Pad1().at(1.1, 0.85)


@jitx.container.inline
class _Landpattern(Landpattern):
    name = "easyeda2kicad:CRYSTAL-SMD_4P-L3.2-W2.5-BL"
    p = {
        1: _pad_OSC1,
        2: _pad_GND_0,
        3: _pad_GND_1,
        4: _pad_OSC2,
    }
    reference_designator = Silkscreen(Text(">REF", 1, Anchor.W).at((0, 4.85)))
    value_label = Custom(Text(">VALUE", 1, Anchor.W).at((0, -4.85)), name="Fab")
    silkscreen = [
        Silkscreen(Polyline(0.15, [(-2.03, -1.68), (-2.03, 1.68)])),
        Silkscreen(Polyline(0.15, [(-2.03, 1.68), (2.03, 1.68)])),
        Silkscreen(Polyline(0.15, [(2.03, 1.68), (2.03, -1.68)])),
        Silkscreen(Polyline(0.15, [(2.03, -1.68), (-2.03, -1.68)])),
        Silkscreen(Polyline(0.15, [(-2.26, -0.25), (-2.26, -1.91)])),
        Silkscreen(Polyline(0.15, [(-2.26, -1.91), (-0.4, -1.91)])),
        Silkscreen(ArcPolyline(0.06, [Arc((-1.6, -1.25), 0.03, 0, -360)])),
    ]
    courtyard = Courtyard(rectangle(3.2, 2.5))


# ======================================================================
# Component
# ======================================================================

class X322512MSB4SI(jitx.Component):
    "12 MHz crystal, 20pF CL, SMD3225-4P"

    mpn = "X322512MSB4SI"
    manufacturer = "YXC"
    reference_designator_prefix = "Y"
    datasheet = "https://datasheet.lcsc.com/datasheet/pdf/a84bd8d530dd46e4b0f6d0ee59d8a89c.pdf"

    # --- Ports ---
    OSC1 = Port()  # Pad "OSC1"
    GND = [Port() for _ in range(2)]  # Pad "GND" x2
    OSC2 = Port()  # Pad "OSC2"

    landpattern = _Landpattern

    # --- Symbol ---
    symbol = BoxSymbol(
        rows=Row(
            left=PinGroup(OSC1, OSC2),
        ),
        columns=Column(
            down=PinGroup(*GND),
        ),
    )

    def __init__(self):
        # --- Pad Mapping ---
        lp = self.landpattern
        self.pad_mapping = PadMapping({
            self.OSC1: lp.p[1],
            self.GND[0]: lp.p[2],
            self.GND[1]: lp.p[3],
            self.OSC2: lp.p[4],
        })


Device: type[X322512MSB4SI] = X322512MSB4SI
