"""
Time-of-flight proximity sensor, 1–1300 mm (ST DS13812 Rev 5)

Pin-to-pin compatible with the VL53L0X it replaces (same 4.4 × 2.4 mm LGA12,
same pin functions); it needs ST's VL53L4CD Ultra Lite Driver instead.

Landpattern from the datasheet's PWB solder pattern (Figure 17): twelve
0.50 × 0.50 mm pads, 0.80 mm pitch, rows at ±0.80 mm. The pads keep the
VL53L0X landpattern's keys (its KiCad import's, not the datasheet's pin
numbers), each at the same place, so routes laid out against `p[n]` on the
VL53L0X still end on the same pin. Because pad 1 is not datasheet pin 1, the
JLCPCB exporter cannot measure the reel orientation; lcsc.lock.json gives it
(0: the EasyEDA footprint's pin 1 is where AVDDVCSEL is here).
"""

import jitx
from jitx import PadMapping
from jitx.anchor import Anchor
from jitx.feature import Courtyard, Custom, Paste, Silkscreen, Soldermask
from jitx.landpattern import Landpattern, Pad
from jitx.net import Port
from jitx.shapes.composites import rectangle
from jitx.shapes.primitive import Arc, ArcPolyline, Polyline, Text
from jitxlib.jlcpcb import LCSCPart
from jitxlib.symbols.box import BoxSymbol, Column, PinGroup, Row


class _Pad(Pad):
    """SMD pad (0.5 x 0.5 mm)."""

    shape = rectangle(0.5, 0.5)
    soldermask = Soldermask(rectangle(0.5, 0.5))
    paste = Paste(rectangle(0.5, 0.5))


# Keys as the VL53L0X landpattern's; the datasheet pin is in each comment.
@jitx.container.inline
class _Landpattern(Landpattern):
    name = "LGA12_VL53L4CD"
    p = {
        1: _Pad().at(-1.6, -0.8),  # 5 XSHUT
        2: _Pad().at(-0.8, -0.8),  # 4 GND2
        3: _Pad().at(0.0, -0.8),  # 3 GND
        4: _Pad().at(0.8, -0.8),  # 2 AVSSVCSEL
        5: _Pad().at(1.6, -0.8),  # 1 AVDDVCSEL
        6: _Pad().at(1.6, 0.0),  # 12 GND4
        7: _Pad().at(1.6, 0.8),  # 11 AVDD
        8: _Pad().at(0.8, 0.8),  # 10 SCL
        9: _Pad().at(0.0, 0.8),  # 9 SDA
        10: _Pad().at(-0.8, 0.8),  # 8 DNC
        11: _Pad().at(-1.6, 0.8),  # 7 GPIO1
        12: _Pad().at(-1.6, 0.0),  # 6 GND3
    }
    reference_designator = Silkscreen(Text(">REF", 1, Anchor.W).at((0, 4.875)))
    value_label = Custom(Text(">VALUE", 1, Anchor.W).at((0, -4.875)), name="Fab")
    silkscreen = [
        Silkscreen(Polyline(0.15, [(-2.28, 0.41), (-2.28, 1.28), (-2.01, 1.28)])),
        Silkscreen(Polyline(0.15, [(2.28, 0.41), (2.28, 1.28), (2.01, 1.28)])),
        Silkscreen(Polyline(0.15, [(-2.28, -0.41), (-2.28, -1.28), (-2.01, -1.28)])),
        Silkscreen(Polyline(0.15, [(2.28, -0.41), (2.28, -1.28), (2.01, -1.28)])),
        # pin 1 marker
        Silkscreen(ArcPolyline(0.25, [Arc((1.65, -1.6), 0.12, 0, -360)])),
    ]
    courtyard = Courtyard(rectangle(4.4, 2.4))


class VL53L4CDV0DH_1(jitx.Component):
    "Time-of-flight proximity sensor"

    mpn = "VL53L4CDV0DH/1"
    manufacturer = "STMicroelectronics"
    lcsc = LCSCPart("C3178291")
    datasheet = "https://www.st.com/resource/en/datasheet/vl53l4cd.pdf"
    reference_designator_prefix = "U"

    AVDDVCSEL = Port()
    AVSSVCSEL = Port()
    GND = Port()
    GND2 = Port()
    XSHUT = Port()
    GND3 = Port()
    GPIO1 = Port()
    DNC = Port()
    SDA = Port()
    SCL = Port()
    AVDD = Port()
    GND4 = Port()

    landpattern = _Landpattern

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


Device: type[VL53L4CDV0DH_1] = VL53L4CDV0DH_1
