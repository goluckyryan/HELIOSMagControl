#!/usr/bin/env python3

import serial
import time
import re
from datetime import datetime

import os
import sys

##  OXFORD 601-048T

def readMagnet():
  try:
    import time
    out = {}
    commandESC = "\x1B"
    commandr = "\r"
    commandR = "R\r"
    ser = serial.Serial('/dev/ttyUSB1', 4800, timeout=1)
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


if __name__ == "__main__":
    out, lines = readMagnet()

    # print("\n".join(lines))
    # print("\x1b[24B")
    # print(repr("\n".join(lines))) # print out the escape charators for debuggings


    if out is None:
        sys.exit(1)

    level = float(out.get('level', 0))
    temp = float(out.get('shield', 0))

    now = datetime.now().isoformat()
    print(f"{now} - He Level: {level}%, Shield Temp: {temp}K")

    #post to influxdb
    os.system(f'curl -s -XPOST "http://192.168.1.193:8086/write?db=testing" --data-binary "HeLevel value={level}" --max-time 1 --connect-timeout 1')
    os.system(f'curl -s -XPOST "http://192.168.1.193:8086/write?db=testing" --data-binary "HeTemp value={temp}" --max-time 1 --connect-timeout 1')
    # os.system(f'curl -s -XPOST "http://192.168.1.193:8086/write?db=testing" --data-binary "HePressure value={pressure}" --max-time 1 --connect-timeout 1')

        