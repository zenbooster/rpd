#!/usr/bin/env python3
from struct import unpack
import neurokit2 as nk
from neurokit2.signal import signal_resample
import numpy as np

RESAMPLE_RATE = 400

with open('out.dat', 'rb') as f:
    #d = f.read(50000*2 + 16)
    d = f.read()
    d = d[16:]
    fmt = '<{}H'.format(len(d) // 2)
    t = unpack(fmt, d)
    d = list(t)
    d = np.array(d)
    d = signal_resample(d, sampling_rate=2000, desired_sampling_rate=RESAMPLE_RATE)
    d = d / (np.amax(d)*10)

    print(len(d))
    df, info = nk.bio_process(emg=d, sampling_rate=RESAMPLE_RATE)
    print(info)
    results = nk.bio_analyze(df, sampling_rate=RESAMPLE_RATE)
    print(results)
    
    df.plot()