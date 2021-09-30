#!/usr/bin/env python3
import inspect
import os
import sys
from struct import *
from enum import IntEnum, auto, unique
from datetime import datetime
from unpack12bit import Unpack12bit

@unique
class ECompressMethod(IntEnum):
    ECM_NONE = 0
    ECM_LZ77 = auto()

class rpdff:
    def _unp_on_produce(v):
        buffer = self.buffer
        buffer += bytes([v & 0xff, v >> 8])

    def __init__(self, fname):
        self.fname = fname
        f = open(fname, 'rb')
        self.f = f
        hdr = f.read(16)
        fmt = '<LLHBBL'
        self.sig, self.utc_time, self.ver, self.compress_method, self.bits_per_sample, self.sample_rate = unpack(fmt, hdr)

        if self.sig != 0x445052:
            print("Invalid header signature!")
            raise Exception("Invalid header signature!")

        print("Header signature is ok.")
        print("Header version is {}.{}.".format(self.ver >> 8, self.ver & 0xff))
        
        ecm = ECompressMethod(self.compress_method)
        ecm_max = len(ECompressMethod) - 1
        msg = "Compress method is {}.".format((self.compress_method > ecm_max) and "unsupported ({})".format(self.compress_method) or ecm.name[4:])
        print(msg)
        if self.compress_method > ecm_max:
            raise Exception(msg)

        print("Bits per sample is {}.".format(self.bits_per_sample))
        if self.bits_per_sample != 12:
            raise Exception("Unsupported value of bits per sample!")

        print("Sample rate is {}.".format(self.sample_rate))

        utc = datetime.utcfromtimestamp(self.utc_time).strftime('%Y-%m-%d %H:%M:%S')
        print("Stream started at {} (UTC)".format(utc))

        self.on_produce = None
        unp = Unpack12bit()
        self.unp = unp

        self.block_size = ((self.sample_rate * self.bits_per_sample) // 16) * 2
        print('\nUse block size = {}'.format(self.block_size))
        
    def __done__(self):
        self.f.close()

    def onProduce(self, f):
        self.on_produce = f
        self.unp.onProduce(self.on_produce)
    
    def readNextBlock(self):
        block = self.f.read(self.block_size)
        
        if not block:
            return False

        unp = self.unp
        state = 0
        v16 = 0
        for b in block:
            if state == 0:
                v16 = b
            else:
                v16 = v16 | (b << 8)
                unp.push(v16)
            
            state = (state + 1) & 1

        return True

def get_script_dir(follow_symlinks=True):
    if getattr(sys, 'frozen', False): # py2exe, PyInstaller, cx_Freeze
        path = os.path.abspath(sys.executable)
    else:
        path = inspect.getabsfile(get_script_dir)
    if follow_symlinks:
        path = os.path.realpath(path)
    return os.path.dirname(path)

buffer = bytes()

def rpdff_on_produce(v):
    global buffer
    buffer += bytes([v & 0xff, v >> 8])

fname = '2021-09-27-21-57-17.rpd'
#fname = '2021-09-28-00-31-44.rpd'
#fname = '2021-09-29-22-49-55.rpd'
o = rpdff(get_script_dir() + os.sep + fname)

o.onProduce(rpdff_on_produce)

with open('out.dat', 'wb') as f:
    while o.readNextBlock():
        f.write(buffer)
        buffer = bytes()
        sys.stdout.write('.')
        sys.stdout.flush()
