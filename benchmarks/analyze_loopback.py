#!/usr/bin/env python3
"""Measure lag between two synchronously recorded channels in a supplied WAV.

Channel 0 is a source-side reference tap; channel 1 is the returned output.
The measured scope is between those taps. No recording is made by this script.
Use an aperiodic probe with pitch/formant ratios 1, or test a timing envelope
separately when the effect intentionally changes waveform shape.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import correlate


def estimate_delay(reference,output,sr,max_lag_ms=500):
    x=np.asarray(reference,dtype=float); y=np.asarray(output,dtype=float)
    if x.ndim!=1 or y.shape!=x.shape or sr<=0 or max_lag_ms<=0:
        raise ValueError('equal-length mono arrays, positive sample rate and lag bound required')
    x=x-x.mean(); y=y-y.mean()
    if len(x)<16 or min(np.linalg.norm(x),np.linalg.norm(y))<1e-10:
        raise ValueError('recording must contain a non-silent reference and return')
    lagmax=min(int(sr*max_lag_ms/1000),len(x)//2)
    raw=correlate(y,x,mode='full',method='fft')[len(x)-1:len(x)+lagmax]
    sx=np.r_[0,np.cumsum(x*x)]; sy=np.r_[0,np.cumsum(y*y)]
    lags=np.arange(lagmax+1)
    denom=np.sqrt(sx[len(x)-lags]*(sy[-1]-sy[lags]))
    scores=np.abs(raw)/np.maximum(denom,1e-20)
    lag=int(np.argmax(scores))
    return dict(delay_samples=lag,delay_ms=lag/sr*1000,normalized_correlation=float(scores[lag]),
        peak_at_search_boundary=bool(lag==lagmax),
        review_required=bool(scores[lag]<.5 or lag==lagmax),
        scope='Delay between synchronized reference and output taps; inspect waveform and routing')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('wav',type=Path)
    p.add_argument('--reference-channel',type=int,default=0)
    p.add_argument('--output-channel',type=int,default=1)
    p.add_argument('--max-lag-ms',type=float,default=500)
    p.add_argument('--output',type=Path)
    a=p.parse_args(); sr,data=wavfile.read(a.wav)
    if data.ndim!=2 or min(a.reference_channel,a.output_channel)<0 or max(a.reference_channel,a.output_channel)>=data.shape[1]:
        p.error('a synchronized multichannel WAV and valid channel indices are required')
    if a.reference_channel==a.output_channel: p.error('reference and output channels must differ')
    result=estimate_delay(data[:,a.reference_channel],data[:,a.output_channel],sr,a.max_lag_ms)
    result.update(source_wav=str(a.wav),sample_rate=sr,reference_channel=a.reference_channel,output_channel=a.output_channel)
    encoded=json.dumps(result,indent=2)+'\n'
    if a.output: a.output.write_text(encoded)
    print(encoded,end='')


if __name__=='__main__': main()
