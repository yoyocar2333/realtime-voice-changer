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

### Measured harmonic-to-noise ratio (synthetic male /a/, +8 semitones)

| Method                       | HNR (higher = cleaner) |
| ---------------------------- | ---------------------- |
| Original voice               | 6.8 dB                 |
| **TD-PSOLA (this project)**  | **5.1 dB**             |
| Phase vocoder (re-binning)   | 4.5 dB                 |
| Time-stretch + resample      | 3.0 dB                 |

(See `tests/test_dsp.py::test_psola_preserves_harmonics`.)

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

Round-trip is typically ~70 ms — imperceptible for conversation.

## Known limitations

Real-time, lightweight, pure-DSP voice conversion has a ceiling: large pitch
shifts (e.g. the +10 "loli" preset) still get a little grainy, because the
method *moves* your existing voice rather than *regenerating* a target timbre.
For broadcast-quality, indistinguishable conversion you need a neural model
(e.g. RVC / so-vits-svc); see the README.
