#!/usr/bin/env python3
from struct import unpack
import matplotlib
import matplotlib.pyplot as plt
import neurokit2 as nk
from neurokit2.signal import signal_resample
import numpy as np
import pandas as pd
import time

#SAMPLE_RATE=2000
SAMPLE_RATE=500
RESAMPLE_RATE = 500

matplotlib.use('Qt5Agg')

with open('2021-10-02-23-43-50.myoblue.rpd', 'rb') as f:
    d = f.read(16)
    if d:
    #if True:
        for i in range(39):
        #i = 0
        #while True:
            d = f.read(30*SAMPLE_RATE*2)
            if not d:
                break
            
            if i < 28:
                continue
                
            print('epoche#{}'.format(i))

            fmt = '<{}H'.format(len(d) // 2)
            t = unpack(fmt, d)
            d = list(t)
            d = np.array(d)
            d = signal_resample(d, sampling_rate=SAMPLE_RATE, desired_sampling_rate=RESAMPLE_RATE)
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
            d = nk.signal_filter(d, lowcut=12, highcut=40, method='butterworth', order=2)
            '''
            df=pd.DataFrame({'signal': d, 'id': [x*2 for x in range(len(d))]})
            df = df.set_index('id')            
            nk.signal_plot(df)
            fig = plt.gcf()
            fig.savefig("process2.png", dpi=300)
            '''

            #mean = np.mean(d)
            var = np.var(d)
            print('var={}'.format(var))
            #d = nk.signal_sanitize(df.signal)
            #d = nk.emg_clean(d, sampling_rate=RESAMPLE_RATE)
            #amp = nk.emg_amplitude(d)
            #print('amp={}'.format(amp))
            
            #plot = df.plot(subplots=True, layout=(1, 1), color=['#f44336'])
            #i+= 1