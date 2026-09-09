"""
3× GPIO-driven red status LEDs (Hubei KENTO KT-0603R).

Active-high drive: GPIO → 330 Ω → LED anode → LED cathode → GND.
At 3.3 V GPIO and ~1.9 V V_F the LED current is about 4 mA, matching the RP2040's
default GPIO drive strength.

KT-0603R (LCSC C2286) is a JLCPCB Basic part — same model as the charge-status LED.

External ports:
- gnd       : board GND
- gpio[0..2]: three GPIO drive lines from the MCU
"""

from jitx import Circuit, Net
from jitx.net import Port
from jitxlib.parts import Resistor

from ..components.diodes.kt_0603_red import KT_0603R


N_LEDS = 3
LED_DRIVE_RESISTOR_OHMS = 330.0  # (3.3 - 1.9 V) / 4 mA ≈ 350 Ω → 330 Ω E-series


class StatusLEDs(Circuit):
    """Three active-high red status LEDs with 330 Ω current-limit resistors."""

    gnd = Port()
    gpio = [Port() for _ in range(N_LEDS)]

    def __init__(self):
        self.GND = Net(name="GND")
        self.GND += self.gnd

        self.leds = [KT_0603R() for _ in range(N_LEDS)]
        self.r_leds = [Resistor(resistance=LED_DRIVE_RESISTOR_OHMS) for _ in range(N_LEDS)]

        # For each LED: GPIO -> R -> LED anode -> LED cathode -> GND
        self.cathode_nets = [self.leds[i].K + self.GND for i in range(N_LEDS)]
        for i in range(N_LEDS):
            self.r_leds[i].insert(self.gpio[i], self.leds[i].A)


Device = StatusLEDs
