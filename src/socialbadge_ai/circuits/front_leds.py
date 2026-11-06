"""
Front LED grid — 16 WS2812C-2020 addressable RGB LEDs in one daisy chain, and
the switch that powers them from VBAT.

LEDGrid (front side):
- 4 × 4 grid at 11.5 mm pitch (as in ~/py_social_badge), wired as a
  serpentine chain: each row runs the opposite way to the one before, so every
  DO is next to the following LED's DI.
- 100 nF on each LED's VDD (datasheet application circuit), beside its VDD
  edge, 2.2 mm from the LED's centre (~0.6 mm copper clearance to its pads).
- Every LED and cap is fixed with `.at()` in the grid's frame; the board
  fixes the grid itself.
- 33 Ω series resistor on the chain's DIN to damp ringing on the first link.
- WS2812C-2020-V6: VDD 3.3–5.3 V, VIH = 0.55·VDD, so 3.3 V data drives it
  directly from any battery voltage (no level shifter).

LEDPower (back side):
- AO3401A P-FET high-side switch from VBAT to VLED. Its gate is pulled up to
  VBAT (off); a BSS138 pulls it low when `enable` is driven high. A gate
  pull-down on the BSS138 keeps the LEDs off while the RP2040 boots — each
  WS2812C draws ~0.5 mA even when dark, ~8 mA for the chain.
- 4.7 µF bulk capacitor on VLED (the 10 µF / 10 V X5R in 0402–0805 is not in
  the JLCPCB catalogue; the 100 nF at each LED carries the local current).

Firmware: drive DIN low while VLED is off, or the chain is back-powered
through its DIN protection diode.
"""

from jitx import Circuit, Net
from jitx.common import Power
from jitx.net import Port, ShortTrace
from jitx.transform import Transform
from jitx.units import F, V, ohm
from jitxlib.parts import Capacitor, Resistor

from ..components.leds.worldsemi_WS2812C_2020 import WS2812C_2020_V6
from ..components.transistors.aos_AO3401A import AO3401A
from ..components.transistors.diodes_BSS138 import BSS138

GRID_N = 4  # LEDs per row and per column
GRID_PITCH = 11.5  # mm
CAP_OFFSET = 2.2  # mm, LED centre to its decoupling cap's centre
N_LEDS = GRID_N * GRID_N


def grid_transform(index: int) -> Transform:
    """Pose of chain LED `index` in the grid's frame (grid centred on origin).

    Even rows run toward -x with the LED unrotated (its DO pad on the -x
    side); odd rows run toward +x rotated 180° (DO on +x). Either way each DO
    faces the next LED's DI.
    """
    row, col = divmod(index, GRID_N)
    half = (GRID_N - 1) * GRID_PITCH / 2.0
    forward = row % 2 == 1  # this row runs toward +x
    x = -half + col * GRID_PITCH if forward else half - col * GRID_PITCH
    y = -half + row * GRID_PITCH
    return Transform((x, y), 180.0 if forward else 0.0)


class LEDGrid(Circuit):
    """Sixteen chained WS2812C-2020 LEDs on a 4 × 4 grid."""

    vled = Power()  # switched VBAT from LEDPower
    din = Port()  # chain data in, from an RP2040 PIO pin

    def __init__(self):
        self.GND = Net(name="GND")
        self.VLED = Net(name="VLED")
        self.GND += self.vled.Vn
        self.VLED += self.vled.Vp

        self.leds = [WS2812C_2020_V6() for _ in range(N_LEDS)]
        self.c_leds = [Capacitor(capacitance=100e-9 * F) for _ in range(N_LEDS)]

        self.r_din = Resistor(resistance=33.0 * ohm)
        self.din_nets = [
            self.din + self.r_din.p1,
            self.r_din.p2 + self.leds[0].DI,
        ]
        self.chain_nets = [self.leds[i].DO + self.leds[i + 1].DI for i in range(N_LEDS - 1)]

        self.decouple_nets = []
        for led, cap in zip(self.leds, self.c_leds):
            self.VLED += led.VDD
            self.GND += led.GND + cap.p2
            self.decouple_nets.append(ShortTrace(cap.p1, led.VDD))

        for i, (led, cap) in enumerate(zip(self.leds, self.c_leds)):
            pose = grid_transform(i)
            led.at(pose)
            # beside the LED's VDD edge (+x when unrotated); the 0402's pads
            # already run along y, p1 at +y toward VDD's +y corner
            cap.at(pose * Transform((CAP_OFFSET, 0.0)))


class LEDPower(Circuit):
    """High-side switch feeding the LED grid from VBAT."""

    vbat = Power()  # battery side, 3.0–4.2 V
    vled = Power()  # switched output to LEDGrid
    enable = Port()  # RP2040 GPIO, high = LEDs powered

    def __init__(self):
        self.GND = Net(name="GND")
        self.VBAT = Net(name="VBAT")
        self.VLED = Net(name="VLED")
        self.GATE = Net(name="VLED_GATE")
        self.GND += self.vbat.Vn + self.vled.Vn
        self.VBAT += self.vbat.Vp
        self.VLED += self.vled.Vp

        self.q_switch = AO3401A()
        self.VBAT += self.q_switch.S
        self.VLED += self.q_switch.D
        self.GATE += self.q_switch.G

        self.r_gate_pu = Resistor(resistance=100e3 * ohm)
        self.gate_pu_nets = [self.r_gate_pu.p1 + self.q_switch.G, self.r_gate_pu.p2 + self.q_switch.S]

        self.q_drive = BSS138()
        self.GATE += self.q_drive.D
        self.GND += self.q_drive.S
        self.enable_net = [self.enable + self.q_drive.G]

        self.r_enable_pd = Resistor(resistance=100e3 * ohm)
        self.enable_pd_nets = [self.r_enable_pd.p1 + self.q_drive.G, self.r_enable_pd.p2 + self.q_drive.S]

        self.c_bulk = Capacitor(capacitance=4.7e-6 * F, rated_voltage_dc=10.0 * V, temperature_coefficient_code="X5R")
        self.bulk_nets = [ShortTrace(self.c_bulk.p1, self.q_switch.D), self.c_bulk.p2 + self.GND]


Device = LEDGrid
