#!/usr/bin/env python3
from struct import unpack
import numpy as np
import pandas as pd
import scipy
from scipy.signal import butter, sosfiltfilt, find_peaks
import time

def butter_bandpass_filter(data, lowcut, highcut, fs, order=2):
    low = lowcut
    high = highcut
    sos = butter(order, [low, high], btype='bandpass', output="sos", fs=fs)
    y = sosfiltfilt(sos, data)
    return y

def remove_peaks(d, h):
    while(True):
        p, _ = find_peaks(d, height=h)
        #print(p)
        if(not len(p)):
            break
        
        for v in p:
            d[v] = h * 0.75

#SAMPLE_RATE=2000
SAMPLE_RATE=500
RESAMPLE_RATE = 500
epoche_seconds = 10
lowcut = 12
highcut=40

features = {
    'iv': [],
    'var': [],
    'e': []
}
sfeatures = {
    'iv': [],
    'var': [],
    'e': []
}
ftsize = 0

with open('2021-10-02-23-43-50.myoblue.rpd', 'rb') as f:
    d = f.read(16)
    if d:
    #if True:
        for i in range(150):
        #i = 0
        #while True:
            d = f.read(epoche_seconds*SAMPLE_RATE*2)
            if not d:
                break
            
            #if i < 99:
            #    continue
                
            print('epoche#{}'.format(i))

            fmt = '<{}H'.format(len(d) // 2)
            t = unpack(fmt, d)
            d = list(t)
            d = np.array(d)
            d = d / (1 << 14)#(np.amax(d)*2)
        
            print(len(d))
            df=pd.DataFrame({'signal': d, 'id': [x*2 for x in range(len(d))]})
            df = df.set_index('id')
            
            d = df.signal
            # подготовка сигнала:
            d = butter_bandpass_filter(d, lowcut, highcut, SAMPLE_RATE, order=2)

            # извлекаем фишки (характеристики) сигнала:
            future_iv = np.mean(np.absolute(d))
            print('iv={}'.format(future_iv))
            future_var = np.var(d)
            print('var={}'.format(future_var))
            
            ws = 6
            df = pd.DataFrame({'signal': np.absolute(d)})
            future_e = df.rolling(ws).sum()[ws-1:].max().signal
            print('E={}'.format(future_e))

            # нормализунем фишки:
            features['iv'].append(future_iv)
            features['var'].append(future_var)
            features['e'].append(future_e)
            
            sfeatures['iv'].append(future_iv)
            sfeatures['iv'].sort()
            sfeatures['var'].append(future_var)
            sfeatures['var'].sort()
            sfeatures['e'].append(future_e)
            sfeatures['e'].sort()

            ftsize += 1

            N = 50
            for k in range(10, 0, -1):
                if ftsize > 2*N*k:
                    for k, v in features.items():
                        print('{}:'.format(k))
                        rf = v
                        sf = sfeatures[k]
                        Xmin = np.array(sf[:N]).mean()
                        Xmax = np.array(sf[-N:]).mean()

                        nf = []                    
                        divider = Xmax - Xmin
                        for v in rf:
                            nf.append((v - Xmin) / divider)

                        # вычисляем пороги:
                        # фильтруем фишки вычисляя скользящие средние:
                        N = 15
                        nff = np.convolve(nf, np.ones(N)/N, mode='valid')
                        mean = nff.mean()
                        var = nff.var()
                        # ищем и удаляем пики превышающие mean и var:
                        remove_peaks(nff, mean)
                        remove_peaks(nff, var)
                        # оставшиеся пики:
                        peaks_m, _ = find_peaks(nff, height=0)
                        peaks_v, _ = find_peaks(nff, height=0)
                        print(peaks_m)
                        print(peaks_v)

                    break

            #i+= 1