"""
Addressable RGB LED, 2.0 x 2.0 mm, integrated WS2812 driver

Auto-generated from KiCad footprint: easyeda2kicad:LED-SMD_4P-L2.0-W2.0-TL_WS2812B-2020
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
    """SMD pad (0.9 x 0.7 mm)."""

    shape = rectangle(0.9, 0.7)
    soldermask = Soldermask(rectangle(0.9, 0.7))
    paste = Paste(rectangle(0.9, 0.7))


# ======================================================================
# Landpattern
# ======================================================================
# NOTE: KiCad Y-axis is inverted vs JITX (KiCad Y+ = down, JITX Y+ = up)
# All Y coordinates are negated during conversion.
# Pads and the landpattern class are declared at module scope (not inside
# Component.__init__) because jitx 4.4 forbids creating new JITX classes
# during instantiation.

_pad_DO = Pad1().at(-0.92, 0.55)
_pad_GND = Pad1().at(-0.92, -0.55)
_pad_DI = Pad1().at(0.92, -0.55)
_pad_VDD = Pad1().at(0.92, 0.55)


@jitx.container.inline
class _Landpattern(Landpattern):
    name = "easyeda2kicad:LED-SMD_4P-L2.0-W2.0-TL_WS2812B-2020"
    p = {
        1: _pad_DO,
        2: _pad_GND,
        3: _pad_DI,
        4: _pad_VDD,
    }
    reference_designator = Silkscreen(Text(">REF", 1, Anchor.W).at((0, 4.55)))
    value_label = Custom(Text(">VALUE", 1, Anchor.W).at((0, -4.55)), name="Fab")
    silkscreen = [
        Silkscreen(Polyline(0.15, [(-0.25, 0.75), (-0.1, 0.75)])),
        Silkscreen(Polyline(0.15, [(-0.1, 0.75), (-0.1, -0.65)])),
        Silkscreen(Polyline(0.15, [(-0.1, -0.65), (-0.1, -0.7)])),
        Silkscreen(Polyline(0.15, [(-0.1, -0.7), (-0.25, -0.7)])),
        Silkscreen(Polyline(0.15, [(-0.25, 0.75), (-0.25, -0.7)])),
        Silkscreen(Polyline(0.25, [(-1.3, 1.15), (-1.3, 1.14)])),
        Silkscreen(Polyline(0.15, [(1, 1.1), (-1, 1.1)])),
        Silkscreen(Polyline(0.15, [(-1, -1.1), (1, -1.1)])),
        Silkscreen(ArcPolyline(0.06, [Arc((-1, 1), 0.03, 0, -360)])),
    ]
    # The EasyEDA courtyard was the 2 × 2 mm body; the pads reach ±1.37 mm in x
    # and ±0.9 mm in y, so it is grown to cover them.
    courtyard = Courtyard(rectangle(3.0, 2.2))


# ======================================================================
# Component
# ======================================================================


class WS2812C_2020_V6(jitx.Component):
    "Addressable RGB LED, 2.0 x 2.0 mm, integrated WS2812 driver"

    mpn = "WS2812C-2020-V6/W"
    manufacturer = "Worldsemi"
    lcsc = LCSCPart("C55160508")
    datasheet = (
        "https://datasheet.lcsc.com/datasheet/pdf/c46fb81601a669a9e6c1d3221ebfe144.pdf"
    )
    reference_designator_prefix = "D"

    # --- Ports ---
    DO = Port()  # Pad "DO"
    GND = Port()  # Pad "GND"
    DI = Port()  # Pad "DI"
    VDD = Port()  # Pad "VDD"

    landpattern = _Landpattern

    # --- Symbol ---
    symbol = BoxSymbol(
        rows=Row(
            left=PinGroup(DO, DI),
        ),
        columns=Column(
            up=PinGroup(VDD),
            down=PinGroup(GND),
        ),
    )

    def __init__(self):
        # --- Pad Mapping ---
        lp = self.landpattern
        self.pad_mapping = PadMapping(
            {
                self.DO: lp.p[1],
                self.GND: lp.p[2],
                self.DI: lp.p[3],
                self.VDD: lp.p[4],
            }
        )


Device: type[WS2812C_2020_V6] = WS2812C_2020_V6
