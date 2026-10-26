"""Minimal JLCPCB gerber-viewer repro: one USB-C mounting-tab slot pad, twice.

Each part is a single through-hole capsule pad -- the TYPE_C_31_M_12's Pad5
(capsule(1.2, 2.0) copper, capsule(0.8, 1.6) slot). The left copy is rotated
-179.99998474121094 deg (J1's angle on the badge board), the right copy
exactly -180 deg. The off-axis angle makes the gerber exporter emit the
capsule as a rotated aperture macro; the exact angle gets a plain obround.
"""

import jitx
from jitx import Circuit, Design
from jitx.board import Board
from jitx.circuit import Placement
from jitx.component import Component
from jitx.feature import Courtyard
from jitx.landpattern import Landpattern
from jitx.net import Port
from jitx.shapes.composites import rectangle
from jitxlib.jlcpcb import JLC04161H_1080
from jitxlib.symbols.box import BoxSymbol

from .hroparts_TYPE_C_31_M_12 import Pad5

OFF_AXIS_ROTATION = -179.99998474121094
EXACT_ROTATION = -180.0
SPACING = 4.0

BOARD_SHAPE = rectangle(8.0, 5.0, radius=0.25)


@jitx.container.inline
class SlotLandpattern(Landpattern):
    p1 = Pad5().at(0, 0)
    courtyard = Courtyard(rectangle(1.6, 2.4))


class SlotPad(Component):
    """A single USB-C mounting-tab slot pad."""

    reference_designator_prefix = "SL"
    p1 = Port()

    landpattern = SlotLandpattern
    symbol = BoxSymbol()


class SlotBoard(Board):
    shape = BOARD_SHAPE


class SlotCircuit(Circuit):
    def __init__(self):
        self.off_axis = SlotPad()
        self.exact = SlotPad()
        self.place(self.off_axis, Placement((-SPACING / 2, 0.0), rotate=OFF_AXIS_ROTATION))
        self.place(self.exact, Placement((SPACING / 2, 0.0), rotate=EXACT_ROTATION))


class TestDesign(Design):
    """Run: `jitx design build socialbadge_ai.components.connectors.test_usbc_slot.TestDesign`"""

    board = SlotBoard()
    substrate = JLC04161H_1080()
    circuit = SlotCircuit()


Device = TestDesign
