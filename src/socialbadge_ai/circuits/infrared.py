"""
Infrared transmitter and receiver.

IRTransmitter:
- Everlight IR11-21C/TR8 940 nm emitter, switched low-side by a BSS138 from
  an RP2040 PWM pin (the 38 kHz carrier).
- 3V3 → 47 Ω → anode: (3.3 − 1.3 V) / 47 Ω ≈ 42 mA, inside the 65 mA
  continuous rating even if the pin is left high. The resistor then
  dissipates ~85 mW, so it is 0603 (0.1 W), not 0402.
- 100 kΩ gate pull-down so the emitter is off while the RP2040 boots.

IRReceiver:
- Everlight IRM-H638T/TR2 38 kHz receiver, powered from 3V3 (not the 4.2 V
  rail the earlier design used: its output idles at VCC, which must not
  exceed the RP2040's 3.3 V I/O).
- Datasheet RC filter: 100 Ω (47–220 Ω) in series with VCC, 4.7 µF (≥2.2 µF)
  to GND, both close to the receiver.
- Output is active-low; the datasheet's ≥10 kΩ pull-up is optional, and the
  RP2040's internal pull-up serves.
"""

from jitx import Circuit, Net
from jitx.common import Power
from jitx.net import Port, ShortTrace
from jitx.units import F, V, ohm
from jitxlib.parts import Capacitor, Resistor, ResistorQuery

from ..components.leds.everlight_IR11_21C import IR11_21C_TR8
from ..components.sensors.everlight_IRM_H638T import IRM_H638T_TR2
from ..components.transistors.diodes_BSS138 import BSS138

IR_LED_RESISTOR_OHMS = 47.0  # (3.3 V − 1.3 V) / 42 mA


class IRTransmitter(Circuit):
    """940 nm IR emitter driven by a low-side FET from a PWM pin."""

    v3v3 = Power()
    drive = Port()  # RP2040 PWM output, high = emitter on

    def __init__(self):
        self.GND = Net(name="GND")
        self.V3V3 = Net(name="3V3")
        self.GND += self.v3v3.Vn
        self.V3V3 += self.v3v3.Vp

        # The emitter is fixed at this circuit's origin (front); its driver is
        # free, for layout to put on the back.
        self.led = IR11_21C_TR8().at(0.0, 0.0)
        self.r_led = Resistor(ResistorQuery(case=["0603"]), resistance=IR_LED_RESISTOR_OHMS * ohm)
        self.q_drive = BSS138()
        self.led_nets = [
            self.r_led.p1 + self.v3v3.Vp,
            self.r_led.p2 + self.led.A,
            self.led.C + self.q_drive.D,
        ]
        self.GND += self.q_drive.S
        self.drive_net = [self.drive + self.q_drive.G]

        self.r_gate_pd = Resistor(resistance=100e3 * ohm)
        self.gate_pd_nets = [self.r_gate_pd.p1 + self.q_drive.G, self.r_gate_pd.p2 + self.q_drive.S]


class IRReceiver(Circuit):
    """38 kHz IR receiver module with its supply RC filter."""

    v3v3 = Power()
    out = Port()  # active-low demodulated output, to an RP2040 GPIO

    def __init__(self):
        self.GND = Net(name="GND")
        self.V3V3 = Net(name="3V3")
        self.VCC_IR = Net(name="IR_RX_VCC")
        self.GND += self.v3v3.Vn
        self.V3V3 += self.v3v3.Vp

        # Receiver and its RC filter are fixed in this circuit's frame (front),
        # the filter beside the VCC pad (2.92, 1.27).
        self.u1 = IRM_H638T_TR2().at(0.0, 0.0)
        self.GND += self.u1.GND[0] + self.u1.GND[1]
        self.out_net = [self.out + self.u1.VOUT]

        self.r_filter = Resistor(resistance=100.0 * ohm).at(4.6, -2.4, rotate=90.0)
        self.c_filter = Capacitor(
            capacitance=4.7e-6 * F, rated_voltage_dc=10.0 * V, temperature_coefficient_code="X5R"
        ).at(4.6, 0.0)
        self.filter_nets = [
            self.r_filter.p1 + self.v3v3.Vp,
            self.r_filter.p2 + self.VCC_IR,
        ]
        self.VCC_IR += self.u1.VCC
        self.c_filter_nets = [ShortTrace(self.c_filter.p1, self.u1.VCC), self.c_filter.p2 + self.GND]


Device = IRReceiver
