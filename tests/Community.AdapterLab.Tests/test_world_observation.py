"""Game-free checks for bounded native-callback diagnostics."""

from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "Community.AdapterLab"))
from world_observation import DETAIL_LIMIT, SUMMARY_INTERVAL, WorldObservation


class WorldObservationTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.events = []
        self.observer = WorldObservation(self.emit, clock=lambda: self.now)

    def emit(self, name, **fields):
        # The real native wrapper adds the callback's thread identity.
        self.events.append((name, {**fields, "thread": threading.get_ident()}))

    def details(self, kind=None):
        return [fields for name, fields in self.events
                if name == "world_callback" and (kind is None or fields["kind"] == kind)]

    def summaries(self):
        return [fields for name, fields in self.events if name == "world_summary"]

    def test_nested_updates_keep_scope_until_outer_exit_without_underflow(self):
        self.observer.exit_update()
        self.observer.enter_update()
        self.observer.enter_update()
        self.observer.observe("cockpit_entered")
        self.observer.exit_update()
        self.observer.observe("cockpit_entered")
        self.observer.exit_update()
        self.observer.observe("cockpit_entered")
        self.observer.exit_update()
        self.observer.observe("cockpit_entered")

        self.assertEqual([event["within_update"] for event in self.details("cockpit_entered")],
                         [True, True, False, False])
        self.assertEqual(self.observer.snapshot()["application_update"], 2)
        self.assertEqual(self.observer.snapshot()["cockpit_entered"], 4)

    def test_another_thread_cannot_inherit_update_scope(self):
        main_thread = threading.get_ident()
        self.observer.enter_update()
        errors = []

        def other_thread():
            try:
                self.observer.observe("native_say")
                self.observer.enter_update()
                self.observer.observe("native_say")
                self.observer.exit_update()
                self.observer.observe("native_say")
            except Exception as error:
                errors.append(error)

        worker = threading.Thread(target=other_thread)
        worker.start()
        worker.join(2)
        self.assertFalse(worker.is_alive(), "Observer callback blocked the worker")
        self.assertEqual(errors, [])
        self.observer.observe("native_say")
        self.observer.exit_update()

        details = self.details("native_say")
        self.assertEqual([event["within_update"] for event in details], [False, True, False, True])
        self.assertTrue(all(event["thread"] != main_thread for event in details[:3]))
        self.assertEqual(details[-1]["thread"], main_thread)

    def test_frame_burst_keeps_counts_without_flooding_diagnostics(self):
        for _ in range(1000):
            self.observer.enter_update()
            self.observer.observe("player_update")
            self.observer.exit_update()

        snapshot = self.observer.snapshot()
        self.assertEqual(snapshot["application_update"], 1000)
        self.assertEqual(snapshot["player_update"], 1000)
        self.assertEqual(snapshot["cockpit_entered"], 0)
        self.assertEqual(len(self.details()), 2)
        self.assertEqual(self.summaries(), [])

    def test_detail_budget_is_shared_while_summary_counts_continue(self):
        kinds = ("cockpit_entered", "state_change", "native_say")
        for _ in range(DETAIL_LIMIT):
            for kind in kinds:
                self.observer.observe(kind)

        self.assertEqual(len(self.details()), DETAIL_LIMIT)
        self.now += SUMMARY_INTERVAL
        self.observer.observe("cockpit_entered")
        self.assertEqual(len(self.details()), DETAIL_LIMIT)
        summary = self.summaries()[0]
        self.assertEqual(summary["details"], DETAIL_LIMIT)
        self.assertEqual(summary["cockpit_entered"], DETAIL_LIMIT + 1)
        self.assertEqual(summary["state_change"], DETAIL_LIMIT)
        self.assertEqual(summary["native_say"], DETAIL_LIMIT)

    def test_summary_uses_injected_clock_and_does_not_catch_up_with_a_log_burst(self):
        self.observer.observe("state_change")
        self.now += SUMMARY_INTERVAL - 0.01
        self.observer.observe("native_say")
        self.assertEqual(self.summaries(), [])

        self.now = 100.0 + SUMMARY_INTERVAL
        self.observer.observe("player_update")
        self.observer.observe("player_update")
        self.assertEqual(len(self.summaries()), 1)
        self.assertEqual(self.summaries()[0]["player_update"], 1)

        self.now += SUMMARY_INTERVAL * 100
        self.observer.observe("player_update")
        self.observer.observe("player_update")
        self.assertEqual(len(self.summaries()), 2)
        self.assertEqual(self.summaries()[-1]["player_update"], 3)

    def test_busy_gate_drops_without_waiting_or_faking_a_snapshot(self):
        self.observer._gate.acquire()
        completed = threading.Event()
        snapshots = []

        def callback_while_busy():
            self.observer.observe("cockpit_entered")
            snapshots.append(self.observer.snapshot())
            completed.set()

        worker = threading.Thread(target=callback_while_busy)
        worker.start()
        try:
            self.assertTrue(completed.wait(1), "Native callback waited on diagnostic contention")
        finally:
            self.observer._gate.release()
            worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(snapshots, [None])
        snapshot = self.observer.snapshot()
        self.assertEqual(snapshot["dropped"], 1)
        self.assertEqual(snapshot["cockpit_entered"], 0)
        self.assertEqual(self.events, [])
        self.observer.observe("cockpit_entered")
        self.assertEqual(self.observer.snapshot()["cockpit_entered"], 1)

    def test_disable_stops_observations_and_accepts_trailing_exit(self):
        self.observer.enter_update()
        self.observer.observe("cockpit_entered")
        self.observer.disable()
        disabled_snapshot = self.observer.snapshot()
        events_before = list(self.events)
        self.now += SUMMARY_INTERVAL * 2
        self.observer.exit_update()
        self.observer.exit_update()
        self.observer.disable()
        self.observer.enter_update()
        for kind in ("cockpit_entered", "state_change", "native_say", "player_update"):
            self.observer.observe(kind)
        self.observer.exit_update()

        self.assertFalse(disabled_snapshot["enabled"])
        self.assertEqual(self.observer.snapshot(), disabled_snapshot)
        self.assertEqual(self.events, events_before)

    def test_emitter_failure_disables_observation_without_escaping_callback(self):
        for failure_event in ("world_callback", "world_summary"):
            with self.subTest(failure_event=failure_event):
                calls = []

                def failing_emit(name, **fields):
                    calls.append(name)
                    if name == failure_event:
                        raise RuntimeError("Diagnostic destination unavailable")

                observer = WorldObservation(failing_emit, clock=lambda: self.now)
                self.now += SUMMARY_INTERVAL
                observer.observe("cockpit_entered")
                self.assertIn(failure_event, calls)
                snapshot = observer.snapshot()
                self.assertIsNotNone(snapshot, "Failed publication leaked the diagnostic lock")
                self.assertFalse(snapshot["enabled"])
                call_count = len(calls)
                observer.observe("cockpit_entered")
                self.assertEqual(observer.snapshot(), snapshot)
                self.assertEqual(len(calls), call_count)

    def test_snapshots_are_detached_scalar_records(self):
        self.observer.observe("cockpit_entered")
        snapshot = self.observer.snapshot()
        self.assertTrue(all(type(value) in (int, bool) for value in snapshot.values()))
        snapshot["cockpit_entered"] = -1
        snapshot["enabled"] = False
        self.assertEqual(self.observer.snapshot()["cockpit_entered"], 1)
        self.assertTrue(self.observer.snapshot()["enabled"])

    def test_invalid_kinds_cannot_extend_the_diagnostic_schema(self):
        before = self.observer.snapshot()
        for kind in ("application_update", "arbitrary_native_pointer", "", None):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.observer.observe(kind)
        self.assertEqual(self.observer.snapshot(), before)
        self.assertEqual(self.events, [])


if __name__ == "__main__":
    unittest.main()
