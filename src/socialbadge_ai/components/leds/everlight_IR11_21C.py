"""
940 nm infrared emitting diode

Auto-generated from KiCad footprint: easyeda2kicad:LED1206-R-RD_RED

Pad 1 here is the cathode and pad 2 the anode, the reverse of the datasheet
(pin 1 anode, pin 2 cathode) and of the EasyEDA footprint JLCPCB places from.
The board was laid out against this numbering, so rather than renumber the
pads the part is turned instead: lcsc.lock.json gives it orientation 180, which
puts the reel part's anode on pad 2, and the silkscreen (polarity triangle,
chamfered cathode end, pin-1 dot) is mirrored from the KiCad import's to
match, so it shows the cathode at pad 1.
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
    """SMD pad (1.485 x 1.62 mm)."""

    shape = rectangle(1.485, 1.62)
    soldermask = Soldermask(rectangle(1.485, 1.62))
    paste = Paste(rectangle(1.485, 1.62))


# ======================================================================
# Landpattern
# ======================================================================
# NOTE: KiCad Y-axis is inverted vs JITX (KiCad Y+ = down, JITX Y+ = up)
# All Y coordinates are negated during conversion.
# Pads and the landpattern class are declared at module scope (not inside
# Component.__init__) because jitx 4.4 forbids creating new JITX classes
# during instantiation.

_pad_C = Pad1().at(1.49, -0)
_pad_A = Pad1().at(-1.49, -0)


@jitx.container.inline
class _Landpattern(Landpattern):
    name = "easyeda2kicad:LED1206-R-RD_RED"
    p = {
        1: _pad_C,
        2: _pad_A,
    }
    reference_designator = Silkscreen(Text(">REF", 1, Anchor.W).at((0, 4)))
    value_label = Custom(Text(">VALUE", 1, Anchor.W).at((0, -4)), name="Fab")
    silkscreen = [
        Silkscreen(Polyline(0.25, [(-0.38, 0.63), (-0.38, -0.63)])),
        Silkscreen(Polyline(0.25, [(-0.38, -0.63), (-0.38, 0.63)])),
        Silkscreen(Polyline(0.25, [(-0.38, 0.63), (0.51, -0)])),
        Silkscreen(Polyline(0.25, [(0.51, -0), (-0.38, -0.63)])),
        Silkscreen(Polyline(0.15, [(-0.83, -1.04), (-2.46, -1.04)])),
        Silkscreen(Polyline(0.15, [(-2.46, -1.04), (-2.46, 1.04)])),
        Silkscreen(Polyline(0.15, [(-2.46, 1.04), (-0.83, 1.04)])),
        Silkscreen(Polyline(0.15, [(0.83, -1.04), (2.31, -1.04)])),
        Silkscreen(Polyline(0.15, [(2.31, -1.04), (2.46, -0.89)])),
        Silkscreen(Polyline(0.15, [(2.46, -0.89), (2.46, 0.89)])),
        Silkscreen(Polyline(0.15, [(2.46, 0.89), (2.31, 1.04)])),
        Silkscreen(Polyline(0.15, [(2.31, 1.04), (0.83, 1.04)])),
        Silkscreen(ArcPolyline(0.06, [Arc((-1.5, 0.75), 0.03, 0, -360)])),
    ]
    courtyard = Courtyard(rectangle(3, 1.5))


# ======================================================================
# Component
# ======================================================================


class IR11_21C_TR8(jitx.Component):
    "940 nm infrared emitting diode"

    mpn = "IR11-21C/TR8"
    manufacturer = "Everlight Elec"
    lcsc = LCSCPart("C19269752")
    datasheet = "https://en.everlight.com/wp-content/plugins/ItemRelationship/product_files/pdf/IR11-21C-TR8.pdf"
    reference_designator_prefix = "D"

    # --- Ports ---
    C = Port()  # Pad "C"
    A = Port()  # Pad "A"

    landpattern = _Landpattern

    # --- Symbol ---
    symbol = BoxSymbol(
        rows=Row(
            left=PinGroup(C, A),
        ),
    )

    def __init__(self):
        # --- Pad Mapping ---
        lp = self.landpattern
        self.pad_mapping = PadMapping(
            {
                self.C: lp.p[1],
                self.A: lp.p[2],
            }
        )


Device: type[IR11_21C_TR8] = IR11_21C_TR8
