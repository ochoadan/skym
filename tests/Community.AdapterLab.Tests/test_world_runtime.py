"""Game-free lifecycle and scheduling checks; no installed game is read."""

from dataclasses import dataclass, replace
from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "Community.AdapterLab"))
from world_runtime import ARM_LIFETIME, DETAIL_LIMIT, DISABLED, WAIT_CANCEL, WorldRuntime


@dataclass(frozen=True)
class TestSample:
    receiver: int = 0x1234567890
    playable: bool = True
    pending_clear: bool = True
    owner_valid: bool = True


class FakeBridge:
    def __init__(self):
        self.handles = []
        self.ready = None
        self.outstanding = False
        self.cancel_allowed = True
        self.off_allowed = True
        self.cancel_calls = 0
        self.polls = 0
        self.poll_hook = lambda: None

    def busy(self):
        return self.outstanding or self.ready is not None

    def cancel_pending(self):
        self.cancel_calls += 1
        if not self.cancel_allowed:
            return False
        self.ready = None
        self.outstanding = False
        return True

    def handle(self, command):
        self.handles.append(command)
        if command == b"/community off":
            return DISABLED if self.off_allowed else b"Community busy; try the command again."
        if command in (b"/community leave", b"/community reconnect"):
            self.ready = None
            self.outstanding = False
            return b"Community disconnected."
        if command == b"/community result":
            return self.poll() or b"No community result pending."
        self.outstanding = True
        return b"Community lab: connecting/sending. Reply will appear automatically."

    def poll(self):
        self.polls += 1
        value, self.ready = self.ready, None
        if value is not None:
            self.outstanding = False
        self.poll_hook()
        return value


class WorldRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.current = TestSample()
        self.samples = 0
        self.events = []
        self.presentations = []
        self.bridge = FakeBridge()
        self.runtime = self.make_runtime(self.bridge)

    def make_runtime(self, bridge):
        return WorldRuntime(bridge, self.sample, self.present, self.emit, singleton=0xABCDEF00,
                            clock=lambda: self.now)

    def sample(self):
        self.samples += 1
        if isinstance(self.current, Exception):
            raise self.current
        return self.current

    def present(self, receiver, message):
        self.presentations.append((receiver, message))

    def emit(self, name, **fields):
        self.events.append((name, fields))

    def frame(self, action=None):
        self.runtime.enter_update()
        if action:
            action()
        self.runtime.exit_update()

    def calibrate(self):
        self.frame(lambda: self.runtime.observe_say(self.current.receiver))
        self.assertTrue(self.runtime.calibrated)

    def arm(self):
        replies = []
        self.frame(lambda: replies.append(self.runtime.handle(b"/community arm")))
        self.assertIn(b"armed for 60 seconds", replies[0])

    def test_validation_only_reads_fresh_state_and_never_presents_or_requests(self):
        self.runtime = self.make_runtime(None)
        self.runtime.enter_update()
        self.assertEqual(self.samples, 0)
        self.runtime.observe_say(self.current.receiver)
        self.runtime.cockpit_entered()
        self.runtime.transition(0xABCDEF00)
        self.runtime.exit_update()
        self.assertEqual(self.samples, 3)
        receiver = next(fields for name, fields in self.events if name == "world_receiver_validation")
        self.assertTrue(receiver["say_receiver_match"])
        self.assertEqual(receiver["update_depth"], 1)
        self.assertTrue(receiver["engine_thread"])
        transition = next(fields for name, fields in self.events if name == "world_transition_validation")
        self.assertTrue(transition["application_receiver"])
        self.assertTrue(any(name == "world_runtime_state" and fields["context"] == "cockpit"
                            for name, fields in self.events))
        self.assertEqual(self.presentations, [])
        self.assertEqual(self.bridge.handles, [])
        self.assertNotIn(str(self.current.receiver), repr(self.events))
        self.assertNotIn(str(0xABCDEF00), repr(self.events))

    def test_validation_records_receiver_equality_even_when_game_state_is_unsafe(self):
        self.runtime = self.make_runtime(None)
        self.current = replace(self.current, playable=False)
        self.frame(lambda: self.runtime.observe_say(self.current.receiver))
        receiver = next(fields for name, fields in self.events if name == "world_receiver_validation")
        self.assertTrue(receiver["say_receiver_match"])
        self.assertFalse(self.runtime.calibrated)
        self.assertEqual(self.presentations, [])

    def test_natural_match_calibrates_and_outer_exit_presents_once_with_fresh_receiver(self):
        self.calibrate()
        self.bridge.ready = b"Server result."
        new_receiver = self.current.receiver + 0x1000
        self.bridge.poll_hook = lambda: setattr(self, "current", replace(self.current, receiver=new_receiver))
        self.frame()
        self.frame()
        self.assertEqual(self.presentations, [(new_receiver, b"Server result.")])
        self.assertFalse(any(isinstance(value, TestSample) for value in vars(self.runtime).values()))
        self.assertTrue(any(name == "world_automatic_submission" for name, _ in self.events))
        self.assertFalse(any(name == "world_automatic_presentation" for name, _ in self.events))

    def test_each_new_lifecycle_logs_recalibration(self):
        self.calibrate()
        self.frame(lambda: self.runtime.observe_say(self.current.receiver))
        self.runtime.transition(0xABCDEF00)
        self.calibrate()
        self.current = replace(self.current, playable=False)
        self.frame()
        self.current = replace(self.current, playable=True)
        self.calibrate()
        self.assertEqual(sum(name == "world_calibration" for name, _ in self.events), 3)

    def test_nested_update_never_delivers_before_outer_exit_and_scope_does_not_underflow(self):
        self.calibrate()
        self.bridge.ready = b"Nested result."
        self.runtime.enter_update()
        self.runtime.enter_update()
        self.runtime.exit_update()
        self.assertEqual(self.presentations, [])
        self.runtime.exit_update()
        self.assertEqual(len(self.presentations), 1)
        self.runtime.exit_update()
        self.runtime.exit_update()
        self.assertEqual(len(self.presentations), 1)

    def test_matching_chat_outside_update_or_other_thread_cannot_calibrate(self):
        self.runtime.observe_say(self.current.receiver)
        self.assertFalse(self.runtime.calibrated)
        self.calibrate()
        self.bridge.ready = b"Must disappear."
        errors = []

        def other_thread():
            try:
                self.frame(lambda: self.runtime.observe_say(self.current.receiver))
            except Exception as error:
                errors.append(error)

        worker = threading.Thread(target=other_thread)
        worker.start()
        worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])
        self.assertFalse(self.runtime.calibrated)
        self.frame()
        self.assertEqual(self.presentations, [])

    def test_mismatch_and_every_fsm_transition_cancel_even_non_application_receiver(self):
        for action in (lambda: self.runtime.observe_say(self.current.receiver + 1),
                       lambda: self.runtime.transition(0xABCDEF00),
                       lambda: self.runtime.transition(0x123456)):
            with self.subTest(action=action):
                self.calibrate()
                self.bridge.ready = b"Old result."
                self.frame(action)
                self.assertFalse(self.runtime.calibrated)
                self.assertIsNone(self.bridge.ready)
        self.assertEqual(self.presentations, [])

    def test_invalid_state_and_read_errors_cancel_without_leaking_exception_details(self):
        original = self.current
        invalid = (replace(original, playable=False), replace(original, pending_clear=False),
                   replace(original, owner_valid=False), replace(original, receiver=0),
                   RuntimeError("SECRET ADDRESS OR CREDENTIAL"))
        for current in invalid:
            with self.subTest(current=current):
                self.current = original
                self.calibrate()
                self.bridge.ready = b"Stale success."
                self.current = current
                self.frame()
                self.assertFalse(self.runtime.calibrated)
                self.assertIsNone(self.bridge.ready)
        self.assertEqual(self.presentations, [])
        self.assertNotIn("SECRET", repr(self.events))

    def test_state_change_after_poll_discards_consumed_bytes_before_native_call(self):
        self.calibrate()
        self.bridge.ready = b"Result consumed just before transition."
        self.bridge.poll_hook = lambda: setattr(self, "current", replace(self.current, pending_clear=False))
        self.frame()
        self.assertEqual(self.presentations, [])
        self.assertFalse(self.runtime.calibrated)
        self.assertTrue(any(name == "world_delivery_discarded" for name, _ in self.events))

    def test_own_native_presentation_reentry_cannot_calibrate_or_invalidate(self):
        self.calibrate()
        self.bridge.ready = b"Owned reply."

        def reenter(receiver, message):
            self.present(receiver, message)
            self.runtime.observe_say(receiver + 1)

        self.runtime._present = reenter
        before = self.bridge.cancel_calls
        self.frame()
        self.assertEqual(len(self.presentations), 1)
        self.assertTrue(self.runtime.calibrated)
        self.assertEqual(self.bridge.cancel_calls, before)

    def test_arm_requires_calibration_outer_scope_and_idle_bridge(self):
        self.assertIn(b"current game update", self.runtime.handle(b"/community arm"))
        replies = []
        self.frame(lambda: replies.append(self.runtime.handle(b"/community arm")))
        self.assertIn(b"unavailable", replies[-1])
        self.calibrate()
        self.bridge.outstanding = True
        self.frame(lambda: replies.append(self.runtime.handle(b"/community arm")))
        self.assertIn(b"already pending", replies[-1])
        self.assertEqual(self.bridge.handles, [])

    def test_one_armed_entry_queues_one_probe_and_owned_notice_on_next_update(self):
        self.calibrate()
        self.arm()
        self.frame(self.runtime.cockpit_entered)
        self.assertEqual(self.bridge.handles, [b"/community"])
        self.assertEqual(self.presentations, [])
        self.frame(self.runtime.cockpit_entered)
        self.assertEqual(self.bridge.handles, [b"/community"])
        self.assertEqual(len(self.presentations), 1)
        self.assertIn(b"connecting/sending", self.presentations[0][1])
        self.bridge.ready = b"Server chose this result."
        self.frame()
        self.assertEqual([text for _, text in self.presentations],
                         [b"Community lab: connecting/sending. Reply will appear automatically.",
                          b"Server chose this result."])

    def test_unarmed_and_expired_entries_never_send_a_probe(self):
        self.calibrate()
        self.frame(self.runtime.cockpit_entered)
        self.arm()
        self.now += ARM_LIFETIME
        self.frame(self.runtime.cockpit_entered)
        self.assertEqual(self.bridge.handles, [])
        self.assertEqual(self.presentations, [])

    def test_leave_and_reconnect_cancel_notice_and_disarm(self):
        for command in (b"/community leave", b"/community reconnect"):
            with self.subTest(command=command):
                self.calibrate()
                self.arm()
                self.frame(self.runtime.cockpit_entered)
                self.assertIn(b"disconnected", self.runtime.handle(command))
                self.assertFalse(self.runtime.calibrated)
                self.calibrate()
                self.frame(self.runtime.cockpit_entered)
                self.assertEqual(self.presentations, [])
        self.assertEqual(self.bridge.handles.count(b"/community"), 2)

    def test_cancel_contention_blocks_requests_and_delivery_until_retry_succeeds(self):
        self.calibrate()
        self.bridge.ready = b"Late committed result."
        self.bridge.cancel_allowed = False
        self.runtime.transition(0xABCDEF00)
        before_polls = self.bridge.polls
        before_handles = list(self.bridge.handles)
        for _ in range(3):
            self.assertEqual(self.runtime.handle(b"/community"), WAIT_CANCEL)
            self.frame(self.runtime.cockpit_entered)
        self.assertEqual(self.bridge.polls, before_polls)
        self.assertEqual(self.bridge.handles, before_handles)
        self.assertEqual(self.presentations, [])
        self.bridge.cancel_allowed = True
        self.frame()
        self.assertIsNone(self.bridge.ready)
        self.assertFalse(self.runtime.calibrated)
        self.calibrate()
        self.assertIn(b"connecting/sending", self.runtime.handle(b"/community"))

    def test_manual_commands_and_result_fallback_still_use_bridge(self):
        self.assertIn(b"connecting/sending", self.runtime.handle(b"/community state"))
        self.bridge.ready = b"Manual result."
        self.assertEqual(self.runtime.handle(b"/community result"), b"Manual result.")
        self.calibrate()
        self.frame()
        self.assertEqual(self.presentations, [])
        self.assertIn(b"/community arm", self.runtime.commands)

    def test_off_is_terminal_even_while_worker_gate_is_busy_and_retries_without_native_calls(self):
        self.calibrate()
        self.bridge.ready = b"Must not display."
        self.bridge.off_allowed = False
        self.assertEqual(self.runtime.handle(b"/community off"), DISABLED)
        self.assertFalse(self.runtime.enabled)
        before_samples = self.samples
        self.frame()
        self.assertEqual(self.samples, before_samples)
        self.assertEqual(self.presentations, [])
        self.bridge.off_allowed = True
        self.frame()
        off_calls = len(self.bridge.handles)
        self.frame()
        self.assertEqual(len(self.bridge.handles), off_calls)
        self.assertEqual(self.runtime.handle(b"/community"), DISABLED)
        self.assertFalse(self.runtime.enabled)

    def test_native_call_or_diagnostic_failure_disables_without_exception_leak(self):
        self.calibrate()
        self.bridge.ready = b"Reply."

        def fail(*args, **kwargs):
            raise RuntimeError("SECRET FAILURE")

        self.runtime._present = fail
        self.frame()
        self.assertFalse(self.runtime.enabled)
        self.assertNotIn("SECRET", repr(self.events))
        self.runtime = self.make_runtime(None)
        self.runtime._emit = fail
        self.frame()
        self.assertFalse(self.runtime.enabled)

    def test_arm_diagnostic_failure_cannot_report_success_or_leave_an_arm(self):
        self.calibrate()

        def failing_emit(name, **fields):
            if name == "world_cockpit_arm" and fields["armed"]:
                raise RuntimeError("SECRET DIAGNOSTIC FAILURE")
            self.emit(name, **fields)

        self.runtime._emit = failing_emit
        responses = []
        self.frame(lambda: responses.append(self.runtime.handle(b"/community arm")))
        self.assertEqual(responses, [DISABLED])
        self.assertFalse(self.runtime.enabled)
        self.assertIsNone(self.runtime._armed_until)
        self.assertNotIn(b"/community", self.bridge.handles)
        self.assertNotIn("SECRET", repr(self.events))

    def test_consumed_arm_diagnostic_failure_stops_before_request_forwarding(self):
        self.calibrate()
        self.arm()

        def failing_emit(name, **fields):
            if name == "world_cockpit_arm" and fields["reason"] == "consumed":
                raise RuntimeError("SECRET DIAGNOSTIC FAILURE")
            self.emit(name, **fields)

        self.runtime._emit = failing_emit
        self.frame(self.runtime.cockpit_entered)
        self.assertFalse(self.runtime.enabled)
        self.assertNotIn(b"/community", self.bridge.handles)
        self.assertIsNone(self.runtime._notice)
        self.assertEqual(self.presentations, [])
        self.assertNotIn("SECRET", repr(self.events))

    def test_request_diagnostic_failure_cannot_retain_notice_after_disabling(self):
        self.calibrate()
        self.arm()

        def failing_emit(name, **fields):
            if name == "world_cockpit_request":
                raise RuntimeError("SECRET DIAGNOSTIC FAILURE")
            self.emit(name, **fields)

        self.runtime._emit = failing_emit
        self.frame(self.runtime.cockpit_entered)
        self.assertFalse(self.runtime.enabled)
        self.assertEqual(self.bridge.handles.count(b"/community"), 1)
        self.assertIsNone(self.runtime._notice)
        self.assertEqual(self.presentations, [])
        self.assertNotIn("SECRET", repr(self.events))

    def test_reentrant_invalidation_during_busy_check_prevents_request(self):
        self.calibrate()
        self.arm()

        def invalidating_busy():
            self.runtime.transition(0xABCDEF00)
            return False

        self.bridge.busy = invalidating_busy
        self.frame(self.runtime.cockpit_entered)
        self.assertNotIn(b"/community", self.bridge.handles)
        self.assertFalse(self.runtime.calibrated)
        self.assertIsNone(self.runtime._notice)
        self.assertGreater(self.bridge.cancel_calls, 0)

    def test_reentrant_invalidation_after_request_discards_notice_and_cancels(self):
        self.calibrate()
        self.arm()
        original_handle = self.bridge.handle

        def invalidating_handle(command):
            result = original_handle(command)
            if command == b"/community":
                self.runtime.transition(0xABCDEF00)
            return result

        self.bridge.handle = invalidating_handle
        self.frame(self.runtime.cockpit_entered)
        self.assertEqual(self.bridge.handles.count(b"/community"), 1)
        self.assertIsNone(self.runtime._notice)
        self.assertFalse(self.bridge.outstanding)
        self.assertFalse(self.runtime.calibrated)
        self.frame()
        self.assertEqual(self.presentations, [])

    def test_bridge_exceptions_are_fixed_code_failures_and_do_not_escape_callbacks(self):
        def fail(*args, **kwargs):
            raise RuntimeError("SECRET BRIDGE FAILURE")

        for operation in ("arm_busy", "cockpit_busy", "cockpit_request", "poll", "command", "lifecycle"):
            with self.subTest(operation=operation):
                self.setUp()
                self.calibrate()
                if operation in ("cockpit_busy", "cockpit_request"):
                    self.arm()
                if operation.endswith("busy"):
                    self.bridge.busy = fail
                elif operation in ("cockpit_request", "command"):
                    self.bridge.handle = fail
                elif operation == "poll":
                    self.bridge.poll = fail
                else:
                    self.bridge.cancel_pending = fail
                if operation == "arm_busy":
                    self.frame(lambda: self.assertEqual(self.runtime.handle(b"/community arm"), DISABLED))
                elif operation.startswith("cockpit"):
                    self.frame(self.runtime.cockpit_entered)
                elif operation == "poll":
                    self.frame()
                elif operation == "command":
                    self.assertEqual(self.runtime.handle(b"/community"), DISABLED)
                else:
                    self.runtime.transition(0xABCDEF00)
                self.assertFalse(self.runtime.enabled)
                self.assertEqual(self.presentations, [])
                failures = [fields for name, fields in self.events if name == "world_bridge_failed"]
                self.assertGreater(len(failures), 0)
                self.assertTrue(all(set(fields) == {"operation"} for fields in failures))
                self.assertNotIn("SECRET", repr(self.events))
    def test_repeated_invalid_frames_have_bounded_scalar_diagnostics(self):
        self.current = replace(self.current, playable=False)
        for _ in range(1000):
            self.frame()
        self.assertLessEqual(len(self.events), 3)
        self.assertEqual(self.bridge.cancel_calls, 1)
        for i in range(300):
            self.current = replace(self.current, playable=bool(i % 2))
            self.frame()
        self.assertLessEqual(len(self.events), DETAIL_LIMIT)
        self.assertTrue(all(type(value) in (str, int, bool) for _, fields in self.events for value in fields.values()))


if __name__ == "__main__":
    unittest.main()
