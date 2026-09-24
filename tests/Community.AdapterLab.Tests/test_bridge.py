"""Game-free lifecycle tests with deliberately delayed/uncooperative service replies."""

from dataclasses import dataclass, field
from pathlib import Path
import sys
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "Community.AdapterLab"))
from bridge import Bridge, LIFETIME
from interaction import Interaction
from service_client import ClientConfig, ServiceError


def service_result(message="Original server response.", revision=1, progress=None):
    return {"message": message, "revision": revision, "progress": revision if progress is None else progress,
            "memberId": "55555555-5555-4555-8555-555555555555",
            "interactionId": "22222222-2222-4222-8222-222222222222", "status": "available"}


class Events:
    def __init__(self):
        self.records = []
        self.changed = threading.Condition()

    def __call__(self, name, **fields):
        with self.changed:
            self.records.append((name, fields))
            self.changed.notify_all()

    def wait(self, name, count=1):
        with self.changed:
            return self.changed.wait_for(
                lambda: sum(event == name for event, _ in self.records) >= count, timeout=3)


@dataclass
class Reply:
    value: object = field(default_factory=service_result)
    release: threading.Event = field(default_factory=threading.Event)
    started: threading.Event = field(default_factory=threading.Event)
    cancelled: object = None
    request_id: str = ""


