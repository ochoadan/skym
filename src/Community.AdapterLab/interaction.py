"""Synchronous, pointer-free correlation for the experimental native chat probe."""

import threading


class Interaction:
    @property
    def enabled(self):
        return self._enabled

    def __init__(self, emit, bridge=None):
        self._local = threading.local()
        self._emit = emit
        self._enabled = True
        self._sequence = 0
        self._bridge = bridge
        if bridge is not None:
            from bridge import COMMANDS
            self._commands = getattr(bridge, "commands", COMMANDS)
        else:
            self._commands = (b"/community", b"/community off")

    def begin(self, message: bytes):
        stack = getattr(self._local, "stack", None)
        if stack is None:
            stack = self._local.stack = []
        entry = None
        if self._enabled and message in self._commands:
            self._sequence += 1
            entry = {"sequence": self._sequence, "shown": False,
                     "disable": message == b"/community off", "command": message}
            self._emit("interaction", sequence=entry["sequence"])
        stack.append(entry)

    def reply(self, system_message: bool):
        stack = getattr(self._local, "stack", [])
        entry = stack[-1] if stack else None
        if not system_message or entry is None or entry["shown"]:
            return None
        entry["shown"] = True
        if self._bridge is not None:
            response = self._bridge.handle(entry["command"])
            # A busy nonblocking callback has not disabled its worker yet.
            if entry["disable"] and response != b"Community adapter disabled until restart.":
                entry["disable"] = False
            self._emit("presentation_requested", sequence=entry["sequence"])
            return response
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
            if entry["disable"] and (self._bridge is None or entry["shown"]):
                self._enabled = False
                self._emit("disabled")
