#!/usr/bin/python3

import serial
import threading
import sys

# --- SETTINGS ---
PORT = '/dev/ttyUSB0'
BAUD = 9600

# Control flag
# False: Live monitor mode (printing)
# True: Command entry mode (silent)
command_mode = False

def read_from_port(ser):
    """Continuously monitors the MPS, but checks if printing is allowed."""
    global command_mode
    while ser.is_open:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
            
            # Only print if we are NOT in command mode
            if not command_mode:
                print(data, end='', flush=True)

def run_console():
    global command_mode
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        
        reader_thread = threading.Thread(target=read_from_port, args=(ser,), daemon=True)
        reader_thread.start()

        print(f"--- Siemens MPS 3600 Live Monitor ({PORT}) ---")
        print("Press [ENTER] to pause data and enter a command.")

        while True:
            # Wait for the 1st Enter
            input("") 
            
            # --- START COMMAND MODE ---
            command_mode = True

            sys.stdout.write("\033[25;1H\033[K")
            sys.stdout.flush()

            # print("\n" + "="*30)
            user_input = input("ENTER COMMAND: ")
            
            if user_input.lower() in ['exit', 'quit']:
                break
            
            # Send the command if it's not empty
            if user_input.strip():
                cmd = user_input + "\r"
                ser.write(cmd.encode('ascii'))
                # print(f"SENT: {user_input}")
            
            # print("="*30 + "\nResuming monitor...")
            
            # --- END COMMAND MODE ---
            command_mode = False

    except serial.SerialException as e:
        print(f"\n[Error] Could not open port: {e}")
    except KeyboardInterrupt:
        print("\nClosing...")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("\nDisconnected.")

if __name__ == "__main__":
    run_console()

'''
#=========== basic working code
import serial
import threading
import sys

# --- SETTINGS ---
PORT = '/dev/ttyUSB0'  # Change to /dev/ttyS4 if using WSL1 or mapped COM
BAUD = 9600

def read_from_port(ser):
    """Continuously monitors the MPS for incoming data."""
    while ser.is_open:
        if ser.in_waiting > 0:
            # Decode responses and print to screen
            data = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
            print(data, end='', flush=True)

def run_console():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        # print(f"--- Siemens MPS 3600 Console Connected ({PORT}) ---")
        # print("Type 'exit' to quit. Press Enter to send commands.")
        # print("-" * 50)

        # Start the background reader thread
        reader_thread = threading.Thread(target=read_from_port, args=(ser,), daemon=True)
        reader_thread.start()

        while True:
            # Get user input
            user_input = input("") 
            
            if user_input.lower() in ['exit', 'quit']:
                break
            
            # Send command with Siemens-required line endings
            # Most MPS 3600 units expect \r (Carriage Return)
            cmd = user_input + "\r"
            ser.write(cmd.encode('ascii'))

    except serial.SerialException as e:
        print(f"\n[Error] Could not open port: {e}")
    except KeyboardInterrupt:
        print("\nClosing...")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("\nDisconnected.")

if __name__ == "__main__":
    run_console()
'''