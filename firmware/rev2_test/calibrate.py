#!/usr/bin/env python3
"""Controlled distance experiment for the badge's VL53L4CD.

    python3 calibrate.py [--distances 5,10,20,30,50,75,100] [--inches] [--hand] [--auto] [--seconds 2]

Walks through a series of setups -- the sensor covered, nothing in front, then
a flat target (a book or white card, big enough to fill the sensor's ~18 deg
view) at each distance in cm (or inches, with --inches), measured from the
front of the sensor -- and at
each one records the firmware's raw readings (its `c` command) for a couple of
seconds. Then prints, per setup: how many readings were valid, the measured
distance (median and spread of the valid ones), signal and ambient rates, and
what the demo would show for it (hue and heartbeat rate, from main.c's DEMO_*
settings). Every reading is also saved to a CSV beside this script.

--hand words the setups for a hand (open palm) rather than a book or card.
--auto needs no Enter presses: each step is spoken aloud (macOS `say`), then
counted down "3, 2, 1" and recorded, so both hands and eyes stay free.

Needs the rev2_test firmware on the badge; uses host.py's serial helpers.
"""

import argparse
import contextlib
import csv
import glob
import io
import os
import re
import shutil
import statistics
import subprocess
import time
from collections import Counter
from pathlib import Path

import host

HERE = Path(__file__).resolve().parent

# Range status codes from ST's ULD (what a non-zero status means)
STATUS = {0: "valid", 1: "sigma high", 2: "signal low", 3: "below min range", 4: "phase out of range",
          5: "hardware fail", 6: "wrap-around", 7: "wrapped target", 255: "no target"}


def demo_settings() -> dict[str, float]:
    """The demo's mapping, read from main.c so this never disagrees with it."""
    text = (HERE / "main.c").read_text()
    return {k: float(v) for k, v in re.findall(r"#define (DEMO_(?:NEAR_MM|FAR_MM|HUE_NEAR|HUE_FAR|BPM_NEAR|BPM_FAR))\s+(\d+)", text)}


def demo_view(mm: float | None, s: dict[str, float]) -> str:
    """Hue and bpm the demo settles at for a filtered distance (None: no valid reading)."""
    near, far = s["DEMO_NEAR_MM"], s["DEMO_FAR_MM"]
    d = far if mm is None or mm >= far else max(mm, near)
    f = (d - near) / (far - near)
    hue = s["DEMO_HUE_NEAR"] + (s["DEMO_HUE_FAR"] - s["DEMO_HUE_NEAR"]) * f
    bpm = s["DEMO_BPM_NEAR"] + (s["DEMO_BPM_FAR"] - s["DEMO_BPM_NEAR"]) * f
    return f"hue {hue:3.0f} ({colour_name(hue)}), {bpm:3.0f} bpm"


def colour_name(hue: float) -> str:
    for limit, name in ((15, "red"), (45, "orange"), (75, "yellow"), (150, "green"), (195, "cyan"), (255, "blue")):
        if hue < limit:
            return name
    return "violet"


def say(text: str) -> None:
    """Speak (blocking) where macOS `say` exists; the text is printed as well either way."""
    if shutil.which("say"):
        subprocess.run(["say", "-r", "190", text], check=False)


def record(fd: int, seconds: float) -> list[dict[str, int]]:
    os.write(fd, b"c")
    with contextlib.redirect_stdout(io.StringIO()):  # host.read_until echoes; keep the screen for the prompts
        out = host.read_until(fd, re.compile(r"$^"), seconds + 0.3)
        os.write(fd, b"q")
        host.read_until(fd, re.compile(r"== DONE .* ==\s*> "), 3)
    keys = ("ms", "mm", "status", "signal", "ambient", "sigma", "spads")
    rows = []
    for line in out.splitlines():
        if line.startswith("RAW,"):
            parts = line.split(",")[1:]
            if len(parts) == len(keys):
                rows.append(dict(zip(keys, map(int, parts))))
    return rows[1:]  # the first comes from before the target was settled


