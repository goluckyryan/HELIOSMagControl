#!/usr/bin/env python3

import serial
import time
import re
from datetime import datetime

# Configuration
PORT = '/dev/ttyUSB1'
BAUDRATE = 4800
TIMEOUT = 1.0           # seconds
POLL_INTERVAL = 2       # seconds between processed updates
LOG_FILE = 'magnet_status_log.csv'

# For tracking previous helium level (simple trend warning)
prev_helium = None

def strip_ansi(text):
    """Remove ANSI escape sequences completely"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def extract_values(clean_text):
    """Extract all key parameters from the cleaned status text"""
    values = {
        'helium_level_%': None,
        'He_temp_K': None,
        'pressure': None,       # likely psi
        'power_W': None,
        'extra_reading_1': None,  # 22.5 - possibly coldhead temp °C
        'extra_reading_2': None,  # 0.0 - possibly voltage/current
        'alarm_threshold': '43',
        'warn_threshold': '38',
        'status': 'OK',
        'board_time': None
    }

    # Main status line pattern (repeated many times)
    # e.g. " 4.51  21.6  97   OK"
    main_match = re.search(r'(\d\.\d{2})\s+(\d+\.\d)\s+(\d{1,3})\s+OK', clean_text)
    if main_match:
        values['He_temp_K'] = main_match.group(1)
        values['pressure'] = main_match.group(2)
        values['helium_level_%'] = main_match.group(3)

    # Power line: "0.0V  485W"
    power_match = re.search(r'0\.0V\s+(\d+)W', clean_text)
    if power_match:
        values['power_W'] = power_match.group(1)

    # Extra readings with thresholds
    # e.g. "22.5" followed by "Alarm >43" "Warn >38"
    extra1_match = re.search(r'(\d+\.\d)\s.*Alarm >43.*Warn >38', clean_text, re.DOTALL)
    if extra1_match:
        values['extra_reading_1'] = extra1_match.group(1)  # likely 22.5

    extra2_match = re.search(r'0\.0\s.*Alarm >43.*Warn >38', clean_text, re.DOTALL)
    if extra2_match:
        values['extra_reading_2'] = '0.0'

    # Board timestamp (even if wrong date)
    time_match = re.search(r'(\d{2}:\d{2}:\d{2}\s+\d{2}-\w+-\d{4})', clean_text)
    if time_match:
        values['board_time'] = time_match.group(1)

    return values

def main():
    global prev_helium
    ser = None
    try:
        ser = serial.Serial(
            port=PORT,
            baudrate=BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=TIMEOUT,
        )
        print(f"Passive monitoring started on {PORT} @ {BAUDRATE} baud")
        print("No commands sent - waiting for continuous stream...")
        print(f"Logging to: {LOG_FILE}\n")

        # Initialize CSV header
        with open(LOG_FILE, 'a') as f:
            f.write("real_time,helium_%,He_temp_K,pressure_psi,power_W,extra_22.5,extra_0.0,board_time\n")

        buffer = ""
        while True:
            data = ser.read(2048).decode('ascii', errors='ignore')
            if data:
                buffer += data

                # Process when buffer has meaningful content (e.g. contains "OK" and numbers)
                if 'OK' in buffer and '.' in buffer:
                    clean = strip_ansi(buffer)
                    values = extract_values(clean)

                    if values['helium_level_%']:  # only process if we got core values
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        helium = values['helium_level_%']

                        # Simple trend check
                        trend_note = ""
                        if prev_helium is not None:
                            diff = float(prev_helium) - float(helium)
                            if diff > 0.5:
                                trend_note = f"  ↓ dropped {diff:.1f}% since last read"
                            elif diff < -0.5:
                                trend_note = f"  ↑ increased {abs(diff):.1f}%"

                        print(f"[{now}]")
                        print(f"  Helium level     : {helium}%{trend_note}")
                        print(f"  He temperature   : {values['He_temp_K']} K")
                        print(f"  Pressure         : {values['pressure']} (likely psi)")
                        print(f"  Power            : {values['power_W']} W")
                        if values['extra_reading_1']:
                            print(f"  Extra (likely coldhead/shield): {values['extra_reading_1']}")
                        if values['extra_reading_2']:
                            print(f"  Extra reading    : {values['extra_reading_2']}")
                        print(f"  Status           : {values['status']}")
                        print(f"  Alarms           : Warn >{values['warn_threshold']}  Alarm >{values['alarm_threshold']}")
                        if values['board_time']:
                            print(f"  Board clock      : {values['board_time']} (RTC unset)")
                        print("-" * 60)

                        # Log to CSV
                        with open(LOG_FILE, 'a') as f:
                            line = (
                                f"{now},"
                                f"{helium},"
                                f"{values['He_temp_K']},"
                                f"{values['pressure']},"
                                f"{values['power_W']},"
                                f"{values.get('extra_reading_1','')},"
                                f"{values.get('extra_reading_2','')},"
                                f"{values.get('board_time','')}\n"
                            )
                            f.write(line)

                        prev_helium = helium
                    buffer = ""  # Reset buffer after successful parse

            time.sleep(0.2)  # Prevent tight loop

    except serial.SerialException as e:
        print(f"Serial port error: {e}")
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        if ser and ser.is_open:
            ser.close()
            print("Serial port closed.")

if __name__ == "__main__":
    main()