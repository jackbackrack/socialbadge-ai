"""
USB Type-C receptacle 16-pin SMD

Auto-generated from KiCad footprint: easyeda2kicad:USB-C_SMD-TYPE-C-31-M-12_1
"""

import jitx
from jitx import PadMapping
from jitx.feature import Courtyard, Custom, Cutout, Paste, Silkscreen, Soldermask
from jitx.landpattern import Landpattern, Pad
from jitx.net import Port
from jitx.shapes.composites import capsule, rectangle
from jitx.shapes.primitive import Arc, ArcPolyline, Circle, Polyline, Text
from jitx.anchor import Anchor
from jitxlib.symbols.box import BoxSymbol, PinGroup, Row, Column


# ======================================================================
# Pad shape definitions
# ======================================================================

class Pad1(Pad):
    """SMD pad (0.3 x 1.3 mm)."""
    shape = rectangle(0.3, 1.3)
    soldermask = Soldermask(rectangle(0.3, 1.3))
    paste = Paste(rectangle(0.3, 1.3))


class Pad2(Pad):
    """SMD pad (0.6 x 1.3002 mm)."""
    shape = rectangle(0.6, 1.3002)
    soldermask = Soldermask(rectangle(0.6, 1.3002))
    paste = Paste(rectangle(0.6, 1.3002))


class Pad3(Pad):
    """SMD pad (0.6 x 1.3 mm)."""
    shape = rectangle(0.6, 1.3)
    soldermask = Soldermask(rectangle(0.6, 1.3))
    paste = Paste(rectangle(0.6, 1.3))


class Pad4(Pad):
    """Through-hole pad."""
    shape = capsule(1.2, 1.8)
    cutout = Cutout(capsule(0.8, 1.4))


class Pad5(Pad):
    """Through-hole pad."""
    shape = capsule(1.2, 2)
    cutout = Cutout(capsule(0.8, 1.6))


class Pad6(Pad):
    """Through-hole pad."""
    shape = Circle(radius=0.375)
    cutout = Cutout(Circle(radius=0.375))


# ======================================================================
# Landpattern
# ======================================================================
# NOTE: KiCad Y-axis is inverted vs JITX (KiCad Y+ = down, JITX Y+ = up)
# All Y coordinates are negated during conversion.
# Pads and the landpattern class are declared at module scope (not inside
# Component.__init__) because jitx 4.4 forbids creating new JITX classes
# during instantiation.

_pad_SBU2 = Pad1().at(-1.75, 2.47)
_pad_CC1 = Pad1().at(-1.25, 2.47)
_pad_DN2 = Pad1().at(-0.75, 2.47)
_pad_DP1 = Pad1().at(-0.25, 2.47)
_pad_DN1 = Pad1().at(0.25, 2.47)
_pad_DP2 = Pad1().at(0.75, 2.47)
_pad_SBU1 = Pad1().at(1.25, 2.47)
_pad_CC2 = Pad1().at(1.75, 2.47)
_pad_GND_0 = Pad2().at(-3.2, 2.47)
_pad_GND_1 = Pad3().at(3.2, 2.47)
_pad_VBUS_0 = Pad3().at(2.4, 2.47)
_pad_VBUS_1 = Pad3().at(-2.4, 2.47)
_pad_EH_0 = Pad4().at(4.33, -2.47)
_pad_EH_1 = Pad5().at(4.33, 1.71)
_pad_EH_2 = Pad5().at(-4.33, 1.71)
_pad_EH_3 = Pad4().at(-4.33, -2.47)
_pad_NC_0 = Pad6().at(-2.9, 1.21)
_pad_NC_1 = Pad6().at(2.9, 1.21)


