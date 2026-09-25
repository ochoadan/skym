"""Bounded, pointer-free T-04.5 diagnostics; no gameplay or service operations.

Signatures/ABIs derive from NMS.py b41bf9e6 (MIT); see notices.
A signature match permits observation, not a claim about callback semantics.
"""

import threading
import time


SIGNATURES = {
    "application_update": "40 53 48 83 EC 20 E8 ? ? ? ? 48 89",
    "fsm_transition": "48 89 6C 24 ? 48 89 74 24 ? 57 48 83 EC ? 4C 8B 51 ? 49 8B E8",
    "player_update": "48 8B C4 48 89 48 ? 55 53 41 54 41 55 41 57 48 8D A8",
    "cockpit_entered": "40 53 48 81 EC E0 00 00 00 48 8B D9 E8 ?? ?? ?? ?? 83 78 10 05",
}
KINDS = ("application_update", "player_update", "cockpit_entered", "state_change", "native_say")
DETAIL_LIMIT = 64
SUMMARY_INTERVAL = 2.0


class WorldObservation:
    @property
    def enabled(self):
        return not self._stopped.is_set()

    def __init__(self, emit, clock=time.monotonic):
        self._emit = emit
        self._clock = clock
        self._local = threading.local()
        self._gate = threading.Lock()
        self._stopped = threading.Event()
        self._counts = dict.fromkeys(KINDS, 0)
        self._details = 0
        self._dropped = 0
        self._next_summary = clock() + SUMMARY_INTERVAL

    def enter_update(self):
        self._local.depth = getattr(self._local, "depth", 0) + 1
        self._record("application_update")

    def exit_update(self):
        self._local.depth = max(0, getattr(self._local, "depth", 0) - 1)

    def observe(self, kind):
        if kind not in KINDS or kind == "application_update":
            raise ValueError("Unknown observation kind")
        self._record(kind)

    def _publish(self, event, **fields):
        try:
            self._emit(event, **fields)
        except Exception:
            # Diagnostic failures must not escape into a native callback.
            self._stopped.set()

    def _record(self, kind):
        if self._stopped.is_set():
            return
        if not self._gate.acquire(blocking=False):
            self._dropped += 1
            return
        try:
            if self._stopped.is_set():
                return
            self._counts[kind] += 1
            if (self._counts[kind] == 1 or kind not in ("application_update", "player_update")) and self._details < DETAIL_LIMIT:
                self._details += 1
                self._publish("world_callback", kind=kind, count=self._counts[kind],
                              within_update=getattr(self._local, "depth", 0) > 0)
            now = self._clock()
            if not self._stopped.is_set() and now >= self._next_summary:
                self._next_summary = now + SUMMARY_INTERVAL
                self._publish("world_summary", **self._snapshot())
        finally:
            self._gate.release()

    def _snapshot(self):
        return {**self._counts, "enabled": not self._stopped.is_set(),
                "details": self._details, "dropped": self._dropped}

    def snapshot(self):
        if not self._gate.acquire(blocking=False):
            return None
        try:
            return self._snapshot()
        finally:
            self._gate.release()

    def disable(self):
        self._stopped.set()
