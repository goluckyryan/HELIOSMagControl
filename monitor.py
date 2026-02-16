#!/usr/bin/env python3

import serial
from datetime import datetime
import json

def sendData(data):
    message = ""#"Test Magnet\n----------\n"
    
    if data['magnet']:
        message += "Helium Level:          %s %%\n" % data['magnet']['level']
        message += "Shield Temperature: %s K\n" % data['magnet']['shield']
    else:
        message += "WARNING: no magnet readback\n"

    
    if data['compressor']:
        if data['compressor']['status'] == 1:
            message += "Compressor: ON\n"
        else:
            message += "Compressor: OFF (WARNING)\n"
        if data['compressor']['errorCount'] > 0:
            message += "WARNING: there are compressor errors\n"
    else:
        message += "WARNING: no compressor readback\n"

    
    if data['chiller']:
        if data['chiller']['status'] == '1':
            message += "Chiller: ON\n"
        else:
            message += "Chiller: OFF (WARNING)\n"
        message += "Chiller Temperature: %s F\n" % data['chiller']['temp']
        message += "Chiller Pressure:      %s \n" % data['chiller']['pressure']
        message += "Chiller Flow:           %s \n" % data['chiller']['flow']
    else:
        message += "WARNING: no chiller readback\n"

    #for to in notify:
    #    send_email("4T: Daily Digest", message, to)


def log(fname="data.log", send=False):
    data = read()
    print(data)
    checkAlarms(data)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    json_data = json.dumps(data)
    log_entry = f"{timestamp}: {json_data}\n"
    with open(fname, 'a') as file:
        file.write(log_entry)
    if send:
        sendData(data)
        

def checkAlarms(data):
    message = ""
    if data['magnet'] is None:
        #message += "No magnet readback\n"
        pass
    else:
        if int(data['magnet']['shield']) > 90:
             message += "Shield is above 90K\n"
        if float(data['magnet']['level']) < 55.:
            message += "He Level is below 55 %%\n"
    if data['compressor'] is None:
        message += "No compressor readback\n"
    else:
        if data['compressor']['status'] != 1:
             message += "Compressor OFF\n"
    if data['chiller'] is None:
        message += "No chiller readback\n"
    else:
        if data['chiller']['status'] != '1':
            message += "Chiller OFF\n"
    if message != "":
        pass


def read():
    out = {}
    out['compressor']  = readCompressor()
    out['magnet']      = readMagnet()
    if out['magnet'] is None:
        out['magnet']      = readMagnet()
    try:
        out['chiller']     = readChiller()
    except:
        out['chiller'] = None
    return out

def readCompressor():
    ser = serial.Serial('/dev/ttyUSB3', 4800, timeout=1)
    command = "\x02DAT\r"
    ser.write(command.encode())
    res = ser.readline().decode('utf-8').strip() 
    found =  res.find("\x02")
    if found < 0:
        return None
    out = {}
    out['status'] =  int(res[43])
    out['hours']  = int(res[9:9+6])
    out['errorCount'] = int(res[49:49+2])
    out['errors'] = []
    names = {52:'SYSTEM ERROR',
             53:'Compressor fail',
             54:'Locked rotor',
             55:'OVERLOAD',
             56:'Phase/fuse ERROR',
             57:'Pressure alarm',
             58:'Helium temp. fail',
             59:'Oil circuit fail',
             60:'RAM ERROR',
             61:'ROM ERROR',
             62:'EEPROM ERROR',
             63:'DC Voltage error',
             64:'MAINS LEVEL !!!!'
             }
    for j in range(52,65):
        if res[j] == '1':
            out['errors'].append(names[j])
    return out

def readMagnet():
  try:
    import time
    out = {}
    commandESC = "\x1B"
    commandr = "\r"
    commandR = "R\r"
    ser = serial.Serial('/dev/ttyUSB2', 4800, timeout=1)
    ser.write(commandESC.encode())
    time.sleep(2)
    ser.write(commandr.encode())
    time.sleep(6)
    ser.reset_input_buffer()
    ser.write(commandR.encode())
    empty = 0
    for i in range(100):
        line = ser.readline().decode('utf-8').strip()
        if line == '':
            empty = empty + 1
        if empty > 10:
            return None
        found = line.find("[11;43H")
        print(line)
        if found >= 0:
            line[found+6:found+6:4]
            found2 = line.find("[6;41H") 
            line[found2+6:found2+6:4] 
            out['level'] = line[found2+6:found2+6+4]
            out['shield'] = line[found+7:found+7+3]
            return out
            break
    return None
  except Exception as e:
    print(e)
    return None

def readChiller():
    ser = serial.Serial('/dev/ttyUSB1', 9600, timeout=1)
    out = {}
    command = "RT\r"
    ser.write(command.encode())
    out['temp'] = ser.readline().decode('utf-8').strip() 

    command = "RW\r"
    ser.write(command.encode())
    out['status'] = ser.readline().decode('utf-8').strip() 

    command = "RK\r"
    ser.write(command.encode())
    out['pressure'] = ser.readline().decode('utf-8').strip()

    command = "RL\r"
    ser.write(command.encode())
    out['flow'] = ser.readline().decode('utf-8').strip() 

    return out

import os
import sys
if __name__ == "__main__":
    current_time = datetime.now()
    #current_minute = current_time.minute
    #if current_minute >= 57 or current_minute <= 3:
    #    log(send=True)
    #else:
    #    log(send=False)
    #sys.exit()

    #start_time = current_time.replace(hour=14, minute=0, second=0, microsecond=0)
    #end_time = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
    start_time = current_time.replace(hour=8, minute=28, second=0, microsecond=0)
    end_time = current_time.replace(hour=8, minute=35, second=0, microsecond=0)
    if start_time <= current_time <= end_time:
        log(send=True)
    else:
        log(send=False)
