"""Reverse-flow design report: per-component/per-net placements, pads,
courtyards, nets, short traces, vias, copper pours, modules and the board outline. Each
component carries both its captured layout placement and the placement the
design code declared, so a consumer can tell code intent from editor moves.

Ported from internal-test-designs' `internal_test_designs.plugins.DesignReport`
so it runs in this project's own venv against its own (newer) jitx/jitxlib
stack, instead of depending on that other project's venv staying in sync.

Usage (from the project root, with .venv active):

    python scripts/design_report.py <module.path.DesignClass> [output_stem]

Writes <output_stem>.txt and <output_stem>.json (default stem:
"design-report-<design-name-slug>").
"""

from __future__ import annotations

import dataclasses
import importlib
import json
import math
import sys
import textwrap
from collections import defaultdict
from collections.abc import Mapping
from enum import Enum
from typing import Any

import jitx
import shapely
from jitx._structural import Proxy
from jitx.anchor import Anchor
from jitx.circuit import Circuit, InstancePlacement, Route
from jitx.component import Component
from jitx.constraints import (
    AndExpr,
    AtomExpr,
    BinaryDesignConstraint,
    BoolExpr,
    BuiltinTag,
    DesignConstraint,
    NotExpr,
    OnLayer,
    OrExpr,
    Tag,
    Tags,
    TrueExpr,
    UnaryDesignConstraint,
)
from jitx.copper import Copper, Pour
from jitx.feature import Courtyard
from jitx.inspect import extract, visit
from jitx.landpattern import Landpattern, Pad, PadMapping
from jitx.net import Net, Port, ShortTrace
from jitx.placement import Placement
from jitx.run.runtime import RuntimeDesign
from jitx.shapes import primitive
from jitx.shapes.shapely import ShapelyGeometry
from jitx.si import Constrain, RoutingStructureConstraint
from jitx.transform import Transform
from jitx.via import Via

DIGITS = 6  # coordinate precision
WIDTH = 96  # wrap width for pad lists


def _text_bounds(text: primitive.Text) -> tuple[float, float, float, float]:
    lines = text.string.split("\n")
    width = max(len(line) for line in lines) * text.size * 0.6
    height = len(lines) * text.size
    match text.anchor.horizontal():
        case Anchor.W:
            x0 = 0.0
        case Anchor.E:
            x0 = -width
        case _:
            x0 = -width / 2
    match text.anchor.vertical():
        case Anchor.S:
            y0 = 0.0
        case Anchor.N:
            y0 = -height
        case _:
            y0 = -height / 2
    return (x0, y0, x0 + width, y0 + height)


def _shapely_from_shape(shape) -> ShapelyGeometry:
    if isinstance(shape.geometry, primitive.Text):
        return ShapelyGeometry(shapely.box(*_text_bounds(shape.geometry))).apply(shape.transform)
    return ShapelyGeometry.from_shape(shape, tolerance=1e-3)


def _out_path(design: RuntimeDesign, stem: str, ext: str = "json") -> str:
    slug = "".join(c if c.isalnum() or c in "-_." else "-" for c in design.name)
    return f"{stem}-{slug}.{ext}"


def _rings(g) -> list[dict]:
    def ring(coords):
        return [[round(x, DIGITS), round(y, DIGITS)] for x, y in coords]

    if g.is_empty:
        return []
    if isinstance(g, shapely.Polygon):
        return [
            {
                "outer": ring(g.exterior.coords[:-1]),
                "holes": [ring(h.coords[:-1]) for h in g.interiors],
            }
        ]
    if isinstance(g, shapely.LineString):
        return [{"outer": ring(g.coords), "holes": []}]
    if hasattr(g, "geoms"):
        return [r for part in g.geoms for r in _rings(part)]
    return []


def _polys(shape, where) -> list[dict]:
    try:
        return _rings(_shapely_from_shape(shape).g)
    except Exception as e:
        print(f"skipping unconvertible shape at {where}: {shape.geometry!r} ({e})")
        return []


def _as_shape(x):
    """Wrap a bare `Primitive` (e.g. a class-level `shape = Circle(...)`) into
    a proper `Shape(geometry, transform)`, which is what `_shapely_from_shape`
    and the rest of this module expect. A `Shape` is returned as-is."""
    from jitx.shapes import Shape as JitxShape
    from jitx.transform import IDENTITY

    return x if isinstance(x, JitxShape) else JitxShape(x, IDENTITY)


def _member(obj, name: str) -> Any:
    """`obj.name`, calling it if it is a method. `RuntimeDesign.nets` and
    `.layers` are plain methods in jitx 4.4 and properties from 4.5 on, so this
    keeps the script working on either side of that change."""
    value = getattr(obj, name)
    return value() if callable(value) else value


def _declared_board_shape(design_cls: type | None):
    """The board's shape exactly as declared in source, bypassing the runtime
    translate step -- which currently collapses any non-rectangular board
    shape down to its axis-aligned bounding rectangle (confirmed against
    jitx 4.5.0a5: true even for an explicit many-sided polygon, so it isn't
    specific to the `Circle` primitive). `design_cls.board` is a lazily
    resolved `Instantiable` wrapper rather than a plain `Board` instance, so
    this reaches into its private `_Instantiable__instantiable` to recover the
    original `Board` subclass and read its `shape` class attribute directly --
    a plain Python object, never touched by the runtime. Returns None (falling
    back to the runtime's, possibly-degraded, shape) if that internal ever
    changes shape in a future jitx release.
    """
    if design_cls is None:
        return None
    try:
        board_cls = design_cls.board._Instantiable__instantiable
        return board_cls.shape
    except Exception:
        return None


def _circle_entry(shape) -> dict | None:
    """`shape`'s native JSON entry if it is (or wraps) a bare `Circle`, else
    None. Distinct from `_polys`, which always discretizes into a polygon --
    this preserves exact circularity for a consumer that wants it."""
    from jitx.shapes.primitive import Circle

    shape = _as_shape(shape)
    if not isinstance(shape.geometry, Circle):
        return None
    (cx, cy), _angle, _scale = shape.transform.trs
    return {
        "type": "circle",
        "center": [round(cx, DIGITS), round(cy, DIGITS)],
        "diameter": round(shape.geometry.diameter, DIGITS),
    }


