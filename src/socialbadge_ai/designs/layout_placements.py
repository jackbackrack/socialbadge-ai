"""Round-trip component placements through a JSON layout file.

Call :py:func:`layout_placements` while the design is being constructed,
after its circuit has been created::

    class MyDesign(Design):
        board = MyBoard()
        circuit = Main()

        def __init__(self):
            layout_placements("layout.json")

The file format is this module's own (there is no ``jitx.layout_input`` in
jitx 4.4/4.5 to defer to): a JSON object with an optional ``board_shape``
(``{"type": "rectangle"|"polygon", ...}``), a ``components`` list of
``{"id": <path relative to the design>, "placement": {"center", "angle",
"side", "flip_x"}}``, and a ``routes`` list of route sketches:

    {"source": <port or pad path>,
     "destination": <port or pad path>,
     "layer": <int>,
     "sketch": {"start": [x, y], "turns": [[x, y], ...], "end": [x, y]}}

Each component and via may carry ``"fixed": true`` (placed by the design
code with ``.at()``); fixed entries are written for reference and skipped on
import, so the code placement always wins. A ``vias`` list holds
``{"id", "def_name", "pose": {"center", "angle", "flip_x", "side"},
"start_layer", "stop_layer", "net", "fixed"}``: an ``id`` naming a design via
moves it; any other ``id`` is a via the layout tool added, created from the
substrate's ``def_name`` via definition on the named ``net``.

``sketch`` may also be a bare list of >= 2 points (``[start, *turns, end]``),
and may be omitted for a route with no path hint. ``source``/``destination``
are paths the same way a component's ``id`` is, but to a ``Port`` or ``Pad``
rather than a component. Coordinates throughout are absolute board mm,
matching everything else in the file. A route sketch is a hint for JITX's own
routing engine, not a resolved copper path -- see
:py:class:`~jitx.circuit.Route.Sketch`.

An optional ``ref_designators`` list holds poses for reference-designator (or
other) silkscreen text labels, one entry per mark:
``{"id": <path, matching design_report.py's per-component "silkscreen[].id">,
"position": [x, y], "angle": <degrees>}``, with ``position``/``angle`` in
absolute board coordinates like everything else here. Reference designators
are plain silkscreen objects and can be set directly, the same way a
component's placement can (confirmed with JITX directly) -- despite being a
class-level declarative field (``reference_designator = Silkscreen(...)`` on
a landpattern, not an instance attribute set in ``__init__`` like a pad or a
via), this resolves and repositions fine via the same ``parse_refpath`` +
``.at(...)`` this module already uses elsewhere -- verified end to end
against a real, previously-built design: position and rotation both land
correctly and survive capture. (An *unestablished*, first-ever-built
throwaway design hit "Encountered a deferred instantiable attribute on an
instantiated object" attempting the same resolution; that looks like a
first-build/stabilization quirk specific to a brand new design name, not a
property of silkscreen features as a category -- if a producer somehow hits
that same error on a design that has never built before, retry once it has.)
A mark's ``shape``, unlike its exported absolute pose, lives in its owning
component's landpattern-local frame, so the importer converts the absolute
pose into that frame using the inverse of the owning component's own board
placement (looked up by the longest matching id prefix among this file's own
``components`` entries) -- which also correctly accounts for a bottom-side
mirror.

Written by :py:func:`layout_placements` itself (see ``_write_layout``) and
read back the same way, so any producer just needs to match that shape.
"""

from __future__ import annotations

import json
import re
from logging import getLogger
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jitx import current
from jitx._structural import Proxy  # same as design_report.py: real class of a proxied instance
from jitx.circuit import Route
from jitx.component import Component
from jitx.constraints import Tag, Tags
from jitx.inspect import visit
from jitx.landpattern import Pad
from jitx.layerindex import Side
from jitx.net import Net, Port, SubNet
from jitx.placement import Placement
from jitx.refpath import Item, RefPath
from jitx.shapes import Shape
from jitx.shapes.composites import rectangle
from jitx.shapes.primitive import Polygon
from jitx.transform import Point, Transform
from jitx.via import Via
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
    # Every component's board-absolute placement, fixed (code-placed) or not,
    # keyed by its id -- used below to convert ref-designator poses (given in
    # absolute board coordinates) into each mark's landpattern-local frame.
    component_placements: dict[str, Placement] = {}
    for entry in data.get("components", ()):
        name = entry["id"]
        placement = entry.get("placement")
        if placement is None:
            continue
        side = _SIDES[str(placement["side"]).lower()]
        pose = Placement(
            _parse_point(placement["center"]),
            float(placement.get("angle", 0.0)),
            on=side,
        )
        component_placements[name] = pose
        if entry.get("fixed"):
            continue  # code placement wins
        try:
            component = parse_refpath(name).access(design)
        except (AttributeError, LookupError, ValueError) as e:
            logger.error("Unable to find %s in layout: %s", name, e)
            continue
        design.circuit.place(component, pose)
    _import_vias(design, data.get("vias", ()))
    for entry in data.get("routes", ()):
        try:
            source = parse_refpath(entry["source"]).access(design)
            destination = parse_refpath(entry["destination"]).access(design)
        except (AttributeError, LookupError, ValueError) as e:
            logger.error(
                "Unable to find route endpoint %s -> %s in layout: %s",
                entry.get("source"),
                entry.get("destination"),
                e,
            )
            continue
        design.circuit += Route(
            source, destination, int(entry["layer"]), sketch=_parse_sketch(entry.get("sketch"))
        )
    _import_ref_designators(design, data.get("ref_designators", ()), component_placements)


