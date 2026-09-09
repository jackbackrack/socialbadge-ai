# Architecture: SocialBadge AI

RP2040-based wearable badge with USB-C power/programming and single-cell Li-ion battery operation.

## Module Hierarchy

```
src/socialbadge_ai/
├── components/
│   ├── mcus/raspberry_pi_RP2040.py           # RP2040 microcontroller (modeled)
│   ├── memory/winbond_W25Q128JVSIQ.py        # 16 MB QSPI flash
│   ├── power_linear_regulators/
│   │   ├── microchip_MCP73831T_2ACI_OT.py    # Li-ion charger
│   │   └── diodes_AP2112K_33TRG1.py          # 3.3V LDO
│   ├── crystals/huiyuan_HY12MSMD3225.py      # 12 MHz crystal
│   ├── diodes/mdd_SS14.py                    # Schottky diode (SMA)
│   ├── connectors/
│   │   ├── hroparts_TYPE_C_31_M_12.py        # USB-C 16-pin receptacle
│   │   └── shouhan_PH2_2P.py                 # JST-PH compatible 2-pin battery
│   └── buttons/xkb_TS_1187A.py               # SMD tactile switch
├── circuits/
│   ├── usb_c.py                              # USB-C: CC resistors, D+/D- with 27Ω
│   ├── charger.py                            # MCP73831 + PROG resistor + status LED
│   ├── power_path.py                         # Schottky-OR (VBUS, VBAT -> SYS)
│   ├── ldo_3v3.py                            # AP2112K with input/output caps
│   └── rp2040_support.py                     # RP2040 + crystal + QSPI flash + BOOTSEL/RESET
└── main.py                                   # Top-level assembly (Phase 3, future)
```

## Power Tree

| Rail        | Voltage   | Source              | Regulator       | Type     | Load                                | Current   | Sequence |
|-------------|-----------|---------------------|-----------------|----------|-------------------------------------|-----------|----------|
| VBUS        | 5 V       | USB-C connector     | —               | Input    | charger input                       | up to 500 mA | always while USB plugged in |
| VBAT        | 3.0-4.2 V | JST-PH (Li-ion)     | —               | Input    | power path                          | as needed | when battery present |
| SYS         | 3.0-5.0 V | VBUS or VBAT (OR'd) | 2× SS14 Schottky | OR-diode | LDO input                           | ~200 mA peak | live whenever any source present |
| 3V3         | 3.3 V     | SYS                 | AP2112K-3.3     | LDO 600 mA | RP2040 IOVDD/ADC_AVDD/VREG_VIN, flash | ~150 mA peak | follows SYS |
| VREG_VOUT   | 1.1 V     | (internal to RP2040) | RP2040 core LDO | LDO     | RP2040 DVDD ×2                       | <100 mA  | follows 3V3 |

### Schottky-OR tradeoff
SS14 forward drop ~0.4 V at 200 mA → SYS sits at ~4.6 V from USB and ~3.0-3.8 V from battery. AP2112K dropout (~0.4 V at 150 mA) leaves enough headroom in both cases.

### Charge current
MCP73831 PROG resistor: 2 kΩ → 500 mA (formula I = 1000 V / R_prog). For a small LiPo (e.g., 500 mAh badge battery), drop to 5 kΩ → 200 mA (0.4 C charge rate) to be gentle.

## Interface Map

| Interface  | From               | To             | Protocol      | Speed     | SI Constrained | Impedance | Note |
|------------|--------------------|----------------|---------------|-----------|----------------|-----------|------|
| USB        | RP2040 USB_DM/DP   | USB-C D+/D-    | USB 1.1 FS    | 12 Mbps   | Soft           | 90Ω diff (loose) | 27Ω series, no ESD initially |
| QSPI       | RP2040 QSPI_*      | W25Q128        | Quad SPI XIP  | 133 MHz   | No             | —         | short trace, on-board |
| SWD        | RP2040 SWCLK/SWD   | (test pads)    | SWD           | —         | No             | —         | exposed via through-hole pads or PicoProbe header |
| CRYSTAL    | RP2040 XIN/XOUT    | 12 MHz Y1      | —             | —         | No             | —         | guard ground around crystal |

## Voltage Domains

| Domain | Voltage     | Components/Pins |
|--------|-------------|-----------------|
| VBUS   | 5 V         | USB-C VBUS, charger VIN |
| VBAT   | 3.0-4.2 V   | JST connector, charger BAT, power-path input |
| SYS    | 3.0-5.0 V   | LDO input |
| 3V3    | 3.3 V       | RP2040 IOVDD/ADC_AVDD/VREG_VIN, W25Q128 VCC, button pull-ups |
| 1V1    | 1.1 V       | RP2040 DVDD (internal regulator) |

## Board (deferred to future phase)

Substrate selection (JLCPCB JLC04161H_1080 4-layer recommended) and main assembly to be defined after circuits build. This plan covers Phase 1 + Phase 2 only.

## Design Notes

- **No power switch.** Auto power-path via Schottky-OR. Battery disconnect only via JST unplug.
- **BOOTSEL** button pulls QSPI_CSn low during power-on; RESET button pulls RUN low. Standard RPi Pico style.
- **27 Ω series resistors** on USB_DM/DP are required by the RP2040 datasheet — not optional.
- **W25Q128** is SOIC-8 (208-mil wide body). RP2040 supports XIP from any QSPI flash with standard mode-0 and CMD 0xEB quad-read.
- **TESTEN pin** must be tied to GND on the PCB (not just left floating).
- **Crystal load caps** are 15 pF typical; HY12MSMD3225 datasheet should confirm CL — defer until datasheet read.
- **Charge LED** = 0805 or 0603 generic red/green LED on MCP73831 STAT (open-drain to GND when charging) via current-limit resistor (1 kΩ on 3V3) — sourced from `jitxlib.parts` LED query.
