import socket
import sys
import select
import base64

buffer = bytes()

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

def sock_read(sock, sz):
    res = bytes()
    
    while sz:
        data = sock.recv(sz)
        if not data:
            print('\nDisconnected from server')
            res = data
            break
        else:
            res += data
            sz -= len(data)
    
    return res

def unp_on_produce(v):
    global buffer
    buffer += bytes([v & 0xff, v >> 8])

host = "192.168.1.131"
port = 23
unp = Unpack12bit()
unp.onProduce(unp_on_produce)

with open("data.bin", "wb") as f:
    #s = socket.socket(AF_INET, SOCK_STREAM)
    s = socket.socket()
    s.connect((host, port))

    data = bytes()
    while True:
        socket_list = [s]
        # Get the list sockets which are readable
        read_sockets, write_sockets, error_sockets = select.select(
            socket_list, [], [])

        for sock in read_sockets:
            #incoming message from remote server
            data = sock_read(sock, 4)
            sz = int(data, 0x10)
            print("sz = {}\n".format(sz))
            
            data = sock_read(sock, sz)
            d = base64.b64decode(data)
            sz = len(d)
            d = decompress(d)

            state = 0
            v16 = 0
            for b in d:
                if state == 0:
                    v16 = b
                else:
                    v16 = v16 | (b << 8)
                    unp.push(v16)
                
                state = (state + 1) & 1
            
            f.write(buffer)
            buffer = bytes()

            #f.write(d)

    s.close()