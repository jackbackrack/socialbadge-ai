"""Shared helpers for hand-built (vendor-drawing) landpatterns.

The FPC connector and the two switches have vendor-recommended land patterns
that no ``jitxlib`` generator expresses, so their ``Landpattern`` classes place
pads directly from the manufacturer drawing. These helpers add the decoration
those classes share: a courtyard, a silkscreen body outline kept clear of the
soldermask openings, a pin-1 dot and the reference-designator text.

All values that are fabrication rules (silkscreen width, silk-to-mask spacing,
soldermask registration) are read from the active substrate / design context,
never hard-coded here.
"""

from collections.abc import Iterable, Sequence

import shapely
import shapely.affinity
from jitx.anchor import Anchor
from jitx.feature import Courtyard, Silkscreen
from jitx.landpattern import Pad, PadShape
from jitx.shapes.composites import rectangle
from jitx.shapes.primitive import Circle, Text
from jitx.shapes.shapely import ShapelyGeometry
from jitxlib.landpatterns import LineWidthContext, SoldermaskRegistrationContext
from jitxlib.landpatterns.pads import SMDPad
from jitxlib.landpatterns.silkscreen import SilkscreenSoldermaskClearanceContext

# IPC-7351B nominal-density courtyard excess for SMT connectors / switches
# (0.25 mm). The vendor drawings give no courtyard; this is the labelled rule.
COURTYARD_EXCESS = 0.25

Point = tuple[float, float]


def smd_pad(width: float, height: float, x: float, y: float) -> SMDPad:
    """A rectangular SMD pad centred at (x, y); mask/paste from context."""
    return SMDPad(rectangle(width, height)).at(x, y)


def rect_at(width: float, height: float, x: float, y: float) -> shapely.Polygon:
    """Axis-aligned shapely rectangle centred at (x, y) (component frame)."""
    return shapely.box(x - width / 2, y - height / 2, x + width / 2, y + height / 2)


def pad_copper(pad: Pad) -> shapely.geometry.base.BaseGeometry:
    """A pad's copper in the landpattern frame, read from the pad itself."""
    if pad.transform is None:
        raise ValueError(f"pad {pad} has no placement")
    shape = pad.shape.shape if isinstance(pad.shape, PadShape) else pad.shape
    x, y = pad.transform.translation
    return shapely.affinity.translate(shape.to_shapely().g, x, y)


def silkscreen_outline(
    polylines: Sequence[Sequence[Point]], pads: Iterable[Pad]
) -> Silkscreen:
    """Silkscreen lines, clipped away from every pad's soldermask opening.

    Each pad's copper is grown by the soldermask registration plus the
    substrate's silk-to-mask spacing before being subtracted.
    """
    width = LineWidthContext.get().line_width
    keepaway = (
        SoldermaskRegistrationContext.get().soldermask_registration
        + SilkscreenSoldermaskClearanceContext.get().clearance
        + width / 2
    )
    lines = shapely.MultiLineString([list(pl) for pl in polylines]).buffer(
        width / 2, cap_style="flat", join_style="mitre"
    )
    masked = shapely.unary_union(
        [pad_copper(p).buffer(keepaway, join_style="mitre") for p in pads]
    )
    return Silkscreen(ShapelyGeometry(lines.difference(masked)))


def courtyard_around(body: Iterable[shapely.Polygon], pads: Iterable[Pad]) -> Courtyard:
    """Rectangular courtyard: bounds of body + pad copper + ``COURTYARD_EXCESS``."""
    geoms = [*body, *(pad_copper(p) for p in pads)]
    minx, miny, maxx, maxy = shapely.unary_union(geoms).bounds
    e = COURTYARD_EXCESS
    return Courtyard(
        rectangle(maxx - minx + 2 * e, maxy - miny + 2 * e, anchor=Anchor.SW).at(
            minx - e, miny - e
        )
    )


def pin1_dot(x: float, y: float) -> Silkscreen:
    """Filled silkscreen dot marking pin 1, sized to the silkscreen line width."""
    width = LineWidthContext.get().line_width
    return Silkscreen(Circle(diameter=2.5 * width).at(x, y))


def refdes_text(x: float, y: float, size: float = 0.8) -> Silkscreen:
    """Reference-designator text (``>REF`` is substituted at export)."""
    return Silkscreen(Text(">REF", size, Anchor.S).at(x, y))
