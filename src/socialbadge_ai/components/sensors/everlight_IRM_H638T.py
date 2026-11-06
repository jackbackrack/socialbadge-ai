"""
38 kHz infrared receiver module

Auto-generated from KiCad footprint: easyeda2kicad:SENSOR-SMD_IRM-H638T-TR2-TL
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
from jitxlib.symbols.box import BoxSymbol, PinGroup, Row, Column


# ======================================================================
# Pad shape definitions
# ======================================================================


class Pad1(Pad):
    """SMD pad (0.9 x 1.5 mm)."""

    shape = rectangle(0.9, 1.5)
    soldermask = Soldermask(rectangle(0.9, 1.5))
    paste = Paste(rectangle(0.9, 1.5))


# ======================================================================
# Landpattern
# ======================================================================
# NOTE: KiCad Y-axis is inverted vs JITX (KiCad Y+ = down, JITX Y+ = up)
# All Y coordinates are negated during conversion.
# Pads and the landpattern class are declared at module scope (not inside
# Component.__init__) because jitx 4.4 forbids creating new JITX classes
# during instantiation.

_pad_GND_0 = Pad1().at(-2.95, 1.27, rotate=90)
_pad_GND_1 = Pad1().at(-2.95, -1.27, rotate=90)
_pad_VOUT = Pad1().at(2.95, -1.27, rotate=90)
_pad_VCC = Pad1().at(2.92, 1.27, rotate=90)


@jitx.container.inline
class _Landpattern(Landpattern):
    name = "easyeda2kicad:SENSOR-SMD_IRM-H638T-TR2-TL"
    p = {
        1: _pad_GND_0,
        2: _pad_GND_1,
        3: _pad_VOUT,
        4: _pad_VCC,
    }
    reference_designator = Silkscreen(Text(">REF", 1, Anchor.W).at((0, 5.27)))
    value_label = Custom(Text(">VALUE", 1, Anchor.W).at((0, -5.27)), name="Fab")
    silkscreen = [
        Silkscreen(Polyline(0.25, [(-2, 2.5), (2, 2.5)])),
        Silkscreen(Polyline(0.25, [(2, 2.5), (2, -2.5)])),
        Silkscreen(Polyline(0.25, [(2, -2.5), (-2, -2.5)])),
        Silkscreen(Polyline(0.25, [(-2, -2.5), (-2, 2.5)])),
        Silkscreen(ArcPolyline(0.06, [Arc((-3.5, 2.5), 0.03, 0, -360)])),
        Silkscreen(ArcPolyline(0.25, [Arc((0, 0.76), 1.53, 0, -360)])),
    ]
    courtyard = Courtyard(rectangle(4, 5))


# ======================================================================
# Component
# ======================================================================


class IRM_H638T_TR2(jitx.Component):
    "38 kHz infrared receiver module"

    mpn = "IRM-H638T/TR2"
    manufacturer = "Everlight Elec"
    lcsc = LCSCPart("C91447")
    datasheet = (
        "https://www.everlighteurope.com/custom/files/datasheets/DMO-0000008.pdf"
    )
    reference_designator_prefix = "U"

    # --- Ports ---
    GND = [Port() for _ in range(2)]  # Pad "GND" x2
    VOUT = Port()  # Pad "VOUT"
    VCC = Port()  # Pad "VCC"

    landpattern = _Landpattern

    # --- Symbol ---
    symbol = BoxSymbol(
        rows=Row(
            left=PinGroup(VOUT),
        ),
        columns=Column(
            up=PinGroup(VCC),
            down=PinGroup(*GND),
        ),
    )

    def __init__(self):
        # --- Pad Mapping ---
        lp = self.landpattern
        self.pad_mapping = PadMapping(
            {
                self.GND[0]: lp.p[1],
                self.GND[1]: lp.p[2],
                self.VOUT: lp.p[3],
                self.VCC: lp.p[4],
            }
        )


Device: type[IRM_H638T_TR2] = IRM_H638T_TR2