def summarise(rows: list[dict[str, int]], s: dict[str, float]) -> dict[str, str]:
    valid = [r for r in rows if r["status"] == 0]
    statuses = Counter(r["status"] for r in rows if r["status"] != 0)
    other = ", ".join(f"{n}x {STATUS.get(k, k)}" for k, n in statuses.most_common())
    if valid:
        mm = sorted(r["mm"] for r in valid)
        med = statistics.median(mm)
        q1, q3 = mm[len(mm) // 4], mm[(3 * len(mm)) // 4]
        measured = f"{med:5.0f} mm = {med / 25.4:4.1f} in  (middle half {q1}-{q3} mm)"
    else:
        med, measured = None, "    -  (no valid reading)"
    sig = statistics.median(r["signal"] for r in rows) if rows else 0
    amb = statistics.median(r["ambient"] for r in rows) if rows else 0
    return {"valid": f"{len(valid)}/{len(rows)}", "measured": measured, "other": other,
            "light": f"signal {sig:5.0f}, ambient {amb:5.0f} kcps", "demo": demo_view(med, s)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--distances", help="target distances (default 5,10,20,30,50,75,100 cm, or 2,4,8,12,18,24,30,39 in)")
    ap.add_argument("--inches", action="store_true", help="distances and results in inches")
    ap.add_argument("--hand", action="store_true", help="use a hand (open palm) as the target")
    ap.add_argument("--auto", action="store_true", help="spoken, timed prompts: no Enter presses")
    ap.add_argument("--seconds", type=float, default=2.0, help="recording time per setup")
    ap.add_argument("--port")
    args = ap.parse_args()

    # (name, printed instruction, spoken prompt)
    setups = [("covered", "Cover the sensor completely with a fingertip.", "Cover the sensor with a fingertip."),
              ("nothing", "Point the front of the badge at open space: nothing within 1.5 m, e.g. at the ceiling.",
               "Now take everything away. Nothing in front of the sensor.")]
    unit, unit_word = ("in", "inches") if args.inches else ("cm", "centimetres")
    distances = args.distances or ("2,4,8,12,18,24,30,39" if args.inches else "5,10,20,30,50,75,100")
    target, target_word = (("Hold your open palm flat", "Hand") if args.hand
                           else ("Hold a book or white card flat", "Target"))
    setups += [(f"{d} {unit}", f"{target}, facing the sensor, {d} {unit} from its front.", f"{target_word} at {d} {unit_word}.")
               for d in distances.split(",")]

    port = args.port or next(iter(sorted(glob.glob("/dev/cu.usbmodem*"))), None)
    if not port:
        raise SystemExit("no /dev/cu.usbmodem* port: is the badge running the rev2_test firmware?")
    fd = host.open_port(port)
    with contextlib.redirect_stdout(io.StringIO()):
        os.write(fd, b"\n")  # stops the boot demo, gets the menu
        host.read_until(fd, re.compile(r"> $"), 4)

    s = demo_settings()
    print(f"demo mapping: {s['DEMO_NEAR_MM']:.0f} mm and closer = red, {s['DEMO_BPM_NEAR']:.0f} bpm; "
          f"{s['DEMO_FAR_MM']:.0f} mm and beyond (or nothing) = blue, {s['DEMO_BPM_FAR']:.0f} bpm\n")
    results, all_rows = [], []
    if args.auto:
        print("spoken prompts; Ctrl-C to quit")
        say("Starting the distance test.")
    for name, instruction, spoken in setups:
        if args.auto:
            print(f"[{name}] {instruction}")
            say(spoken)
            time.sleep(1.5)  # time to move
            say("Hold it. 3, 2, 1.")
            print("    recording...")
        else:
            input(f"[{name}] {instruction}\n    Press Enter when it's steady (Ctrl-C to quit) ")
        rows = record(fd, args.seconds)
        if args.auto:
            say("Got it.")
        summary = summarise(rows, s)
        print(f"    {summary['valid']} valid, {summary['measured'].strip()}  -> demo: {summary['demo']}\n")
        results.append((name, summary))
        all_rows += [{"setup": name, **r} for r in rows]
    os.close(fd)
    if args.auto:
        say("All done.")

    print("results:")
    print(f"  {'setup':9s} {'valid':7s} {'measured':48s} demo would show")
    for name, r in results:
        print(f"  {name:9s} {r['valid']:7s} {r['measured']:48s} {r['demo']}")
        detail = "; ".join(x for x in (r["light"], r["other"]) if x)
        print(f"  {'':9s} {'':7s} {detail}")

    out = HERE / f"calibration-{time.strftime('%Y%m%d-%H%M%S')}.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["setup", "ms", "mm", "status", "signal", "ambient", "sigma", "spads"])
        w.writeheader()
        w.writerows(all_rows)
    print(f"\nevery reading saved to {out}")


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        main()
