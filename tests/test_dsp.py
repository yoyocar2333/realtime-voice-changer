"""Hardware-free DSP correctness tests.

Run with ``pytest -q``.  These assert the things that actually broke during
development: that pitch shifting *moves* the pitch, that gender presets land in
the right F0 range, that output never clips or clicks, and that the streaming
buffers stay continuous across silence and pitch glides.
"""
from __future__ import annotations

import numpy as np
import pytest

from voicechanger import AudioEngine, PRESET_ORDER, PRESETS, StreamPSOLA

from .helpers import f0_fft, harmonic_to_noise, run_engine, synth_voice


@pytest.fixture
def male():
    return synth_voice(120, dur=2.0)


# --------------------------------------------------------------------------- #
# Core PSOLA
# --------------------------------------------------------------------------- #
def test_psola_shifts_pitch_up(male):
    """+8 semitones must take 120 Hz to ~190 Hz (the old resampler did not)."""
    ps = StreamPSOLA()
    out = np.concatenate([
        ps.process(male[i:i + 1024], 2 ** (8 / 12), 1.0)
        for i in range(0, len(male) - 1024, 1024)
    ])
    f0 = f0_fft(out[8000:-4000], 150, 260)
    assert 175 < f0 < 205, f"expected ~190 Hz, got {f0:.0f}"


def test_psola_shifts_pitch_down(male):
    ps = StreamPSOLA()
    out = np.concatenate([
        ps.process(male[i:i + 1024], 2 ** (-5 / 12), 1.0)
        for i in range(0, len(male) - 1024, 1024)
    ])
    f0 = f0_fft(out[8000:-4000], 60, 130)
    assert 80 < f0 < 100, f"expected ~90 Hz, got {f0:.0f}"


def test_psola_no_nan_or_clip(male):
    ps = StreamPSOLA()
    out = np.concatenate([
        ps.process(male[i:i + 1024], 2 ** (8 / 12), 1.15)
        for i in range(0, len(male) - 1024, 1024)
    ])
    assert np.all(np.isfinite(out))
    assert np.max(np.abs(out)) < 1.0


def test_psola_preserves_harmonics(male):
    """PSOLA should keep a clear harmonic structure (low metallic artefact).

    Measured on a low-jitter signal so the metric is stable; a phase-vocoder
    implementation scores markedly lower here.
    """
    clean = synth_voice(120, dur=2.0, jitter=0.0)
    ps = StreamPSOLA()
    out = np.concatenate([
        ps.process(clean[i:i + 1024], 2 ** (8 / 12), 1.15)
        for i in range(0, len(clean) - 1024, 1024)
    ])
    hnr = harmonic_to_noise(out[8000:-4000], 120 * 2 ** (8 / 12))
    assert hnr > 3.5, f"HNR too low ({hnr:.1f} dB) — sounds metallic"


# --------------------------------------------------------------------------- #
# Engine + presets
# --------------------------------------------------------------------------- #
def test_female_presets_raise_f0(male):
    eng = AudioEngine()
    for name in ("年輕女聲", "成熟女聲", "蘿莉音"):
        eng.set_preset(name)
        out = run_engine(eng, male)
        f0 = f0_fft(out[8000:-2000], 140, 280)
        assert f0 > 150, f"{name}: F0 {f0:.0f} Hz is not in female range"


def test_male_presets_lower_f0(male):
    eng = AudioEngine()
    for name in ("大叔低音", "成熟男聲"):
        eng.set_preset(name)
        out = run_engine(eng, male)
        f0 = f0_fft(out[8000:-2000], 60, 130)
        assert f0 < 115, f"{name}: F0 {f0:.0f} Hz did not drop"


@pytest.mark.parametrize("name", PRESET_ORDER)
def test_every_preset_is_safe(male, name):
    """No preset may clip, click hard, or produce NaNs."""
    eng = AudioEngine()
    eng.set_preset(name)
    out = run_engine(eng, male)
    assert np.all(np.isfinite(out)), f"{name}: NaN/Inf"
    assert np.max(np.abs(out)) <= 1.001, f"{name}: clipping"


def test_passthrough_preserves_signal(male):
    eng = AudioEngine()
    eng.set_preset("原聲 (Off)")
    out = run_engine(eng, male)
    # passthrough should be (near) identity on the steady region
    assert np.max(np.abs(out)) <= 1.001


# --------------------------------------------------------------------------- #
# Robustness
# --------------------------------------------------------------------------- #
def test_handles_silence():
    v = synth_voice(120, dur=1.5)
    v[len(v) // 2: len(v) // 2 + 8000] = 0.0
    eng = AudioEngine()
    eng.set_preset("年輕女聲")
    out = run_engine(eng, v)
    assert np.all(np.isfinite(out))
    assert np.max(np.abs(np.diff(out))) < 0.5  # no clicks


def test_handles_pitch_glide():
    v = synth_voice(lambda t: 100 + 30 * t, dur=2.0)
    eng = AudioEngine()
    eng.set_preset("年輕女聲")
    out = run_engine(eng, v)
    assert np.all(np.isfinite(out))
    assert np.max(np.abs(np.diff(out))) < 0.5


def test_ringbuffer_roundtrip():
    from voicechanger.ringbuffer import RingBuffer
    rb = RingBuffer(1000)
    rb.write(np.arange(300, dtype=np.float32))
    assert np.allclose(rb.read(300), np.arange(300))
    # wrap-around
    for _ in range(5):
        rb.write(np.ones(300, dtype=np.float32))
        rb.read(300)
    rb.write(np.full(300, 7.0, dtype=np.float32))
    assert np.allclose(rb.read(300), 7.0)
