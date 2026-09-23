"""Experimental pyMHF mod; load only through launch.py after lab setup.

Hook signatures and ABI declarations: NMS.py b41bf9e6, MIT; see notices.
No NMS.py runtime package or game structures are imported.
"""

import ctypes
import json
import os
from pathlib import Path
import queue
import threading
import time

from pymhf import Mod
from pymhf.core import _internal
from pymhf.core._types import FUNCDEF
from pymhf.core.hooking import manual_hook

from interaction import Interaction
from runtime_guard import check_process


# Module import precedes mod registration. A refusal defines no hook class.
_report, _rvas = check_process(os.getpid())
_run_dir = Path(_internal.CONFIG["community_lab"]["run_dir"])
_log_path = _run_dir / "events.jsonl"
_output = _log_path.open("x", encoding="utf-8", buffering=1)
_events = queue.Queue(maxsize=128)
_dropped = 0


def emit(event, **fields):
    global _dropped
    item = {"event": event, "time_ns": time.time_ns(),
            "thread": threading.get_native_id(), **fields}
    try:
        _events.put_nowait(item)
    except queue.Full:
        _dropped += 1


def write_events():
    while True:
        item = _events.get()
        item["dropped_total"] = _dropped
        _output.write(json.dumps(item) + "\n")


threading.Thread(target=write_events, name="CommunityLabLog", daemon=True).start()
emit("probe_loaded", sha256=_report["sha256"])


class CommunityProbe(Mod):
    __author__ = "nms-community-platform contributors"
    __version__ = "0.1.0"
    __description__ = "Local native chat probe; no service connection"

    def __init__(self):
        self.interaction = Interaction(emit)
        super().__init__()

    @manual_hook("Community.ParseText", offset=_rvas["parse_text"],
                 func_def=FUNCDEF(None, (ctypes.c_void_p, ctypes.c_void_p)))
    def parse_before(self, this, message):
        # Only transient callback arguments; no pointers go into events or workers.
        value = ctypes.string_at(message, 0x3FF).split(b"\0", 1)[0] if message else b""
        self.interaction.begin(value)

    @manual_hook("Community.ParseText", offset=_rvas["parse_text"],
                 func_def=FUNCDEF(None, (ctypes.c_void_p, ctypes.c_void_p)),
                 detour_time="after")
    def parse_after(self, this, message):
        self.interaction.end()

    @manual_hook("Community.Say", offset=_rvas["say"],
                 func_def=FUNCDEF(None, (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool)))
    def say_before(self, this, message, system_message):
        if not message:
            return
        response = self.interaction.reply(system_message)
        if response is not None:
            # The bounded ASCII string fits in the upstream 0x3FF-byte buffer.
            ctypes.memmove(message, response + b"\0", len(response) + 1)
            emit("presentation_written")
