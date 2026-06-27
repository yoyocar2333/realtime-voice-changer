"""Thread-safe single-producer/single-consumer float ring buffer.

Used to bridge the duplex callback (producer) and the monitor output stream
(consumer) without blocking either audio thread.
"""
from __future__ import annotations

import threading

import numpy as np

__all__ = ["RingBuffer"]


class RingBuffer:
    """Fixed-size float32 ring buffer with overwrite-on-overrun semantics."""

    def __init__(self, size: int) -> None:
        self.buf = np.zeros(size, dtype=np.float32)
        self.size = size
        self.w = 0
        self.r = 0
        self.count = 0
        self.lock = threading.Lock()

    def write(self, data: np.ndarray) -> None:
        with self.lock:
            n = len(data)
            if n > self.size:
                data = data[-self.size:]
                n = self.size
            end = self.w + n
            if end <= self.size:
                self.buf[self.w:end] = data
            else:
                k = self.size - self.w
                self.buf[self.w:] = data[:k]
                self.buf[:end - self.size] = data[k:]
            self.w = end % self.size
            self.count = min(self.size, self.count + n)
            if self.count == self.size:      # overrun: drop oldest
                self.r = self.w

    def read(self, n: int) -> np.ndarray:
        with self.lock:
            out = np.zeros(n, dtype=np.float32)
            avail = min(n, self.count)
            end = self.r + avail
            if end <= self.size:
                out[:avail] = self.buf[self.r:end]
            else:
                k = self.size - self.r
                out[:k] = self.buf[self.r:]
                out[k:avail] = self.buf[:end - self.size]
            self.r = (self.r + avail) % self.size
            self.count -= avail
            return out