@jitx.container.inline
class _Landpattern(Landpattern):
    name = "easyeda2kicad:USB-C_SMD-TYPE-C-31-M-12_1"
    p = {
        1: _pad_SBU2,
        2: _pad_CC1,
        3: _pad_DN2,
        4: _pad_DP1,
        5: _pad_DN1,
        6: _pad_DP2,
        7: _pad_SBU1,
        8: _pad_CC2,
        9: _pad_GND_0,
        10: _pad_GND_1,
        11: _pad_VBUS_0,
        12: _pad_VBUS_1,
        13: _pad_EH_0,
        14: _pad_EH_1,
        15: _pad_EH_2,
        16: _pad_EH_3,
        17: _pad_NC_0,
        18: _pad_NC_1,
    }
    reference_designator = Silkscreen(Text(">REF", 1, Anchor.W).at((0, 6.474)))
    value_label = Custom(Text(">VALUE", 1, Anchor.W).at((0, -6.474)), name="Fab")
    silkscreen = [
        Silkscreen(Polyline(0.25, [(-4.47, -1.38), (-4.47, 0.49)])),
        Silkscreen(Polyline(0.25, [(4.47, -5.09), (-4.47, -5.09)])),
        Silkscreen(Polyline(0.25, [(-4.47, -5.09), (-4.47, -3.61)])),
        Silkscreen(Polyline(0.25, [(4.47, -1.38), (4.47, 0.49)])),
        Silkscreen(Polyline(0.25, [(4.47, -5.09), (4.47, -3.61)])),
        Silkscreen(ArcPolyline(0.06, [Arc((4.48, 2.76), 0.03, 0, -360)])),
    ]
    courtyard = Courtyard(rectangle(8.94, 7.35))


# ======================================================================
# Component
# ======================================================================

class TYPE_C_31_M_12(jitx.Component):
    "USB Type-C receptacle 16-pin SMD"

    mpn = "TYPE-C-31-M-12"
    manufacturer = "Korean Hroparts Elec"
    reference_designator_prefix = "J"
    datasheet = "https://datasheet.lcsc.com/datasheet/pdf/9e56b777c022540fcce7c7f67825f55e.pdf"

    # --- Ports ---
    SBU2 = Port()  # Pad "SBU2"
    CC1 = Port()  # Pad "CC1"
    DN2 = Port()  # Pad "DN2"
    DP1 = Port()  # Pad "DP1"
    DN1 = Port()  # Pad "DN1"
    DP2 = Port()  # Pad "DP2"
    SBU1 = Port()  # Pad "SBU1"
    CC2 = Port()  # Pad "CC2"
    GND = [Port() for _ in range(2)]  # Pad "GND" x2
    VBUS = [Port() for _ in range(2)]  # Pad "VBUS" x2
    EH = [Port() for _ in range(4)]  # Pad "EH" x4
    NC = [Port() for _ in range(2)]  # Pad "" x2

    landpattern = _Landpattern

    # --- Symbol ---
    symbol = BoxSymbol(
        rows=Row(
            left=PinGroup(SBU2, CC1, DN2, DP1, DN1, DP2, SBU1, CC2, *EH, *NC),
        ),
        columns=Column(
            up=PinGroup(*VBUS),
            down=PinGroup(*GND),
        ),
    )

    def __init__(self):
        # --- Pad Mapping ---
        lp = self.landpattern
        self.pad_mapping = PadMapping({
            self.SBU2: lp.p[1],
            self.CC1: lp.p[2],
            self.DN2: lp.p[3],
            self.DP1: lp.p[4],
            self.DN1: lp.p[5],
            self.DP2: lp.p[6],
            self.SBU1: lp.p[7],
            self.CC2: lp.p[8],
            self.GND[0]: lp.p[9],
            self.GND[1]: lp.p[10],
            self.VBUS[0]: lp.p[11],
            self.VBUS[1]: lp.p[12],
            self.EH[0]: lp.p[13],
            self.EH[1]: lp.p[14],
            self.EH[2]: lp.p[15],
            self.EH[3]: lp.p[16],
            self.NC[0]: lp.p[17],
            self.NC[1]: lp.p[18],
        })


Device: type[TYPE_C_31_M_12] = TYPE_C_31_M_12
