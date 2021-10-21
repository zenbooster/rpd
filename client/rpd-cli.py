#!/usr/bin/env python3
import socket
import sys
import os
import select
import asyncio
import base64
from struct import *
from datetime import datetime
from enum import IntEnum, auto, unique

MAX_RPD_FILES_DATA_SIZE = 1024*1024*1024*1 # 1G

@unique
class ECompressMethod(IntEnum):
    ECM_NONE = 0
    ECM_LZ77 = auto()

@unique
class EState(IntEnum):
    ES_WAIT_FOR_SIZE = auto()
    ES_WAIT_FOR_DATA = auto()

class Unpack12bit:
    def __init__(self):
        self.on_produce = None
        self.reset();
    
    def reset(self):
        self.t = 0
        self.ov = 0
    
    def onProduce(self, f):
        self.on_produce = f

    
    def push(self, v):
        while True:
            rs = (4 - self.t) << 2
            mask = 0xfff >> (self.t << 2)
            self.on_produce((self.ov >> rs) | ((v & mask) << (16 - rs)))
            
            self.t = (self.t + 1) & 3
            self.ov = v
        
            # на 2-м шаге надо 2 раза вызвать on_produce:
            if self.t == 3:
                continue

            break

def _LZ_ReadVarSize(x, buf):
    # Read complete value (stop when byte contains zero in 8:th bit)
    y = 0
    num_bytes = 0
    chk = True
    while chk:
        b = buf[0]
        buf = buf[1:]
        
        y = (y << 7) | (b & 0x0000007f)
        num_bytes += 1

        chk = b & 0x00000080
 
    # Store value in x
    x = y
 
    # Return number of bytes read and so on...
    return (num_bytes, x)

def decompress(src):
    insize = len(src)
    length = 0
    offset = 0
    out = bytes()
    
    if insize >= 1:
        marker = src[0]
        inpos = 1
        #outpos = 0
        
        chk = True
        while chk:
            symbol = src[inpos]
            inpos += 1
            if symbol == marker:
                # We had a marker byte
                if src[inpos] == 0:
                    # It was a single occurrence of the marker byte
                    out += bytes([marker])
                    #outpos += 1
                    inpos += 1
                else:
                    # Extract true length and offset
                    n, length = _LZ_ReadVarSize(length, src[inpos:])
                    inpos += n
                    n, offset = _LZ_ReadVarSize(offset, src[inpos:])
                    inpos += n
     
                    # Copy corresponding data from history window
                    for i in range(length):
                        out += out[-offset:-offset+1]
            else:
                # No marker, plain copy
                out += bytes([symbol])

            chk = inpos < insize

    return out

host = "192.168.1.131"
port = 23

TIMEOUT = 2

