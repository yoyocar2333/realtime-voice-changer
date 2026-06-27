"""Tiny JSON settings store (last-used devices, preset, gate).

Saved to the user config dir so the app remembers your setup between runs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

__all__ = ["load", "save", "config_path"]


def config_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    d = base / "realtime-voice-changer"
    d.mkdir(parents=True, exist_ok=True)
    return d / "settings.json"


def load() -> dict[str, Any]:
    try:
        return json.loads(config_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def save(settings: dict[str, Any]) -> None:
    try:
        config_path().write_text(
            json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass
