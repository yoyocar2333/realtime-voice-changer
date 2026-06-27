# Changelog

## 1.0.0

First public release.

### Engine
- **TD-PSOLA** time-domain pitch/formant shifter — natural voice conversion
  without the metallic phase-vocoder artefact.
- Fully decoupled pitch (semitones) and formant (vocal-tract scale) control.
- Streaming, stateful processor with ~45 ms look-ahead; CPU < 17 % of one core.

### Features
- **Dual output**: virtual cable (for Discord) + headphone monitor, so you can
  hear yourself.
- 9 presets across 女聲 / 男聲 / 特效 / 原聲.
- Live input/output meters, CPU readout, noise gate.
- Manual trim sliders (pitch, 3-band EQ, gain) layered on top of presets.
- Settings persistence (last devices / preset / gate).
- GUI (tkinter) and headless CLI (`--no-gui`).

### Robustness
- Click-free across silence, voiced/unvoiced transitions and pitch glides.
- Soft limiter + smoothed makeup gain prevent clipping and onset spikes.
- 19 hardware-free DSP tests (pitch correctness, harmonic preservation,
  continuity, safety) runnable in CI.
