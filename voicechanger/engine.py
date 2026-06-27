"""Audio engine: ties PSOLA + effects together and drives the sound devices.

The engine exposes a pure :meth:`AudioEngine.process` method (no hardware
required) so the DSP chain can be unit-tested offline, and a :meth:`start`
method that opens the real duplex + monitor streams via ``sounddevice``.
"""
from __future__ import annotations

import threading
import time

import numpy as np

from . import effects
from .presets import PRESETS, Preset
from .psola import StreamPSOLA
from .ringbuffer import RingBuffer

__all__ = ["AudioEngine"]


class AudioEngine:
    def __init__(self, sr: int = 44100, block: int = 1024) -> None:
        self.sr = sr
        self.block = block
        self.running = False
        self._lock = threading.Lock()

        self.preset_name = "原聲 (Off)"
        self.preset: Preset = PRESETS[self.preset_name]

        self.psola = StreamPSOLA(sr=sr)
        self.out_fifo = np.zeros(0, dtype=np.float32)
        self.reverb_buf = np.zeros(int(sr * 0.3), dtype=np.float32)

        self.monitor_ring = RingBuffer(sr)
        self.monitor_on = True

        # live meters
        self.input_level = 0.0
        self.output_level = 0.0
        self.cpu_usage = 0.0

        # manual trims (added on top of the active preset)
        self.adj_pitch = 0.0
        self.adj_bass = 0.0
        self.adj_mid = 0.0
        self.adj_treble = 0.0
        self.adj_gain = 0.0
        self.noise_gate = 0.01

        # de-click / smoothing state
        self._makeup = 1.0            # smoothed makeup gain
        self._last_out = 0.0          # last emitted sample (block-boundary declick)

        self._stream = None
        self._mon_stream = None

    # ------------------------------------------------------------------ #
    def set_preset(self, name: str) -> None:
        with self._lock:
            self.preset_name = name
            self.preset = PRESETS[name]
            self.psola.reset()
            self.out_fifo = np.zeros(0, dtype=np.float32)
            self.reverb_buf[:] = 0

    # ------------------------------------------------------------------ #
    def process(self, audio: np.ndarray) -> np.ndarray:
        """Run the full DSP chain on one block.  Hardware-independent."""
        t0 = time.perf_counter()
        with self._lock:
            p = self.preset
            ap, ab, am, at_, ag = (self.adj_pitch, self.adj_bass, self.adj_mid,
                                   self.adj_treble, self.adj_gain)
            gate = self.noise_gate
            rbuf = self.reverb_buf

        self.input_level = float(np.max(np.abs(audio))) if len(audio) else 0.0
        if self.input_level < gate:
            self.output_level = 0.0
            self._last_out = 0.0
            self._makeup = 1.0
            self.psola.reset()           # clean slate → no re-onset transient
            self.out_fifo = np.zeros(0, dtype=np.float32)
            return np.zeros(len(audio), dtype=np.float32)

        in_rms = float(np.sqrt(np.mean(audio**2)) + 1e-9)
        pr = 2.0 ** ((p.pitch + ap) / 12.0)
        fr = p.formant

        if self._is_passthrough(p, ap, ab, am, at_, ag):
            self.psola.process(audio, 1.0, 1.0)        # keep state warm
            self.output_level = self.input_level
            return audio.astype(np.float32)

        produced = self.psola.process(audio, pr, fr)
        self.out_fifo = np.concatenate([self.out_fifo, produced])
        need = len(audio)
        if len(self.out_fifo) >= need:
            out = self.out_fifo[:need].copy()
            self.out_fifo = self.out_fifo[need:]
        else:
            # still priming: emit silence (a partial block embeds a step/click)
            self.output_level = 0.0
            self._last_out = 0.0
            return np.zeros(need, dtype=np.float32)

        out_rms = float(np.sqrt(np.mean(out**2)) + 1e-9)
        target_makeup = float(np.clip(in_rms / out_rms, 0.5, 2.5))
        # smooth the makeup gain so it never spikes at an onset
        self._makeup = 0.6 * self._makeup + 0.4 * target_makeup
        out = out * self._makeup

        tb, tm, tt = p.bass + ab, p.mid + am, p.treble + at_
        if abs(tb) > 0.3 or abs(tm) > 0.3 or abs(tt) > 0.3:
            out = effects.eq(out, self.sr, tb, tm, tt)
        if p.pres_gain > 0.05 and p.pres_lo > 0:
            out = effects.presence(out, self.sr, p.pres_lo, p.pres_hi, p.pres_gain)
        if p.robot:
            out = effects.robot(out)
        if p.reverb > 0.05:
            out = effects.reverb(out, rbuf, wet=p.reverb * 0.8)

        tg = p.gain + ag
        if abs(tg) > 0.1:
            out = out * (10 ** (tg / 20))

        if np.max(np.abs(out)) > 0.8:                  # soft limiter
            out = np.tanh(out * 1.1) * 0.9

        # block-boundary declick: ease the first samples from the previous
        # block's last value so warm-up / gate-release steps don't click
        if abs(out[0] - self._last_out) > 0.05:
            n = min(96, len(out))
            ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
            out[:n] = self._last_out * (1.0 - ramp) + out[:n] * ramp
        self._last_out = float(out[-1])

        out = np.clip(out, -1.0, 1.0).astype(np.float32)

        self.output_level = float(np.max(np.abs(out)))
        self.cpu_usage = min(100.0, (time.perf_counter() - t0) / (self.block / self.sr) * 100)
        return out

    def _is_passthrough(self, p: Preset, ap, ab, am, at_, ag) -> bool:
        pr = 2.0 ** ((p.pitch + ap) / 12.0)
        return (abs(pr - 1.0) < 0.01 and abs(p.formant - 1.0) < 0.02
                and not p.robot and p.reverb < 0.05
                and abs(p.bass) < 0.3 and abs(p.mid) < 0.3 and abs(p.treble) < 0.3
                and abs(p.gain + ag) < 0.1
                and abs(ab) < 0.3 and abs(am) < 0.3 and abs(at_) < 0.3)

    # ------------------------------------------------------------------ #
    @staticmethod
    def list_devices() -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
        """Return ``(inputs, outputs)`` as ``(index, name)`` lists."""
        try:
            import sounddevice as sd
            devs = sd.query_devices()
            ins = [(i, d["name"]) for i, d in enumerate(devs) if d["max_input_channels"] > 0]
            outs = [(i, d["name"]) for i, d in enumerate(devs) if d["max_output_channels"] > 0]
            return ins, outs
        except Exception:
            return [], []

    def start(self, in_dev, out_dev, mon_dev) -> None:
        if self.running:
            return
        import sounddevice as sd

        def cb(indata, outdata, frames, t, status):
            try:
                proc = self.process(indata[:, 0].astype(np.float32))
                outdata[:, 0] = proc
                if outdata.shape[1] > 1:
                    outdata[:, 1] = proc
                if self.monitor_on and mon_dev is not None:
                    self.monitor_ring.write(proc)
            except Exception:
                outdata[:] = 0

        self._stream = sd.Stream(
            device=(in_dev, out_dev), samplerate=self.sr, blocksize=self.block,
            dtype="float32", channels=(1, 1), callback=cb, latency="low")
        self._stream.start()

        if mon_dev is not None:
            def mon_cb(outdata, frames, t, status):
                try:
                    d = self.monitor_ring.read(frames)
                    outdata[:, 0] = d
                    if outdata.shape[1] > 1:
                        outdata[:, 1] = d
                except Exception:
                    outdata[:] = 0

            self._mon_stream = sd.OutputStream(
                device=mon_dev, samplerate=self.sr, blocksize=self.block,
                dtype="float32", channels=1, callback=mon_cb, latency="low")
            self._mon_stream.start()

        self.running = True

    def stop(self) -> None:
        self.running = False
        for s in (self._stream, self._mon_stream):
            try:
                if s:
                    s.stop()
                    s.close()
            except Exception:
                pass
        self._stream = None
        self._mon_stream = None
