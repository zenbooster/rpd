#!/usr/bin/env python3
from struct import unpack
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy.signal import butter, sosfiltfilt
import time

def butter_bandpass_filter(data, lowcut, highcut, fs, order=2):
    low = lowcut
    high = highcut
    sos = butter(order, [low, high], btype='bandpass', output="sos", fs=fs)
    y = sosfiltfilt(sos, data)
    return y
    
#SAMPLE_RATE=2000
SAMPLE_RATE=500
RESAMPLE_RATE = 500
epoche_seconds = 10
lowcut = 12
highcut=40

matplotlib.use('Qt5Agg')

with open('2021-10-02-23-43-50.myoblue.rpd', 'rb') as f:
    d = f.read(16)
    if d:
    #if True:
        for i in range(105):
        #i = 0
        #while True:
            d = f.read(epoche_seconds*SAMPLE_RATE*2)
            if not d:
                break
            
            if i < 99:
                continue
                
            print('epoche#{}'.format(i))

            fmt = '<{}H'.format(len(d) // 2)
            t = unpack(fmt, d)
            d = list(t)
            d = np.array(d)
            #d = signal_resample(d, sampling_rate=SAMPLE_RATE, desired_sampling_rate=RESAMPLE_RATE)
            d = d / (1 << 14)#(np.amax(d)*2)
        
            print(len(d))
            df=pd.DataFrame({'signal': d, 'id': [x*2 for x in range(len(d))]})
            df = df.set_index('id')
            '''
            nk.signal_plot(df)
            fig = plt.gcf()
            fig.savefig("process1.png", dpi=300)
            '''
            
            d = df.signal
            d = butter_bandpass_filter(d, lowcut, highcut, SAMPLE_RATE, order=2)
            '''
            df=pd.DataFrame({'signal': d, 'id': [x*2 for x in range(len(d))]})
            df = df.set_index('id')            
            nk.signal_plot(df)
            fig = plt.gcf()
            fig.savefig("process2.png", dpi=300)
            '''

            future_iv = np.mean(np.absolute(d))
            print('iv={}'.format(future_iv))
            future_var = np.var(d)
            print('var={}'.format(future_var))
            
            ws = 6
            df = pd.DataFrame({'signal': np.absolute(d)})
            future_e = df.rolling(ws).sum()[ws-1:].max().signal
            print('E={}'.format(future_e))
            
            #i+= 1