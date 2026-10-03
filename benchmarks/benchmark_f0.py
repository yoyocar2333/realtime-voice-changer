#!/usr/bin/env python3
"""Seeded, equal-input-support comparison of the existing ACF detector and YIN.

This isolates F0 estimation. It does not measure converted audio, hardware
latency, or human speech quality. YIN uses fixed-support difference/CMNDF,
threshold selection and parabolic interpolation, without temporal step 6.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import scipy
from scipy.signal import correlate

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from voicechanger.psola import StreamPSOLA

SR = 44100
FMIN, FMAX = 70.0, 300.0
HOP = 0.02


def yin_difference(frame: np.ndarray, max_lag: int) -> np.ndarray:
    """d(tau)=sum_j (x[j]-x[j+tau])**2 with the SAME j count at every lag."""
    x = np.asarray(frame, dtype=np.float64)
    width = len(x) - max_lag
    if width < max_lag:
        raise ValueError("YIN frame must contain at least twice max_lag samples")
    corr = correlate(x, x[:width], mode="valid", method="fft")
    prefix = np.r_[0.0, np.cumsum(x*x)]
    energy = prefix[width:] - prefix[:-width]
    diff = np.maximum(prefix[width] + energy - 2.0*corr, 0.0)
    diff[0] = 0.0
    return diff


def yin_f0(frame: np.ndarray, sr: int = SR) -> tuple[float, bool]:
    x = np.asarray(frame, dtype=np.float64)
    x = x - x.mean()
    if np.sqrt(np.mean(x*x)) < 0.005:
        return 0.0, False
    lo, hi = int(sr/FMAX), int(sr/FMIN)-1
    d = yin_difference(x, hi)
    cmnd = np.ones_like(d)
    cmnd[1:] = d[1:]*np.arange(1,len(d))/np.maximum(np.cumsum(d[1:]), 1e-20)
    candidates = np.flatnonzero(cmnd[lo:hi+1] < 0.1)
    if len(candidates):
        lag = lo + int(candidates[0])
        while lag < hi and cmnd[lag+1] < cmnd[lag]:
            lag += 1
    else:
        lag = lo + int(np.argmin(cmnd[lo:hi+1]))
    voiced = bool(cmnd[lag] < 0.3)
    refined = float(lag)
    if 0 < lag < hi:
        a,b,c = cmnd[lag-1:lag+2]
        den = a-2*b+c
        if abs(den) > 1e-20:
            refined += float(np.clip(0.5*(a-c)/den,-0.5,0.5))
    return sr/refined, voiced


def synth(case: str, duration: float, seed: int) -> tuple[np.ndarray,np.ndarray]:
    """Eight 1/k harmonics with shared random phase; analytically known F0."""
    rng = np.random.default_rng(seed)
    t = np.arange(round(duration*SR))/SR
    if case.startswith("tone_"):
        f0 = np.full_like(t,float(case.split("_")[1]))
    elif case == "glide_up":
        f0 = 80+200*t/duration
    elif case == "glide_down":
        f0 = 280-200*t/duration
    else:
        raise ValueError(case)
    phase = 2*np.pi*np.cumsum(f0)/SR + rng.uniform(0,2*np.pi)
    x = sum(np.sin(k*phase)/k for k in range(1,9))
    x = x / np.sqrt(np.mean(x*x))*0.1
    return x.astype(np.float32), f0


def summarize(rows: list[dict]) -> list[dict]:
    output = []
    keys = sorted({(r['method'],r['window_ms'],r['snr_db'],r['kind']) for r in rows},key=str)
    for method,window,snr,kind in keys:
        group = [r for r in rows if (r['method'],r['window_ms'],r['snr_db'],r['kind'])==(method,window,snr,kind)]
        errors = [abs(r['error_cents']) for r in group if r['pred_voiced'] and r['true_voiced']]
        voiced = [r for r in group if r['true_voiced']]
        unvoiced = [r for r in group if not r['true_voiced']]
        output.append(dict(method=method,window_ms=window,snr_db=snr,kind=kind,
            frames=len(group),median_abs_cents=float(np.median(errors)) if errors else None,
            p95_abs_cents=float(np.percentile(errors,95)) if errors else None,
            voiced_miss_rate=sum(not r['pred_voiced'] for r in voiced)/len(voiced) if voiced else None,
            error_over_50c_or_miss=sum(not r['pred_voiced'] or abs(r['error_cents'])>50 for r in voiced)/len(voiced) if voiced else None,
            unvoiced_false_alarm=sum(r['pred_voiced'] for r in unvoiced)/len(unvoiced) if unvoiced else None,
            rtf=float(sum(r['compute_s'] for r in group)/(len(group)*HOP)),
            p95_compute_ms=float(np.percentile([r['compute_s']*1000 for r in group],95))))
    return output


def run(seeds: int, windows: list[int]) -> tuple[list[dict],dict]:
    rows=[]
    cases=['tone_80','tone_110','tone_160','tone_220','tone_280','glide_up','glide_down']
    snrs=[-5,0,5,10,20,'clean']
    centers=np.arange(round(0.12*SR),round(1.09*SR),round(HOP*SR))
    detectors={w:StreamPSOLA(sr=SR) for w in windows}
    for w,p in detectors.items(): p._win_len=round(w*SR/1000)
    # Warm numerical kernels before timing.
    warm,_=synth('tone_160',0.1,999)
    yin_f0(warm[:round(0.04*SR)])
    for seed in range(seeds):
        for case_index,case in enumerate(cases):
            clean,truth=synth(case,1.2,seed)
            rng=np.random.default_rng(10000+seed*100+case_index)
            noise=rng.standard_normal(len(clean)); noise/=np.sqrt(np.mean(noise*noise))
            for snr in snrs:
                audio=clean if snr=='clean' else clean+noise*0.1*10**(-snr/20)
                audio=audio.astype(np.float32)
                for window,p in detectors.items():
                    p.buf=audio; p.base=0; p.period=int(SR/120)
                    for center in centers:
                        n=p._win_len; a=int(center)-n//2; frame=audio[a:a+n]
                        # Both algorithms see exactly the same finite frame.
                        for method in ('ACF','YIN-CMNDF'):
                            t0=time.perf_counter()
                            if method=='ACF':
                                period,is_v=p._detect_period(int(center)); fhat=SR/period
                            else: fhat,is_v=yin_f0(frame)
                            dt=time.perf_counter()-t0
                            rows.append(dict(method=method,window_ms=window,snr_db=snr,seed=seed,case=case,
                                kind='steady' if case.startswith('tone') else 'glide',center_sample=int(center),
                                true_voiced=True,pred_voiced=bool(is_v),true_f0=float(truth[center]),
                                f0_hz=float(fhat),error_cents=float(1200*np.log2(fhat/truth[center])) if fhat else None,compute_s=dt))
        for case in ('silence','noise'):
            rng=np.random.default_rng(20000+seed)
            audio=np.zeros(round(1.2*SR),dtype=np.float32) if case=='silence' else (0.1*rng.standard_normal(round(1.2*SR))).astype(np.float32)
            for window,p in detectors.items():
                p.buf=audio; p.base=0; p.period=int(SR/120)
                for center in centers:
                    n=p._win_len; a=int(center)-n//2; frame=audio[a:a+n]
                    for method in ('ACF','YIN-CMNDF'):
                        t0=time.perf_counter()
                        if method=='ACF': period,is_v=p._detect_period(int(center)); fhat=SR/period
                        else: fhat,is_v=yin_f0(frame)
                        dt=time.perf_counter()-t0
                        rows.append(dict(method=method,window_ms=window,snr_db='n/a',seed=seed,case=case,kind=case,
                            center_sample=int(center),true_voiced=False,pred_voiced=bool(is_v),true_f0=0.,f0_hz=float(fhat),error_cents=None,compute_s=dt))
    metadata=dict(sample_rate=SR,hop_ms=HOP*1000,windows_ms=windows,seeds=list(range(seeds)),
        duration_s=1.2,voiced_cases=cases,snr_db=snrs,frames_per_signal=len(centers),
        f0_range_hz=[FMIN,FMAX],analysis_timestamp='frame center',
        estimator_lookahead_ms={str(w):(round(w*SR/1000)-round(w*SR/1000)//2-1)/SR*1000 for w in windows},
        platform=platform.platform(),python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,
        psola_sha256=hashlib.sha256((ROOT/'voicechanger/psola.py').read_bytes()).hexdigest(),
        benchmark_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        hardware_loopback_measured=False,
        scope='Isolated frame-level synthetic F0 comparison; no PSOLA smoothing, transformation or audio devices')
    return rows,metadata


def make_plot(summary:list[dict],path:Path)->None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(8.0,2.5),layout='constrained')
    for ax,kind,title in zip(axes,['steady','glide'],['Steady harmonics','Linear pitch glides']):
        for method,color in [('ACF','#244c70'),('YIN-CMNDF','#007c86')]:
            data=[r for r in summary if r['method']==method and r['window_ms']==40 and r['kind']==kind]
            data=sorted(data,key=lambda r:99 if r['snr_db']=='clean' else r['snr_db'])
            x=np.arange(len(data)); y=[100*r['error_over_50c_or_miss'] for r in data]
            ax.plot(x,y,'o-',label=method,color=color,markersize=4)
            ax.set_xticks(x,[str(r['snr_db']) for r in data])
        ax.set(title=title,xlabel='SNR (dB)',ylim=(-2,102))
        ax.grid(axis='y',alpha=.2); ax.spines[['top','right']].set_visible(False)
    axes[0].set_ylabel('>50 cents or unvoiced (%)'); axes[1].legend(frameon=False,fontsize=9)
    fig.savefig(path,dpi=190); plt.close(fig)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--seeds',type=int,default=10)
    ap.add_argument('--windows-ms',type=int,nargs='+',default=[30,40,60])
    ap.add_argument('--output',type=Path,default=ROOT/'benchmark_results/f0_pilot')
    args=ap.parse_args()
    if args.seeds<1 or any(w*SR/1000<2*(int(SR/FMIN)-1) for w in args.windows_ms): ap.error('positive seed count and windows >= 29 ms required')
    rows,meta=run(args.seeds,args.windows_ms); summary=summarize(rows)
    args.output.mkdir(parents=True,exist_ok=True)
    with (args.output/'frames.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (args.output/'summary.json').write_text(json.dumps(dict(metadata=meta,summary=summary),ensure_ascii=False,indent=2)+'\n')
    make_plot(summary,args.output/'f0_comparison.svg')
    print(json.dumps({'output':str(args.output),'frames':len(rows),'seeds':args.seeds}))


if __name__=='__main__': main()
