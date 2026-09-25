# Architecture

This document explains how the voice changer works and why it sounds the way
it does.

## Signal flow

```
                 ┌──────────── AudioEngine.process (per 1024-sample block) ───────────┐
 mic ──► input   │  noise gate ─► StreamPSOLA (pitch + formant) ─► makeup gain ─►      │
        block    │  EQ ─► presence ─► robot? ─► reverb? ─► output gain ─► soft limiter │
                 │                                              ─► boundary de-click   │──┬─► CABLE Input ─► Discord
                 └────────────────────────────────────────────────────────────────────┘  └─► RingBuffer ─► headphones (monitor)
```

Two `sounddevice` streams run concurrently:

- a **duplex `Stream`** (mic → CABLE) carries the low-latency, sample-accurate
  path that Discord reads from;
- an **`OutputStream`** (headphones) plays a copy pushed through a thread-safe
  `RingBuffer`, so you can hear yourself while Discord also receives the audio.

## Why TD-PSOLA instead of a phase vocoder

A naive pitch shifter resamples the signal, which shifts pitch **and** formants
together and sounds like a chipmunk. The common fix — a phase vocoder — shifts
them independently in the frequency domain, but loses phase coherence between
frequency bins, producing the metallic *"TV-whistleblower"* timbre.

**TD-PSOLA (Time-Domain Pitch-Synchronous OverLap-Add)** avoids the frequency
domain entirely:

1. **Pitch detection** — autocorrelation over a ~40 ms window estimates the
   local pitch period `P` (with a voiced/unvoiced decision).
2. **Analysis epochs** — the input is marked every `P` samples.
3. **Grain extraction** — a 2·`P` Hann-windowed grain is taken around each
   epoch (50 % overlap → constant power).
4. **Pitch** is changed by re-spacing the synthesis grains at `P / pitch_ratio`.
   Closer spacing ⇒ higher pitch. The grain *contents* are untouched, so the
   waveform stays natural — no phasiness.
5. **Formant** is changed *independently* by resampling each grain
   (`formant_ratio > 1` shortens the apparent vocal tract → more female/child).

Because grains are real slices of your own voice replayed at a new rate, the
harmonic structure is preserved and the result sounds like a person, not a
robot.

### Measured harmonic preservation (synthetic male /a/, +8 semitones)

The regression test uses a synthetic 120 Hz vowel with deterministic excitation.
On the current implementation, the same helper metric gives approximately:

| Signal | HNR (higher = cleaner) |
| --- | ---: |
| Original synthetic vowel | 20.1 dB |
| TD-PSOLA output (+8 st, formant 1.15×) | 18.2 dB |

The exact value is metric- and signal-dependent, so the CI test uses a conservative
threshold rather than treating HNR as a perceptual MOS score. See
`tests/test_dsp.py::test_psola_preserves_harmonics`.

## Real-time streaming

`StreamPSOLA` is fully stateful and block-based. It keeps an input buffer with
~45 ms of look-ahead (needed to centre a grain on an epoch and to run pitch
detection), generates analysis epochs and synthesis grains continuously, and
returns whatever output samples are ready each call. Buffers are trimmed every
block so memory stays bounded.

`AudioEngine` adds the polish that keeps the stream click-free:

- output is held silent until the PSOLA FIFO is primed (no partial blocks);
- the makeup gain is smoothed with an EMA so it never spikes at an onset;
- a short block-boundary cross-fade removes any residual step;
- the gate resets PSOLA on silence so speech resumes from a clean state.

## Latency budget

| Source                       | Approx.    |
| ---------------------------- | ---------- |
| PSOLA look-ahead             | ~45 ms     |
| Block size (1024 @ 44.1 kHz) | ~23 ms     |
| System audio buffers         | device-dependent |

The offline pipeline begins emitting processed blocks after roughly 46–70 ms depending on pitch direction/preset. Real end-to-end round-trip latency is higher and device/driver-dependent; the benchmark intentionally reports the DSP contribution separately.

## Known limitations

Real-time, lightweight, pure-DSP voice conversion has a ceiling: large pitch
shifts (e.g. the +10 "loli" preset) still get a little grainy, because the
method *moves* your existing voice rather than *regenerating* a target timbre.
For broadcast-quality, indistinguishable conversion you need a neural model
(e.g. RVC / so-vits-svc); see the README.


## Reproducible offline benchmark

Run `python benchmarks/benchmark_offline.py` to measure pitch-target accuracy, steady-state block compute time, and DSP startup buffering on the current host. The benchmark calls the production `AudioEngine` and does not require audio hardware.
