"""
SocialBadge AI — top-level design.

50 × 50 mm square board with 0.25 mm rounded corners on the JLCPCB 4-layer FR-4
1080-prepreg stackup (JLC04161H_1080). Combines the USB-C interface, Li-ion
charger, Schottky power-path, 3.3 V LDO, and RP2040 support circuits into a
single buildable design.

Rev 2: the front (Top) carries a 4 × 4 addressable LED grid, an IR emitter and
receiver, and a VL53L0X distance sensor; all other circuitry is on the back
(Bottom). The LED grid runs from VBAT through a switch the RP2040 controls.

Power tree (already documented in ARCHITECTURE.md):

  USB-C VBUS -+---[ SS14 ]--+
              |              SYS --[ AP2112K-3.3 ]--> 3V3 --> RP2040 + flash
              +--[ MCP73831 ]--> VBAT --[ SS14 ]--+
                                ^
                     [ AO3401A reverse-battery P-FET ]
                                ^
                            JST-PH battery

Design rules and passive defaults are tuned for the JLCPCB Standard 4-layer fab class.
"""

import os

from jitx import Circuit, Design, Net, Pour
from jitx.board import Board
from jitx.layerindex import Side
from jitx.net import ShortTrace
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
from jitxlib.landpatterns.ipc import DensityLevel, DensityLevelContext
from jitxlib.parts import CapacitorQuery, Minimize, ResistorQuery
from jitxlib.symbols.net_symbols import GroundSymbol, PowerSymbol

from ..circuits.charger import Charger
from ..circuits.distance_sensor import DistanceSensor
from ..circuits.front_leds import LEDGrid, LEDPower
from ..circuits.infrared import IRReceiver, IRTransmitter
from ..circuits.ldo_3v3 import LDO_3V3
from ..circuits.power_path import PowerPath
from ..circuits.rp2040_support import RP2040Support
from ..circuits.status_leds import N_LEDS, StatusLEDs
from ..circuits.usb_c import USB_C
from ..components.transistors.aos_AO3401A import AO3401A
from jitx_warp_integration.layout_placements import layout_placements

from ..components.connectors.shouhan_PH2_2P import PH2_2P

# Tags applied to nets so the design rules can match them by class.
class PowerTag(Tag):
    """Marks power rails for the wider-trace rule."""


class GroundTag(Tag):
    """Marks ground nets for the wider-trace rule."""


# Board outline — 50.0 × 50.0 mm with 0.25 mm rounded corners (the
# ~/py_social_badge size).
BOARD_SHAPE = rectangle(50.0, 50.0, radius=0.25)

# RP2040 GPIO assignments for the rev-2 front-side peripherals (GPIO0..2 are
# the status LEDs). GPIO4/5 are I2C0 SDA/SCL; GPIO6 is PWM slice 3 channel A.
GPIO_TOF_SDA = 4
GPIO_TOF_SCL = 5
GPIO_IR_TX = 6
GPIO_IR_RX = 7
GPIO_TOF_XSHUT = 8
GPIO_TOF_INT = 9
GPIO_LED_ENABLE = 10
GPIO_LED_DATA = 11


