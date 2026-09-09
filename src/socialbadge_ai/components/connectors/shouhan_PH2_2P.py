"""
JST-PH-compatible 2.0 mm 2-pin SMD right-angle battery connector (SHOU HAN 2.0-2P WT)

Pad layout (from kicad_mod; signal pads on front edge, mounting tabs on back):
  Pad 1 (PIN1):   1.0 × 3.5 mm, front-edge, +1.0 mm in X     → battery wire 1
  Pad 2 (PIN2):   1.0 × 3.5 mm, front-edge, -1.0 mm in X     → battery wire 2
  Pad 3 (MOUNT1): 1.5 × 3.5 mm, back-edge, +3.35 mm in X     → solder tab (tie GND)
  Pad 4 (MOUNT2): 1.5 × 3.5 mm, back-edge, -3.35 mm in X     → solder tab (tie GND)

Battery polarity is user's choice — assign PIN1/PIN2 to BAT+/BAT- per the wired battery.
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
    """SMD pad (1 x 3.5 mm)."""
    shape = rectangle(1, 3.5)
    soldermask = Soldermask(rectangle(1, 3.5))
    paste = Paste(rectangle(1, 3.5))


class Pad2(Pad):
    """SMD pad (1.5 x 3.5 mm)."""
    shape = rectangle(1.5, 3.5)
    soldermask = Soldermask(rectangle(1.5, 3.5))
    paste = Paste(rectangle(1.5, 3.5))


# ======================================================================
# Landpattern
# ======================================================================
# Pads and the landpattern class are declared at module scope (not inside
# Component.__init__) because jitx 4.4 forbids creating new JITX classes
# during instantiation.

_pad_p1 = Pad1().at(1, -2.85)
_pad_p2 = Pad1().at(-1, -2.85)
_pad_p3 = Pad2().at(3.35, 2.85)
_pad_p4 = Pad2().at(-3.35, 2.85)


@jitx.container.inline
class _Landpattern(Landpattern):
    name = "easyeda2kicad:CONN-SMD_2.0-2PWT"
    p = {
        1: _pad_p1,
        2: _pad_p2,
        3: _pad_p3,
        4: _pad_p4,
    }
    reference_designator = Silkscreen(Text(">REF", 1, Anchor.W).at((0, 6.85)))
    value_label = Custom(Text(">VALUE", 1, Anchor.W).at((0, -6.85)), name="Fab")
    silkscreen = [
        Silkscreen(Polyline(0.25, [(-0.27, -1.5), (0.27, -1.5)])),
        Silkscreen(Polyline(0.25, [(4, -3.2), (4, 0.92)])),
        Silkscreen(Polyline(0.25, [(-2.37, 4.5), (2.37, 4.5)])),
        Silkscreen(Polyline(0.25, [(-4, -3.2), (-4, 0.92)])),
        Silkscreen(Polyline(0.25, [(1.73, -1.5), (3.3, -1.5)])),
        Silkscreen(Polyline(0.25, [(3.3, -1.5), (3.3, -3.2)])),
        Silkscreen(Polyline(0.25, [(3.3, -3.2), (4, -3.2)])),
        Silkscreen(Polyline(0.25, [(-4, -3.2), (-3.3, -3.2)])),
        Silkscreen(Polyline(0.25, [(-3.3, -3.2), (-3.3, -1.5)])),
        Silkscreen(Polyline(0.25, [(-3.3, -1.5), (-1.73, -1.5)])),
        Silkscreen(ArcPolyline(0.06, [Arc((4, -4), 0.03, 0, -360)])),
    ]
    courtyard = Courtyard(rectangle(8, 7.72))


# ======================================================================
# Component
# ======================================================================

class PH2_2P(jitx.Component):
    "JST-PH 2mm 2-pin SMD right-angle battery connector"

    mpn = "2.0-2P WT"
    manufacturer = "SHOU HAN"
    reference_designator_prefix = "J"
    datasheet = "https://datasheet.lcsc.com/datasheet/pdf/dce18c3d77bfbed062e0f133b57b17e3.pdf"

    # --- Ports ---
    PIN1 = Port()    # Pad 1 — battery wire 1
    PIN2 = Port()    # Pad 2 — battery wire 2
    MOUNT1 = Port()  # Pad 3 — mechanical solder tab (tie GND)
    MOUNT2 = Port()  # Pad 4 — mechanical solder tab (tie GND)

    landpattern = _Landpattern

    # --- Symbol ---
    symbol = BoxSymbol(
        rows=Row(
            left=PinGroup(PIN1, PIN2),
            right=PinGroup(MOUNT1, MOUNT2),
        ),
    )

    def __init__(self):
        # --- Pad Mapping ---
        lp = self.landpattern
        self.mappings = [PadMapping({
            self.PIN1: [lp.p[1]],
            self.PIN2: [lp.p[2]],
            self.MOUNT1: [lp.p[3]],
            self.MOUNT2: [lp.p[4]],
        })]


Device: type[PH2_2P] = PH2_2P
