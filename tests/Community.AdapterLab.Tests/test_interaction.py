import sys
from pathlib import Path
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "Community.AdapterLab"))
from interaction import Interaction


class InteractionTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.probe = Interaction(lambda event, **fields: self.events.append((event, fields)))

    def test_only_exact_command_replaces_one_system_reply(self):
        self.probe.begin(b"/community")
        self.assertIsNone(self.probe.reply(False))
        self.assertIn(b"Local probe #1", self.probe.reply(True))
        self.assertIsNone(self.probe.reply(True))
        self.probe.end()
        self.assertIsNone(self.probe.reply(True))
        self.assertEqual([e[0] for e in self.events], ["interaction", "presentation_requested"])

    def test_unrelated_and_nested_chat_are_preserved(self):
        self.probe.begin(b"/community")
        self.probe.begin(b"ordinary message")
        self.assertIsNone(self.probe.reply(True))
        self.probe.end()
        self.assertIn(b"Local probe #1", self.probe.reply(True))
        self.probe.end()
        for value in (b"/communityx", b" /community", b"/community ", b"hello"):
            self.probe.begin(value)
            self.assertIsNone(self.probe.reply(True))
            self.probe.end()

    def test_other_thread_cannot_consume_response(self):
        self.probe.begin(b"/community")
        output = []
        worker = threading.Thread(target=lambda: output.append(self.probe.reply(True)))
        worker.start()
        worker.join()
        self.assertEqual(output, [None])
        self.assertIn(b"Local probe #1", self.probe.reply(True))
        self.probe.end()

    def test_no_reply_is_recorded_and_cannot_leak(self):
        self.probe.begin(b"/community")
        self.probe.end()
        self.assertIsNone(self.probe.reply(True))
        self.assertEqual(self.events[-1][0], "no_system_reply")

    def test_disable_preserves_later_native_messages(self):
        self.probe.begin(b"/community off")
        self.assertIn(b"disabled", self.probe.reply(True))
        self.probe.end()
        self.probe.begin(b"/community")
        self.assertIsNone(self.probe.reply(True))
        self.probe.end()
        self.assertEqual(self.events[-1][0], "disabled")

    def test_cockpit_arm_is_opt_in_and_forwards_once_through_native_reply(self):
        from bridge import COMMANDS
        from unittest.mock import Mock
        facade = Mock(commands=COMMANDS + (b"/community arm",))
        facade.handle.return_value = b"Armed."
        interaction = Interaction(lambda *args, **fields: None, facade)
        self.probe.begin(b"/community arm")
        self.assertIsNone(self.probe.reply(True))
        self.probe.end()
        interaction.begin(b"/community arm")
        self.assertIsNone(interaction.reply(False))
        self.assertEqual(interaction.reply(True), b"Armed.")
        self.assertIsNone(interaction.reply(True))
        interaction.end()
        facade.handle.assert_called_once_with(b"/community arm")


if __name__ == "__main__":
    unittest.main()
