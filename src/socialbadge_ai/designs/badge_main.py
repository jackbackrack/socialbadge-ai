"""
SocialBadge AI — top-level design.

50 × 50 mm square board with 0.25 mm rounded corners on the JLCPCB 4-layer FR-4
1080-prepreg stackup (JLC04161H_1080). Combines the USB-C interface, Li-ion
charger, Schottky power-path, 3.3 V LDO, and RP2040 support circuits into a
single buildable design.

Power tree (already documented in ARCHITECTURE.md):

  USB-C VBUS -+---[ SS14 ]--+
              |              SYS --[ AP2112K-3.3 ]--> 3V3 --> RP2040 + flash
              +--[ MCP73831 ]--> VBAT --[ SS14 ]--+
                                ^
                            JST-PH battery

Design rules and passive defaults are tuned for the JLCPCB Standard 4-layer fab class.
"""

from jitx import Circuit, Design, Net, Pour
from jitx.board import Board
from jitx.constraints import (
    BinaryDesignConstraint,
    IsCopper,
    IsPad,
    IsTrace,
    Tag,
    UnaryDesignConstraint,
)
from jitx.shapes.composites import rectangle
from jitxlib.jlcpcb import JLC04161H_1080
from jitxlib.parts import CapacitorQuery, ResistorQuery
from jitxlib.symbols.net_symbols import GroundSymbol, PowerSymbol

from ..circuits.charger import Charger
from ..circuits.ldo_3v3 import LDO_3V3
from ..circuits.power_path import PowerPath
from ..circuits.rp2040_support import RP2040Support
from ..circuits.status_leds import N_LEDS, StatusLEDs
from ..circuits.usb_c import USB_C
from ..components.connectors.shouhan_PH2_2P import PH2_2P


# Tags applied to nets so the design rules can match them by class.
class PowerTag(Tag):
    """Marks power rails for the wider-trace rule."""


class GroundTag(Tag):
    """Marks ground nets for the wider-trace rule."""


# Board outline — 50 × 50 mm with 0.25 mm rounded corners.
BOARD_SHAPE = rectangle(50.0, 50.0, radius=0.25)


class BadgeBoard(Board):
    """50 × 50 mm board with 0.25 mm rounded corners."""

    shape = BOARD_SHAPE


class BadgeCircuit(Circuit):
    """Top-level netlist for the badge.

    Instantiates all five subcircuits, wires up the power tree, ties USB-C data
    lines and SWD to the RP2040, and exposes pours on inner GND/Power planes.
    """

    def __init__(self):
        # --- Nets ---
        self.GND = Net(name="GND", symbol=GroundSymbol())
        self.VBUS = Net(name="VBUS", symbol=PowerSymbol())
        self.VBAT = Net(name="VBAT", symbol=PowerSymbol())
        self.SYS = Net(name="SYS", symbol=PowerSymbol())
        self.V3V3 = Net(name="3V3", symbol=PowerSymbol())

        GroundTag().assign(self.GND)
        PowerTag().assign(self.VBUS)
        PowerTag().assign(self.VBAT)
        PowerTag().assign(self.SYS)
        PowerTag().assign(self.V3V3)

        # --- Subcircuits ---
        self.usb = USB_C()
        self.charger = Charger()
        self.path = PowerPath()
        self.ldo = LDO_3V3()
        self.mcu = RP2040Support()
        self.status = StatusLEDs()

        # Battery connector — MOUNT tabs tie to GND
        self.battery = PH2_2P()

        # --- Power tree ---
        # USB-C VBUS → charger input, power-path VBUS input
        self.VBUS += self.usb.vbus.Vp + self.charger.vbus.Vp + self.path.vbus.Vp
        # Charger output → battery (BAT positive) and power-path VBAT input
        self.VBAT += (
            self.charger.vbat.Vp
            + self.path.vbat.Vp
            + self.battery.PIN1
        )
        # Power-path output → LDO input
        self.SYS += self.path.sys.Vp + self.ldo.vin.Vp
        # LDO output → MCU 3V3 + charger LED pull-up
        self.V3V3 += self.ldo.vout.Vp + self.mcu.v3v3.Vp + self.charger.v3v3.Vp

        # GND across everything
        self.GND += (
            self.usb.vbus.Vn
            + self.charger.vbus.Vn
            + self.charger.vbat.Vn
            + self.charger.v3v3.Vn
            + self.path.vbus.Vn
            + self.path.vbat.Vn
            + self.path.sys.Vn
            + self.ldo.vin.Vn
            + self.ldo.vout.Vn
            + self.mcu.v3v3.Vn
            + self.status.gnd
            + self.battery.PIN2
            + self.battery.MOUNT1
            + self.battery.MOUNT2
        )

        # --- USB data lines: USB-C circuit ↔ RP2040 support ---
        self.usb_dp_link = [self.usb.DP + self.mcu.usb_dp]
        self.usb_dn_link = [self.usb.DN + self.mcu.usb_dn]

        # --- Status LEDs driven by GPIO[0..2] (active-high) ---
        self.status_led_drive = [
            self.mcu.gpio[i] + self.status.gpio[i] for i in range(N_LEDS)
        ]

        # --- Pours.
        # Stackup is SIG / GND / PWR / SIG — inner layer 1 is a solid GND
        # reference plane and inner layer 2 is the 3V3 power plane. The two
        # outer signal layers (0, 3) get GND fills in unrouted areas.
        self.GND += Pour(BOARD_SHAPE, layer=0, isolate=0.25, rank=1)
        self.GND += Pour(BOARD_SHAPE, layer=1, isolate=0.25, rank=1)
        self.V3V3 += Pour(BOARD_SHAPE, layer=2, isolate=0.25, rank=1)
        self.GND += Pour(BOARD_SHAPE, layer=3, isolate=0.25, rank=1)


class BadgeDesign(Design):
    """Buildable design entry point.

    Run: `python -m jitx build socialbadge_ai.designs.badge_main.BadgeDesign`
    """

    board = BadgeBoard()
    substrate = JLC04161H_1080()

    # SMT production defaults — JLCPCB full assembly, ceramic decoupling.
    capacitor_defaults = CapacitorQuery(
        mounting="smd",
        type="ceramic",
        case=["0402", "0603", "0805"],
    )
    resistor_defaults = ResistorQuery(
        mounting="smd",
        case=["0402", "0603", "0805"],
    )

    circuit = BadgeCircuit()

    def __init__(self):
        # Production-friendly defaults calibrated to JLC 4-layer 1080
        # (minimum trace width / clearance 0.0889 mm / 3.5 mil per JLC standard rules).
        self.rules = [
            UnaryDesignConstraint(IsTrace).trace_width(0.125),
            BinaryDesignConstraint(IsCopper, IsCopper).clearance(0.125),
            UnaryDesignConstraint(IsPad).thermal_relief(0.125, 0.2, 4),
            UnaryDesignConstraint(
                PowerTag() | GroundTag(), priority=1
            ).trace_width(0.4),
        ]
