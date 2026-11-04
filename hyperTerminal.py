#!/usr/bin/python3

import serial
import threading
import sys
import tty
import termios

# --- Configuration ---
PORT = '/dev/ttyUSB1'
BAUD = 9600
# In XP, 'Local Echo' was usually OFF for industrial gear.
# Local Echo means the program will print back what you type. 
# If your terminal already shows what you type, leave this OFF to avoid duplicate characters.
LOCAL_ECHO = False

def serial_to_screen(ser):
    """
    Takes data from the Power Supply and dumps it directly
    to your terminal. This allows the device to use ANSI
    escape codes to move your cursor, clear the screen, etc.
    """
    while True:
        try:
            if ser.in_waiting > 0:
                # We read byte-by-byte for maximum compatibility
                data = ser.read(ser.in_waiting)
                sys.stdout.write(data.decode('utf-8', errors='replace'))
                sys.stdout.flush()
        except Exception as e:
            print(f"\n[Serial Error]: {e}")
            break

def keyboard_to_serial(ser):
    """
    Takes your keypresses and sends them immediately to the
    Power Supply. It does NOT wait for Enter.
    """
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        # Put the terminal into 'Raw Mode' (classic HyperTerminal style)
        tty.setraw(sys.stdin.fileno())
        while True:
            char = sys.stdin.read(1)
           
            # Ctrl+Q to exit
            if ord(char) == 17:
                break
           
            # Send character to the device
            ser.write(char.encode())

            # Local Echo logic
            if LOCAL_ECHO:
                sys.stdout.write(char)
                sys.stdout.flush()
               
    finally:
        # Restore terminal settings so your bash shell isn't broken
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.1)
        print(f"--- Connected to {PORT} (HyperTerminal Replica) ---")
        print("--- Press Ctrl+Q to Quit ---\n")

        # Start the 'Receiver' thread
        threading.Thread(target=serial_to_screen, args=(ser,), daemon=True).start()

        # Start the 'Sender' (Main Thread)
        keyboard_to_serial(ser)

    except serial.SerialException as e:
        print(f"Error: Could not open {PORT}. {e}")
    finally:
        if 'ser' in locals():
            ser.close()

if __name__ == "__main__":
    main()