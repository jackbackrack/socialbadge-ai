#!/usr/bin/env python3
"""Run the rev 2 bring-up tests over the badge's USB serial port.

    python3 host.py [commands] [--port /dev/cu.usbmodemXXXX]

`commands` is a string of the firmware's one-key commands, run in order
(default "a": all tests; "d", the distance-to-colour demo, runs until Ctrl-C;
"b" reboots the badge to BOOTSEL). Each test's output is printed as it
arrives, and a summary of the "== DONE <test>: <result> ==" lines at the end. Standard
library only (termios), no pyserial.
"""

import argparse
import glob
import os
import re
import select
import sys
import termios
import time

DONE = re.compile(r"== DONE (\S+): (.*) ==")
TIMEOUT_S = {"s": 10, "g": 30, "t": 30, "i": 30, "r": 20, "a": 90}


def open_port(path: str) -> int:
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    attrs = termios.tcgetattr(fd)
    attrs[0] = 0  # iflag: raw
    attrs[1] = 0  # oflag
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attrs[3] = 0  # lflag: no echo, non-canonical
    attrs[4] = attrs[5] = termios.B115200  # ignored by USB CDC
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    termios.tcflush(fd, termios.TCIOFLUSH)
    return fd


def read_until(fd: int, pattern: re.Pattern, timeout: float) -> str:
    buf, end = "", time.time() + timeout
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.2)
        if not r:
            continue
        chunk = os.read(fd, 4096).decode(errors="replace")
        sys.stdout.write(chunk)
        sys.stdout.flush()
        buf += chunk
        if pattern.search(buf):
            return buf
    return buf


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("commands", nargs="?", default="a")
    ap.add_argument("--port")
    args = ap.parse_args()

    port = args.port
    for _ in range(50):  # the port appears a few seconds after flashing
        ports = sorted(glob.glob("/dev/cu.usbmodem*"))
        if port or ports:
            break
        time.sleep(0.2)
    port = port or (ports[0] if ports else None)
    if not port:
        sys.exit("no /dev/cu.usbmodem* port: is the badge running the test firmware?")

    fd = open_port(port)
    os.write(fd, b"\n")  # prompts the menu, and confirms the firmware answers
    read_until(fd, re.compile(r"> $"), 3)
    results = []
    for c in args.commands:
        os.write(fd, c.encode())
        done = re.compile(r"== DONE (?:all|\w+): .* ==\s*> " if c == "a" else r"== DONE .* ==\s*> ")
        if c == "d":  # runs until stopped: Ctrl-C sends the board a key, so it turns the grid off itself
            try:
                out = read_until(fd, done, float("inf"))
            except KeyboardInterrupt:
                os.write(fd, b"q")
                out = read_until(fd, done, 5)
        elif c == "b":  # the port goes away as the board reboots
            try:
                read_until(fd, re.compile(r"rebooting"), 3)
            except OSError:
                pass
            print("\nrebooted to BOOTSEL: copy build/rev2_test.uf2 to /Volumes/RPI-RP2")
            return
        else:
            out = read_until(fd, done, TIMEOUT_S.get(c, 30))
        results += DONE.findall(out)
        if not DONE.search(out):
            results.append((c, "NO ANSWER (timed out)"))
    os.close(fd)
    print("\nsummary:")
    for test, result in results:
        if test != "all":
            print(f"  {test:11s} {result}")


if __name__ == "__main__":
    main()
