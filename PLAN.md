2026-05-19

boa
reset-art
R@@k7@@1*
121000358    routing
325218336759 account

2026-05-18

# Project Plan: SocialBadge AI Badge

## Architecture Summary

See `ARCHITECTURE.md` for power tree, interface map, and module hierarchy.

## Data Sources (pending user approval)

| Component                       | MPN                    | Package      | LCSC      | Datasheet                                  | Footprint Method |
|---------------------------------|------------------------|--------------|-----------|--------------------------------------------|------------------|
| RP2040 (done)                   | RP2040                 | QFN-56       | C2040     | datasheets/rp2040.pdf (local)              | JITX QFN generator (done) |
| Li-ion charger                  | MCP73831T-2ACI/OT      | SOT-23-5     | C424093   | Microchip site download to datasheets/     | JITX SOT23_5 generator |
| 3.3V LDO                        | AP2112K-3.3TRG1        | SOT-25       | C51118    | Diodes Inc site download to datasheets/    | JITX SOT23_5 generator |
| QSPI flash                      | W25Q128JVSIQ           | SOIC-8 (208-mil) | C97521 | Winbond site download to datasheets/       | JITX SOIC generator |
| Schottky diode                  | SS14                   | SMA (DO-214AC) | C2480   | MDD datasheet download to datasheets/      | LCSC .kicad_mod (needs approval) |
| 12 MHz crystal                  | HY12MSMD3225EB1R30     | 3225 4-pad SMD | C7275086 | Huiyuan datasheet (TBD) or generic 3225 dims | LCSC .kicad_mod (needs approval) |
| USB-C receptacle                | TYPE-C-31-M-12         | non-standard | C165948   | Korean Hroparts drawing (LCSC)             | LCSC .kicad_mod (needs approval) |
| JST-PH 2.0 2P (SMD)             | 2.0-2P WT (SHOU HAN)   | non-standard | C668620   | SHOU HAN drawing (LCSC)                    | LCSC .kicad_mod (needs approval) |
| Tactile switch                  | TS-1187A-B-A-B         | non-standard | C318884   | XKB drawing (LCSC)                         | LCSC .kicad_mod (needs approval) |
| Status LED                      | (generic 0603 red)     | 0603         | —         | sourced via jitxlib.parts query             | jitxlib.parts query (no model needed) |
| Resistors / capacitors          | (various)              | 0402/0603    | —         | —                                           | jitxlib.parts query (no model needed) |

**Footprint consent required:** for the five components marked "(needs approval)", we'd download .kicad_mod files via `parts2jitx-lcsc <C-number> --footprint`, which uses EasyEDA-derived footprint data. This needs explicit per-project approval from the user before Phase 1 starts.

---

## Phase 1: Components

### [comp-01] RP2040 microcontroller — COMPLETED

- **File:** `src/socialbadge_ai/components/mcus/raspberry_pi_RP2040.py`
- **Status:** completed (modeled in earlier conversation)

### [comp-02] MCP73831T-2ACI/OT Li-ion charger

- **Type:** component
- **Skill:** jitx-component-modeler
- **Description:** Single-cell Li-ion/LiPo linear charger, 4.2 V termination, programmable current via PROG pin. SOT-23-5 package, 5 pins: VSS, VBAT, VDD, STAT, PROG.
- **Inputs:** Microchip datasheet (download to datasheets/mcp73831.pdf), JITX SOT23_5 generator
- **Verification:** `python -m jitx build socialbadge_ai.components.power_linear_regulators.test_mcp73831.TestDesign`
- **Status:** pending

### [comp-03] AP2112K-3.3TRG1 3.3V LDO

- **Type:** component
- **Skill:** jitx-component-modeler
- **Description:** 600 mA fixed 3.3V LDO with enable, low dropout (~250 mV). SOT-25 (SOT-23-5) package, 5 pins: VIN, GND, EN, NC, VOUT.
- **Inputs:** Diodes Inc datasheet (download), JITX SOT23_5 generator
- **Verification:** `python -m jitx build socialbadge_ai.components.power_linear_regulators.test_ap2112.TestDesign`
- **Status:** pending