class DelayedClient:
    """Ignores cancellation until released, simulating an already committed request."""

    def __init__(self, replies):
        self.replies = replies
        self.calls = 0
        self.operations = []
        self.closed = threading.Event()

    def probe(self, request_id, cancelled):
        self.operations.append("probe")
        return self.respond(request_id, cancelled)

    def state(self, cancelled):
        self.operations.append("state")
        return self.respond(None, cancelled)

    def respond(self, request_id, cancelled):
        reply = self.replies[self.calls]
        self.calls += 1
        reply.request_id = request_id
        reply.cancelled = cancelled
        reply.started.set()
        if not reply.release.wait(5):
            raise RuntimeError("Test did not release the delayed service reply")
        if isinstance(reply.value, Exception):
            raise reply.value
        return reply.value

    def close(self):
        self.closed.set()


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.events = Events()
        self.fixtures = []
        self.now = 100.0

    def tearDown(self):
        for bridge, client in self.fixtures:
            for reply in client.replies:
                reply.release.set()
            bridge.handle(b"/community off")
            bridge._thread.join(3)
            self.assertFalse(bridge._thread.is_alive(), "Bridge worker leaked after test cleanup")

    def make_bridge(self, *replies):
        client = DelayedClient(list(replies))
        bridge = Bridge(ClientConfig(18181, "test-community", "alice", "A" * 64),
                        self.events, client=client, clock=lambda: self.now)
        self.fixtures.append((bridge, client))
        return bridge, client, Interaction(self.events, bridge)

    @staticmethod
    def command(interaction, text):
        interaction.begin(text)
        try:
            return interaction.reply(True)
        finally:
            interaction.end()

    def result(self, interaction):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            value = self.command(interaction, b"/community result")
            if value is not None and b"connecting or waiting" not in value:
                return value
            threading.Event().wait(0.005)
        self.fail("Worker did not publish a response")

    def test_delayed_network_does_not_block_callback_and_only_one_request_is_outstanding(self):
        reply = Reply()
        bridge, client, interaction = self.make_bridge(reply)
        started = time.monotonic()
        self.assertIn(b"connecting/sending", self.command(interaction, b"/community"))
        self.assertLess(time.monotonic() - started, 0.5)
        self.assertTrue(reply.started.wait(2))
        self.assertFalse(reply.release.is_set())
        for _ in range(5):
            self.assertIn(b"already pending", self.command(interaction, b"/community"))
            self.assertIn(b"connecting or waiting", self.command(interaction, b"/community result"))
        self.assertEqual(client.calls, 1)
        reply.release.set()
        self.assertEqual(self.result(interaction), b"[test-community #1 progress 1] Original server response.")
        self.assertIn(b"No community result", self.command(interaction, b"/community result"))
        self.assertEqual(client.calls, 1)
        self.assertEqual(sum(name == "server_presentation" for name, _ in self.events.records), 1)

    def test_no_request_is_sent_without_the_correlated_native_system_reply(self):
        reply = Reply()
        _, client, interaction = self.make_bridge(reply)
        interaction.begin(b"/community")
        self.assertIsNone(interaction.reply(False))
        interaction.end()
        self.assertEqual(client.calls, 0)
        self.assertIsNone(interaction.reply(True))
        self.assertIn(b"No community result", self.command(interaction, b"/community result"))
        self.assertEqual(client.calls, 0)

    def test_state_command_is_async_read_only_and_displays_progress_once(self):
        reply = Reply(service_result("Persisted response.", 301, 299))
        _, client, interaction = self.make_bridge(reply)
        started = time.monotonic()
        self.assertIn(b"reading saved progress", self.command(interaction, b"/community state"))
        self.assertLess(time.monotonic() - started, 0.5)
        self.assertTrue(reply.started.wait(2))
        self.assertIn(b"already pending", self.command(interaction, b"/community"))
        self.assertIn(b"already pending", self.command(interaction, b"/community state"))
        reply.release.set()
        self.assertEqual(self.result(interaction), b"[test-community #301 progress 299] Persisted response.")
        self.assertIn(b"No community result", self.command(interaction, b"/community result"))
        self.assertEqual(client.operations, ["state"])
        response = next(fields for name, fields in self.events.records if name == "server_response")
        self.assertEqual((response["operation"], response["progress"], response["member_id"]),
                         ("state", 299, reply.value["memberId"]))

    def test_state_without_correlated_native_reply_or_exact_command_does_nothing(self):
        _, client, interaction = self.make_bridge(Reply())
        interaction.begin(b"/community state")
        self.assertIsNone(interaction.reply(False))
        interaction.end()
        for text in (b"/community statex", b"/community state ", b" /community state"):
            self.assertIsNone(self.command(interaction, text))
        self.assertEqual(client.operations, [])

    def test_reconnect_cancels_state_read_and_next_read_keeps_progress(self):
        old = Reply(service_result("Old read.", 300, 298))
        new = Reply(service_result("Fresh read.", 300, 298))
        _, client, interaction = self.make_bridge(old, new)
        self.command(interaction, b"/community state")
        self.assertTrue(old.started.wait(2))
        self.command(interaction, b"/community reconnect")
        self.assertTrue(old.cancelled())
        old.release.set()
        self.assertTrue(self.events.wait("late_response_discarded"))
        self.assertTrue(client.closed.wait(2))
        deadline = time.monotonic() + 2
        while b"reading saved progress" not in self.command(interaction, b"/community state"):
            self.assertLess(time.monotonic(), deadline)
            threading.Event().wait(0.005)
        self.assertTrue(new.started.wait(2))
        new.release.set()
        self.assertEqual(self.result(interaction), b"[test-community #300 progress 298] Fresh read.")
        self.assertEqual(client.operations, ["state", "state"])

    def test_expired_state_read_can_be_reissued_without_a_mutation(self):
        reply = Reply()
        _, client, interaction = self.make_bridge(reply)
        self.command(interaction, b"/community state")
        self.assertTrue(reply.started.wait(2))
        self.now += LIFETIME + 1
        value = self.command(interaction, b"/community result")
        self.assertIn(b"state result expired", value)
        self.assertNotIn(b"outcome unknown", value)
        self.assertTrue(reply.cancelled())
        reply.release.set()
        self.assertTrue(self.events.wait("late_response_discarded"))
        self.assertEqual(client.operations, ["state"])

    def test_ready_result_survives_missing_unrelated_and_other_thread_native_replies(self):
        reply = Reply()
        _, _, interaction = self.make_bridge(reply)
        self.command(interaction, b"/community")
        self.assertTrue(reply.started.wait(2))
        reply.release.set()
        self.assertTrue(self.events.wait("server_response"))
        interaction.begin(b"/community result")
        interaction.end()  # The game's Parse callback produced no system Say.
        interaction.begin(b"/community result")
        observed = []
        other = threading.Thread(target=lambda: observed.append(interaction.reply(True)))
        other.start()
        other.join(2)
        self.assertEqual(observed, [None])
        interaction.begin(b"ordinary message")
        self.assertIsNone(interaction.reply(True))
        interaction.end()
        self.assertIsNone(interaction.reply(False))
        interaction.end()
        self.assertFalse(any(name == "server_presentation" for name, _ in self.events.records))
        self.assertEqual(self.result(interaction), b"[test-community #1 progress 1] Original server response.")

    def test_leave_and_reconnect_discard_late_response_before_accepting_new_generation(self):
        for lifecycle_command in (b"/community leave", b"/community reconnect"):
            with self.subTest(command=lifecycle_command):
                old = Reply(service_result("Old generation must disappear.", 1))
                new = Reply(service_result("Fresh generation response.", 2))
                _, client, interaction = self.make_bridge(old, new)
                discarded_before = sum(name == "late_response_discarded" for name, _ in self.events.records)
                self.command(interaction, b"/community")
                self.assertTrue(old.started.wait(2))
                self.command(interaction, lifecycle_command)
                self.assertTrue(old.cancelled())
                old.release.set()
                self.assertTrue(self.events.wait("late_response_discarded", discarded_before + 1))
                self.assertTrue(client.closed.wait(2))
                self.assertIn(b"No community result", self.command(interaction, b"/community result"))
                deadline = time.monotonic() + 2
                while b"connecting/sending" not in self.command(interaction, b"/community"):
                    self.assertLess(time.monotonic(), deadline)
                    threading.Event().wait(0.005)
                self.assertTrue(new.started.wait(2))
                self.assertFalse(new.cancelled())
                self.assertNotEqual(old.request_id, new.request_id)
                new.release.set()
                self.assertEqual(self.result(interaction), b"[test-community #2 progress 2] Fresh generation response.")

    def test_off_cancels_pending_request_without_waiting_then_closes_worker(self):
        reply = Reply()
        bridge, client, interaction = self.make_bridge(reply)
        self.command(interaction, b"/community")
        self.assertTrue(reply.started.wait(2))
        started = time.monotonic()
        self.assertIn(b"disabled", self.command(interaction, b"/community off"))
        self.assertLess(time.monotonic() - started, 0.5)
        self.assertTrue(reply.cancelled())
        self.assertIsNone(self.command(interaction, b"/community"))
        reply.release.set()
        bridge._thread.join(3)
        self.assertFalse(bridge._thread.is_alive())
        self.assertTrue(client.closed.is_set())
        self.assertTrue(self.events.wait("late_response_discarded"))
        self.assertFalse(any(name == "server_presentation" for name, _ in self.events.records))

    def test_off_without_native_reply_leaves_command_enabled_for_a_real_shutdown(self):
        bridge, client, interaction = self.make_bridge(Reply())
        interaction.begin(b"/community off")
        interaction.end()
        self.assertIn(b"disabled", self.command(interaction, b"/community off"))
        bridge._thread.join(3)
        self.assertFalse(bridge._thread.is_alive())
        self.assertTrue(client.closed.is_set())

    def test_contended_lock_returns_immediately_and_busy_off_can_be_retried(self):
        bridge, client, interaction = self.make_bridge(Reply())
        with bridge._lock:
            started = time.monotonic()
            self.assertIn(b"busy", self.command(interaction, b"/community off"))
            self.assertLess(time.monotonic() - started, 0.5)
        self.assertEqual(client.calls, 0)
        self.assertIn(b"disabled", self.command(interaction, b"/community off"))
        bridge._thread.join(3)
        self.assertFalse(bridge._thread.is_alive())

    def test_expired_pending_request_is_cancelled_and_its_late_result_is_not_presented(self):
        reply = Reply(service_result("Expired success must disappear.", 1))
        _, _, interaction = self.make_bridge(reply)
        self.command(interaction, b"/community")
        self.assertTrue(reply.started.wait(2))
        self.now += LIFETIME + 1
        self.assertIn(b"expired; outcome unknown", self.command(interaction, b"/community result"))
        self.assertTrue(reply.cancelled())
        reply.release.set()
        self.assertTrue(self.events.wait("late_response_discarded"))
        self.assertIn(b"No community result", self.command(interaction, b"/community result"))

    def test_ready_response_also_expires_before_the_next_game_callback(self):
        reply = Reply(service_result("Expired ready result must disappear.", 1))
        bridge, _, interaction = self.make_bridge(reply)
        self.command(interaction, b"/community")
        self.assertTrue(reply.started.wait(2))
        reply.release.set()
        self.assertTrue(self.events.wait("server_response"))
        # Synchronize publication, which occurs after the server_response diagnostic.
        deadline = time.monotonic() + 2
        while True:
            with bridge._lock:
                ready = bridge._ready is not None
            if ready:
                break
            self.assertLess(time.monotonic(), deadline)
            threading.Event().wait(0.005)
        self.now += LIFETIME + 1
        self.assertIn(b"expired", self.command(interaction, b"/community result"))
        self.assertIn(b"No community result", self.command(interaction, b"/community result"))

    def test_service_errors_and_unexpected_exception_are_bounded_and_worker_recovers(self):
        for error, expected in ((ServiceError("unavailable"), b"unavailable or timed out"),
                                (ServiceError("invalid_session"), b"invalid_session"),
                                (ServiceError("invalid_response"), b"invalid_response"),
                                (RuntimeError("SECRET-CREDENTIAL-DO-NOT-LOG"), b"client error")):
            with self.subTest(error=type(error).__name__, expected=expected):
                failed = Reply(error)
                recovered = Reply(service_result("Recovered.", 2))
                _, _, interaction = self.make_bridge(failed, recovered)
                failed.release.set()
                self.command(interaction, b"/community")
                value = self.result(interaction)
                self.assertIn(expected, value)
                self.assertNotIn(b"SECRET", value)
                self.assertNotIn("SECRET", repr(self.events.records))
                recovered.release.set()
                self.command(interaction, b"/community")
                self.assertEqual(self.result(interaction), b"[test-community #2 progress 2] Recovered.")

    def test_service_text_is_ascii_bounded_and_cannot_introduce_native_formatting(self):
        reply = Reply(service_result("<RED>\n\x00\u2603" + "x" * 700, 1))
        _, _, interaction = self.make_bridge(reply)
        reply.release.set()
        self.command(interaction, b"/community")
        value = self.result(interaction)
        self.assertLessEqual(len(value), 640)
        self.assertTrue(value.isascii())
        for forbidden in (b"<", b">", b"\n", b"\x00"):
            self.assertNotIn(forbidden, value)


if __name__ == "__main__":
    unittest.main()