class BadgeBoard(Board):
    """50.0 × 50.0 mm board with 0.25 mm rounded corners."""

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
        self.VLED = Net(name="VLED", symbol=PowerSymbol())

        GroundTag().assign(self.GND)
        PowerTag().assign(self.VBUS)
        PowerTag().assign(self.VBAT)
        PowerTag().assign(self.SYS)
        PowerTag().assign(self.V3V3)
        PowerTag().assign(self.VLED)

        # --- Subcircuits ---
        self.usb = USB_C()
        self.charger = Charger()
        self.path = PowerPath()
        self.ldo = LDO_3V3()
        self.mcu = RP2040Support()
        self.status = StatusLEDs()

        # Battery connector — MOUNT tabs tie to GND
        self.battery = PH2_2P()

        # Reverse-battery protection: AO3401A P-FET in the battery's + lead,
        # drain to the connector, source to VBAT, gate to GND. A correct pack
        # first conducts through the body diode, then VGS = −VBAT turns the
        # channel fully on (both directions, so charging still works; ~30 mV
        # at 500 mA). A reversed pack leaves VGS ≥ 0 and the body diode
        # reverse-biased, so the charger and the LED switch never see −VBAT.
        # Limit: with USB present the charger lifts VBAT and turns the FET on,
        # trickling its pre-charge current into a reversed pack.
        self.BAT_P = Net(name="BAT_P")
        PowerTag().assign(self.BAT_P)
        self.q_rev = AO3401A()
        self.BAT_P += self.battery.PIN1
        self.st_q_rev_at_battery = ShortTrace(self.battery.PIN1, self.q_rev.D)
        self.VBAT += self.q_rev.S
        self.GND += self.q_rev.G

        # Front-side peripherals (rev 2), fixed on the front with .at(): the
        # LED grid centred on the board, the sensors along the bottom edge
        # below its last row. Each circuit fixes its own front parts; their
        # back-side parts (switch, driver, pull-ups) are placed by the layout
        # file (jitx_export.json) like the rest of the board.
        self.led_power = LEDPower()
        self.leds = LEDGrid().at(0.0, 0.0, on=Side.Top)
        self.ir_tx = IRTransmitter().at(-12.0, -21.5, on=Side.Top)
        self.tof = DistanceSensor().at(0.0, -21.5, on=Side.Top)
        self.ir_rx = IRReceiver().at(12.0, -21.5, on=Side.Top)

        # --- Power tree ---
        # USB-C VBUS → charger input, power-path VBUS input
        self.VBUS += self.usb.vbus.Vp + self.charger.vbus.Vp + self.path.vbus.Vp
        # Charger output → battery (BAT positive) and power-path VBAT input
        self.VBAT += (
            self.charger.vbat.Vp
            + self.path.vbat.Vp
            + self.led_power.vbat.Vp
        )
        # Switched VBAT → LED grid
        self.VLED += self.led_power.vled.Vp + self.leds.vled.Vp
        # Power-path output → LDO input
        self.SYS += self.path.sys.Vp + self.ldo.vin.Vp
        # LDO output → MCU 3V3 + charger LED pull-up
        self.V3V3 += (
            self.ldo.vout.Vp
            + self.mcu.v3v3.Vp
            + self.charger.v3v3.Vp
            + self.ir_tx.v3v3.Vp
            + self.ir_rx.v3v3.Vp
            + self.tof.v3v3.Vp
        )

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
            + self.led_power.vbat.Vn
            + self.led_power.vled.Vn
            + self.leds.vled.Vn
            + self.ir_tx.v3v3.Vn
            + self.ir_rx.v3v3.Vn
            + self.tof.v3v3.Vn
        )

        # --- USB data lines: USB-C circuit ↔ RP2040 support ---
        self.usb_dp_link = [self.usb.data.p + self.mcu.usb.p]
        self.usb_dn_link = [self.usb.data.n + self.mcu.usb.n]
        # No impedance or length-matching constraint: the RP2040 is USB 1.1
        # full speed (12 Mb/s, 4–20 ns edges), and the ~25 mm pair is
        # electrically short. Route D+/D- side by side over the L3 GND plane.

        # --- Status LEDs driven by GPIO[0..2] (active-high) ---
        self.status_led_drive = [
            self.mcu.gpio[i] + self.status.gpio[i] for i in range(N_LEDS)
        ]

        # --- Front-side peripherals ---
        self.peripheral_nets = [
            Net([self.mcu.gpio[GPIO_TOF_SDA], self.tof.sda], name="I2C_SDA"),
            Net([self.mcu.gpio[GPIO_TOF_SCL], self.tof.scl], name="I2C_SCL"),
            Net([self.mcu.gpio[GPIO_TOF_XSHUT], self.tof.xshut], name="TOF_XSHUT"),
            Net([self.mcu.gpio[GPIO_TOF_INT], self.tof.gpio1], name="TOF_INT"),
            Net([self.mcu.gpio[GPIO_IR_TX], self.ir_tx.drive], name="IR_TX"),
            Net([self.mcu.gpio[GPIO_IR_RX], self.ir_rx.out], name="IR_RX"),
            Net([self.mcu.gpio[GPIO_LED_ENABLE], self.led_power.enable], name="LED_EN"),
            Net([self.mcu.gpio[GPIO_LED_DATA], self.leds.din], name="LED_DATA"),
        ]

        # --- Pours.
        # Stackup is SIG / PWR / GND / SIG — inner layer 1 is the 3V3 power
        # plane and inner layer 2 a solid GND reference plane, next to the back
        # where nearly all the circuitry and the USB D+/D- lines are (rev 2 swapped
        # them; rev 1 had GND on layer 1). The two outer signal layers (0, 3)
        # get GND fills in unrouted areas.
        # Assigned as circuit attributes (not just `net += Pour(...)`), so each
        # pour is also "strongly" owned by the circuit rather than only
        # reachable via the net — the latter is deprecated (and, separately,
        # invisible to structural traversal like `visit()`/`query()`, which
        # the reverse-flow design-report script relies on to enumerate pours).
        self.gnd_pour_l0 = Pour(BOARD_SHAPE, layer=0, isolate=0.25, rank=1)
        self.v3v3_pour_l1 = Pour(BOARD_SHAPE, layer=1, isolate=0.25, rank=1)
        self.gnd_pour_l2 = Pour(BOARD_SHAPE, layer=2, isolate=0.25, rank=1)
        self.gnd_pour_l3 = Pour(BOARD_SHAPE, layer=3, isolate=0.25, rank=1)
        self.GND += self.gnd_pour_l0
        self.GND += self.gnd_pour_l2
        self.GND += self.gnd_pour_l3
        self.V3V3 += self.v3v3_pour_l1


class BadgeDesign(Design):
    """Buildable design entry point.

    Run: `python -m jitx build socialbadge_ai.designs.badge_main.BadgeDesign`
    """

    board = BadgeBoard()
    substrate = JLC04161H_1080()

    # SMT production defaults — JLCPCB full assembly, ceramic decoupling.
    # rank=Minimize("case") prefers the smallest available case (0402) and
    # only falls back to 0603/0805 when 0402 isn't stocked for that value —
    # otherwise the live JLCPCB catalog query can non-deterministically pick
    # a larger case with no preference set.
    capacitor_defaults = CapacitorQuery(
        case=["0402", "0603", "0805"],
        rank=Minimize("case"),
    )
    resistor_defaults = ResistorQuery(
        case=["0402", "0603", "0805"],
        rank=Minimize("case"),
    )

    circuit = BadgeCircuit()

    def __init__(self):
        # Pin the IPC density level explicitly: jitxlib-standard 4.5.0a1
        # defaults to B (median keepout), where this design was tuned for
        # the older C (least/tightest) default — pin it rather than drift
        # with whatever a future library version defaults to.
        DensityLevelContext(DensityLevel.C).set()

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
        # apply_board_shape=False: jitx_export.json still has the captured
        # 30mm-era board shape, which would otherwise silently override the
        # BOARD_SHAPE above on every build. Component placements from
        # the file are still replayed.
        #
        # Skipped when WARP_LIVE=1: a live warp session pushes placements
        # directly through rd.layout, and the runtime rejects place() on
        # anything already placed in code.
        if os.environ.get("WARP_LIVE") != "1":
            layout_placements("jitx_export.json", apply_board_shape=False)
