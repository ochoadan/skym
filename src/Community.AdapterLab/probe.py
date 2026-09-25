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
from preflight import COMPATIBILITY
from runtime_guard import check_process


# Module import precedes mod registration. A refusal defines no hook class.
_observe_world = _internal.CONFIG["community_lab"].get("observe_world", False)
_validate_world = _internal.CONFIG["community_lab"].get("validate_world", False)
_auto_world = _internal.CONFIG["community_lab"].get("auto_world", False)
_world_hooks = _observe_world or _validate_world or _auto_world
if (_observe_world or _validate_world) and _internal.CONFIG["community_lab"].get("service_config"):
    raise ValueError("World observation cannot connect a service")
if _auto_world and not _internal.CONFIG["community_lab"].get("service_config"):
    raise ValueError("Automatic world mode requires a service configuration")
_report, _rvas = check_process(os.getpid(), observe_world=_observe_world,
                             validate_world=_validate_world or _auto_world)
_run_dir = Path(_internal.CONFIG["community_lab"]["run_dir"])
_log_path = _run_dir / "events.jsonl"
_output = _log_path.open("x", encoding="utf-8", buffering=1)
_events = queue.SimpleQueue()
_event_gate = threading.Lock()
_dropped = 0


def emit(event, **fields):
    global _dropped
    item = {"event": event, "time_ns": time.time_ns(),
            "thread": threading.get_native_id(), **fields}
    if not _event_gate.acquire(blocking=False):
        _dropped += 1
        return
    try:
        if _events.qsize() >= 128:
            _dropped += 1
        else:
            _events.put(item)
    finally:
        _event_gate.release()


def write_events():
    while True:
        item = _events.get()
        item["dropped_total"] = _dropped
        _output.write(json.dumps(item) + "\n")


threading.Thread(target=write_events, name="CommunityLabLog", daemon=True).start()
emit("probe_loaded", sha256=_report["sha256"], observe_world=_observe_world,
     validate_world=_validate_world, auto_world=_auto_world)


class CommunityProbe(Mod):
    __author__ = "nms-community-platform contributors"
    __version__ = COMPATIBILITY["adapterVersion"]
    __description__ = "Local native chat probe with optional bounded service worker"

    def __init__(self):
        service_config = _internal.CONFIG["community_lab"].get("service_config")
        bridge = None
        if service_config:
            from service_client import ClientConfig
            from bridge import Bridge
            bridge = Bridge(ClientConfig.load(service_config), emit, automatic=_auto_world,
                            delivery_delay=_internal.CONFIG["community_lab"].get("delivery_delay", 0.0))
        self.observation = None
        self.world = None
        if _world_hooks:
            from world_observation import WorldObservation
            self.observation = WorldObservation(emit)
        if _validate_world or _auto_world:
            from native_state import NativeState, SINGLETON_RVA, current_process_reader
            from world_runtime import WorldRuntime
            state = NativeState(_internal.BASE_ADDRESS, current_process_reader())
            present = None
            if _auto_world:
                native_say = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p,
                                              ctypes.c_bool)(_internal.BASE_ADDRESS + _rvas["say"])

                def present(receiver, response):
                    if not isinstance(response, bytes) or len(response) > 640 or b"\0" in response:
                        raise ValueError("Invalid presentation payload")
                    response.decode("ascii")
                    # Native Say copies all 0x3FF bytes synchronously, including
                    # the zero-filled tail. A short string allocation is unsafe.
                    buffer = ctypes.create_string_buffer(0x3FF)
                    buffer.value = response
                    native_say(receiver, ctypes.addressof(buffer), True)
                    emit("automatic_submission")

            self.world = WorldRuntime(bridge, state.sample, present, emit,
                                      _internal.BASE_ADDRESS + SINGLETON_RVA)
        self.interaction = Interaction(emit, self.world if _auto_world else bridge)
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
        if self.world is not None and self.world.enabled and not self.interaction.enabled:
            self.world.disable()
        if self.observation is not None and self.observation.enabled and not self.interaction.enabled:
            snapshot = self.observation.snapshot() or {}
            self.observation.disable()
            emit("world_disabled", **{**snapshot, "enabled": False})

    @manual_hook("Community.Say", offset=_rvas["say"],
                 func_def=FUNCDEF(None, (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool)))
    def say_before(self, this, message, system_message):
        if self.world is not None:
            self.world.observe_say(this)
        if self.observation is not None:
            self.observation.observe("native_say")
        if not message:
            return
        response = self.interaction.reply(system_message)
        if response is not None:
            # The bounded ASCII string fits in the upstream 0x3FF-byte buffer.
            ctypes.memmove(message, response + b"\0", len(response) + 1)
            emit("presentation_written")

    if _world_hooks:
        # Never infer the singleton from ApplicationUpdate.this. This build's
        # caller does not supply it. State reads use guarded module globals.
        @manual_hook("Community.ApplicationUpdate", offset=_rvas["application_update"],
                     func_def=FUNCDEF(None, (ctypes.c_void_p,)))
        def update_before(self, this):
            self.observation.enter_update()
            if self.world is not None:
                self.world.enter_update()

        @manual_hook("Community.ApplicationUpdate", offset=_rvas["application_update"],
                     func_def=FUNCDEF(None, (ctypes.c_void_p,)), detour_time="after")
        def update_after(self, this):
            try:
                if self.world is not None:
                    self.world.exit_update()
            finally:
                self.observation.exit_update()

        @manual_hook("Community.PlayerUpdate", offset=_rvas["player_update"],
                     func_def=FUNCDEF(None, (ctypes.c_void_p, ctypes.c_float)))
        def player_update(self, this, step):
            self.observation.observe("player_update")

        @manual_hook("Community.CockpitEntered", offset=_rvas["cockpit_entered"],
                     func_def=FUNCDEF(None, (ctypes.c_void_p,)))
        def cockpit_entered(self, this):
            self.observation.observe("cockpit_entered")
            if self.world is not None:
                self.world.cockpit_entered()

        @manual_hook("Community.FsmTransition", offset=_rvas["fsm_transition"],
                     func_def=FUNCDEF(None, (ctypes.c_void_p, ctypes.c_uint64,
                                           ctypes.c_uint64, ctypes.c_bool)))
        def fsm_transition(self, this, new_state, user_data, force_restart):
            # The parent FSM declaration types its state argument as uint64.
            # Do not infer a readable string or application ownership from it.
            self.observation.observe("state_change")
            if self.world is not None:
                self.world.transition(this)
