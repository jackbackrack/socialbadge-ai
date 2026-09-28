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

import importlib
import json
import math
import sys
import textwrap
from collections import defaultdict
from typing import Any

import jitx
import shapely
from jitx._structural import Proxy
from jitx.anchor import Anchor
from jitx.circuit import Circuit
from jitx.component import Component
from jitx.copper import Copper, Pour
from jitx.feature import Courtyard
from jitx.inspect import extract, visit
from jitx.landpattern import Pad, PadMapping
from jitx.net import Net, Port, ShortTrace
from jitx.placement import Placement
from jitx.run.runtime import RuntimeDesign
from jitx.shapes import primitive
from jitx.shapes.shapely import ShapelyGeometry
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


def declared_placements(design: RuntimeDesign) -> dict[str, dict | None]:
    """Each component's placement as the design code set it (`.at(...)` /
    `Circuit.place`), keyed by component path. Call this after `submit` and
    BEFORE `capture`: capture overwrites component transforms with the layout
    tool's result, which includes any moves made in the editor since."""
    return {
        str(trace.path): _pose(_compose(trace.transform, comp.transform))
        for trace, comp in visit(design.root, Component)
    }


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
    declared: dict[str, dict | None] | None = None,
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

    modules = [
        {
            "id": str(trace.path),
            "def_name": Proxy.type(circuit).__name__,
            "placement": _pose(_compose(trace.transform, circuit.transform)),
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
        code_pose = declared.get(cid) if declared is not None else None

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
                "placement": pose or False,
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
        shape = _polys(xform * pour.shape, ref) if xform is not None else []
        pours.append(
            {
                "id": ref,
                "net": net["name"] if net else None,
                "layer": layers.normalize(pour.layer),
                "rank": pour.rank,
                "isolate": pour.isolate,
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

    netlist = sorted(entries.values(), key=lambda n: (n["name"] is None, n["name"]))
    for index, net in enumerate(netlist):
        net["id"] = net["name"] or f"net#{index}"

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
    return {
        "design": design.name,
        "summary": {
            "conductor_layers": len(design.root.substrate.stackup.conductors),
            "board_extent": _extent(board),
            "modules": len(modules),
            "components": len(components),
            "unplaced_components": sum(1 for c in components if not c["placement"]),
            "code_placed_components": sum(1 for c in components if c["declared_placement"]),
            "moved_from_declared": sum(1 for c in components if c["moved_from_declared"]),
            "pads": sum(len(c["pads"]) for c in components),
            "nets": len(netlist),
            "named_nets": sum(1 for n in netlist if n["name"]),
            "short_traces": len(shorts),
            "vias": len(vias),
            "pours": len(pours),
        },
        "board_shape": board if geometry else [],
        "board_shape_native": board_native if geometry else None,
        "modules": modules,
        "components": components,
        "nets": netlist,
        "short_traces": shorts,
        "vias": vias,
        "pours": pours,
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
        f"  stackup     {s['conductor_layers']} conductor layers",
        f"  contents    {s['modules']} modules, {s['components']} components "
        f"({s['unplaced_components']} unplaced, {s['code_placed_components']} placed in "
        f"code, {s['moved_from_declared']} moved since), {s['pads']} pads, "
        f"{s['nets']} nets ({s['named_nets']} named), "
        f"{s['short_traces']} short traces, {s['vias']} vias, {s['pours']} pours",
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
            + (f"   mfr {comp['manufacturer']}" if comp["manufacturer"] else ""),
        ]
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

    if data["pours"]:
        out += ["", f"POURS  {len(data['pours'])}"]
        out += [
            f"  {p['id']:<32} layer {p['layer']:<3} rank {p['rank']:<3}"
            f" {_span(p['extent'])}  net {p['net'] or '-'}"
            + ("" if p["owned"] else "   [NET-ONLY]")
            for p in data["pours"]
        ]

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
    declared: dict[str, dict | None] | None = None,
) -> None:
    data = _collect(design, design_cls, geometry=geometry, declared=declared)
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
        d.capture()
        export(d, cls, out=out, declared=declared)


if __name__ == "__main__":
    main()
