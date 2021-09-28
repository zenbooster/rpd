from struct import *
import time
from datetime import datetime
from enum import IntEnum, auto, unique
import serial

@unique
class ECompressMethod(IntEnum):
    ECM_NONE = 0
    ECM_LZ77 = auto()

#s = serial.Serial('com5', 1000000, timeout=1)

while True:
    try:
        s = serial.Serial('com5', 1000000, timeout=1)
        block = s.read(246)
        if not block:
            print('timeout')
            continue

        utc_time = int(time.time())
        utc = datetime.utcfromtimestamp(utc_time).strftime('%Y-%m-%d %H:%M:%S')
        print("Stream started at {} (UTC)".format(utc))
        
        name = utc
        name = name.replace(' ', '-')
        name = name.replace(':', '-')
        name += '.myoblue.rpd'

        with open(name, 'wb') as f:
            fmt = '<LLHBBL'
            sig = 0x445052
            ver = 0x0100
            bits_per_sample = 16
            sample_rate = 500
            hdr = pack(fmt, sig, utc_time, ver, ECompressMethod.ECM_NONE, bits_per_sample, sample_rate)
            f.write(hdr)

            while True:
                sig = block[:2]
                if sig != b'\xff\xff':
                    raise Exception('Invalid signature!')

                sensor_num = block[2:3][0]
                print('sensor_num = {}'.format(sensor_num))
                msg_num = block[3:6]
                msg_num = msg_num[0] + (msg_num[1] << 8) + (msg_num[2] << 16)
                print('msg_num = {}'.format(msg_num))
                vdd = block[6:8]
                vdd = round((vdd[0] + (vdd[1] << 8)) * 0.6/16384*6*2, 2)
                print('battery charge = {}'.format(vdd))
                
                block = block[8:] # оставляем только данные
                f.write(block)
                
                block = s.read(246)
                if not block:
                    print('timeout')
                    break

        print("Stream ended")

    except Exception as e:
        print('Exception: {}'.format(str(e)))
        if s:
            s = None