#!/usr/bin/env python3
"""Reproducible, hardware-free benchmark for the streaming DSP pipeline.

The benchmark synthesizes a 120 Hz male /a/ vowel, feeds it through the real
AudioEngine in 1024-sample blocks, and reports:
  * measured output F0 for pitch-shifting presets,
  * pitch error against the semitone target,
  * per-block processing cost relative to the real-time audio budget,
  * startup buffering before the first non-silent processed block.

Numbers are host-dependent except the pitch target and nominal block/lookahead
budgets. This script intentionally avoids microphone/audio-device dependencies.
"""
from __future__ import annotations

import platform
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voicechanger import AudioEngine, PRESETS  # noqa: E402

SR = 44_100
BLOCK = 1_024
F0_IN = 120.0
DURATION = 3.0
PRESETS_TO_BENCH = ["年輕女聲", "成熟女聲", "蘿莉音", "大叔低音", "成熟男聲"]


def synth_voice(f0: float = F0_IN, dur: float = DURATION, seed: int = 1) -> np.ndarray:
    """Synthesize a repeatable glottal-source /a/ vowel."""
    formants = [(730, 80, 1.0), (1090, 90, 0.6), (2440, 120, 0.3), (3400, 150, 0.15)]
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    exc = np.zeros(n)
    pos = 0.0
    while pos < n:
        i = int(pos)
        exc[i] = 1.0
        pos += max(20, SR / f0 * (1 + 0.01 * rng.standard_normal()))

    out = np.zeros(n)
    for fc, bw, amp in formants:
        r = np.exp(-np.pi * bw / SR)
        th = 2 * np.pi * fc / SR
        a1 = -2 * r * np.cos(th)
        a2 = r * r
        b0 = (1 - r) * np.sqrt(1 - 2 * r * np.cos(2 * th) + r * r)
        y = np.zeros(n)
        for k in range(2, n):
            y[k] = b0 * exc[k] - a1 * y[k - 1] - a2 * y[k - 2]
        out += amp * y
    return (out / (np.max(np.abs(out)) + 1e-9) * 0.5).astype(np.float32)


def estimate_f0(x: np.ndarray, lo: float, hi: float) -> float:
    """Estimate F0 from the strongest spectral peak in a constrained band."""
    if len(x) < 1024:
        return 0.0
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    band = (freqs >= lo) & (freqs <= hi)
    if not np.any(band):
        return 0.0
    return float(freqs[band][np.argmax(spec[band])])


def run_one(name: str, audio: np.ndarray) -> dict[str, float]:
    block_budget_ms = BLOCK / SR * 1000.0

    outputs: list[np.ndarray] = []
    times_ms: list[float] = []
    first_nonzero_block = None

    for pass_idx in range(2):
        engine = AudioEngine(sr=SR, block=BLOCK)
        engine.set_preset(name)
        pass_outputs = []
        pass_times = []
        pass_first = None
        for block_idx, i in enumerate(range(0, len(audio) - BLOCK + 1, BLOCK)):
            block = audio[i:i + BLOCK]
            t0 = time.perf_counter()
            out = engine.process(block)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            pass_outputs.append(out)
            pass_times.append(dt_ms)
            if pass_first is None and np.max(np.abs(out)) > 1e-5:
                pass_first = block_idx
        if pass_idx == 1:
            outputs = pass_outputs
            times_ms = pass_times
            first_nonzero_block = pass_first

    y = np.concatenate(outputs)
    steady = y[int(0.6 * SR): int(2.4 * SR)]
    preset = PRESETS[name]
    expected = F0_IN * 2 ** (preset.pitch / 12.0)
    lo = max(45.0, expected * 0.72)
    hi = min(400.0, expected * 1.28)
    measured = estimate_f0(steady, lo, hi)
    pitch_err_pct = abs(measured - expected) / expected * 100.0

    steady_times = np.asarray(times_ms[5:] if len(times_ms) > 5 else times_ms)
    p50 = float(np.percentile(steady_times, 50))
    p95 = float(np.percentile(steady_times, 95))
    cpu_p50 = p50 / block_budget_ms * 100.0
    startup_ms = float((first_nonzero_block or 0) * block_budget_ms)

    return {
        "expected_f0": expected,
        "measured_f0": measured,
        "pitch_err_pct": pitch_err_pct,
        "p50_ms": p50,
        "p95_ms": p95,
        "cpu_p50": cpu_p50,
        "startup_ms": startup_ms,
    }


def main() -> None:
    audio = synth_voice()
    print("# Offline DSP benchmark")
    print()
    print(f"- Python: {platform.python_version()}")
    print(f"- Platform: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"- Sample rate: {SR} Hz")
    print(f"- Block size: {BLOCK} samples ({BLOCK / SR * 1000:.2f} ms audio budget)")
    print(f"- Input: synthetic male /a/, F0={F0_IN:.1f} Hz, duration={DURATION:.1f} s")
    print()
    print("| Preset | Target F0 | Measured F0 | Pitch error | p50 compute | p95 compute | p50 budget | Startup |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for name in PRESETS_TO_BENCH:
        r = run_one(name, audio)
        print(
            f"| {name} | {r['expected_f0']:.1f} Hz | {r['measured_f0']:.1f} Hz | "
            f"{r['pitch_err_pct']:.2f}% | {r['p50_ms']:.2f} ms | {r['p95_ms']:.2f} ms | "
            f"{r['cpu_p50']:.1f}% | {r['startup_ms']:.1f} ms |"
        )
    print()
    print("Host-dependent compute percentages are relative to one 1024-sample real-time block budget.")
    print("Device/driver buffering is not included in the offline startup figure.")


if __name__ == "__main__":
    main()