def _extent(polys) -> list[float] | None:
    points = [p for poly in polys for p in poly["outer"]]
    if not points:
        return None
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return [min(xs), min(ys), max(xs), max(ys)]


def _stackup_entries(stackup: Any) -> list[dict]:
    """Every conductor layer, top to bottom, index 0..N-1 matching the layer
    numbers everywhere else in this file (pad/via/pour/route "layer"
    fields). jitx's own Conductor/Stackup classes have no notion of "signal"
    vs. "plane" layer -- that's a per-design usage convention, not a stackup
    property, so a consumer wanting that distinction should look at which
    layers this design's pours/routes actually land on (both already in this
    report) rather than expect it here. This is the physical layer list: what
    layer indices exist and what they're made of."""
    conductors = stackup.conductors
    n = len(conductors)
    entries = []
    for i, conductor in enumerate(conductors):
        side = "top" if i == 0 else "bottom" if i == n - 1 else "inner"
        entries.append(
            {
                "layer": i,
                "side": side,
                "name": conductor.name,
                # jitx: "If not specified, the name of the class is used."
                "material": conductor.material_name or Proxy.type(conductor).__name__,
                "thickness": conductor.thickness,
            }
        )
    return entries


def _pose(xform: Transform | None) -> dict | None:
    if xform is None:
        return None
    (x, y), angle, (sx, _) = xform.trs
    pose = {
        "center": [round(x, DIGITS), round(y, DIGITS)],
        "angle": round(angle, DIGITS),
        "flip_x": sx < 0,
    }
    if isinstance(xform, Placement):
        pose["side"] = xform.side.name
    return pose


def _compose(*xforms: Transform | None) -> Transform | None:
    result = None
    for xform in xforms:
        if xform is None:
            return None
        result = xform if result is None else result * xform
    return result


def _value(value) -> str | None:
    if value is None:
        return None
    try:
        return format(value, "~P")
    except (TypeError, ValueError):
        return str(value)


def _owner(path: str, candidates) -> str | None:
    enclosing = [
        c
        for c in candidates
        if c != path and (path.startswith(f"{c}.") or path.startswith(f"{c}["))
    ]
    return max(enclosing, key=len, default=None)


def _child(base: str, name: str) -> str:
    return base + name if name.startswith("[") else f"{base}.{name}"


def _padshapes(coppers, where) -> list[dict]:
    groups: dict[str, tuple[list[dict], list[int]]] = {}
    for copper in coppers:
        polys = _polys(copper.shape, where)
        groups.setdefault(json.dumps(polys, sort_keys=True), (polys, []))[1].append(copper.layer)
    return [{"shape": p, "layers": sorted(ls)} for p, ls in groups.values()]


def declared_placements(design: RuntimeDesign) -> dict[str, dict]:
    """How the design code placed each component and module, keyed by path.
    Call this after `submit` and BEFORE `capture`: capture overwrites
    transforms with the layout tool's result, editor moves included.

    Each entry is {"placed_by", "fixed", "relative", "pose"}:
      * "fixed": True only for a GLOBAL `.at(...)` placement - the component's
        own transform, with no floating circuit between it and the board. Its
        pose is design intent; a layout tool should hold it.
      * "relative": {"to": <component or module path>, "pose": offset} for a
        placement that is rigid with respect to something that can itself
        move: `circuit.place(x, ..., relative_to=anchor)`, or `.at(...)` inside
        a floating circuit (`circuit.at(floating=True)`, or a subcircuit that
        was itself `place`d). "pose" is in the anchor's frame; a layout tool
        should lock the two together with that offset.
      * `circuit.place(x, ...)` with no anchor, inside a circuit that is on the
        board frame, is neither: a layout replayed from a file lands here, and
        it is a user placement, so it is free to move (fixed False, relative
        None) with its requested pose as the starting point.
      * "pose": absolute board pose where it can be resolved from code (a
        chain of relative placements ending at the board), else None.
    Components and modules the code left alone are absent.
    """
    circuits: dict[str, Circuit] = {str(t.path): c for t, c in visit(design.root, Circuit)}
    comps: dict[str, Component] = {str(t.path): c for t, c in visit(design.root, Component)}
    paths: dict[int, str] = {id(o): p for p, o in (*circuits.items(), *comps.items())}
    circuit_paths = list(circuits)

    def frame(path: str, local: Transform | None) -> tuple[str | None, Transform | None]:
        """(anchor, pose relative to it) for `local` expressed in the frame of the
        circuit that owns `path`: walk up until the board (anchor None) or the
        first floating circuit (its frame is the anchor)."""
        xform = local
        owner = _owner(path, circuit_paths)
        while owner is not None:
            parent = circuits[owner].transform
            if parent is None:
                return owner, xform
            xform = _compose(parent, xform)
            owner = _owner(owner, circuit_paths)
        return None, xform

    entries: dict[str, dict] = {}
    for path, comp in comps.items():
        if comp.transform is None:
            continue
        anchor, xform = frame(path, comp.transform)
        entries[path] = {
            "placed_by": "at",
            "fixed": anchor is None,
            "relative": None if anchor is None else {"to": anchor, "pose": _pose(xform)},
            "local": (anchor, xform),
        }

    for trace, request in visit(design.root, InstancePlacement):
        target = request.instance()
        if target is None or id(target) not in paths:
            continue
        path = paths[id(target)]
        other = request.relative_to() if request.relative_to is not None else None
        if other is not None and id(other) in paths:
            anchor, xform = paths[id(other)], request.placement
        else:
            anchor, xform = frame(str(trace.path), request.placement)
        entries[path] = {
            "placed_by": "place",
            "fixed": False,
            "relative": None if anchor is None else {"to": anchor, "pose": _pose(xform)},
            "local": (anchor, xform),
        }

    # Absolute pose: follow each relative chain to the board. A floating
    # module that nothing places has no code pose, so its chain is None.
    absolute: dict[str, Transform | None] = {}

    def resolve(path: str, seen: frozenset[str] = frozenset()) -> Transform | None:
        if path in absolute:
            return absolute[path]
        entry = entries.get(path)
        if entry is None or path in seen:
            return None
        anchor, xform = entry["local"]
        base = None if anchor is None else resolve(anchor, seen | {path})
        result = xform if anchor is None else _compose(base, xform)
        absolute[path] = result
        return result

    for path, entry in entries.items():
        entry["pose"] = _pose(resolve(path))
        del entry["local"]
    # Floating modules are anchors for their children even when nothing places
    # them; record that before capture gives them a transform.
    for path, circuit in circuits.items():
        if circuit.transform is None:
            entries.setdefault(
                path,
                {"placed_by": None, "fixed": False, "relative": None, "pose": None},
            )["floating"] = True
    return entries


