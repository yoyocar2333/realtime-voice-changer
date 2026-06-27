"""Real-time TD-PSOLA voice changer.

Public API
----------
- :class:`~voicechanger.engine.AudioEngine` — the DSP chain + device driver
- :class:`~voicechanger.psola.StreamPSOLA` — the pitch/formant core
- :data:`~voicechanger.presets.PRESETS` — built-in voice presets
"""
from __future__ import annotations

from .engine import AudioEngine
from .presets import PRESETS, PRESET_ORDER, Preset
from .psola import StreamPSOLA

__version__ = "1.0.0"
__all__ = ["AudioEngine", "StreamPSOLA", "PRESETS", "PRESET_ORDER", "Preset", "__version__"]