class TcpClientProtocol(asyncio.Protocol):
    def recv_header(self, data):
        global recv_func

        hdr = data
        d = base64.b64decode(hdr)
        sz = len(d)

        fmt = '<LLHBBL'
        sig, utc_time, ver, compress_method, bits_per_sample, sample_rate = unpack(fmt, d)
        d = pack(fmt, sig, utc_time, ver, ECompressMethod.ECM_NONE, bits_per_sample, sample_rate)
        #d = pack(fmt, sig, utc_time, ver, ECompressMethod.ECM_NONE, 16, sample_rate)

        self.f.write(d)
        if sig != 0x445052:
            print("Invalid header signature!")
            raise Exception("Invalid header signature!")
        else:
            print("Header signature is ok.")
            print("Header version is {}.{}.".format(ver >> 8, ver & 0xff))
            
            ecm = ECompressMethod(compress_method)
            ecm_max = len(ECompressMethod) - 1
            msg = "Compress method is {}.".format((compress_method > ecm_max) and "unsupported ({})".format(compress_method) or ecm.name[4:])
            print(msg)
            if compress_method > ecm_max:
                raise Exception(msg)
            else:
                print("Bits per sample is {}.".format(bits_per_sample))
                print("Sample rate is {}.".format(sample_rate))

                utc = datetime.utcfromtimestamp(utc_time).strftime('%Y-%m-%d %H:%M:%S')
                print("Stream started at {} (UTC)".format(utc))
                
                name = utc
                name = name.replace(' ', '-')
                name = name.replace(':', '-')
                name += '.rpd'
                
                self.f.close()
                os.rename(self.fname, name)
                self.fname = name
                self.f = open(self.fname, "ab")

                self.recv_func = self.recv_block

    def recv_block(self, data):
        d = base64.b64decode(data)

        d = decompress(d)
        '''
        state = 0
        v16 = 0
        for b in d:
            if state == 0:
                v16 = b
            else:
                v16 = v16 | (b << 8)
                self.unp.push(v16)
            
            state = (state + 1) & 1
        
        self.f.write(self.buffer)
        self.buffer = bytes()
        '''
        self.f.write(d)

    def unp_on_produce(self, v):
        self.buffer += bytes([v & 0xff, v >> 8])

    def __init__(self, on_con_lost):
        # это надо бы налету проверять и делать, но пока хоть так...
        filesizes = sum(os.path.getsize(f) for f in os.listdir() if (os.path.isfile(f) and f.endswith('.rpd')))
        print("Total .rpd files data size = {}".format(filesizes))
        if filesizes >= MAX_RPD_FILES_DATA_SIZE:
            oldest_file = min([os.path.abspath(f) for f in os.listdir() if f.endswith('.rpd')], key=os.path.getctime)
            print('remove oldest_file: {}'.format(oldest_file))
            os.remove(oldest_file)
    
        self.fname = "data.rpd"
        self.f = open(self.fname, "wb")
        self.transport = None
        self.on_con_lost = on_con_lost
        
        self.queue = bytes()
        self.state = EState.ES_WAIT_FOR_SIZE
        self.recv_func = self.recv_header

        loop = asyncio.get_running_loop()
        self.timeout_handle = loop.call_later(TIMEOUT, self._timeout,)

        self.buffer = bytes()
        self.unp = Unpack12bit()
        self.unp.onProduce(self.unp_on_produce)
    
    def __done__(self):
        self.f.close()

    def connection_made(self, transport):
        self.transport = transport

        print("Connected to RPD server!")
        #transport.write(self.message.encode())

    def data_received(self, data):
        self.timeout_handle.cancel()
        loop = asyncio.get_running_loop()
        self.timeout_handle = loop.call_later(TIMEOUT, self._timeout,)

        self.queue += data
        
        if self.state == EState.ES_WAIT_FOR_SIZE:
            if len(self.queue) >= 4:
                t = self.queue[:4]
                self.queue = self.queue[4:]
                self.sz = int(t, 0x10)
                print("block size = {}".format(self.sz))
                self.state = EState.ES_WAIT_FOR_DATA
        else: # ES_WAIT_FOR_DATA
            if len(self.queue) >= self.sz:
                t = self.queue[:self.sz]
                self.queue = self.queue[self.sz:]

                self.recv_func(t)
                self.state = EState.ES_WAIT_FOR_SIZE

    def connection_lost(self, exc):
        print('The server closed the connection\n')
        self.on_con_lost.set_result(True)
    
    def _timeout(self):
        print('Timeout!\n')
        self.transport.close()

async def main():
    # Get a reference to the event loop as we plan to use
    # low-level APIs.
    message = 'vibro'

    while True:
        loop = asyncio.get_running_loop()
        on_con_lost = loop.create_future()

        while True:
            try:
                coro = loop.create_connection(lambda: TcpClientProtocol(on_con_lost), host, port)
                #coro = asyncio.ensure_future(coro)
                transport, protocol = await asyncio.wait_for(coro, timeout=TIMEOUT)

            except (OSError, asyncio.exceptions.TimeoutError) as e:
                print("Server not up retrying again...")
            else:
                break

        # Wait until the protocol signals that the connection
        # is lost and close the transport.

        try:
            await on_con_lost

        finally:
            transport.close()

asyncio.run(main())