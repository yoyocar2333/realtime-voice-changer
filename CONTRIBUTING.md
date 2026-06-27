# Contributing

Thanks for your interest! This is a small, focused project — contributions that
keep it lightweight and dependency-free are very welcome.

## Setup

```bash
git clone https://github.com/NTUquantum/realtime-voice-changer.git
cd realtime-voice-changer
python -m pip install -e ".[dev]"
pytest -q
```

## Guidelines

- **No new heavy dependencies.** The whole point is a light, no-GPU tool. NumPy,
  SciPy and sounddevice are the ceiling.
- **Keep DSP testable offline.** Audio logic must be exercisable without
  hardware. Add/extend tests in `tests/` using the synthetic-voice helpers — if
  you change the engine, prove it still shifts pitch correctly and stays
  click-free.
- **Run `pytest -q` before opening a PR.** CI runs it on Python 3.9–3.12.
- Match the existing style: type hints, short docstrings, no unnecessary
  abstraction.

## Ideas / good first issues

- A phase-locked phase-vocoder fallback engine (selectable per preset).
- Per-preset look-ahead tuning for lower latency on small shifts.
- Optional noise suppression before PSOLA.
- More presets (with measured F0 in the description).
- Packaging a standalone Windows `.exe` (PyInstaller) in CI.

## Reporting bugs

Open an issue with your OS, Python version, the preset used, and what you heard
vs expected. For audio glitches, a short `.wav` of input and output helps a lot.
