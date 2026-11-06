"""
Time-of-flight ranging sensor

Auto-generated from KiCad footprint: easyeda2kicad:OPTO-SMD_12P_VL53L0CXV0DH-1
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
    """SMD pad (0.5 x 0.65 mm)."""

    shape = rectangle(0.5, 0.65)
    soldermask = Soldermask(rectangle(0.5, 0.65))
    paste = Paste(rectangle(0.5, 0.65))


class Pad2(Pad):
    """SMD pad (0.55 x 0.55 mm)."""

    shape = rectangle(0.55, 0.55)
    soldermask = Soldermask(rectangle(0.55, 0.55))
    paste = Paste(rectangle(0.55, 0.55))


# ======================================================================
# Landpattern
# ======================================================================
# NOTE: KiCad Y-axis is inverted vs JITX (KiCad Y+ = down, JITX Y+ = up)
# All Y coordinates are negated during conversion.
# Pads and the landpattern class are declared at module scope (not inside
# Component.__init__) because jitx 4.4 forbids creating new JITX classes
# during instantiation.

_pad_SHT = Pad1().at(-1.6, -0.88)
_pad_GND2 = Pad1().at(-0.8, -0.88)
_pad_GND = Pad1().at(0, -0.88)
_pad_VSS = Pad1().at(0.8, -0.88)
_pad_VDD = Pad1().at(1.6, -0.88)
_pad_GND4 = Pad2().at(1.6, -0)
_pad_AVDD = Pad1().at(1.6, 0.88)
_pad_SCL = Pad1().at(0.8, 0.88)
_pad_SDA = Pad1().at(0, 0.88)
_pad_DNC = Pad1().at(-0.8, 0.88)
_pad_GP1 = Pad1().at(-1.6, 0.88)
_pad_GND3 = Pad2().at(-1.6, -0)


@jitx.container.inline
class _Landpattern(Landpattern):
    name = "easyeda2kicad:OPTO-SMD_12P_VL53L0CXV0DH-1"
    p = {
        1: _pad_SHT,
        2: _pad_GND2,
        3: _pad_GND,
        4: _pad_VSS,
        5: _pad_VDD,
        6: _pad_GND4,
        7: _pad_AVDD,
        8: _pad_SCL,
        9: _pad_SDA,
        10: _pad_DNC,
        11: _pad_GP1,
        12: _pad_GND3,
    }
    reference_designator = Silkscreen(Text(">REF", 1, Anchor.W).at((0, 4.875)))
    value_label = Custom(Text(">VALUE", 1, Anchor.W).at((0, -4.875)), name="Fab")
    silkscreen = [
        Silkscreen(Polyline(0.15, [(-2.28, 0.41), (-2.28, 1.28)])),
        Silkscreen(Polyline(0.15, [(-2.28, 1.28), (-2.01, 1.28)])),
        Silkscreen(Polyline(0.15, [(2.28, 0.41), (2.28, 1.28)])),
        Silkscreen(Polyline(0.15, [(2.28, 1.28), (2.01, 1.28)])),
        Silkscreen(Polyline(0.15, [(-2.28, -0.41), (-2.28, -1.28)])),
        Silkscreen(Polyline(0.15, [(-2.28, -1.28), (-2.01, -1.28)])),
        Silkscreen(Polyline(0.15, [(2.28, -0.41), (2.28, -1.28)])),
        Silkscreen(Polyline(0.15, [(2.28, -1.28), (2.01, -1.28)])),
        Silkscreen(ArcPolyline(0.06, [Arc((2.2, -1.2), 0.03, 0, -360)])),
        Silkscreen(ArcPolyline(0.25, [Arc((1.65, -1.6), 0.12, 0, -360)])),
        Silkscreen(ArcPolyline(0.15, [Arc((-0.95, -0), 0.07, 0, -360)])),
        Silkscreen(ArcPolyline(0.25, [Arc((0.95, -0), 0.12, 0, -360)])),
    ]
    courtyard = Courtyard(rectangle(4.4, 2.4))


# ======================================================================
# Component
# ======================================================================


class VL53L0CXV0DH_1(jitx.Component):
    "Time-of-flight ranging sensor"

    mpn = "VL53L0CXV0DH/1"
    manufacturer = "STMicroelectronics"
    lcsc = LCSCPart("C91199")
    datasheet = (
        "https://datasheet.lcsc.com/datasheet/pdf/be43197a59484f34ae07aa7af39d77a0.pdf"
    )
    reference_designator_prefix = "U"

    # --- Ports ---
    XSHUT = Port()  # Pad "XSHUT"
    GND2 = Port()  # Pad "GND2"
    GND = Port()  # Pad "GND"
    AVSSVCSEL = Port()  # Pad "AVSSVCSEL"
    AVDDVCSEL = Port()  # Pad "VDD" (datasheet pin 1, AVDDVCSEL)
    GND4 = Port()  # Pad "GND4"
    AVDD = Port()  # Pad "AVDD"
    SCL = Port()  # Pad "SCL"
    SDA = Port()  # Pad "SDA"
    DNC = Port()  # Pad "DNC"
    GPIO1 = Port()  # Pad "GPIO1"
    GND3 = Port()  # Pad "GND3"

    landpattern = _Landpattern

    # --- Symbol ---
    symbol = BoxSymbol(
        rows=Row(
            left=PinGroup(XSHUT, AVDD, SCL, SDA, DNC, GPIO1),
        ),
        columns=Column(
            up=PinGroup(AVDDVCSEL),
            down=PinGroup(GND2, GND, AVSSVCSEL, GND4, GND3),
        ),
    )

    def __init__(self):
        # --- Pad Mapping ---
        lp = self.landpattern
        self.pad_mapping = PadMapping(
            {
                self.XSHUT: lp.p[1],
                self.GND2: lp.p[2],
                self.GND: lp.p[3],
                self.AVSSVCSEL: lp.p[4],
                self.AVDDVCSEL: lp.p[5],
                self.GND4: lp.p[6],
                self.AVDD: lp.p[7],
                self.SCL: lp.p[8],
                self.SDA: lp.p[9],
                self.DNC: lp.p[10],
                self.GPIO1: lp.p[11],
                self.GND3: lp.p[12],
            }
        )


Device: type[VL53L0CXV0DH_1] = VL53L0CXV0DH_1
