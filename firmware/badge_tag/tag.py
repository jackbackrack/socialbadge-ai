#!/usr/bin/env python3
"""Talk to a badge running the badge_tag firmware over USB serial.

    python3 tag.py id 5          set this badge's ID (1..16), kept in flash
    python3 tag.py status        ID, IR power, frozen IDs, badges heard now
    python3 tag.py power 10      IR carrier duty, percent (1..50): lower = shorter range
    python3 tag.py clear         forget the frozen IDs
    python3 tag.py selftest      send 10 frames, decode them on this badge's own receiver
    python3 tag.py monitor       print badges coming, going and freezing, until Ctrl-C
    python3 tag.py boot          reboot to BOOTSEL (then copy build/badge_tag.uf2 to /Volumes/RPI-RP2)

With two badges on one computer, pick one with --port (`ls /dev/cu.usbmodem*`).
Standard library only (termios), as ../rev2_test/host.py.
"""

import argparse
import glob
import os
import select
import sys
import termios
import time


def open_port(path: str) -> int:
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    attrs = termios.tcgetattr(fd)
    attrs[0] = attrs[1] = attrs[3] = 0  # raw, no echo
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    termios.tcflush(fd, termios.TCIOFLUSH)
    return fd


def lines(fd: int, timeout: float):
    """Lines from the badge until `timeout` seconds pass with nothing new."""
    buf, end = "", time.time() + timeout
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.1)
        if not r:
            continue
        try:
            buf += os.read(fd, 4096).decode(errors="replace")
        except OSError:  # the port went away (boot)
            return
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            yield line.rstrip("\r")
            end = time.time() + timeout


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["id", "status", "power", "clear", "selftest", "monitor", "boot"])
    ap.add_argument("value", nargs="?")
    ap.add_argument("--port")
    args = ap.parse_args()

    ports = sorted(glob.glob("/dev/cu.usbmodem*"))
    port = args.port or (ports[0] if len(ports) == 1 else None)
    if not port:
        sys.exit("no badge port found" if not ports else f"several badges: pick one with --port ({', '.join(ports)})")
    fd = open_port(port)

    if args.command == "monitor":
        print(f"{port}: watching (Ctrl-C to stop)")
        os.write(fd, b"status\n")
        try:
            for line in lines(fd, float("inf")):
                if line.startswith(("EVT", "STATUS")):
                    print(time.strftime("%H:%M:%S"), line)
        except KeyboardInterrupt:
            pass
        return

    if args.command in ("id", "power") and args.value is None:
        sys.exit(f"{args.command} needs a value")
    cmd = args.command + (f" {args.value}" if args.value is not None else "")
    os.write(fd, (cmd + "\n").encode())
    wait = 3.0 if args.command == "selftest" else 1.0
    for line in lines(fd, wait):
        if line.startswith(("OK", "ERR", "STATUS")):
            print(line)
            if args.command != "selftest" or "selftest" in line:
                break
    if args.command == "boot":
        print("copy build/badge_tag.uf2 to /Volumes/RPI-RP2 to reflash")


if __name__ == "__main__":
    main()
