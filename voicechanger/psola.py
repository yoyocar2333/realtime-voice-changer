"""Streaming TD-PSOLA pitch/formant shifter.

TD-PSOLA (Time-Domain Pitch-Synchronous OverLap-Add) modifies pitch and
formants entirely in the time domain by detecting glottal pitch periods and
re-laying windowed "grains" at a new spacing.  Because it never enters the
frequency domain it avoids the metallic "phase-vocoder" artefact that plagues
naive real-time voice changers.

- pitch  is controlled by the *spacing* of synthesis grains.
- formant is controlled by *resampling* each grain (changing the apparent
  vocal-tract length) and is fully decoupled from pitch.

The :class:`StreamPSOLA` processor is stateful and designed for block-based
real-time use: feed it arbitrary-sized chunks and it returns whatever output
samples are ready, maintaining continuity across calls.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import resample

__all__ = ["StreamPSOLA"]


class StreamPSOLA:
    """Real-time streaming TD-PSOLA processor.

    Parameters
    ----------
    sr:
        Sample rate in Hz.
    lookahead_s:
        Seconds of look-ahead buffered before emitting output.  Needs to cover
        the pitch-detection window plus one pitch period.  ~45 ms is a good
        default for speech.
    f0_min, f0_max:
        Search range for the autocorrelation pitch detector (Hz).
    """

    def __init__(
        self,
        sr: int = 44100,
        lookahead_s: float = 0.045,
        f0_min: float = 70.0,
        f0_max: float = 300.0,
    ) -> None:
        self.sr = sr
        self.look = int(lookahead_s * sr)
        self.f0_min = f0_min
        self.f0_max = f0_max
        self._win_len = int(0.04 * sr)  # pitch-detection window
        self.reset()

    # ------------------------------------------------------------------ #
    def reset(self) -> None:
        """Clear all internal state (call when parameters change abruptly)."""
        self.buf = np.zeros(0, dtype=np.float32)
        self.base = 0                 # absolute index of buf[0]
        self.next_a = 0               # next analysis-epoch absolute index
        self.epochs: list[tuple[int, int, bool]] = []  # (pos, period, voiced)
        self.next_s = 0.0             # next synthesis-epoch absolute index
        self.out = np.zeros(0, dtype=np.float32)
        self.out_base = 0
        self.period = int(self.sr / 120)  # running period estimate

    # ------------------------------------------------------------------ #
    def _detect_period(self, center: int) -> tuple[int, bool]:
        """Estimate the pitch period near ``center`` via autocorrelation.

        Returns ``(period_samples, voiced)``.  Falls back to the previous
        estimate when the frame is silent or unvoiced.
        """
        w = self._win_len
        a = center - self.base - w // 2
        b = a + w
        if a < 0 or b > len(self.buf):
            return self.period, True
        frame = self.buf[a:b].astype(np.float64)
        frame -= np.mean(frame)
        if np.sqrt(np.mean(frame**2)) < 0.005:
            return self.period, False
        corr = np.correlate(frame, frame, "full")[len(frame) - 1:]
        lo = int(self.sr / self.f0_max)
        hi = int(self.sr / self.f0_min)
        seg = corr[lo:hi]
        if len(seg) == 0:
            return self.period, False
        peak = int(np.argmax(seg)) + lo
        voiced = corr[peak] > 0.3 * corr[0]
        return (peak, True) if voiced else (self.period, False)

    # ------------------------------------------------------------------ #
    def process(
        self, samples: np.ndarray, pitch_ratio: float, formant_ratio: float
    ) -> np.ndarray:
        """Push ``samples`` and return any output samples that are ready.

        Parameters
        ----------
        samples:
            1-D float32 input block.
        pitch_ratio:
            Output/input fundamental ratio.  ``2 ** (semitones / 12)``.
        formant_ratio:
            Vocal-tract scaling.  ``>1`` shortens the tract (more female/child),
            ``<1`` lengthens it (more male).
        """
        self.buf = np.concatenate([self.buf, samples])
        end_abs = self.base + len(self.buf)

        # --- place analysis epochs up to the look-ahead boundary ----------
        while self.next_a + self.period < end_abs - self.look:
            period, voiced = self._detect_period(self.next_a)
            self.period = int(0.7 * self.period + 0.3 * period)
            self.epochs.append((self.next_a, self.period, voiced))
            self.next_a += self.period

        target = end_abs - self.look
        need = target - self.out_base
        if need > len(self.out):
            self.out = np.concatenate(
                [self.out, np.zeros(need - len(self.out) + 1, dtype=np.float32)]
            )

        # --- synthesise grains at the new spacing -------------------------
        while self.next_s < target and self.epochs:
            centers = [e[0] for e in self.epochs]
            j = min(range(len(centers)), key=lambda k: abs(centers[k] - self.next_s))
            ep, period, voiced = self.epochs[j]
            a = ep - period - self.base
            b = ep + period - self.base
            if a < 0 or b > len(self.buf) or b - a < 4:
                self.next_s += max(20, self.period / pitch_ratio)
                continue

            grain = self.buf[a:b].copy() * np.hanning(b - a).astype(np.float32)
            if formant_ratio and abs(formant_ratio - 1.0) > 0.02:
                grain = self._formant_resample(grain, formant_ratio)

            c = int(self.next_s) - self.out_base
            s = c - len(grain) // 2
            e = s + len(grain)
            g = grain
            if s < 0:
                g = g[-s:]
                s = 0
            if e > len(self.out):
                self.out = np.concatenate(
                    [self.out, np.zeros(e - len(self.out), dtype=np.float32)]
                )
            self.out[s:e] += g
            step = (period / pitch_ratio) if voiced else period
            self.next_s += max(20, step)

        # --- emit the stable region --------------------------------------
        avail = min(int(self.next_s) - self.out_base - self.period, len(self.out))
        if avail <= 0:
            ready = np.zeros(0, dtype=np.float32)
        else:
            ready = self.out[:avail].copy()
            self.out = self.out[avail:]
            self.out_base += avail

        self._trim()
        return ready

    # ------------------------------------------------------------------ #
    @staticmethod
    def _formant_resample(grain: np.ndarray, formant_ratio: float) -> np.ndarray:
        """Resample a grain to shift formants, keeping its length constant."""
        target = max(4, int(len(grain) / formant_ratio))
        res = resample(grain, target)
        if target < len(grain):
            pad = (len(grain) - target) // 2
            res = np.concatenate(
                [np.zeros(pad), res, np.zeros(len(grain) - target - pad)]
            )
        else:
            start = (target - len(grain)) // 2
            res = res[start:start + len(grain)]
        return res.astype(np.float32)

    # ------------------------------------------------------------------ #
    def _trim(self) -> None:
        """Drop consumed history to keep buffers bounded."""
        keep_from = min(self.next_a, int(self.next_s)) - 2 * self.period - self.look
        if keep_from > self.base:
            cut = keep_from - self.base
            if 0 < cut < len(self.buf):
                self.buf = self.buf[cut:]
                self.base += cut
                self.epochs = [e for e in self.epochs if e[0] >= self.base - 2 * self.period]
