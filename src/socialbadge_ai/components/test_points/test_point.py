"""
Generic bare-copper test point.

A single exposed SMD pad with no component ever placed on it — not in the
BOM, not soldered by assembly, just a probe-friendly landing spot on a power
or ground net for bring-up debugging with a multimeter.
"""

from jitx.anchor import Anchor
from jitx.component import NonPopulatedComponent
from jitx.net import Port
from jitx.feature import Courtyard, Silkscreen
from jitx.landpattern import Landpattern
from jitx.shapes.primitive import Circle, Text
from jitxlib.landpatterns.pads import SMDPad
from jitxlib.symbols.box import BoxSymbol

PAD_DIAMETER = 1.2  # mm — large enough for a multimeter probe tip or hook clip
REF_DES_TEXT_SIZE = 0.8  # mm
REF_DES_OFFSET = 1.3  # mm above pad center


class TestPointLandpattern(Landpattern):
    p1 = SMDPad(Circle(diameter=PAD_DIAMETER)).at(0, 0)
    courtyard = Courtyard(Circle(diameter=PAD_DIAMETER + 0.5))
    # ">REF" is a placeholder the gerber/export pipeline substitutes with
    # each instance's actual reference designator (e.g. "TP3") at export
    # time, even though this landpattern object is shared across instances.
    reference_designator = Silkscreen(
        Text(">REF", REF_DES_TEXT_SIZE, Anchor.C).at(0, REF_DES_OFFSET)
    )


class TestPoint(NonPopulatedComponent):
    """A bare, unpopulated copper test point for probing a single net."""

    reference_designator_prefix = "TP"
    p1 = Port()
    landpattern = TestPointLandpattern()
    symbol = BoxSymbol()


Device: type[TestPoint] = TestPoint
