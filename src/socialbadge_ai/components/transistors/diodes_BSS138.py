"""
N-channel MOSFET 50 V 200 mA SOT-23

Auto-generated from KiCad footprint: easyeda2kicad:SOT-23-3_L2.9-W1.6-P1.90-LS2.8-BR
"""

import jitx
from jitx import PadMapping
from jitx.feature import Courtyard, Custom, Paste, Silkscreen, Soldermask
from jitx.landpattern import Landpattern, Pad
from jitx.net import Port
from jitx.shapes.composites import rectangle
from jitx.shapes.primitive import Arc, ArcPolyline, Polyline, Text
from jitx.anchor import Anchor
from jitxlib.jlcpcb import LCSCPart
from jitxlib.symbols.box import BoxSymbol, PinGroup, Row


# ======================================================================
# Pad shape definitions
# ======================================================================


class Pad1(Pad):
    """SMD pad (1.07 x 0.6 mm)."""

    shape = rectangle(1.07, 0.6)
    soldermask = Soldermask(rectangle(1.07, 0.6))
    paste = Paste(rectangle(1.07, 0.6))


# ======================================================================
# Landpattern
# ======================================================================
# NOTE: KiCad Y-axis is inverted vs JITX (KiCad Y+ = down, JITX Y+ = up)
# All Y coordinates are negated during conversion.
# Pads and the landpattern class are declared at module scope (not inside
# Component.__init__) because jitx 4.4 forbids creating new JITX classes
# during instantiation.

_pad_G = Pad1().at(1.24, -0.95)
_pad_S = Pad1().at(1.24, 0.95)
_pad_D = Pad1().at(-1.24, -0)


@jitx.container.inline
class _Landpattern(Landpattern):
    name = "easyeda2kicad:SOT-23-3_L2.9-W1.6-P1.90-LS2.8-BR"
    p = {
        1: _pad_G,
        2: _pad_S,
        3: _pad_D,
    }
    reference_designator = Silkscreen(Text(">REF", 1, Anchor.W).at((0, 4.95)))
    value_label = Custom(Text(">VALUE", 1, Anchor.W).at((0, -4.95)), name="Fab")
    silkscreen = [
        Silkscreen(Polyline(0.15, [(0.88, 1.54), (-0.88, 1.54)])),
        Silkscreen(Polyline(0.15, [(-0.88, 1.54), (-0.88, 0.49)])),
        Silkscreen(Polyline(0.15, [(0.88, -1.54), (-0.88, -1.54)])),
        Silkscreen(Polyline(0.15, [(-0.88, -1.54), (-0.88, -0.49)])),
        Silkscreen(Polyline(0.15, [(0.88, 0.46), (0.88, -0.46)])),
        Silkscreen(ArcPolyline(0.06, [Arc((1.4, -1.46), 0.03, 0, -360)])),
    ]
    # The EasyEDA courtyard was the 1.6 × 2.92 mm body; the pads reach ±1.775 mm
    # in x and ±1.25 mm in y, so it is grown to cover them (+0.25 mm).
    courtyard = Courtyard(rectangle(4.1, 3.0))


# ======================================================================
# Component
# ======================================================================


class BSS138(jitx.Component):
    "N-channel MOSFET 50 V 200 mA SOT-23"

    mpn = "BSS138-7-F"
    manufacturer = "Diodes Incorporated"
    lcsc = LCSCPart("C40912")
    datasheet = (
        "https://datasheet.lcsc.com/datasheet/pdf/e14366bd137adeb6bb9eee9bd5f8402d.pdf"
    )
    reference_designator_prefix = "Q"

    # --- Ports ---
    G = Port()  # Pad "G"
    S = Port()  # Pad "S"
    D = Port()  # Pad "D"

    landpattern = _Landpattern

    # --- Symbol ---
    symbol = BoxSymbol(
        rows=Row(
            left=PinGroup(G, S, D),
        ),
    )

    def __init__(self):
        # --- Pad Mapping ---
        lp = self.landpattern
        self.pad_mapping = PadMapping(
            {
                self.G: lp.p[1],
                self.S: lp.p[2],
                self.D: lp.p[3],
            }
        )


Device: type[BSS138] = BSS138
