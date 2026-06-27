"""Voice presets.

Each :class:`Preset` bundles a pitch shift (real semitones), an independent
formant ratio, tone-shaping EQ, an optional presence boost and effect flags.
``pitch`` and ``formant`` are the two parameters that actually change *who* the
voice sounds like; everything else is polish.
"""
from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["Preset", "PRESETS", "PRESET_ORDER"]


@dataclass(frozen=True)
class Preset:
    icon: str
    group: str          # 女聲 / 男聲 / 特效 / 原聲
    desc: str
    pitch: float = 0.0          # semitones
    formant: float = 1.0        # vocal-tract scale (>1 = shorter = more female)
    bass: float = 0.0
    mid: float = 0.0
    treble: float = 0.0
    pres_lo: float = 0.0
    pres_hi: float = 0.0
    pres_gain: float = 0.0
    robot: bool = False
    reverb: float = 0.0
    gain: float = 0.0           # output makeup (dB)


PRESETS: dict[str, Preset] = {
    "年輕女聲": Preset("👧", "女聲",
        "男聲→年輕女聲。PSOLA 自然引擎，音高+8半音、共振峰+15%",
        pitch=8, formant=1.15, bass=-2, mid=1, treble=2,
        pres_lo=2500, pres_hi=5500, pres_gain=0.18, gain=1),
    "成熟女聲": Preset("👩", "女聲",
        "較低沉自然的女聲。音高+5半音、共振峰+8%（金屬感最少）",
        pitch=5, formant=1.08, bass=-1, mid=2, treble=1,
        pres_lo=1800, pres_hi=4500, pres_gain=0.15, gain=1),
    "蘿莉音": Preset("🎀", "女聲",
        "高音動漫風。音高+10半音、共振峰+25%（移較多，偶有顆粒感）",
        pitch=10, formant=1.25, bass=-5, mid=2, treble=4,
        pres_lo=3500, pres_hi=7000, pres_gain=0.2, gain=1),
    "大叔低音": Preset("🧔", "男聲",
        "渾厚大叔。音高-6半音、共振峰-15%",
        pitch=-6, formant=0.85, bass=5, treble=-2, gain=2),
    "成熟男聲": Preset("👨", "男聲",
        "自然低沉男聲。音高-3半音、共振峰-8%",
        pitch=-3, formant=0.92, bass=3, mid=1, treble=-1, gain=1),
    "機器人": Preset("🤖", "特效",
        "電子機械音",
        pitch=0, formant=1.0, bass=2, mid=-3, treble=5, robot=True, reverb=0.15),
    "外星人": Preset("👽", "特效",
        "高音＋機械＋殘響",
        pitch=5, formant=1.3, treble=6, robot=True, reverb=0.3, gain=1),
    "洞穴迴響": Preset("🏔️", "特效",
        "深邃環境殘響",
        pitch=-2, formant=0.95, bass=4, mid=-1, treble=-3, reverb=0.5),
    "原聲 (Off)": Preset("🎙️", "原聲",
        "不處理，直接通過"),
}

PRESET_ORDER: list[str] = [
    "年輕女聲", "成熟女聲", "蘿莉音",
    "大叔低音", "成熟男聲",
    "機器人", "外星人", "洞穴迴響", "原聲 (Off)",
]
