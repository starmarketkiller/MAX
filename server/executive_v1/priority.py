"""P0 interactive gate: Jarvis interactive model calls yield the local worker.

While an interactive Jarvis synthesis is in flight the durable dispatcher
does not claim new background work (P1-P4); work already running is never
interrupted (max concurrency is 1, and killing a model call mid-way would
waste it).  Background claiming resumes as soon as the gate closes.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager


class InteractiveGate:
    def __init__(self):
        self._lock = threading.Lock()
        self._active = 0

    @property
    def active(self):
        with self._lock:
            return self._active > 0

    @contextmanager
    def interactive(self):
        with self._lock:
            self._active += 1
        try:
            yield
        finally:
            with self._lock:
                self._active -= 1

    def background_should_yield(self):
        return self.active


INTERACTIVE_GATE = InteractiveGate()