def declared_pour_shapes(design: RuntimeDesign) -> dict[int, Any]:
    """Every `Pour`'s shape exactly as declared in code, keyed by `id(pour)`.
    Call this after `submit` and BEFORE `capture`: capture replaces a pour's
    `.shape` with the router's computed fill (copper minus isolation gaps
    around every via/pad it had to avoid, often split into many pieces with
    holes) -- useful for a real board render, but large, and not something a
    consumer doing its own fill (e.g. a different pour algorithm, or one that
    hasn't placed vias yet) can use as an input. Pour identity survives
    capture, so `id(pour)` before and after refer to the same pour.

    A pour the reverse-flow linker synthesizes during capture itself (rather
    than one the design declared) has no entry here -- there is no "before"
    for it, declared and computed are the same thing.
    """
    shapes: dict[int, Any] = {}
    for _trace, pour in design.query(Pour):
        shapes.setdefault(id(pour), pour.shape)
    for _trace, net in visit(design.root, Net):
        for member in net._connected:
            if isinstance(member, Pour):
                shapes.setdefault(id(member), member.shape)
    return shapes


def _tag_label(tag: Tag) -> str:
    """A tag's name: its class name, or the member name for a built-in tag
    (`IsPad`, `IsVia`, ...)."""
    return tag.value if isinstance(tag, BuiltinTag) else repr(tag)


def _tag_names(*objs) -> list[str]:
    """Tags assigned directly to any of `objs` (`SomeTag().assign(obj)`), by
    tag class name. jitx stores them as a `Tags` property on the object
    itself; a tag on a container (component, circuit, landpattern) also
    applies to every copper object inside it - the export records where
    the tag was assigned and leaves that inheritance to the consumer."""
    names: list[str] = []
    for obj in objs:
        tags = Tags.get(obj)
        if tags is not None:
            names += [_tag_label(t) for t in tags.tags if _tag_label(t) not in names]
    return names


def _tag_type(tag: Tag) -> dict:
    """A tag's place in the tag hierarchy: a rule on a tag also matches every
    subclass of it, so a consumer needs the ancestors to match rules."""
    if isinstance(tag, BuiltinTag):
        return {"parents": [], "doc": None, "builtin": True}
    cls = tag.__class__
    parents = [c.__name__ for c in cls.__mro__[1:] if issubclass(c, Tag) and c is not Tag]
    doc = cls.__doc__ if cls.__doc__ is not Tag.__doc__ else None
    return {"parents": parents, "doc": doc.strip() if doc else None, "builtin": False}


