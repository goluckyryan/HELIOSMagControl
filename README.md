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

