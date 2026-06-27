"""Lightweight post-processing effects applied after the PSOLA stage.

All functions are stateless except :func:`reverb`, which takes an explicit
delay buffer so the caller owns the state.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt

__all__ = ["eq", "presence", "robot", "reverb"]


def eq(audio: np.ndarray, sr: int, bass: float = 0.0,
       mid: float = 0.0, treble: float = 0.0) -> np.ndarray:
    """Three-band shelving/peaking EQ (dB).

    bass < 300 Hz, mid 500-2500 Hz, treble > 4000 Hz.
    """
    out = audio.copy()
    try:
        if abs(bass) > 0.3:
            sos = butter(2, 300 / (sr / 2), btype="low", output="sos")
            out = out + sosfilt(sos, audio).astype(np.float32) * (10 ** (bass / 20) - 1)
        if abs(mid) > 0.3:
            sos = butter(2, [500 / (sr / 2), 2500 / (sr / 2)], btype="band", output="sos")
            out = out + sosfilt(sos, audio).astype(np.float32) * (10 ** (mid / 20) - 1)
        if abs(treble) > 0.3:
            sos = butter(2, 4000 / (sr / 2), btype="high", output="sos")
            out = out + sosfilt(sos, audio).astype(np.float32) * (10 ** (treble / 20) - 1)
    except ValueError:
        pass
    return out.astype(np.float32)


def presence(audio: np.ndarray, sr: int, lo: float, hi: float, gain: float) -> np.ndarray:
    """Boost a band (``lo``-``hi`` Hz) to add clarity / "air" to a voice."""
    try:
        sos = butter(2, [lo / (sr / 2), hi / (sr / 2)], btype="band", output="sos")
        return (audio + sosfilt(sos, audio).astype(np.float32) * gain).astype(np.float32)
    except ValueError:
        return audio


def robot(audio: np.ndarray) -> np.ndarray:
    """Robotic timbre: compress phase toward zero and taper block edges.

    A pure zero-phase reconstruction clicks at block boundaries, so we keep a
    fraction of the original phase and cross-fade the edges.
    """
    spec = np.fft.rfft(audio)
    mag = np.abs(spec)
    phase = np.angle(spec) * 0.15
    out = np.fft.irfft(mag * np.exp(1j * phase), len(audio)).astype(np.float32) * 0.5
    taper = max(8, len(out) // 16)
    ramp = np.linspace(0, 1, taper, dtype=np.float32)
    out[:taper] *= ramp
    out[-taper:] *= ramp[::-1]
    return out


def reverb(audio: np.ndarray, delay_buf: np.ndarray,
           wet: float = 0.3, decay: float = 0.4) -> np.ndarray:
    """Simple feedback comb reverb.  ``delay_buf`` holds state across calls."""
    out = np.zeros_like(audio)
    length = len(delay_buf)
    for i in range(len(audio)):
        j = i % length
        out[i] = audio[i] + wet * delay_buf[j]
        delay_buf[j] = audio[i] + decay * delay_buf[j]
    return out.astype(np.float32)
