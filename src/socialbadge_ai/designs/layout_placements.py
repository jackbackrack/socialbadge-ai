"""Round-trip component placements through a JSON layout file.

Call :py:func:`layout_placements` while the design is being constructed,
after its circuit has been created::

    class MyDesign(Design):
        board = MyBoard()
        circuit = Main()

        def __init__(self):
            layout_placements("layout.json")

The file format is the one read by ``jitx.layout_input.LayoutInput``, with
component ids being paths relative to the current design.
"""

from __future__ import annotations

import json
import re
from logging import getLogger
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jitx import current
from jitx.component import Component
from jitx.inspect import visit
from jitx.layerindex import Side
from jitx.placement import Placement
from jitx.refpath import Item, RefPath
from jitx.shapes import Shape
from jitx.shapes.composites import rectangle
from jitx.shapes.primitive import Polygon
from jitx.transform import Point, Transform
from shapely.geometry import Polygon as ShapelyPolygon

logger = getLogger(__name__)

_SIDES = {"top": Side.Top, "bottom": Side.Bottom}
# attribute name, or a bracketed index / quoted mapping key
_STEP = re.compile(r"\.?([A-Za-z_][A-Za-z0-9_]*)|\[([^\]]*)\]")


def parse_refpath(text: str) -> RefPath:
    """Parse a path the way :py:class:`~jitx.refpath.RefPath` prints itself.

    Quoted keys may not contain quotes or square brackets.

    >>> parse_refpath("a.b[0]['x'].c")
    RefPath(('a', 'b', 0, Item('x'), 'c'))
    """
    steps: list[str | int | Item] = []
    pos = 0
    while pos < len(text):
        m = _STEP.match(text, pos)
        if m is None or (m.group(0).startswith(".") and not steps):
            raise ValueError(f"Unable to parse path {text!r} at position {pos}")
        attr, index = m.groups()
        if attr is not None:
            steps.append(attr)
        else:
            index = index.strip()
            if len(index) >= 2 and index[0] == index[-1] and index[0] in "'\"":
                steps.append(Item(index[1:-1]))
            else:
                steps.append(int(index))
        pos = m.end()
    return RefPath(steps)


def layout_placements(filename: str | Path) -> None:
    """Apply placements from a layout file, and write the current placements.

    If ``filename`` exists, each component it lists is placed in the current
    design's circuit, and its board shape, if any, replaces the shape of the
    design's board. Regardless, a file with ``-input`` appended to the stem
    of ``filename`` is written with the board shape and every component in the
    current design, with its board placement if it has one.

    Args:
        filename: Path to the layout JSON file.
    """
    path = Path(filename)
    design = current.design
    _write_layout(path.with_name(f"{path.stem}-input{path.suffix}"))
    if not path.exists():
        return
    with open(path) as file:
        data = json.load(file)
    board = data.get("board_shape")
    if board is not None:
        design.board.shape = _parse_board(board)
    for entry in data.get("components", ()):
        name = entry["id"]
        placement = entry["placement"]
        try:
            component = parse_refpath(name).access(design)
        except (AttributeError, LookupError, ValueError) as e:
            logger.error("Unable to find %s in layout: %s", name, e)
            continue
        side = _SIDES[str(placement["side"]).lower()]
        design.circuit.place(
            component,
            Placement(
                _parse_point(placement["center"]),
                float(placement.get("angle", 0.0)),
                on=side,
            ),
        )


def _write_layout(path: Path) -> None:
    design = current.design
    components: list[dict[str, Any]] = []
    for trace, component in visit(design, Component):
        entry: dict[str, Any] = {"id": str(trace.path)}
        if component.transform is not None:
            xform: Transform = component.transform
            if trace.transform is not None:
                xform = trace.transform * xform
            entry["placement"] = _placement_entry(xform)
        components.append(entry)
    with open(path, "w") as file:
        json.dump(
            {"board_shape": _board_entry(design.board.shape), "components": components},
            file,
            indent=2,
        )
        file.write("\n")


def _board_entry(shape: Shape) -> dict[str, Any]:
    # arcs are discretized, holes are dropped as the format has none
    geometry = shape.to_shapely().g
    if not isinstance(geometry, ShapelyPolygon):
        raise ValueError(f"Board shape is not a single polygon: {geometry.geom_type}")
    return {
        "type": "polygon",
        "points": [[x, y] for x, y in geometry.exterior.coords[:-1]],
    }


def _parse_point(value: Any) -> Point:
    if isinstance(value, Mapping):
        return float(value["x"]), float(value["y"])
    x, y = value
    return float(x), float(y)


def _parse_board(entry: Mapping[str, Any]) -> Shape:
    kind = entry.get("type")
    if kind == "rectangle":
        shape = rectangle(float(entry["width"]), float(entry["height"]))
    elif kind == "polygon":
        shape = Polygon([_parse_point(point) for point in entry["points"]])
    else:
        raise ValueError(f"Unknown board shape in layout: {kind!r}")
    center = entry.get("center")
    return shape.at(_parse_point(center)) if center else shape


def _placement_entry(xform: Transform) -> dict[str, Any]:
    (x, y), angle, (sx, sy) = xform.trs
    mirrored = sx * sy < 0
    if isinstance(xform, Placement):
        side = xform.side
    else:
        side = Side.Bottom if mirrored else Side.Top
    return {
        "center": [x, y],
        "angle": angle,
        "side": "Top" if side is Side.Top else "Bottom",
        "flip_x": mirrored,
    }
