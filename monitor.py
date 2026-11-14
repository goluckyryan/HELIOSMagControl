#!/usr/bin/env python3

import serial
import time
import re
from datetime import datetime

import os
import sys

from render_raw import parse_raw

##  OXFORD 601-048T

port='/dev/oxford601'

def readMagnet():
  try:
    out = {}
    commandESC = "\x1B"
    commandr = "\r"
    commandR = "R\r"
    ser = serial.Serial(port, 4800, timeout=120)
    ser.write(commandESC.encode())
    time.sleep(2)
    ser.write(commandr.encode())
    time.sleep(6)
    ser.reset_input_buffer()
    ser.write(commandR.encode())
    empty = 0
    lines = []
    for i in range(100):
        line = ser.readline().decode('utf-8').strip()
        if line == '':
            empty = empty + 1
        if empty > 10:
            return None, None
        found = line.find("[11;43H")
        # print(line)
        lines.append(line)
        if found >= 0:
            line[found+6:found+6:4]
            found2 = line.find("[6;41H") 
            line[found2+6:found2+6:4] 
            out['level'] = line[found2+6:found2+6+4]
            out['shield'] = line[found+7:found+7+3]
            return out, lines
            break
    return None, None
  except Exception as e:
    print(e)
    return None, None
  finally:
    if ser and ser.is_open:
       ser.close()


import requests

# Fallback record of every good reading, appended before any network push.
HE_LOG = "he_level.log"

def WriteDiscordMessage(message: str):
  #load discord webhook
  with open('discord.WebHook', 'r') as hook_file:
    webHook = hook_file.read()
    url = webHook.strip()
    formatted_message = f"```python\n{message}\n```"
    payload = {"content": formatted_message}
    requests.post(url, json=payload, timeout=30)
  return

def WriteDiscordFile(filepath: str):
    # Load webhook URL
    with open('discord.WebHook', 'r') as hook_file:
        url = hook_file.read().strip()

    with open(filepath, 'rb') as f:
        files = {
            'file': (filepath, f)  # (filename, file_object)
        }

        response = requests.post(url, files=files, timeout=30)
        response.raise_for_status()

from txt_to_png import render_text_file_to_png