### [comp-04] W25Q128JVSIQ 16 MB QSPI flash

- **Type:** component
- **Skill:** jitx-component-modeler
- **Description:** 128 Mbit (16 MB) Quad-SPI NOR flash. SOIC-8 208-mil wide body. Pins: CS#, DO/IO1, WP#/IO2, GND, DI/IO0, CLK, HOLD#/IO3, VCC.
- **Inputs:** Winbond datasheet (download), JITX SOIC generator
- **Verification:** `python -m jitx build socialbadge_ai.components.memory.test_w25q128.TestDesign`
- **Status:** pending

### [comp-05] SS14 Schottky diode

- **Type:** component
- **Skill:** jitx-component-modeler
- **Description:** 1 A, 40 V Schottky in SMA (DO-214AC). 2-pin polarized. Used ×2 for VBUS/VBAT power OR.
- **Inputs:** MDD datasheet, LCSC kicad_mod (or hand-spec'd SMA standard dimensions)
- **Verification:** `python -m jitx build socialbadge_ai.components.diodes.test_ss14.TestDesign`
- **Status:** pending

### [comp-06] 12 MHz crystal HY12MSMD3225EB1R30

- **Type:** component
- **Skill:** jitx-component-modeler
- **Description:** 12 MHz fundamental crystal in 3.2×2.5 mm 4-pad SMD package. CL TBD from datasheet (typical 8 pF or 12 pF). Pins: XI, GND1, XO, GND2 (or all 4 active, 2 of which are case-ground).
- **Inputs:** Huiyuan datasheet (LCSC), LCSC kicad_mod (or hand-specified 3225 dims)
- **Verification:** `python -m jitx build socialbadge_ai.components.crystals.test_hy12m.TestDesign`
- **Status:** pending

### [comp-07] TYPE-C-31-M-12 USB-C receptacle

- **Type:** component
- **Skill:** jitx-component-modeler
- **Description:** 16-pin USB Type-C receptacle, mid-mount, USB 2.0-only data lines (no SS pairs). VBUS, CC1, CC2, D+ ×2, D- ×2, GND, SHIELD.
- **Inputs:** LCSC kicad_mod download (REQUIRES APPROVAL)
- **Verification:** `python -m jitx build socialbadge_ai.components.connectors.test_usbc.TestDesign`
- **Status:** pending

### [comp-08] JST-PH 2.0 2-pin battery connector

- **Type:** component
- **Skill:** jitx-component-modeler
- **Description:** SMD horizontal 2-pin 2.0 mm pitch battery connector, JST-PH compatible. Pins: 1 = BAT+, 2 = BAT-.
- **Inputs:** LCSC kicad_mod download (REQUIRES APPROVAL)
- **Verification:** `python -m jitx build socialbadge_ai.components.connectors.test_jstph.TestDesign`
- **Status:** pending

### [comp-09] TS-1187A-B-A-B tactile switch

- **Type:** component
- **Skill:** jitx-component-modeler
- **Description:** SMD momentary tactile button. Two functional contacts. Used ×2 for BOOTSEL and RESET.
- **Inputs:** LCSC kicad_mod download (REQUIRES APPROVAL)
- **Verification:** `python -m jitx build socialbadge_ai.components.buttons.test_ts1187.TestDesign`
- **Status:** pending

---

## Phase 2: Application Circuits

### [cir-01] USB-C interface

- **Type:** circuit
- **Skill:** jitx-circuit-builder
- **Dependencies:** [comp-07]
- **Description:** USB-C receptacle with 5.1 kΩ CC1 and CC2 pulldowns (advertise device, accept 5 V/500 mA), 27 Ω series resistors on D+/D-, VBUS+GND nets exposed, shield connected to GND via 1 MΩ + capacitor (or hard-tied — TBD). D+ and D- pairs from both rows of the connector tied together.
- **Inputs:** USB-C spec for sink CC resistors, RP2040 datasheet for D+/D- series resistor requirement
- **Engineering questions:**
  - Hard-tie shield to GND or soft-ground? → recommend hard-tie for a wearable.
  - ESD protection diodes on D+/D-? → defer, not required for FS USB.
- **Verification:** `python -m jitx build socialbadge_ai.circuits.test_usb_c.TestDesign`
- **Status:** pending

### [cir-02] Charger circuit

- **Type:** circuit
- **Skill:** jitx-circuit-builder
- **Dependencies:** [comp-02]
- **Description:** MCP73831 with VBUS input, VBAT output to battery connector, 1 µF input and 4.7 µF output caps, PROG resistor (default 2 kΩ for 500 mA — adjustable), STAT pin to a status LED (anode to 3V3, cathode to STAT via 1 kΩ — STAT is open-drain low when charging).
- **Inputs:** Microchip MCP73831 datasheet — application circuit Figure 5-1
- **Engineering questions:**
  - Target charge current? Default 500 mA (R_PROG = 2 kΩ).
  - Status LED location/color? Default 0603 red.
- **Verification:** `python -m jitx build socialbadge_ai.circuits.test_charger.TestDesign`
- **Status:** pending

### [cir-03] Power path

- **Type:** circuit
- **Skill:** jitx-circuit-builder
- **Dependencies:** [comp-05]
- **Description:** Two SS14 Schottkys with anodes on VBUS and VBAT, cathodes tied together at SYS rail. Adds 100 nF on SYS for transient stability.
- **Inputs:** —
- **Verification:** `python -m jitx build socialbadge_ai.circuits.test_power_path.TestDesign`
- **Status:** pending

### [cir-04] 3.3 V LDO

- **Type:** circuit
- **Skill:** jitx-circuit-builder
- **Dependencies:** [comp-03]
- **Description:** AP2112K with 1 µF input cap, 1 µF output cap, EN tied to VIN (always enabled), NC pin per datasheet.
- **Inputs:** Diodes Inc AP2112K datasheet — application circuit
- **Verification:** `python -m jitx build socialbadge_ai.circuits.test_ldo_3v3.TestDesign`
- **Status:** pending

### [cir-05] RP2040 support circuit

- **Type:** circuit
- **Skill:** jitx-circuit-builder
- **Dependencies:** [comp-01 (done), comp-04, comp-06, comp-09]
- **Description:** Full RP2040 support per RPi datasheet Minimal Design Example: 100 nF on each of 6 IOVDD pins, 100 nF on ADC_AVDD, 100 nF + 4.7 µF (or 1 µF) on VREG_VIN, 4.7 µF on VREG_VOUT (which also feeds both DVDD pins through a short trace), 12 MHz crystal with two CL caps on XIN/XOUT, RESET button on RUN with 10 kΩ pull-up + 100 nF debounce, BOOTSEL button on QSPI_CS via a 1 kΩ isolation resistor to flash's CS#, W25Q128 connected to QSPI_SD0..3/SCLK/CSn with 100 nF decoupling, TESTEN tied to GND.
- **Inputs:** RP2040 datasheet Chapter 2.9 "Minimal Design Example" (page 230-ish)
- **Engineering questions:**
  - BOOTSEL via direct switch on flash CS or via QSPI_CSn directly? → use isolation resistor pattern from RPi Pico schematic.
  - Crystal CL caps: 15 pF default unless datasheet says otherwise.
- **Verification:** `python -m jitx build socialbadge_ai.circuits.test_rp2040_support.TestDesign`
- **Status:** pending

---

## Phase 3 + 4: Top-level assembly + substrate + build

Deferred. Plan a separate session once Phase 2 circuits all build clean.

---

## Open Decisions (block Phase 0 → 1 gate)

1. **LCSC/EasyEDA footprint consent** — needed for SS14, crystal, USB-C, JST connector, tact button. Without this, those five components cannot proceed.
2. **Charge current target** — 500 mA default OK or different value?
3. **Status/charge LED** — include in plan or skip?
4. **Crystal CL caps** — accept 15 pF default or read from Huiyuan datasheet first?