def _owning_component(mark_id: str, component_placements: Mapping[str, Placement]) -> str | None:
    """The id in ``component_placements`` that owns ``mark_id``, i.e. the
    longest one of which ``mark_id`` is a dotted/indexed child (mirrors
    design_report.py's own ``_owner``/``_child`` convention)."""
    owners = [
        c
        for c in component_placements
        if mark_id != c and mark_id.startswith((f"{c}.", f"{c}["))
    ]
    return max(owners, key=len, default=None)


def _import_ref_designators(
    design: Any, entries: Any, component_placements: Mapping[str, Placement]
) -> None:
    """Apply a pose to a reference-designator (or other) silkscreen mark, by
    resolving its path (see this module's own docstring) and repositioning
    its shape -- the same `parse_refpath` + `.at(...)` approach used for
    routes and vias, which turns out to work for this too, despite being a
    class-level declarative field rather than an instance attribute.

    ``entry["position"]``/``entry["angle"]`` are absolute board coordinates
    (matching every other pose in this file), but a mark's ``shape`` lives in
    its owning component's landpattern-local frame -- so the absolute pose is
    converted into that frame via the inverse of the owning component's own
    board placement (which also accounts for a bottom-side mirror) before
    being applied.
    """
    for entry in entries:
        mark_id = entry["id"]
        try:
            mark = parse_refpath(mark_id).access(design)
        except (AttributeError, LookupError, ValueError) as e:
            logger.error("Unable to find ref designator mark %s in layout: %s", mark_id, e)
            continue
        owner_id = _owning_component(mark_id, component_placements)
        if owner_id is None:
            logger.error("Unable to find owning component of ref designator mark %s", mark_id)
            continue
        angle = float(entry.get("angle", 0.0))
        absolute = Transform(_parse_point(entry["position"]), angle)
        local_target = (~component_placements[owner_id]) * absolute
        # `Shape.at(t)` sets the new transform to `t * self.transform` (an
        # *additional* positioning transform), not a replacement -- so the
        # mark's own already-authored local offset/rotation has to be backed
        # out first, or it would double up on top of `local_target`.
        delta = local_target * ~mark.shape.transform
        mark.shape = mark.shape.at(delta)


