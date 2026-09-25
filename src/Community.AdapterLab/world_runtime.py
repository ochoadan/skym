"""Game-free scheduler for the opt-in, attended cockpit/presentation experiment.

Only the injected sample/present functions touch native state. Samples and their
receivers stay callback-local; queued notices contain owned bytes only. A natural
Say match calibrates this lifecycle, not every future game build or receiver.
Checks are scoped to the observed engine scheduling. They cannot make receiver
lifetime atomic against an arbitrary native thread changing it after a read.
"""

import threading
import time

from bridge import COMMANDS


ARM_LIFETIME = 60.0
DETAIL_LIMIT = 128
DISABLED = b"Community adapter disabled until restart."
WAIT_CANCEL = b"Community lifecycle change pending; try the command again."


class WorldRuntime:
    commands = COMMANDS + (b"/community arm",)

    def __init__(self, bridge, sample, present, emit, singleton,
                 clock=time.monotonic, thread_id=threading.get_native_id):
        self._bridge = bridge
        self._sample = sample
        self._present = present
        self._emit = emit
        self._singleton = singleton  # Fixed image-global identity, never a sampled owner.
        self._clock = clock
        self._thread_id = thread_id
        self._local = threading.local()
        self._gate = threading.Lock()
        self._engine_thread = None
        self._enabled = True
        self._calibrated = False
        self._armed_until = None
        self._notice = None
        self._cancel_required = False
        self._off_required = False
        self._invalid_reason = None
        self._epoch = 0
        self._frame = 0
        self._last_events = {}
        self._details = 0

    @property
    def enabled(self):
        return self._enabled

    @property
    def calibrated(self):
        return self._calibrated

    def _scope(self):
        depth = getattr(self._local, "depth", 0)
        return {"within_update": depth > 0, "update_depth": depth,
                "engine_thread": self._thread_id() == self._engine_thread}

    def _outer(self):
        return (getattr(self._local, "depth", 0) == 1
                and self._thread_id() == self._engine_thread
                and not getattr(self._local, "presenting", False))

    def _event(self, key, name, **fields):
        # Fixed keys, scalar fields and one shared budget bound all diagnostics.
        state = tuple(sorted(fields.items()))
        if self._last_events.get(key) == state:
            return
        self._last_events[key] = state
        if self._details >= DETAIL_LIMIT:
            return
        self._details += 1
        try:
            self._emit(name, **fields)
        except Exception:
            # Do not let diagnostic errors escape into a native detour.
            self._stop()

    def _clear(self):
        self._epoch += 1
        self._calibrated = False
        self._last_events.pop("calibration", None)
        self._armed_until = None
        self._notice = None

    def _stop(self):
        self._clear()
        self._enabled = False
        self._cancel_required = False
        self._off_required = self._bridge is not None

    def _acquire(self):
        if self._gate.acquire(blocking=False):
            return True
        # An overlapping callback cannot wait for the first callback. Mark its
        # in-flight result invalid and let the next callback retry cancellation.
        self._clear()
        self._cancel_required = self._bridge is not None
        self._invalid_reason = "callback_contention"
        return False

    def _reset(self, reason):
        if reason != self._invalid_reason or self._calibrated or self._armed_until is not None or self._notice:
            self._clear()
            self._cancel_required = self._bridge is not None
            self._invalid_reason = reason
            self._event("invalidation", "world_runtime_invalidated", reason=reason)

    def _retry_cancel(self):
        try:
            if self._off_required:
                if self._bridge.handle(b"/community off") == DISABLED:
                    self._off_required = False
                return False
            if self._cancel_required:
                if self._bridge is None or self._bridge.cancel_pending():
                    self._cancel_required = False
            return not self._cancel_required and self._enabled
        except Exception:
            self._bridge_failed("lifecycle")
            return False

    def _bridge_failed(self, operation):
        self._stop()
        self._event("bridge_error", "world_bridge_failed", operation=operation)

    def _active(self, epoch):
        return (self._enabled and self._calibrated and not self._cancel_required
                and self._epoch == epoch and self._outer())

    def _read(self, context):
        try:
            value = self._sample()
            receiver_valid = type(value.receiver) is int and value.receiver > 0
            fields = {"playable": bool(value.playable), "pending_clear": bool(value.pending_clear),
                      "owner_valid": bool(value.owner_valid and receiver_valid), "read_ok": True}
        except Exception:
            value = None
            fields = {"playable": False, "pending_clear": False, "owner_valid": False, "read_ok": False}
        self._event("sample_" + context, "world_runtime_state", context=context,
                    **fields, **self._scope())
        if value is None:
            self._reset("read_error")
        elif not fields["owner_valid"]:
            self._reset("owner_invalid")
        elif not fields["playable"]:
            self._reset("not_playable")
        elif not fields["pending_clear"]:
            self._reset("pending_transition")
        else:
            self._invalid_reason = None
        return value

    @staticmethod
    def _safe(value):
        return (value is not None and type(value.receiver) is int and value.receiver > 0
                and value.owner_valid and value.playable and value.pending_clear)

    def enter_update(self):
        self._local.depth = getattr(self._local, "depth", 0) + 1
        if not self._acquire():
            return
        try:
            if self._engine_thread is None:
                self._engine_thread = self._thread_id()
            if self._enabled and self._thread_id() != self._engine_thread:
                self._reset("update_thread_mismatch")
            elif self._enabled and self._local.depth == 1:
                self._frame += 1
            self._retry_cancel()
        finally:
            self._gate.release()

    def exit_update(self):
        depth = getattr(self._local, "depth", 0)
        if depth == 0:
            return
        try:
            if not self._acquire():
                return
            try:
                if not self._retry_cancel() or not self._enabled:
                    return
                if not self._outer():
                    return
                if not self._safe(self._read("update")):
                    self._retry_cancel()
                    return
                self._expire_arm()
                if self._bridge is None or not self._calibrated or self._cancel_required:
                    return
                if self._notice is not None:
                    message, frame = self._notice
                    if frame > self._frame:
                        return
                    self._notice = None
                else:
                    try:
                        message = self._bridge.poll()
                    except Exception:
                        self._bridge_failed("poll")
                        self._retry_cancel()
                        return
                if message is not None:
                    self._deliver(message)
            finally:
                self._gate.release()
        finally:
            self._local.depth = depth - 1

    def _deliver(self, message):
        epoch = self._epoch
        current = self._read("presentation")
        if (not self._safe(current) or not self._outer() or not self._enabled or not self._calibrated
                or self._cancel_required or self._epoch != epoch):
            self._event("discard", "world_delivery_discarded", reason="state_changed")
            self._retry_cancel()
            return
        self._local.presenting = True
        try:
            self._present(current.receiver, message)
            self._event("presentation", "world_automatic_submission", sequence=self._frame)
        except Exception:
            self._event("presentation_error", "world_presentation_failed", reason="native_call_failed")
            self._stop()
        finally:
            self._local.presenting = False
        self._retry_cancel()

    def observe_say(self, receiver):
        if getattr(self._local, "presenting", False) or not self._acquire():
            return
        try:
            if not self._retry_cancel() or not self._enabled:
                return
            current = self._read("say")
            matches = current is not None and current.owner_valid and current.receiver == receiver
            self._event("receiver", "world_receiver_validation", say_receiver_match=matches, **self._scope())
            if not matches:
                self._reset("say_receiver_mismatch" if current is not None else "say_state_invalid")
            elif not self._safe(current):
                pass  # Equality is useful validation even while presentation is unsafe.
            elif not self._scope()["engine_thread"] or not self._scope()["within_update"]:
                self._reset("say_scope_invalid")
            elif self._enabled and not self._cancel_required:
                self._calibrated = True
                self._event("calibration", "world_calibration", calibrated=True)
            self._retry_cancel()
        finally:
            self._gate.release()

    def _expire_arm(self):
        if self._armed_until is not None and self._clock() >= self._armed_until:
            self._armed_until = None
            self._event("arm", "world_cockpit_arm", armed=False, reason="expired")

    def cockpit_entered(self):
        if not self._acquire():
            return
        try:
            if not self._retry_cancel() or not self._enabled:
                return
            current = self._read("cockpit")
            if not self._outer():
                self._reset("cockpit_scope_invalid")
            if not self._safe(current) or not self._outer():
                self._retry_cancel()
                return
            self._expire_arm()
            if self._bridge is None or not self._calibrated or self._armed_until is None or self._cancel_required:
                return
            epoch = self._epoch
            self._armed_until = None  # One entry consumes the arm, even if busy.
            self._event("arm", "world_cockpit_arm", armed=False, reason="consumed")
            if not self._active(epoch):
                self._retry_cancel()
                return
            try:
                busy = self._bridge.busy()
            except Exception:
                self._bridge_failed("busy")
                self._retry_cancel()
                return
            if not self._active(epoch):
                self._retry_cancel()
                return
            if busy:
                message = b"Community request already pending; cockpit probe was not sent."
            else:
                try:
                    message = self._bridge.handle(b"/community")
                except Exception:
                    self._bridge_failed("cockpit_request")
                    self._retry_cancel()
                    return
                if not self._active(epoch):
                    self._retry_cancel()
                    return
                self._event("cockpit", "world_cockpit_request", sequence=self._frame)
            if self._active(epoch):
                self._notice = (message, self._frame + 1)
            else:
                self._retry_cancel()
        finally:
            self._gate.release()

    def transition(self, receiver):
        if not self._acquire():
            return
        try:
            if not self._enabled:
                self._retry_cancel()
                return
            self._event("transition", "world_transition_validation",
                        application_receiver=receiver == self._singleton, **self._scope())
            self._reset("fsm_transition")  # Every FSM is conservative cancellation.
            self._retry_cancel()
        finally:
            self._gate.release()

    def handle(self, command):
        if command == b"/community off":
            self.disable()
            return DISABLED
        if not self._acquire():
            return WAIT_CANCEL
        try:
            if not self._enabled:
                self._retry_cancel()
                return DISABLED
            if command in (b"/community leave", b"/community reconnect"):
                self._reset("command_leave")
            if not self._retry_cancel():
                return DISABLED if not self._enabled else WAIT_CANCEL
            if self._bridge is None:
                return b"Community receiver validation only; no service is connected."
            if command == b"/community arm":
                if not self._outer():
                    return b"Community cockpit probe requires a current game update. Try again."
                if not self._safe(self._read("arm")) or not self._calibrated or self._cancel_required:
                    self._retry_cancel()
                    return b"Community cockpit probe unavailable. Send /community state to validate chat first."
                epoch = self._epoch
                try:
                    busy = self._bridge.busy()
                except Exception:
                    self._bridge_failed("busy")
                    self._retry_cancel()
                    return DISABLED
                if not self._active(epoch):
                    self._retry_cancel()
                    return DISABLED if not self._enabled else WAIT_CANCEL
                if busy:
                    return b"Community request already pending. Wait for its reply before arming."
                self._armed_until = self._clock() + ARM_LIFETIME
                self._event("arm", "world_cockpit_arm", armed=True, reason="command")
                if not self._active(epoch):
                    self._retry_cancel()
                    return DISABLED if not self._enabled else WAIT_CANCEL
                return b"Community cockpit probe armed for 60 seconds. Enter your landed ship once."
            try:
                return self._bridge.handle(command)
            except Exception:
                self._bridge_failed("command")
                self._retry_cancel()
                return DISABLED
        finally:
            self._gate.release()

    def disable(self):
        # Terminal state is immediate even if another callback owns the gate.
        self._stop()
        if not self._gate.acquire(blocking=False):
            return
        try:
            self._retry_cancel()
        finally:
            self._gate.release()
