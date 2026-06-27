"""Shared helpers: synthesise glottal-source voices and measure DSP output.

These let us verify the voice changer without any audio hardware by feeding
known signals and checking the measured pitch / harmonic clarity / continuity.
"""
from __future__ import annotations

import numpy as np

SR = 44100

# A male /a/ vowel formant set and a couple of variants.
MALE_A = [(730, 80, 1.0), (1090, 90, 0.6), (2440, 120, 0.3), (3400, 150, 0.15)]


def synth_voice(f0, formants=MALE_A, dur=1.5, jitter=0.015, seed=1, sr=SR):
    """Glottal pulse train (with natural jitter) through formant resonators.

    ``f0`` may be a scalar or a callable ``f0(t_array) -> array`` for glides.
    """
    rng = np.random.default_rng(seed)
    n = int(dur * sr)
    if callable(f0):
        f0arr = f0(np.arange(n) / sr)
    else:
        f0arr = np.full(n, float(f0))
    pos = 0.0
    exc = np.zeros(n)
    while pos < n:
        i = int(pos)
        exc[i] = 1.0
        pos += max(20, sr / f0arr[i] * (1 + jitter * rng.standard_normal()))
    out = np.zeros(n)
    for fc, bw, amp in formants:
        r = np.exp(-np.pi * bw / sr)
        th = 2 * np.pi * fc / sr
        a1 = -2 * r * np.cos(th)
        a2 = r * r
        b0 = (1 - r) * np.sqrt(1 - 2 * r * np.cos(2 * th) + r * r)
        y = np.zeros(n)
        for k in range(2, n):
            y[k] = b0 * exc[k] - a1 * y[k - 1] - a2 * y[k - 2]
        out += amp * y
    return (out / (np.max(np.abs(out)) + 1e-9) * 0.5).astype(np.float32)


def f0_fft(x, lo, hi, sr=SR):
    """Fundamental frequency via the dominant spectral peak in ``[lo, hi]``."""
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    freqs = np.fft.rfftfreq(len(x), 1 / sr)
    band = (freqs > lo) & (freqs < hi)
    return float(freqs[band][np.argmax(spec[band])]) if np.any(band) else 0.0


def harmonic_to_noise(x, f0, sr=SR):
    """HNR (dB): harmonic energy vs everything else.  Higher = cleaner."""
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    freqs = np.fft.rfftfreq(len(x), 1 / sr)
    harm = 0.0
    for h in range(1, 30):
        hf = f0 * h
        if hf > sr / 2 - 100:
            break
        harm += np.sum(spec[(freqs > hf - 12) & (freqs < hf + 12)] ** 2)
    total = np.sum(spec[(freqs > 50) & (freqs < 8000)] ** 2)
    return float(10 * np.log10(harm / (total - harm + 1e-9)))


def run_engine(engine, x, block=1024):
    """Feed ``x`` to an AudioEngine block-by-block; return concatenated output."""
    out = [engine.process(x[i:i + block]) for i in range(0, len(x) - block, block)]
    return np.concatenate(out)
