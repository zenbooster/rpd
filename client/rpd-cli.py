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

host = "192.168.1.129"
port = 3827

TIMEOUT = 2

class TcpClientProtocol(asyncio.Protocol):
    def recv_block(self, data):
        d = base64.b64decode(data)

        #d = decompress(d)
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

    #def unp_on_produce(self, v):
    #    self.buffer += bytes([v & 0xff, v >> 8])

    def __init__(self, on_con_lost):
        # это надо бы налету проверять и делать, но пока хоть так...
        filesizes = sum(os.path.getsize(f) for f in os.listdir() if (os.path.isfile(f) and f.endswith('.raw')))
        print("Total .rpd files data size = {}".format(filesizes))
        if filesizes >= MAX_RPD_FILES_DATA_SIZE:
            oldest_file = min([os.path.abspath(f) for f in os.listdir() if f.endswith('.raw')], key=os.path.getctime)
            print('remove oldest_file: {}'.format(oldest_file))
            os.remove(oldest_file)
    
        self.fname = "data.raw"
        self.f = open(self.fname, "wb")
        self.transport = None
        self.on_con_lost = on_con_lost
        
        self.queue = bytes()
        self.state = EState.ES_WAIT_FOR_SIZE
        self.recv_func = self.recv_block

        loop = asyncio.get_running_loop()
        self.timeout_handle = loop.call_later(TIMEOUT, self._timeout,)

        self.buffer = bytes()
        #self.unp = Unpack12bit()
        #self.unp.onProduce(self.unp_on_produce)
    
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
#            if len(self.queue) >= 4:
#                t = self.queue[:4]
#                self.queue = self.queue[4:]
            if len(self.queue) >= 2:
                t = self.queue[:2]
                self.queue = self.queue[2:]
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
    #message = 'v'

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