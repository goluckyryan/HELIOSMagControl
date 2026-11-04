**Project Overview**
- **Purpose:** Simple serial monitoring and control utilities for magnet/cryogenics and power supply hardware used in the HELIOS setup. Provides a passive monitor for an Oxford 601-048T controller and an interactive console for an Siemens Magnet Power Suppy.

**Files**

Entry points:
- **Monitor:** [monitor.py](monitor.py) — passive serial monitor/parser for the Oxford unit; posts a status screenshot to Discord, writes He level/temp to InfluxDB, and appends a local CSV record. Normally run from cron — see [Running the Monitor](#running-the-monitor).
- **Monitor loop:** [continuous_monitor.sh](continuous_monitor.sh) — runs `monitor.py` on a fixed interval instead of cron. Takes the interval in minutes (default 30); refuses anything under 5.
- **MPS Console:** [hyperTerminal.py](hyperTerminal.py) — interactive terminal for the Siemens MPS. Raw character-at-a-time pass-through, so the unit owns the screen and its ANSI redraws work. Ctrl+Q to quit.
- **Oxford Console:** [MonitorTerminal.py](MonitorTerminal.py) — interactive terminal for the Oxford 601-048T, for driving it by hand (`ON`, `OFF`, `DEM`, …) rather than the one-shot `R` scrape that `monitor.py` does. Sends the wake sequence on connect and maps Enter to CR, as the Oxford requires. Ctrl+Q to quit.
- **Serial Explorer:** [helios_serial_explorer.py](helios_serial_explorer.py) — one-shot diagnostic; sends `R` and dumps the raw response with escape sequences annotated (`<ESC>`, `<CR>`, …). Use when the parsed output looks wrong and you need to see what actually came off the wire.

Supporting modules (imported by `monitor.py`, not run directly):
- **ANSI parser:** [render_raw.py](render_raw.py) — `parse_raw()` replays the Oxford's ANSI escape stream into a flat 40×80 character grid.
- **PNG renderer:** [txt_to_png.py](txt_to_png.py) — `render_text_file_to_png()` renders that grid to PNG, preserving the reverse-video highlight. See [PNG Rendering Notes](#png-rendering-notes).

**Requirements**
- **Python:** 3.8+ recommended
- **Packages:** pyserial, requests, Pillow
  - Install with: `pip install pyserial requests Pillow`
- **curl:** required — the InfluxDB write shells out to `curl` rather than using a Python client. Without it the He level and temp writes are lost.
- **Permissions:** Ensure the user has read/write access to the serial devices (udev rules or run with sudo).

**Discord**
- Create a file named `discord.WebHook` in the repo root containing **only** the webhook URL — no quotes, no surrounding text. It is read with a bare `read().strip()`.
- Already covered by the `*WebHook` rule in `.gitignore`, so it will not be committed.
---

## Running the Monitor

Installed as a cron job (`crontab -e`):

```
0 7 * * * /home/helios/HELIOSMagControl/monitor.py >> /home/helios/HELIOSMagControl/monitor_cron.log 2>&1
```

`2>&1` matters: without it only stdout is captured and tracebacks are handed to
cron's mailer, which discards them when no MTA is installed.

A PID lock at `/tmp/monitor_magpi.pid` prevents overlapping runs. A bad serial
read is retried up to 5 times at 5 minute intervals; if all attempts fail the
script alerts Discord and exits non-zero.

### Outputs

| File | Contents |
|---|---|
| `he_level.log` | CSV record of every good reading — the fallback if a push fails |
| `magnet_out.txt` | Parsed status screen, plain text |
| `magnet_out.png` | Same screen rendered for Discord |
| `monitor_cron.log` | Run log (stdout + stderr) |

`he_level.log` is written **before** any network push, so a reading survives even
if both Discord and InfluxDB are unreachable. The header is written once, on
creation:

```
timestamp,he_level_percent,shield_temp_k
2026-09-11 16:18:24,73.2,67.0
```

### Failure handling

Discord and InfluxDB are on different networks — Discord over the internet,
InfluxDB on the local `192.168.1.0/24` LAN — so one being down must not affect
the other. The Discord push is wrapped in `try/except` and every webhook POST
has a 30 s timeout; a failure is logged and the InfluxDB write still runs.

> Prior to 2026-09-11 the Discord upload was unguarded. When the WiFi uplink
> dropped on 2026-09-01, the resulting exception killed the script before the
> InfluxDB write on every run, losing 10 days of He level data even though the
> InfluxDB server was reachable the whole time.

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
