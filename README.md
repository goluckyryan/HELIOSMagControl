**Project Overview**
- **Purpose:** Simple serial monitoring and control utilities for magnet/cryogenics and power supply hardware used in the HELIOS setup. Provides a passive monitor for an Oxford 601-048T controller and an interactive console for an Siemens Magnet Power Suppy.

**Files**
- **Monitor:** [monitor.py](monitor.py) — passive serial monitor/parser for the Oxford unit; writes CSV logs.
- **MPS Console:** [MPSControl.py](MPSControl.py) — interactive console to view and send commands to a Siemens MPS unit.

**Requirements**
- **Python:** 3.8+ recommended
- **Packages:** pyserial
  - Install with: `pip install pyserial`
- **Permissions:** Ensure the user has read/write access to the serial devices (udev rules or run with sudo).

**Discord**
- simply create `discord.WebHook`, paste the webHook without anything.
---

## Oxford 601-048T Serial Interface

- **Port:** `/dev/ttyUSB1`
- **Baud:** 4800
- **Protocol:** Send ESC → wait 2s → send CR → wait 6s → flush → send command + CR

### Command Reference

| Command | Syntax | Function |
|---|---|---|
| `R` | `R` | Run process display (full status screen) |
| `X` | `X` | Show command help menu (any unrecognized command also shows this) |
| `T` | `T hh:mm:ss` | Set clock time |
| `D` | `D dd/mm/yy` | Set date |
| `S` | `S hh:mm:ss` | Set start time |
| `X` | `X nn nn ..` | Simulate received CAN message (hex bytes) |
| `Z` | `Z nnn` | Set ADC reading for 0% He level (calibration) |
| `H` | `H nnn` | Set ADC reading for 100% He level (calibration) |
| `DEM` | `DEMxydddd` | Set shim demand: x=channel(0-4), y=polarity(+/-), dddd=mA |
| `ON` | `ON` | Switch on shim amplifiers |
| `OFF` | `OFF` | Switch off shim amplifiers |

Any unrecognized command returns the help menu. Confirmed: A, B, C, H (no arg) all return help.

---

## Status Flags (from R display)

### NIN_ = Inputs (signals the supervisory RECEIVES)

| Flag | Meaning |
|---|---|
| `NIN_MSG_SYSON` | CAN message: System On — main PSU saying "I am ready" |
| `NIN_MSG_EISOK` | CAN message: Emergency Interlock System OK |
| `NIN_MSG_HTROK` | CAN message: Heater OK |
| `NIN_MSG_SWITOK` | CAN message: Switch (quench protection) OK |
| `NIN_MSG_FRIG_NORM` | CAN message: Fridge (cryocooler) normal |
| `NIN_MSG_ALARMOK` | CAN message: No alarms |
| `NIN_MAN_SAMPLE` | Manual: trigger He level sample |
| `NIN_MAN_BAT_TST` | Manual: battery test trigger |
| `NIN_PROBE_OC` | He level probe open circuit fault |
| `NIN_ERDU_LOADOK` | ERDU (Emergency Run Down Unit) load OK |

### NOUT_ = Outputs (signals the supervisory SENDS)

| Flag | Meaning |
|---|---|
| `NOUT_MEASURE_ON` | **Magnet measure/enable output to main PSU (inhibit control)** |
| `NOUT_HE_WARN` | He level warning |
| `NOUT_HE_ALARM` | He level alarm |
| `NOUT_FRIDGE_ON` | Fridge on signal |
| `NOUT_FRIDGE_ALARM` | Fridge alarm |
| `NOUT_FRIDGE_WARN` | Fridge warning |
| `NOUT_EIS_ON` | EIS on signal |
| `NOUT_BAT_TEST_ERDU` | Battery test ERDU |
| `NOUT_ERDU_BATOK` | ERDU battery OK |
| `NOUT_AIR_CON_ON` | Air conditioning on |

---

## Inhibit Diagnosis (2026-03-31)

The main magnet PSU has no current. Root cause hypothesis:

- `NIN_MSG_SYSON` is **inactive** — supervisory is not receiving the "system on" CAN message from the main PSU
- As a result, `NOUT_MEASURE_ON` stays **inactive** — the enable signal to the main PSU is not asserted
- All other `NIN_MSG_*` flags are active: EIS OK, HTR OK, SWIT OK, FRIG NORM, ALARM OK
- He level (75.5%) and shield temp (64K) are both within safe limits — not the cause

**Inhibit chain:** `NIN_MSG_SYSON` inactive → `NOUT_MEASURE_ON` inactive → main PSU inhibited

**Possible fixes:**
1. Check the main magnet PSU rack for fault indicators, tripped interlocks, or a physical "System On" / "Enable" switch
2. Check CAN bus connection between main PSU and Oxford supervisory
3. If CAN message ID for `NIN_MSG_SYSON` is known, it can be injected via `X nn nn..` to test — no manual available to confirm the ID

**Note:** There is no serial command to manually set or clear the inhibit. The `ON`/`OFF` commands only control shim amplifiers, not the main magnet.

---

## PNG Rendering Notes

- Active flags (reverse video on Oxford terminal display) → **yellow background** in PNG
- Inactive flags → plain text on dark background
- Rendered by `render_raw.py` (parses ANSI escape sequences + tracks reverse-video attribute) and `txt_to_png.py` (Pillow-based PNG renderer)
- Column alignment uses `font.getlength()` for accurate per-span pixel positioning
