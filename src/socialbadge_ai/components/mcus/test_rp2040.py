"""Build smoke test for the RP2040 component."""

import jitx
from jitx.container import inline
from jitx.sample import SampleDesign

from .raspberry_pi_RP2040 import RP2040


class TestDesign(SampleDesign):
    @inline
    class circuit(jitx.Circuit):
        dut = RP2040()
