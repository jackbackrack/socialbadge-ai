"""
Winbond W25Q128JVEIQ — 128 Mbit (16 MB) Serial NOR Flash, Quad SPI

133 MHz Quad SPI, XIP supported. WSON-8 8x6-mm (Package Code E):
8.00 x 6.00 mm body, 4 pads/side at 1.27 mm pitch, 3.40 x 4.30 mm exposed
thermal pad (tied to GND per datasheet note — optional but recommended).

Pinout (from datasheet section 3.1, page 5):
  Pin 1: /CS              — chip select
  Pin 2: DO  (IO1)        — data out / quad data 1
  Pin 3: /WP (IO2)        — write protect / quad data 2
  Pin 4: GND
  Pin 5: DI  (IO0)        — data in / quad data 0
  Pin 6: CLK              — serial clock
  Pin 7: /HOLD or /RESET (IO3) — quad data 3
  Pin 8: VCC

For RP2040 QSPI XIP wiring:
  RP2040 QSPI_SD0 (pin 53)  ↔  flash DI/IO0  (pin 5)
  RP2040 QSPI_SD1 (pin 55)  ↔  flash DO/IO1  (pin 2)
  RP2040 QSPI_SD2 (pin 54)  ↔  flash /WP/IO2 (pin 3)
  RP2040 QSPI_SD3 (pin 51)  ↔  flash /HOLD/IO3 (pin 7)
  RP2040 QSPI_SCLK (pin 52) ↔  flash CLK (pin 6)
  RP2040 QSPI_CSn (pin 56)  ↔  flash /CS (pin 1)
"""

import jitx
from jitx import PadMapping
from jitx.net import Port
from jitx.shapes.composites import rectangle
from jitx.toleranced import Toleranced
from jitxlib.jlcpcb import LCSCPart
from jitxlib.landpatterns.generators.son import SON, SONLead
from jitxlib.landpatterns.ipc import DensityLevel
from jitxlib.landpatterns.leads import LeadProfile
from jitxlib.landpatterns.package import RectanglePackage
from jitxlib.symbols.box import BoxSymbol, PinGroup, Row, Column


class W25Q128JVEIQ(jitx.Component):
    mpn = "W25Q128JVEIQ"
    manufacturer = "Winbond"
    reference_designator_prefix = "U"
    datasheet = "https://datasheet.lcsc.com/datasheet/pdf/d009d960f1daec6149edaa35b7dae856.pdf"
    # Auto-measured orientation snapped to 265 deg (residual noise from our
    # IPC-generated pads not exactly matching the real footprint); the real
    # part is a plain rectangular WSON-8, so the true value is the nearby
    # clean multiple of 90, pinned explicitly instead.
    lcsc = LCSCPart("C2456297", orientation=270.0)

    CS_n = Port()       # Pin 1
    DO = Port()         # Pin 2 (IO1)
    WP_n = Port()       # Pin 3 (IO2)
    GND = Port()        # Pin 4
    DI = Port()         # Pin 5 (IO0)
    CLK = Port()        # Pin 6
    HOLD_n = Port()     # Pin 7 (IO3)
    VCC = Port()        # Pin 8

    # WSON-8 8x6-mm (Package Code E) dimensions, datasheet section 10.4, page 70.
    # Ground-truthed against the real LCSC/EasyEDA KiCad footprint for C2456297:
    # the 4-pad rows run along the 6 mm (E) edge (pitch axis) and are separated
    # across the 8 mm (D) edge (span axis) — i.e. the pins sit on the *short*
    # edges of the body, not the long ones. The generator's DualColumn layout
    # always puts its "span" axis first, so span/package.width take D and
    # package.length (the pitch-axis extent) takes E.
    landpattern = (
        SON(num_leads=8)
        .lead_profile(
            LeadProfile(
                span=Toleranced.min_max(7.90, 8.10),    # D — across-rows body length
                pitch=1.27,                              # e — lead pitch, BSC
                type=SONLead(
                    length=Toleranced.min_max(0.45, 0.55),  # L — pad length
                    width=Toleranced.min_max(0.35, 0.48),   # b — pad width
                ),
            )
        )
        .package_body(
            RectanglePackage(
                width=Toleranced.min_max(7.90, 8.10),    # D — across-rows body length
                length=Toleranced.min_max(5.90, 6.10),   # E — body width (pin-row direction)
                height=Toleranced.min_max(0.70, 0.80),   # A — total height
            )
        )
        # Exposed thermal pad: D2 is on the span axis (X), E2 on the pitch axis (Y).
        .thermal_pad(rectangle(3.40, 4.30))
        # `landpattern` is a class attribute, evaluated at import time —
        # long before BadgeDesign.__init__ sets its ambient
        # DensityLevelContext(DensityLevel.C), so that context can never
        # reach here. Set it explicitly here instead (matching
        # raspberry_pi_RP2040.py's own generator), to match the rest of the
        # design rather than silently falling back to jitxlib-standard's
        # global default (B — looser: toe 0.3mm / courtyard_excess 0.25mm
        # vs C's 0.2mm / 0.1mm).
        .density_level(DensityLevel.C)
    )

    symbol = BoxSymbol(
        rows=Row(
            left=PinGroup(CS_n, DO, WP_n, DI),
            right=PinGroup(VCC, HOLD_n, CLK),
        ),
        columns=Column(
            down=PinGroup(GND),
        ),
    )

    def __init__(self):
        # Exposed pad is not internally bonded to any signal; datasheet note
        # says it may be left floating or tied to GND — tie it to GND for
        # better thermal/EMI performance (standard practice for this package).
        lp = self.landpattern
        self.pad_mapping = PadMapping({
            self.CS_n: lp.p[1],
            self.DO: lp.p[2],
            self.WP_n: lp.p[3],
            self.GND: [lp.p[4], lp.thermal_pads[0]],
            self.DI: lp.p[5],
            self.CLK: lp.p[6],
            self.HOLD_n: lp.p[7],
            self.VCC: lp.p[8],
        })


Device: type[W25Q128JVEIQ] = W25Q128JVEIQ
