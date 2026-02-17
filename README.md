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

**Quick Start**
- Run the Oxford monitor (passive logger):

```bash
python3 monitor.py
```

- Run the MPS interactive console:

```bash
python3 MPSControl.py
```

**Configuration**
- `monitor.py` configuration (top of file):
  - **PORT:** default serial device (current value: `/dev/ttyUSB1`)
  - **BAUDRATE:** default 4800
  - **TIMEOUT:** read timeout in seconds
  - **POLL_INTERVAL:** loop delay between iterations
  - **LOG_FILE:** CSV log file (default: `magnet_status_log.csv`)

- `MPSControl.py` configuration (top of file):
  - **PORT:** default `/dev/ttyUSB0`
  - **BAUD:** default 9600

Edit these constants in the respective files to match your system device nodes.

**What `monitor.py` does**
- Opens the configured serial port in passive (read-only) mode.
- Reads raw data, strips ANSI/VT100 escape sequences, and extracts key values using regular expressions:
  - Helium percentage, He temperature (K), pressure (likely psi), power (W), and board timestamp when present.
- Prints parsed values to the console and appends CSV rows to the configured log file. CSV header is created when the script starts.
- Handles `KeyboardInterrupt` and closes the serial port cleanly.

**What `MPSControl.py` does**
- Opens the configured serial port and starts a background reader thread that prints incoming data (unless in command mode).
- Press Enter to pause the live display and enter a single-line command to send to the MPS (commands are sent with `\r`).
- Type `exit` or `quit` to close the console.

**Log format**
- The CSV created by `monitor.py` uses the header:
  `real_time,helium_%,He_temp_K,pressure_psi,power_W,extra_22.5,extra_0.0,board_time`
- `real_time` is the local host timestamp when the parse completed.
