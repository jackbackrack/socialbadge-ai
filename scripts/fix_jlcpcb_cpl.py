"""Correct the JLCPCB pick-and-place file written by the `jlcpcb` export.

jitxlib-jlcpcb (4.0.0a3 here, and still in 4.0.0a7) gets two things wrong for
bottom-side parts, as eink-placard found in JLCPCB's placement preview on
2026-11-03 (this script is ported from its scripts/fix_jlcpcb_cpl.py):

1. Rotation. A part's orientation correction `c` (lcsc.lock.json) is measured
   in the landpattern's own frame. The exporter writes `-(r + c)` for a bottom
   part, but mirroring the landpattern also mirrors `c`, so the right value is
   `c - r`. The two agree for c = 0 or 180 and differ by 180 degrees for 90 or
   270.
2. Position. The CPL gives the JITX landpattern origin, while JLCPCB places
   the EasyEDA footprint's origin there. Where the two origins differ (connectors,
   switches, some ICs) the part lands off its pads.

This script rewrites `<stem>-cpl.csv` in place with both corrected. The
exporter's original is kept as `<stem>-cpl.orig.csv` and is always the input,
so running the script twice gives the same result. Run it after every export:

    WARP_LIVE=1 python scripts/fix_jlcpcb_cpl.py <packet-dir>

It builds the design object model (no runtime, so it is safe while a design
session is up; WARP_LIVE=1 keeps it from replaying jitx_export.json) to read
each part's landpattern, and reads EasyEDA footprints
from the jitxlib-jlcpcb cache, fetching any that are missing.
"""

import csv
import json
import math
import shutil
import sys
from pathlib import Path

from jitx._structural import instantiation
from jitx.component import Component
from jitx.inspect import extract, visit
from jitx.landpattern import Pad
from jitx.substrate import SubstrateContext
from jitxlib.jlcpcb.export.orientation import TOP_LAYERS, fetch
from jitxlib.jlcpcb.part import part_of

from socialbadge_ai.designs.badge_main import BadgeDesign

ROOT = Path(__file__).resolve().parent.parent
# Below this the two origins are taken to agree: SOT-23 pad-size differences
# move the pad centroid by ~0.07 mm without moving the origin.
TOLERANCE_MM = 0.1


def _rotate(v: tuple[float, float], degrees: float) -> tuple[float, float]:
    a = math.radians(degrees)
    return (
        v[0] * math.cos(a) - v[1] * math.sin(a),
        v[0] * math.sin(a) + v[1] * math.cos(a),
    )


def _mean(points: list[tuple[float, float]]) -> tuple[float, float]:
    return (
        sum(x for x, _ in points) / len(points),
        sum(y for _, y in points) / len(points),
    )


def jitx_centroids() -> dict[str, tuple[float, float]]:
    """Pad centroid in the landpattern frame, per LCSC part number."""
    out: dict[str, tuple[float, float]] = {}
    with instantiation.activate():
        design = BadgeDesign()
        with SubstrateContext(design.substrate):
            for comp in extract(design.circuit, Component):
                part = part_of(comp)
                if part is None or part.partnumber in out:
                    continue
                points = []
                for trace, pad in visit(comp, Pad):
                    t, p = trace.transform, getattr(pad, "transform", None)
                    t = t * p if (t is not None and p is not None) else (t or p)
                    points.append((t.translation[0], t.translation[1]))
                out[part.partnumber] = _mean(points)
    return out


def easyeda_centroid(lcsc: str) -> tuple[float, float]:
    """Pad centroid about the EasyEDA footprint origin, y up."""
    pads = [p for p in fetch(lcsc) if int(p["layer"]) in TOP_LAYERS]
    return _mean([(float(p["x"]), -float(p["y"])) for p in pads])


def main(packet: Path) -> None:
    (cpl,) = [p for p in packet.glob("*-cpl.csv")]
    (bom,) = list(packet.glob("*-bom.csv"))
    orig = cpl.with_name(cpl.name.replace("-cpl.csv", "-cpl.orig.csv"))
    if not orig.exists():
        shutil.copyfile(cpl, orig)

    lcsc_of: dict[str, str] = {}
    with bom.open(newline="") as f:
        for row in csv.DictReader(f):
            for ref in row["Designator"].split(","):
                lcsc_of[ref.strip()] = row["JLCPCB Part #"]
    lock = json.loads((ROOT / "lcsc.lock.json").read_text())["parts"]
    jitx = jitx_centroids()

    with orig.open(newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    for row in rows:
        lcsc = lcsc_of.get(row["Designator"], "")
        c = float(lock.get(lcsc, {}).get("orientation", 0.0))
        rot = float(row["Rotation"])
        bottom = row["Layer"] == "Bottom"
        # Undo the exporter's formula to recover the placement rotation r.
        r = (-rot - c) if bottom else (rot - c)
        new_rot = ((c - r) if bottom else rot) % 360.0

        dx = dy = 0.0
        if lcsc in jitx:
            e = _rotate(easyeda_centroid(lcsc), c)
            local = (jitx[lcsc][0] - e[0], jitx[lcsc][1] - e[1])
            if math.hypot(*local) > TOLERANCE_MM:
                if bottom:  # JITX bottom placement is R(r) . diag(-1, 1)
                    local = (-local[0], local[1])
                dx, dy = _rotate(local, r)

        x, y = float(row["Mid X"]) + dx, float(row["Mid Y"]) + dy
        if abs(new_rot - rot % 360.0) > 1e-6 or dx or dy:
            print(
                f"{row['Designator']:5s} {lcsc:10s} rot {rot:6.1f} -> {new_rot:6.1f}"
                f"  shift ({dx:+.3f}, {dy:+.3f}) mm"
            )
        row["Mid X"], row["Mid Y"] = f"{x:.4f}", f"{y:.4f}"
        row["Rotation"] = f"{new_rot:.2f}"

    with cpl.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {cpl} (exporter original kept as {orig.name})")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "jlcpcb")