def _jsonable(value):
    """Best-effort JSON form of a constraint effect: dataclasses become dicts,
    classes (e.g. a Via type) their name, enums their value, and anything
    else its str()."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, type):
        return value.__name__
    if isinstance(value, Enum):
        return _jsonable(value.value)
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if dataclasses.is_dataclass(value):
        return {f.name: _jsonable(getattr(value, f.name)) for f in dataclasses.fields(value)}
    return str(value)


def _design_rule(trace, rule: DesignConstraint) -> dict:
    """A `design_constraint(...)` rule: its tag condition(s), as jitx prints
    the boolean expression, and every effect it sets."""
    if isinstance(rule, BinaryDesignConstraint):
        conditions = [rule.first, rule.second]
        effects = {"clearance": rule.clearance_constraint}
    elif isinstance(rule, UnaryDesignConstraint):
        conditions = [rule.condition]
        effects = {
            "trace_width": rule.trace_width_constraint,
            "stitch_via": rule.stitch_via_constraint,
            "fence_via": rule.fence_via_constraint,
            "thermal_relief": rule.thermal_relief_constraint,
            "serpentine_params": rule.serpentine_params_constraint,
            "coupled_pair_params": rule.coupled_pair_params_constraint,
            "pour_feature_size": rule.pour_feature_size_constraint,
            "routing_structure": rule.routing_structure_constraint,
        }
    else:
        conditions, effects = [], {}
    effects = {k: _jsonable(v) for k, v in effects.items() if v is not None}
    return {
        "id": str(trace.path),
        "name": rule.name,
        "priority": rule.priority,
        "kind": "binary" if isinstance(rule, BinaryDesignConstraint) else "unary",
        "conditions": [str(c) for c in conditions],
        "condition_trees": [_expr_tree(c) for c in conditions],
        "effects": effects,
    }


def _expr_tree(expr: BoolExpr) -> dict:
    """A rule condition as a tree a consumer can evaluate without parsing:
    {"tag": name} (plus "layer" for OnLayer), {"not": x}, {"and": [a, b]},
    {"or": [a, b]}, or {"any": true} for a condition that matches everything."""
    if isinstance(expr, AtomExpr):
        node: dict = {"tag": _tag_label(expr.atom)}
        if isinstance(expr.atom, OnLayer):
            node["layer"] = expr.atom.index
        return node
    if isinstance(expr, NotExpr):
        return {"not": _expr_tree(expr.expr)}
    if isinstance(expr, AndExpr):
        return {"and": [_expr_tree(expr.left), _expr_tree(expr.right)]}
    if isinstance(expr, OrExpr):
        return {"or": [_expr_tree(expr.left), _expr_tree(expr.right)]}
    if isinstance(expr, TrueExpr):
        return {"any": True}
    return {"expr": str(expr)}


def _expr_tags(expr: BoolExpr) -> list[Tag]:
    """Every tag named in a rule condition."""
    if isinstance(expr, AtomExpr):
        return [expr.atom]
    if isinstance(expr, NotExpr):
        return _expr_tags(expr.expr)
    if isinstance(expr, AndExpr | OrExpr):
        return _expr_tags(expr.left) + _expr_tags(expr.right)
    return []


# Built-in tags that hold for a routed trace segment of a net.
_TRACE_BUILTINS = frozenset({"IsCopper", "IsTrace"})


def _tag_closure(tags: list[Tag]) -> frozenset[str]:
    """The tag names a trace of a net carrying `tags` matches: each tag, its
    ancestor tags (a rule on a parent tag matches subclasses) and the
    built-in trace tags."""
    names = set(_TRACE_BUILTINS)
    for tag in tags:
        names.add(_tag_label(tag))
        names.update(_tag_type(tag)["parents"])
    return frozenset(names)


def _matches(expr: BoolExpr, names: frozenset[str], layer: int, normalize) -> bool:
    """Whether a rule condition holds for a trace with tag set `names` on
    (normalized) conductor `layer`."""
    if isinstance(expr, AtomExpr):
        if isinstance(expr.atom, OnLayer):
            return normalize(expr.atom.index) == layer
        return _tag_label(expr.atom) in names
    if isinstance(expr, NotExpr):
        return not _matches(expr.expr, names, layer, normalize)
    if isinstance(expr, AndExpr):
        return _matches(expr.left, names, layer, normalize) and _matches(
            expr.right, names, layer, normalize
        )
    if isinstance(expr, OrExpr):
        return _matches(expr.left, names, layer, normalize) or _matches(
            expr.right, names, layer, normalize
        )
    return isinstance(expr, TrueExpr)


def _best(candidates):
    """The winning (value, source) among matching rules: highest priority,
    ties going to the first defined. `candidates` is (priority, value, source)."""
    best = None
    for priority, value, source in candidates:
        if best is None or priority > best[0]:
            best = (priority, value, source)
    return (best[1], best[2]) if best else (None, None)


def _per_layer(values: Mapping[int, float | None]):
    """A per-layer value, compressed: a single number when every layer agrees,
    else {"default": commonest, "<layer>": value, ...} for the layers that
    differ. None when nothing is set."""
    present = {k: v for k, v in values.items() if v is not None}
    if not present:
        return None
    distinct = list(present.values())
    if len(set(distinct)) == 1 and len(present) == len(values):
        return distinct[0]
    common = max(set(distinct), key=distinct.count)
    out: dict[str, float] = {"default": common}
    out.update({str(k): v for k, v in present.items() if v != common})
    return out


# Tag names (or ancestors) that say which face a component belongs on,
# without placing it - e.g. `class BottomSide(Tag)` assigned in a floorplan.
_SIDE_TAGS = {"TopSide": "Top", "BottomSide": "Bottom"}


def _side_hint(comp, declared_pose: dict | None) -> str | None:
    """Which board face the design wants this part on: a TopSide/BottomSide
    tag (or subclass) on the component wins; else the side of its code
    placement; else None (no preference)."""
    tags = Tags.get(comp)
    for tag in tags.tags if tags is not None else []:
        for name in (_tag_label(tag), *_tag_type(tag)["parents"]):
            if name in _SIDE_TAGS:
                return _SIDE_TAGS[name]
    return declared_pose.get("side") if declared_pose else None


def _same_pose(a: dict, b: dict, tol: float = 1e-4) -> bool:
    return (
        math.dist(a["center"], b["center"]) <= tol
        and abs((a["angle"] - b["angle"] + 180) % 360 - 180) <= tol
        and a["flip_x"] == b["flip_x"]
        and a.get("side") == b.get("side")
    )


def _collect(
    design: RuntimeDesign,
    design_cls: type | None = None,
    *,
    geometry: bool,
    declared: dict[str, dict] | None = None,
    declared_pours: dict[int, Any] | None = None,
) -> dict:
    nets: RuntimeDesign.Nets = _member(design, "nets")
    layers: RuntimeDesign.Layers = _member(design, "layers")

    coppers_at = defaultdict(list)
    for trace, copper in design.query(Copper):
        coppers_at[str(trace.path)].append(copper)

    entries: dict[int, dict] = {}

    def net_of(element) -> dict | None:
        group = nets.find(element)
        if group is None:
            return None
        return entries.setdefault(id(group), {"name": group.name, "pads": [], "vias": []})

    def existing_net(element) -> dict | None:
        """The entry of a net already in the export, never adding one - for
        lookups that shouldn't create empty nets (tags, routing structures)."""
        group = nets.find(element)
        return entries.get(id(group)) if group is not None else None

    modules = [
        {
            "id": str(trace.path),
            "def_name": Proxy.type(circuit).__name__,
            "placement": _pose(_compose(trace.transform, circuit.transform)),
            "floating": bool((declared or {}).get(str(trace.path), {}).get("floating")),
            "relative": (declared or {}).get(str(trace.path), {}).get("relative"),
            "tags": _tag_names(circuit),
        }
        for trace, circuit in visit(design.root, Circuit)
    ]
    module_ids = [m["id"] for m in modules]
    for module in modules:
        module["parent_id"] = _owner(module["id"], module_ids)

    components = []
    pad_centers: dict[str, tuple[float, float]] = {}
    pads_of_port: dict[int, list[str]] = defaultdict(list)
    for ctrace, comp in visit(design.root, Component):
        cid = str(ctrace.path)
        placement = _compose(ctrace.transform, comp.transform)
        pose = _pose(placement)
        code = declared.get(cid) if declared is not None else None
        code_pose = code["pose"] if code is not None else None

        port_paths = {id(port): str(t.path) for t, port in visit(comp, Port)}
        port_of_pad = {
            id(pad): port
            for mapping in extract(comp, PadMapping)
            for pad, port in mapping.inverse().items()
        }

        pads = []
        for ptrace, pad in visit(comp, Pad):
            path = str(ptrace.path)
            ref = f"{cid}/{path}"
            local = _compose(ptrace.transform, pad.transform)
            port = port_of_pad.get(id(pad))
            net = net_of(pad) or (net_of(port) if port is not None else None)
            if net is not None:
                net["pads"].append(ref)
            if port is not None:
                pads_of_port[id(port)].append(ref)
            absolute = _compose(placement, local)
            if absolute is not None:
                pad_centers[ref] = absolute.trs[0]
            coppers = coppers_at.get(_child(cid, path), ())
            pads.append(
                {
                    "pin_id": port_paths.get(id(port)) if port is not None else None,
                    "pad_id": path,
                    "name": Proxy.type(pad).__name__,
                    "pose": _pose(local),
                    "net": net["name"] if net else None,
                    "shapes": _padshapes(coppers, ref) if geometry else None,
                    "layers": sorted({c.layer for c in coppers}),
                    "tags": _tag_names(pad),
                }
            )

        courtyard = [
            poly
            for t, feature in visit(comp, Courtyard)
            if t.transform is not None
            for poly in _polys(t.transform * feature.shape, t.path)
        ]
        components.append(
            {
                "id": cid,
                "reference": comp.reference_designator,
                "value": _value(comp.value),
                "mpn": comp.mpn,
                "manufacturer": comp.manufacturer,
                "def_name": Proxy.type(comp).__name__,
                # tags on the component or its landpattern (they tag every pad)
                "tags": _tag_names(comp, *extract(comp, Landpattern)),
                "placement": pose or False,
                # See declared_placements: fixed = global `.at(...)` (hold it);
                # relative = rigid offset from another part or module (lock them
                # together); neither = free to move.
                "fixed": bool(code and code["fixed"]),
                "relative": code["relative"] if code is not None else None,
                "placed_by": code["placed_by"] if code is not None else None,
                # the face the design wants the part on (tag or code placement),
                # independent of where the placer put it - see _side_hint
                "side_hint": _side_hint(comp, code_pose),
                "declared_placement": code_pose,
                "moved_from_declared": None
                if code_pose is None or pose is None
                else not _same_pose(code_pose, pose),
                "courtyard": courtyard if geometry else [],
                "courtyard_extent": _extent(courtyard),
                "pads": pads,
                "module_id": _owner(cid, module_ids),
            }
        )

    vias = []
    for trace, via in visit(design.root, Via):
        ref = str(trace.path)
        net = net_of(via)
        if net is not None:
            net["vias"].append(ref)
        span = [getattr(via, name, None) for name in ("start_layer", "stop_layer")]
        vias.append(
            {
                "id": ref,
                "def_name": Proxy.type(via).__name__,
                "pose": _pose(_compose(trace.transform, via.transform)),
                "start_layer": layers.normalize(span[0]) if span[0] is not None else None,
                "stop_layer": layers.normalize(span[1]) if span[1] is not None else None,
                "net": net["name"] if net else None,
                "tags": _tag_names(via),
            }
        )

    # Resolved routing: real Route objects the router (interactive or auto)
    # has already produced, not the code-authored kind (this design has none
    # of those) -- reverse-flow synthesizes one per routed segment, complete
    # with .traces (the actual copper) once the design has been captured.
    #
    # "sketch" below is doubly provisional: it reads the private
    # `route.sketch._points()` (no public accessor exists), and on top of
    # that, for these reverse-flow-synthesized routes the values it returns
    # are frequently wrong -- segment lengths that don't match the real
    # distance between the resolved endpoints, not just a coordinate-frame
    # issue. These Route objects don't exist at all pre-capture, so this
    # looks like a bug in jitx's own reverse-flow linker. Treat "sketch" as
    # unverified until that's understood; id/net/layer/source/destination
    # are reliable.
    routes = []
    route_objs = list(design.query(Route))
    if route_objs:
        port_paths = {id(p): str(t.path) for t, p in visit(design.root, Port)}
        pad_paths = {id(p): str(t.path) for t, p in visit(design.root, Pad)}
        via_paths = {id(v): str(t.path) for t, v in visit(design.root, Via)}

        def endpoint_ref(obj) -> dict:
            for kind, paths in (("port", port_paths), ("pad", pad_paths), ("via", via_paths)):
                path = paths.get(id(obj))
                if path is not None:
                    return {"kind": kind, "path": path}
            return {"kind": Proxy.type(obj).__name__, "path": None}

        for trace, route in route_objs:
            ref = str(trace.path)
            net = net_of(route.source) or net_of(route.destination)
            sketch = None
            if route.sketch is not None:
                points = route.sketch._points()
                if trace.transform is not None:
                    points = [trace.transform * p for p in points]
                sketch = {
                    "start": list(points[0]),
                    "turns": [list(p) for p in points[1:-1]],
                    "end": list(points[-1]),
                }
            routes.append(
                {
                    "id": ref,
                    "net": net["name"] if net else None,
                    "layer": layers.normalize(route.layer),
                    "source": endpoint_ref(route.source),
                    "destination": endpoint_ref(route.destination),
                    "sketch": sketch,
                }
            )

    # A pour is attached with `net += Pour(...)`, so the reliable way back to
    # its net is the Net whose connections hold it; `nets.find` is the fallback
    # for a pour the runtime has assigned a computed net to directly.
    #
    # The same scan also *discovers* pours: one attached only through
    # `net += Pour(...)`, never assigned to a circuit attribute (a pattern jitx
    # warns is deprecated), is invisible to `design.query(Pour)` and every other
    # structural walk. Those are reported with "owned": false, an id derived
    # from the net's path, and geometry in the net's frame.
    net_of_pour: dict[int, Net] = {}
    net_only: list[tuple[str, Transform | None, Pour]] = []
    for ntrace, net in visit(design.root, Net):
        members = [m for m in net._connected if isinstance(m, Pour)]
        for k, member in enumerate(members):
            if id(member) not in net_of_pour:
                net_of_pour[id(member)] = net
                net_only.append((f"{ntrace.path}+pour[{k}]", ntrace.transform, member))

    pours = []

    def add_pour(ref: str, xform: Transform | None, pour: Pour, owned: bool) -> None:
        owner = net_of_pour.get(id(pour))
        net = net_of(owner) if owner is not None else net_of(pour)
        if net is not None:
            net["pour"] = True
            net.setdefault("pours", []).append(ref)
        # As declared, not the router's computed fill (copper minus isolation
        # gaps around every via/pad, often many pieces with holes): smaller,
        # and a consumer doing its own fill can't use the computed one as
        # input anyway. Falls back to the current shape for a pour the
        # reverse-flow linker synthesized during capture itself, which has no
        # "before" to report.
        base_shape = (declared_pours or {}).get(id(pour), pour.shape)
        shape = _polys(xform * base_shape, ref) if xform is not None else []
        pours.append(
            {
                "id": ref,
                "net": net["name"] if net else None,
                "layer": layers.normalize(pour.layer),
                "rank": pour.rank,
                "isolate": pour.isolate,
                "tags": _tag_names(pour),
                "owned": owned,
                "shape": shape if geometry else [],
                "extent": _extent(shape),
            }
        )

    owned_ids = set()
    for trace, pour in design.query(Pour):
        owned_ids.add(id(pour))
        add_pour(str(trace.path), trace.transform, pour, owned=True)
    for ref, xform, pour in net_only:
        if id(pour) not in owned_ids:
            add_pour(ref, xform, pour, owned=False)

    # A net's tags are the union over every Net object merged into it.
    for net_obj in extract(design.root, Net):
        entry = existing_net(net_obj)
        if entry is not None:
            entry.setdefault("tags", [])
            entry["tags"] += [t for t in _tag_names(net_obj) if t not in entry["tags"]]
    for entry in entries.values():
        entry.setdefault("tags", [])

    rule_objs = list(visit(design.root, DesignConstraint))
    rules = [_design_rule(trace, rule) for trace, rule in rule_objs]

    # Every tag used anywhere - on an object or in a rule condition -
    # with its ancestors, so rules on a parent tag can be matched.
    used: list[Tag] = []
    for _trace, holder in visit(
        design.root, (Net, Pour, Component, Circuit, Landpattern, Pad, Via)
    ):
        tags = Tags.get(holder)
        used += tags.tags if tags is not None else []
    for _trace, rule in rule_objs:
        if isinstance(rule, BinaryDesignConstraint):
            used += _expr_tags(rule.first) + _expr_tags(rule.second)
        elif isinstance(rule, UnaryDesignConstraint):
            used += _expr_tags(rule.condition)
    tag_types: dict[str, dict] = {}
    for tag in used:
        tag_types.setdefault(_tag_label(tag), _tag_type(tag))

    # ---- routing widths and clearances -------------------------------
    # What jitx itself knows, resolved per net and per conductor layer:
    #   * fab minimums on the substrate (the floor for everything),
    #   * design rules: `design_constraint(cond).trace_width(w)` and
    #     `design_constraint(a, b).clearance(c)`, matched against the net's
    #     tags (+ ancestors, OnLayer, built-in trace tags), highest priority
    #     winning,
    #   * routing structures applied to signal topologies with
    #     `Constrain(...).structure(rs)`, which override rules on their nets.
    fab = design.root.substrate.constraints
    n_layers = len(design.root.substrate.stackup.conductors)
    all_layers = range(n_layers)
    norm = layers.normalize
    width_rules = [
        (r.priority, r.trace_width_constraint.width, f"rule {t.path}", r.condition)
        for t, r in rule_objs
        if isinstance(r, UnaryDesignConstraint) and r.trace_width_constraint is not None
    ]
    clearance_rules = [
        (r.priority, r.clearance_constraint.clearance, f"rule {t.path}", r.first, r.second)
        for t, r in rule_objs
        if isinstance(r, BinaryDesignConstraint) and r.clearance_constraint is not None
    ]

    net_tag_objs: dict[int, list[Tag]] = defaultdict(list)
    for net_obj in extract(design.root, Net):
        entry = existing_net(net_obj)
        tags = Tags.get(net_obj)
        if entry is not None and tags is not None:
            net_tag_objs[id(entry)] += tags.tags
    closures = {id(e): _tag_closure(net_tag_objs[id(e)]) for e in entries.values()}
    untagged = _tag_closure([])
    every = [*closures.values(), untagged]

    def width_on(names, layer):
        return _best(
            (p, w, src) for p, w, src, cond in width_rules if _matches(cond, names, layer, norm)
        )

    def everywhere(side, layer) -> bool:
        return all(_matches(side, n, layer, norm) for n in every)

    def clearance_on(names, layer):
        # rules pitting this net against every net - a per-net clearance
        return _best(
            (p, c, src)
            for p, c, src, a, b in clearance_rules
            if (_matches(a, names, layer, norm) and everywhere(b, layer))
            or (_matches(b, names, layer, norm) and everywhere(a, layer))
        )

    def value_of(pick):
        return {layer: pick(layer)[0] for layer in all_layers}

    def source_of(pick):
        return sorted({s for L in all_layers if (s := pick(L)[1]) is not None}) or None

    default_width = value_of(lambda L: width_on(untagged, L))
    default_clear = value_of(lambda L: clearance_on(untagged, L))
    rules_summary = {
        "trace_width": _per_layer(
            {L: v if v is not None else fab.min_copper_width for L, v in default_width.items()}
        ),
        "clearance": _per_layer(
            {
                L: v if v is not None else fab.min_copper_copper_space
                for L, v in default_clear.items()
            }
        ),
        "min_trace_width": fab.min_copper_width,
        "min_clearance": fab.min_copper_copper_space,
        "min_copper_edge_space": fab.min_copper_edge_space,
        "min_copper_hole_space": fab.min_copper_hole_space,
        "sources": {
            "trace_width": source_of(lambda L: width_on(untagged, L)) or ["fab minimum"],
            "clearance": source_of(lambda L: clearance_on(untagged, L)) or ["fab minimum"],
        },
    }

    for entry in entries.values():
        names = closures[id(entry)]
        entry["trace_width"] = entry["clearance"] = None
        entry["rule_sources"] = None
        if names == untagged:
            continue  # nothing tag-specific: the defaults apply
        width = value_of(lambda L, n=names: width_on(n, L))
        clear = value_of(lambda L, n=names: clearance_on(n, L))
        if width != default_width:
            entry["trace_width"] = _per_layer(width)
        if clear != default_clear:
            entry["clearance"] = _per_layer(clear)
        if entry["trace_width"] is not None or entry["clearance"] is not None:
            entry["rule_sources"] = {
                "trace_width": source_of(lambda L, n=names: width_on(n, L)),
                "clearance": source_of(lambda L, n=names: clearance_on(n, L)),
            }

    # Routing structures on signal topologies override rules for their nets.
    constrains = {str(t.path): c for t, c in visit(design.root, Constrain)}
    for trace, rsc in visit(design.root, RoutingStructureConstraint):
        owner = _owner(str(trace.path), list(constrains))
        if owner is None:
            continue
        structure = rsc.structure
        widths = {norm(k): lay.trace_width for k, lay in structure.layers.items()}
        clears = {norm(k): lay.clearance for k, lay in structure.layers.items()}
        for topology in constrains[owner].topologies:
            for end in (topology.begin, topology.end):
                for port in (end, *extract(end, Port)):
                    entry = existing_net(port)
                    if entry is None:
                        continue
                    # only the structure's layers are routable: no "default"
                    entry["trace_width"] = {str(k): v for k, v in sorted(widths.items())}
                    if any(v is not None for v in clears.values()):
                        entry["clearance"] = {
                            str(k): v for k, v in sorted(clears.items()) if v is not None
                        }
                    entry["routing_structure"] = structure.name
                    entry["rule_sources"] = {
                        "trace_width": [f"routing structure {structure.name}"],
                        "clearance": [f"routing structure {structure.name}"]
                        if any(v is not None for v in clears.values())
                        else None,
                    }
                    entry["routing_layers"] = sorted(widths)

    netlist = sorted(entries.values(), key=lambda n: (n["name"] is None, n["name"]))
    for index, net in enumerate(netlist):
        net["id"] = net["name"] or f"net#{index}"

    # Clearance rules that depend on BOTH nets (neither side matches every
    # net) can't be a per-net number; list the net pairs they bind.
    net_clearances = []
    pair_rules = [
        rule
        for rule in clearance_rules
        if not any(everywhere(side, L) for side in rule[3:] for L in all_layers)
    ]
    if pair_rules:
        for i, na in enumerate(netlist):
            for nb in netlist[i + 1 :]:
                ca, cb = closures[id(na)], closures[id(nb)]
                picks = {
                    L: _best(
                        (p, c, src)
                        for p, c, src, a, b in pair_rules
                        if (_matches(a, ca, L, norm) and _matches(b, cb, L, norm))
                        or (_matches(a, cb, L, norm) and _matches(b, ca, L, norm))
                    )
                    for L in all_layers
                }
                value = _per_layer({L: v for L, (v, _s) in picks.items()})
                if value is not None:
                    net_clearances.append(
                        {
                            "nets": [na["id"], nb["id"]],
                            "clearance": value,
                            "source": sorted({s for _v, s in picks.values() if s is not None}),
                        }
                    )

    shorts = []
    short_traces = list(visit(design.root, ShortTrace))
    port_refs: dict[int, str] = {}
    if short_traces:
        for trace, port in visit(design.root, Port):
            port_refs.setdefault(id(port), str(trace.path))
    for trace, short in short_traces:
        endpoints = []
        for port in short._connected:
            if not isinstance(port, Port):
                continue
            net = net_of(port)
            if net is not None:
                net["short_trace"] = True
            endpoints.append(
                {
                    "port": port_refs.get(id(port)),
                    "pads": sorted(pads_of_port.get(id(port), ())),
                    "net": net["id"] if net else None,
                }
            )
        ends = [
            pad_centers[e["pads"][0]]
            for e in endpoints
            if e["pads"] and e["pads"][0] in pad_centers
        ]
        distance = round(math.dist(*ends), DIGITS) if len(ends) == 2 else None
        shorts.append({"id": str(trace.path), "endpoints": endpoints, "distance": distance})

    declared_shape = _declared_board_shape(design_cls)
    board_shape = (
        _as_shape(declared_shape) if declared_shape is not None else design.root.board.shape
    )
    board = _polys(board_shape, "board")
    board_native = _circle_entry(board_shape)
    stackup = _stackup_entries(design.root.substrate.stackup)
    return {
        "design": design.name,
        "summary": {
            "conductor_layers": len(stackup),
            "board_extent": _extent(board),
            "modules": len(modules),
            "components": len(components),
            "unplaced_components": sum(1 for c in components if not c["placement"]),
            "fixed_components": sum(1 for c in components if c["fixed"]),
            "relative_components": sum(1 for c in components if c["relative"]),
            "bottom_side_hints": sum(1 for c in components if c["side_hint"] == "Bottom"),
            "moved_from_declared": sum(1 for c in components if c["moved_from_declared"]),
            "pads": sum(len(c["pads"]) for c in components),
            "nets": len(netlist),
            "named_nets": sum(1 for n in netlist if n["name"]),
            "short_traces": len(shorts),
            "vias": len(vias),
            "routes": len(routes),
            "pours": len(pours),
            "design_rules": len(rules),
            "tag_types": len(tag_types),
        },
        "board_shape": board if geometry else [],
        "board_shape_native": board_native if geometry else None,
        "stackup": stackup,
        "modules": modules,
        "components": components,
        "nets": netlist,
        "short_traces": shorts,
        "vias": vias,
        "routes": routes,
        "pours": pours,
        "tag_types": dict(sorted(tag_types.items())),
        "rules": rules_summary,
        "net_clearances": net_clearances,
        "design_rules": rules,
    }


