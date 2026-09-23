"""Synchronous, pointer-free correlation for the experimental native chat probe."""

import threading


class Interaction:
    def __init__(self, emit):
        self._local = threading.local()
        self._emit = emit
        self._enabled = True
        self._sequence = 0

    def begin(self, message: bytes):
        stack = getattr(self._local, "stack", None)
        if stack is None:
            stack = self._local.stack = []
        entry = None
        if self._enabled and message in (b"/community", b"/community off"):
            self._sequence += 1
            entry = {"sequence": self._sequence, "shown": False,
                     "disable": message == b"/community off"}
            self._emit("interaction", sequence=entry["sequence"])
        stack.append(entry)

    def reply(self, system_message: bool):
        stack = getattr(self._local, "stack", [])
        entry = stack[-1] if stack else None
        if not system_message or entry is None or entry["shown"]:
            return None
        entry["shown"] = True
        text = ("Community adapter disabled until restart." if entry["disable"] else
                f"Community adapter ready. Local probe #{entry['sequence']}.")
        self._emit("presentation_requested", sequence=entry["sequence"])
        return text.encode("ascii")

    def end(self):
        stack = getattr(self._local, "stack", [])
        entry = stack.pop() if stack else None
        if entry is not None:
            if not entry["shown"]:
                self._emit("no_system_reply", sequence=entry["sequence"])
            if entry["disable"]:
                self._enabled = False
                self._emit("disabled")
