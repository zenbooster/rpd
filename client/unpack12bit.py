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