def _place(pose, side: bool = True) -> str:
    if not pose:
        return "unplaced"
    x, y = pose["center"]
    out = f"({x:8.3f}, {y:8.3f}) {pose['angle']:6.1f}°"
    if side and pose.get("flip_x"):
        out += " flipX"
    if side and "side" in pose:
        out += f" {pose['side']}"
    return out


def _span(extent) -> str:
    if not extent:
        return "-"
    x0, y0, x1, y1 = extent
    return f"{x1 - x0:.3f} x {y1 - y0:.3f} mm  ({x0:.3f},{y0:.3f})..({x1:.3f},{y1:.3f})"


def _refs(refs, indent: str) -> list[str]:
    if not refs:
        return []
    return textwrap.wrap(
        "  ".join(sorted(refs)),
        WIDTH,
        initial_indent=indent,
        subsequent_indent=indent,
        break_on_hyphens=False,
        break_long_words=False,
    )


def _report(data: dict) -> str:
    s = data["summary"]
    out = [
        f"DESIGN  {data['design']}",
        f"  board       {_span(s['board_extent'])}",
        f"  stackup     {s['conductor_layers']} conductor layers: "
        + ", ".join(
            f"{c['layer']} ({c['side']}, {c['material']}, {c['thickness']}mm)"
            for c in data["stackup"]
        ),
        f"  contents    {s['modules']} modules, {s['components']} components "
        f"({s['unplaced_components']} unplaced, {s['fixed_components']} fixed by code, "
        f"{s['relative_components']} relative, "
        f"{s['moved_from_declared']} moved since), {s['pads']} pads, "
        f"{s['nets']} nets ({s['named_nets']} named), "
        f"{s['short_traces']} short traces, {s['vias']} vias, {s['routes']} routes, {s['pours']} pours",
        "  note        mm and degrees. `at` is the captured layout; `code` is where the "
        "design code put it,",
        "              shown only when the layout has moved it. A placement is in "
        "board coordinates, a "
        "pad pose in component coordinates,",
        "              and a pad layer is landpattern-relative: 0 is the side "
        "the component sits on.",
        "",
        f"COMPONENTS  {len(data['components'])}",
    ]

    for comp in data["components"]:
        pads = comp["pads"]
        named = [x for x in (comp["value"], comp["mpn"], comp["def_name"]) if x]
        padw = max((len(p["pad_id"]) for p in pads), default=0)
        pinw = max((len(p["pin_id"] or "?") for p in pads), default=0)
        out += [
            "",
            f"  {comp['reference'] or comp['id']}  {'  '.join(named)}",
            f"      path    {comp['id']}   in {comp['module_id'] or '(top)'}",
            f"      at      {_place(comp['placement'])}"
            + ("   [FIXED]" if comp["fixed"] else "")
            + (f"   [SIDE {comp['side_hint']}]" if comp["side_hint"] else "")
            + (f"   [RELATIVE to {comp['relative']['to']}]" if comp["relative"] else "")
            + (f"   mfr {comp['manufacturer']}" if comp["manufacturer"] else ""),
        ]
        if comp["tags"]:
            out.append(f"      tags    {', '.join(comp['tags'])}")
        if comp["moved_from_declared"]:
            out.append(f"      code    {_place(comp['declared_placement'])}   [MOVED]")
        if comp["courtyard_extent"]:
            out.append(f"      court   {_span(comp['courtyard_extent'])}")
        out.append(f"      pads    {len(pads)}")
        out += [
            f"        {p['pad_id']:<{padw}}  pin {p['pin_id'] or '?':<{pinw}}"
            f"  {_place(p['pose']):<34}"
            f"  layers {','.join(map(str, p['layers'])) or '-':<10}"
            f" net {p['net'] or '-'}"
            for p in pads
        ]

    out += ["", f"NETS  {len(data['nets'])}"]
    for net in data["nets"]:
        counts = f"{len(net['pads'])} pads"
        if net["vias"]:
            counts += f", {len(net['vias'])} vias"
        if net.get("short_trace"):
            counts += "   [SHORT TRACE]"
        if net.get("pour"):
            counts += "   [POUR]"
        if net["tags"]:
            counts += f"   tags {', '.join(net['tags'])}"
        out.append(f"  {net['id']:<24} {counts}")
        out += _refs(net["pads"], " " * 6)
        out += _refs([f"via {v}" for v in net["vias"]], " " * 6)

    out += ["", f"SHORT TRACES  {len(data['short_traces'])}"]
    for short in data["short_traces"]:
        apart = (
            f"pads {short['distance']:.3f} mm apart"
            if short["distance"] is not None
            else "distance unknown"
        )
        out += ["", f"  {short['id']}   {apart}"]
        for end in short["endpoints"]:
            out.append(f"      pin  {end['port']}   net {end['net'] or '-'}")
            out += _refs(end["pads"], " " * 11)

    if data["vias"]:
        out += ["", f"VIAS  {len(data['vias'])}"]
        out += [
            f"  {v['id']:<32} {v['def_name']:<20} {_place(v['pose'], side=False)}"
            f"  layers {v['start_layer']}..{v['stop_layer']}  net {v['net'] or '-'}"
            for v in data["vias"]
        ]

    if data["routes"]:
        out += ["", f"ROUTES  {len(data['routes'])}"]
        out += [
            f"  {rt['id']:<32} layer {rt['layer']:<3} net {rt['net'] or '-':<12}"
            f" {rt['source']['kind']} {rt['source']['path'] or '?'}"
            f"  ->  {rt['destination']['kind']} {rt['destination']['path'] or '?'}"
            for rt in data["routes"]
        ]

    if data["pours"]:
        out += ["", f"POURS  {len(data['pours'])}"]
        out += [
            f"  {p['id']:<32} layer {p['layer']:<3} rank {p['rank']:<3}"
            f" {_span(p['extent'])}  net {p['net'] or '-'}"
            + ("" if p["owned"] else "   [NET-ONLY]")
            for p in data["pours"]
        ]

    if data["design_rules"]:
        out += ["", f"DESIGN RULES  {len(data['design_rules'])}"]
        for rule in data["design_rules"]:
            effects = ", ".join(f"{k} {v}" for k, v in rule["effects"].items()) or "-"
            out.append(
                f"  {rule['name'] or rule['id']:<32} prio {rule['priority']:<3}"
                f" when {' , '.join(rule['conditions'])}  ->  {effects}"
            )

    out += ["", f"MODULES  {len(data['modules'])}"]
    children = defaultdict(list)
    for module in data["modules"]:
        children[module["parent_id"]].append(module)

    def tree(parent, depth):
        for module in children[parent]:
            indent = "  " * (depth + 1)
            out.append(f"{indent}{module['id']:<{max(4, 44 - len(indent))}} {module['def_name']}")
            tree(module["id"], depth + 1)

    tree(None, 0)
    return "\n".join(out) + "\n"


