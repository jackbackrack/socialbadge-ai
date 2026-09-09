"""
Winbond W25Q128JVSIQ — 128 Mbit (16 MB) Serial NOR Flash, Quad SPI

133 MHz Quad SPI, XIP supported. SOIC-8 208-mil (5.28 × 5.28 mm body, 7.90 mm lead span).

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
from jitx.net import Port
from jitx.toleranced import Toleranced
from jitxlib.landpatterns.generators.soic import SOIC, SOIC_DEFAULT_LEAD_PROFILE
from jitxlib.landpatterns.ipc import DensityLevel
from jitxlib.landpatterns.package import RectanglePackage
from jitxlib.symbols.box import BoxSymbol, PinGroup, Row, Column


class W25Q128JVSIQ(jitx.Component):
    mpn = "W25Q128JVSIQ"
    manufacturer = "Winbond"
    reference_designator_prefix = "U"
    datasheet = "https://datasheet.lcsc.com/datasheet/pdf/d009d960f1daec6149edaa35b7dae856.pdf"

    CS_n = Port()       # Pin 1
    DO = Port()         # Pin 2 (IO1)
    WP_n = Port()       # Pin 3 (IO2)
    GND = Port()        # Pin 4
    DI = Port()         # Pin 5 (IO0)
    CLK = Port()        # Pin 6
    HOLD_n = Port()     # Pin 7 (IO3)
    VCC = Port()        # Pin 8

    # SOIC-8 208-mil dimensions (datasheet section 10.1, page 67)
    landpattern = (
        SOIC(num_leads=8)
        .lead_profile(SOIC_DEFAULT_LEAD_PROFILE)
        .package_body(
            RectanglePackage(
                width=Toleranced.min_max(5.18, 5.38),    # E — 208 mil body width
                length=Toleranced.min_max(5.18, 5.38),   # D — body length
                height=Toleranced.min_max(1.75, 2.16),   # A — total height
            )
        )
        .density_level(DensityLevel.B)
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


Device: type[W25Q128JVSIQ] = W25Q128JVSIQ
