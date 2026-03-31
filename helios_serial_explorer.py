#!/usr/bin/env python3
"""
HELIOS Magnet Serial Explorer
Connects to /dev/ttyUSB1 (Oxford 601-048T), sends R command,
and dumps the raw response with annotations.
"""

import serial
import time
import sys
import re

PORT   = '/dev/ttyUSB1'
BAUD   = 4800

def repr_bytes(data: bytes) -> str:
    """Human-readable representation of raw bytes including escape sequences."""
    out = []
    i = 0
    while i < len(data):
        b = data[i]
        c = chr(b)
        if b == 0x1B:
            out.append('<ESC>')
        elif b == 0x0D:
            out.append('<CR>')
        elif b == 0x0A:
            out.append('<LF>\n')
        elif b == 0x08:
            out.append('<BS>')
        elif b < 0x20 or b == 0x7F:
            out.append(f'<0x{b:02X}>')
        else:
            out.append(c)
        i += 1
    return ''.join(out)

def read_all(ser, timeout=8.0, idle_timeout=1.5) -> bytes:
    """Read until idle_timeout seconds of silence or overall timeout."""
    buf = b''
    t_start = time.time()
    t_last  = time.time()
    while True:
        chunk = ser.read(256)
        if chunk:
            buf += chunk
            t_last = time.time()
        else:
            if time.time() - t_last > idle_timeout:
                break
        if time.time() - t_start > timeout:
            break
    return buf

def main():
    print(f"Opening {PORT} at {BAUD} baud...")
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(0.5)

    print("--- Step 1: Send ESC (wake) ---")
    ser.write(b'\x1B')
    time.sleep(2)

    print("--- Step 2: Send CR (reset cursor) ---")
    ser.write(b'\r')
    time.sleep(6)

    print("--- Step 3: Flush input buffer ---")
    ser.reset_input_buffer()

    print("--- Step 4: Send 'R<CR>' (Read command) ---")
    ser.write(b'R\r')

    print("--- Collecting response... ---")
    raw = read_all(ser, timeout=10.0, idle_timeout=1.5)

    ser.close()

    print(f"\n=== RAW BYTES ({len(raw)} bytes) ===")
    print(repr_bytes(raw))

    print(f"\n=== DECODED TEXT (printable only) ===")
    text = raw.decode('utf-8', errors='replace')
    # strip ANSI escape sequences for clean view
    clean = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', text)
    clean = re.sub(r'\x1b[^[]', '', clean)
    print(clean)

    print(f"\n=== ANSI CURSOR POSITION SEQUENCES FOUND ===")
    for m in re.finditer(r'\x1b\[(\d+);(\d+)H', text):
        row, col = int(m.group(1)), int(m.group(2))
        # grab next few chars after the sequence
        pos = m.end()
        snippet = text[pos:pos+12].replace('\x1b','<ESC>').replace('\r','<CR>').replace('\n','<LF>')
        print(f"  Row {row:2d}, Col {col:2d}  →  '{snippet}'")

if __name__ == '__main__':
    main()
