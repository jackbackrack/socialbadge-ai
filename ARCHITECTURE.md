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

## Rev 2 additions (2026-11-04)

Board grows to 50 × 50 mm. Front (Top): LED grid + sensors. Back (Bottom):
everything else.

| Block | File | Supply | RP2040 pins |
|---|---|---|---|
| `LEDGrid` — 16 × WS2812C-2020-V6, 4 × 4 at 11.5 mm, serpentine chain | `circuits/front_leds.py` | VLED | GPIO11 data (PIO) |
| `LEDPower` — AO3401A high-side switch VBAT → VLED | `circuits/front_leds.py` | VBAT | GPIO10 enable (high = on) |
| `IRTransmitter` — IR11-21C, BSS138 low-side, 47 Ω | `circuits/infrared.py` | 3V3 | GPIO6 (PWM3 A) |
| `IRReceiver` — IRM-H638T 38 kHz, 100 Ω / 4.7 µF filter | `circuits/infrared.py` | 3V3 | GPIO7 (active low) |
| `DistanceSensor` — VL53L4CD (was VL53L0X, out of stock), 2.2 kΩ I²C pull-ups | `circuits/distance_sensor.py` | 3V3 | GPIO4 SDA, GPIO5 SCL (I2C0), GPIO8 XSHUT, GPIO9 INT |

New domain **VLED** = VBAT through the AO3401A (3.0–4.2 V; ~4.2 V while
charging). WS2812C-2020-V6 runs from 3.3 V and needs VIH ≥ 0.55·VDD, so the
RP2040's 3.3 V data needs no level shifter. Worst case all-white is about
16 × 15 mA = 240 mA from the battery.

### Protection (2026-11-05)

| Block | Parts | Notes |
|---|---|---|
| USB-C ESD — `circuits/usb_c.py` | USBLC6-2SC6 (C7519) on D+/D−; PESD5V0S1BL (C84374) on CC1, CC2 | Copied from eink-placard. D+/D− run *through* the USBLC6 (connector → pins 3/1, pins 4/6 → 27 Ω). 100 nF on its VBUS pin. No VBUS TVS: a 6 V SMF clamps at ~10 V, above the MCP73831's 7 V VDD abs max. |
| Reverse battery — `designs/badge_main.py` | AO3401A P-FET in the battery + lead | Drain to J2 pin 1 (`BAT_P`), source to VBAT, gate to GND. Blocks a reversed pack; ~30 mV drop at 500 mA. With USB present the charger can turn it on and trickle its pre-charge current into a reversed pack. |
| USB D+/D− — `circuits/usb_c.py`, `circuits/rp2040_support.py` | no routing structure or length matching | The RP2040 is USB 1.1 full speed (12 Mb/s); the ~25 mm path is electrically short, so D+/D− are plain traces routed side by side over L3 GND. The 27 Ω series resistors (`RP2040Support.r_usb_dp/dn`) sit at U3's USB pads, each pinned by a `ShortTrace`. |

Inner planes swapped in rev 2: L2 (layer 1) is now 3V3 and L3 (layer 2) GND,
so the back, where the USB lines and nearly all the circuitry are, sits on GND.