def _parse_sketch(entry: Any) -> Route.Sketch | list[Point] | None:
    if entry is None:
        return None
    if isinstance(entry, list):
        return [_parse_point(p) for p in entry]
    return Route.Sketch(
        Route.Sketch.Terminal(_parse_point(entry["start"])),
        [_parse_point(p) for p in entry.get("turns", ())],
        Route.Sketch.Terminal(_parse_point(entry["end"])),
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
            entry["fixed"] = True
        components.append(entry)
    routes = _route_entries(design)
    vias = _via_entries(design)
    with open(path, "w") as file:
        json.dump(
            {
                "board_shape": _board_entry(design.board.shape),
                "components": components,
                "vias": vias,
                "routes": routes,
            },
            file,
            indent=2,
        )
        file.write("\n")


class LayoutToolVia(Tag):
    """Marks a via created from a layout file: it is the layout tool's (free,
    not code-placed) and keeps the tool's ``layout_id`` so the next export
    round-trips it under the same id."""

    def __init__(self, layout_id: str) -> None:
        super().__init__()
        self.layout_id = layout_id


def layout_tool_via_id(via: Via) -> str | None:
    """The layout-file id of a via created by :py:func:`layout_placements`,
    or ``None`` for a via the design code declared."""
    tags = Tags.get(via)
    for tag in tags.tags if tags is not None else ():
        if isinstance(tag, LayoutToolVia):
            return tag.layout_id
    return None


def _via_nets(design: Any) -> dict[int, Net]:
    nets: dict[int, Net] = {}
    for _, net in visit(design, Net):
        if not isinstance(net, Net) or isinstance(net, SubNet):
            continue  # bundle sub-nets carry no vias
        for member in net.connected:
            if isinstance(member, Via):
                nets.setdefault(id(member), net)
    return nets


def _layer_index(design: Any, layer: int | None) -> int | None:
    """Normalize a (possibly negative, from-the-bottom) layer index the way
    the design-report exporter does: 0 is the top conductor."""
    if layer is None:
        return None
    return layer % len(design.substrate.stackup.conductors)


def _via_entries(design: Any) -> list[dict[str, Any]]:
    nets = _via_nets(design)
    entries: list[dict[str, Any]] = []
    for trace, via in visit(design, Via):
        if via.transform is None:
            continue
        xform: Transform = via.transform
        if trace.transform is not None:
            xform = trace.transform * xform
        net = nets.get(id(via))
        tool_id = layout_tool_via_id(via)
        entries.append(
            {
                "id": tool_id if tool_id is not None else str(trace.path),
                "def_name": Proxy.type(via).__name__,
                "pose": _placement_entry(xform),
                "start_layer": _layer_index(design, via.start_layer),
                "stop_layer": _layer_index(design, via.stop_layer),
                "net": net.name if net is not None else None,
                "fixed": tool_id is None,
            }
        )
    return entries


def _via_types(design: Any) -> dict[str, type[Via]]:
    types: dict[str, type[Via]] = {}
    substrate = Proxy.type(design.substrate)
    for name in dir(substrate):
        obj = getattr(substrate, name, None)
        if isinstance(obj, type) and issubclass(obj, Via):
            types.setdefault(obj.__name__, obj)
    for _, via in visit(design, Via):
        cls = Proxy.type(via)
        types.setdefault(cls.__name__, cls)
    return types


def _names_design_object(design: Any, path: RefPath) -> bool:
    """Whether ``path`` starts at an attribute of the design (e.g.
    ``circuit...``), as opposed to a layout tool's own via name."""
    steps = list(path.steps)
    if not steps or not isinstance(steps[0], str):
        return False
    return hasattr(design, steps[0])


def _import_vias(design: Any, entries: Any) -> None:
    """Move free design vias and create the vias the layout tool added."""
    types: dict[str, type[Via]] | None = None
    nets: dict[str, Net] | None = None
    for entry in entries:
        if entry.get("fixed"):
            continue  # code placement wins
        pose = entry["pose"]
        side = _SIDES[str(pose.get("side", "Top")).lower()]
        center = _parse_point(pose["center"])
        angle = float(pose.get("angle", 0.0))
        layout_id = str(entry["id"])
        try:
            path = parse_refpath(layout_id)
        except ValueError:
            path = None
        if path is not None and _names_design_object(design, path):
            # The id is a path into the design. A design via found there is
            # moved; one that doesn't exist yet is a via the backend
            # (reverse-flow linker / router) synthesizes during capture, e.g.
            # "circuit.usb._Capture__link.vias[0]" -- echoed back by the
            # layout tool, not something to create (that duplicates it).
            try:
                existing = path.access(design)
            except (AttributeError, LookupError, ValueError):
                existing = None
            if isinstance(existing, Via):
                existing.at(center, on=side, rotate=angle)
            else:
                logger.debug("Skipping layout via %s: not a pre-capture design via", layout_id)
            continue
        if types is None:
            types = _via_types(design)
            nets = {
                n.name: n
                for _, n in visit(design, Net)
                if isinstance(n, Net) and not isinstance(n, SubNet) and n.name
            }
        assert nets is not None
        cls = types.get(str(entry.get("def_name")))
        net = nets.get(str(entry.get("net")))
        if cls is None or net is None:
            logger.error(
                "Skipping layout via %s: unknown via definition %r or net %r",
                entry.get("id"),
                entry.get("def_name"),
                entry.get("net"),
            )
            continue
        via = cls().at(center, on=side, rotate=angle)
        LayoutToolVia(layout_id).assign(via)
        net += via
        design.circuit += via


def _route_entries(design: Any) -> list[dict[str, Any]]:
    routes = list(visit(design, Route))
    if not routes:
        return []
    # Only every port/pad gets a stable path; a route may end on either.
    endpoint_paths: dict[int, str] = {}
    for trace, port in visit(design, Port):
        endpoint_paths.setdefault(id(port), str(trace.path))
    for trace, pad in visit(design, Pad):
        endpoint_paths.setdefault(id(pad), str(trace.path))

    entries: list[dict[str, Any]] = []
    for trace, route in routes:
        xform = trace.transform
        source = endpoint_paths.get(id(route.source))
        destination = endpoint_paths.get(id(route.destination))
        if source is None or destination is None:
            logger.warning(
                "Skipping route %s: endpoint is not a plain Port/Pad (Via or"
                " RouteConnectionEndpoint), which this format can't reference yet",
                trace.path,
            )
            continue
        entry: dict[str, Any] = {
            "id": str(trace.path),
            "source": source,
            "destination": destination,
            "layer": route.layer,
        }
        if route.sketch is not None:
            points = route.sketch._points()
            if xform is not None:
                points = [xform * p for p in points]
            entry["sketch"] = {
                "start": list(points[0]),
                "turns": [list(p) for p in points[1:-1]],
                "end": list(points[-1]),
            }
        entries.append(entry)
    return entries


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
