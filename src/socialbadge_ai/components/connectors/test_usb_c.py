"""Build/fab smoke test for the USB-C connector alone: TYPE_C_31_M_12 centered
on a board sized just large enough to hold its courtyard (8.94 x 7.35 mm),
plus a 1 mm margin per side so the part isn't flush with the board edge.
"""

from jitx import Circuit, Design
from jitx.board import Board
from jitx.circuit import Placement
from jitx.shapes.composites import rectangle
from jitxlib.jlcpcb import JLC04161H_1080

from .hroparts_TYPE_C_31_M_12 import TYPE_C_31_M_12

BOARD_SHAPE = rectangle(10.94, 9.35, radius=0.25)

# Same not-quite-180 angle J1 has on the full badge board; a non-multiple of
# 90 makes the gerber exporter emit the capsule pads as a rotated aperture
# macro instead of a standard obround.
DUT_ROTATION = -179.99998474121094


class TestUSBCBoard(Board):
    """10.94 x 9.35 mm board -- just big enough for the USB-C connector's
    8.94 x 7.35 mm courtyard, with a 1 mm margin on each side."""

    shape = BOARD_SHAPE


class TestUSBCCircuit(Circuit):
    def __init__(self):
        self.dut = TYPE_C_31_M_12()
        self.place(self.dut, Placement((0.0, 0.0), rotate=DUT_ROTATION))


class TestDesign(Design):
    """Run: `python -m jitx build socialbadge_ai.components.connectors.test_usb_c.TestDesign`"""

    board = TestUSBCBoard()
    substrate = JLC04161H_1080()
    circuit = TestUSBCCircuit()


Device = TestDesign