if __name__ == "__main__":

    os.chdir('/home/helios/HELIOSMagControl')

    # --- PID lock: prevent overlapping instances ---
    PIDFILE = '/tmp/monitor_magpi.pid'
    if os.path.exists(PIDFILE):
        try:
            with open(PIDFILE, 'r') as pf:
                old_pid = int(pf.read().strip())
            os.kill(old_pid, 0)  # raises OSError if PID is dead
            print(f"monitor.py already running as PID {old_pid}, exiting.")
            sys.exit(0)
        except (OSError, ValueError):
            # stale pidfile -- safe to remove and continue
            try:
                os.remove(PIDFILE)
            except OSError:
                pass
    with open(PIDFILE, 'w') as pf:
        pf.write(str(os.getpid()))

    try:
     MAX_RETRIES = 5
     RETRY_INTERVAL = 300  # 5 minutes
     attempt = 0
     out = None
     raw = None
     while attempt < MAX_RETRIES:
        attempt += 1
        out, raw = readMagnet()

        # print("\n".join(lines))
        # print("\x1b[24B")
        # print(repr("\n".join(lines))) # print out the escape charators for debuggings

        now = datetime.now().strftime("%H:%M:%S  %d-%b-%Y")

        if out is None:
            print(f"{now} - readMagnet error (attempt {attempt}/{MAX_RETRIES}), retrying in {RETRY_INTERVAL//60} min...")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_INTERVAL)
            continue

        # prase the raw into simple lines
        lines = parse_raw("\n".join(raw), rows=40, cols=80).splitlines()
        if "Platform Magnet Supervisory" not in lines[1]:
            print(f"{now} - the raw data is fragmented (attempt {attempt}/{MAX_RETRIES}), retry in {RETRY_INTERVAL//60} min...")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_INTERVAL)
            continue

        # Data integrity check: validate extracted values
        try:
            level_val = float(out.get('level', -1))
            shield_val = float(out.get('shield', -1))
        except (ValueError, TypeError):
            level_val = -1
            shield_val = -1

        if level_val < 0 or level_val > 100:
            now = datetime.now().strftime('%H:%M:%S  %d-%b-%Y')
            print(f'{now} - INVALID He level: {out.get("level")} (attempt {attempt}/{MAX_RETRIES}), retry in {RETRY_INTERVAL//60} min...')
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_INTERVAL)
            out = None
            continue

        if shield_val < 0 or shield_val > 300:
            now = datetime.now().strftime('%H:%M:%S  %d-%b-%Y')
            print(f'{now} - INVALID shield temp: {out.get("shield")} (attempt {attempt}/{MAX_RETRIES}), retry in {RETRY_INTERVAL//60} min...')
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_INTERVAL)
            out = None
            continue

        break

     # --- If we exhausted retries with no valid data, alert Discord ---
     if out is None:
        alert_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        alert_msg = (
            f"\u26a0\ufe0f Magnet Pi: Oxford 601 serial read failed "
            f"{MAX_RETRIES} times in a row.\n"
            f"Last attempt: {alert_now}\n"
            f"<@1009911251322798246> <@945796346231787561> "
            f"-- please check the Oxford 601 and serial cable."
        )
        print(alert_msg)
        try:
            with open('discord.WebHook', 'r') as hook_file:
                url = hook_file.read().strip()
            requests.post(url, json={"content": alert_msg}, timeout=30)
        except Exception as e:
            print(f"Failed to post Discord alert: {e}")
        sys.exit(1)

     level = float(out.get('level', 0))
     temp = float(out.get('shield', 0))

     # Append the reading to its own log before any push, so the measurement
     # survives even if Discord or InfluxDB is unreachable.
     try:
         new_log = not os.path.exists(HE_LOG)
         with open(HE_LOG, "a", encoding="utf-8") as he_file:
             if new_log:
                 he_file.write("timestamp,he_level_percent,shield_temp_k\n")
             stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
             he_file.write(f"{stamp},{level},{temp}\n")
     except OSError as e:
         print(f"Failed to append to {HE_LOG}: {e}")

     # fix the date in line 2
     lines[2] = lines[2][:36]+ now + lines[2][36+len(now):]

     if len(sys.argv) >= 2:
         print("\n".join(lines))

     with open("magnet_out.txt", "w", encoding="utf-8") as f:
         f.write("\n".join(lines) + "\n")

     # A Discord outage must not stop the InfluxDB write below.
     try:
         render_text_file_to_png("magnet_out.txt", "magnet_out.png")
         WriteDiscordFile("magnet_out.png")
     except Exception as e:
         fail_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
         print(f"{fail_now} - Discord push failed: {type(e).__name__}: {e}")

     # post magnet_out.txt to discord using webhook
     # lines = parse_raw("\n".join(raw), rows=40, cols=80)
     # WriteDiscordMessage(lines)


     now = datetime.now().isoformat()
     print(f"{now} - He Level: {level}%, Shield Temp: {temp}K")

     #post to influxdb
     os.system(f'curl -s -XPOST "http://192.168.1.193:8086/write?db=testing" --data-binary "HeLevel value={level}" --max-time 1 --connect-timeout 1')
     os.system(f'curl -s -XPOST "http://192.168.1.193:8086/write?db=testing" --data-binary "HeTemp value={temp}" --max-time 1 --connect-timeout 1')
     # os.system(f'curl -s -XPOST "http://192.168.1.193:8086/write?db=testing" --data-binary "HePressure value={pressure}" --max-time 1 --connect-timeout 1')
    finally:
        # --- Clean up PID lock ---
        try:
            if os.path.exists(PIDFILE):
                os.remove(PIDFILE)
        except OSError:
            pass


    
        
