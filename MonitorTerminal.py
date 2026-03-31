#!/usr/bin/python3
"""
MonitorTerminal.py — Interactive terminal for Oxford 601-048T Magnet Supervisory
Copied from hyperTerminal.py, adapted for the Oxford monitor on /dev/ttyUSB1.

Usage:
    python3 MonitorTerminal.py

On connect, the wake sequence (ESC + CR) is sent automatically.
Then type commands: R, X, ON, OFF, DEM, etc.
Press Ctrl+Q to quit.
"""

import serial
import threading
import sys
import tty
import termios
import time

# --- Configuration ---
PORT = '/dev/ttyUSB1'
BAUD = 4800
LOCAL_ECHO = True   # ON: so you can see what you type (Oxford doesn't echo back commands cleanly)

def serial_to_screen(ser):
    """
    Takes data from the Oxford monitor and dumps it directly
    to your terminal, preserving ANSI escape codes for cursor
    movement, box drawing, reverse video, etc.
    """
    while True:
        try:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                sys.stdout.write(data.decode('utf-8', errors='replace'))
                sys.stdout.flush()
        except Exception as e:
            print(f"\n[Serial Error]: {e}")
            break

def keyboard_to_serial(ser):
    """
    Takes your keypresses and sends them immediately to the Oxford.
    Does NOT wait for Enter — sends each character as typed.
    Enter key sends CR (as Oxford expects).
    Press Ctrl+Q to exit.
    """
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setraw(sys.stdin.fileno())
        while True:
            char = sys.stdin.read(1)

            # Ctrl+Q to exit
            if ord(char) == 17:
                break

            # Map Enter key (LF) to CR, which Oxford expects
            if char == '\n':
                char = '\r'

            ser.write(char.encode())

            if LOCAL_ECHO:
                sys.stdout.write(char)
                sys.stdout.flush()

    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

def wake_oxford(ser):
    """
    Oxford 601-048T requires a wake sequence before accepting commands:
      1. Send ESC  — wake from idle
      2. Wait 2s
      3. Send CR   — reset cursor/state
      4. Wait 6s
      5. Flush input buffer
    """
    print("[Wake] Sending ESC...", flush=True)
    ser.write(b'\x1B')
    time.sleep(2)
    print("[Wake] Sending CR...", flush=True)
    ser.write(b'\r')
    time.sleep(6)
    ser.reset_input_buffer()
    print("[Wake] Done. Oxford is ready. Type a command (e.g. R) and press Enter.\n", flush=True)

def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.1)
        print(f"--- Connected to {PORT} at {BAUD} baud (Oxford 601-048T Monitor Terminal) ---")
        print("--- Press Ctrl+Q to Quit ---")
        print("--- Commands: R  X  ON  OFF  DEM  T  D  S  Z  H ---\n")

        # Wake the Oxford before handing over to interactive mode
        wake_oxford(ser)

        # Start receiver thread
        threading.Thread(target=serial_to_screen, args=(ser,), daemon=True).start()

        # Interactive keyboard sender (main thread)
        keyboard_to_serial(ser)

    except serial.SerialException as e:
        print(f"Error: Could not open {PORT}. {e}")
    finally:
        if 'ser' in locals():
            ser.close()
        print("\n--- Disconnected ---")

if __name__ == "__main__":
    main()