def export(
    design: RuntimeDesign,
    design_cls: type | None = None,
    *,
    out: str = "",
    geometry: bool = True,
    declared: dict[str, dict] | None = None,
    declared_pours: dict[int, Any] | None = None,
) -> None:
    data = _collect(
        design, design_cls, geometry=geometry, declared=declared, declared_pours=declared_pours
    )
    paths = [
        f"{out}.{ext}" if out else _out_path(design, "design-report", ext)
        for ext in ("txt", "json")
    ]
    with open(paths[0], "w") as f:
        f.write(_report(data))
    with open(paths[1], "w") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {paths[0]} and {paths[1]}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: design_report.py <module.path.DesignClass> [output_stem]")
        sys.exit(1)
    design_path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else ""
    mname, cname = design_path.rsplit(".", 1)
    mod = importlib.import_module(mname)
    cls = getattr(mod, cname)
    if not issubclass(cls, jitx.Design):
        print(f"{mname}.{cname} is not a jitx Design")
        sys.exit(1)
    with jitx.runtime as r:
        d = r.submit(cls)
        declared = declared_placements(d)  # before capture overwrites them
        declared_pours = declared_pour_shapes(d)  # before capture computes the fill
        d.capture()
        export(d, cls, out=out, declared=declared, declared_pours=declared_pours)


if __name__ == "__main__":
    main()
