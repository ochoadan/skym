"""Real Python/C# loopback checks; synthetic native callbacks, never game attachment.

Build the Release server first. Only missing .NET 10/runtime artifacts cause skips;
protocol, startup, timeout and assertion failures fail the test. Private temporary
configuration and child logs are retained under ignored local/t04-4/tests.
"""

import http.client
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid

REPOSITORY = Path(__file__).resolve().parents[2]
SERVER_DLL = REPOSITORY / "src/Community.Server/bin/Release/net10.0/Community.Server.dll"
sys.path.insert(0, str(REPOSITORY / "src/Community.AdapterLab"))
from bridge import Bridge
from interaction import Interaction
from service_client import ClientConfig, ServiceClient, ServiceError


class ServerProcess:
    def __init__(self, directory, community, message):
        self.directory = directory
        directory.mkdir()
        with socket.socket() as available:
            available.bind(("127.0.0.1", 0))
            port = available.getsockname()[1]
        self.config = {
            "bindAddress": "127.0.0.1", "port": port, "communityId": community,
            "dataDirectory": "data", "completionMessage": message,
            "sessionLifetimeSeconds": 900, "adminKey": secrets.token_hex(32),
            "principals": [{"id": "alice", "key": secrets.token_hex(32)}],
        }
        self.process = None
        self.log = None
        self.runs = 0
        self.log_paths = []

    def client_config(self):
        path = self.directory / "adapter.json"
        path.write_text(json.dumps({
            "host": self.config["bindAddress"], "port": self.config["port"],
            "communityId": self.config["communityId"], "principalId": "alice",
            "key": self.config["principals"][0]["key"],
        }), encoding="utf-8")
        return ClientConfig.load(path)

    def request(self, method, path, token=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.config["port"], timeout=1)
        try:
            headers = {} if token is None else {"Authorization": "Bearer " + token}
            connection.request(method, path, headers=headers)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def start(self):
        if self.process is not None:
            raise AssertionError("Previous test server process was not stopped")
        path = self.directory / "server.json"
        path.write_text(json.dumps(self.config, indent=2), encoding="utf-8")
        self.runs += 1
        log_path = self.directory / f"server-{self.runs}.log"
        self.log_paths.append(log_path)
        self.log = log_path.open("wb")
        self.process = subprocess.Popen(
            [shutil.which("dotnet"), str(SERVER_DLL), "--config", str(path)],
            cwd=REPOSITORY, stdout=self.log, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise AssertionError(f"Server exited {self.process.returncode}; evidence: {log_path}")
            try:
                status, raw = self.request("GET", "/health")
                if status == 200 and json.loads(raw) == {
                    "protocolVersion": 2, "communityId": self.config["communityId"], "status": "ready"
                }:
                    return
            except (OSError, http.client.HTTPException):
                pass
            threading.Event().wait(0.025)
        raise AssertionError(f"Server was not ready within 10 seconds; evidence: {log_path}")

    def stop(self):
        if self.process is None:
            return
        status, raw = self.request("POST", "/admin/stop", self.config["adminKey"])
        if status != 200 or json.loads(raw) != {"status": "stopping"}:
            raise AssertionError("Authenticated test server shutdown failed")
        code = self.process.wait(timeout=10)
        self.process = None
        self.log.close()
        self.log = None
        if code != 0:
            raise AssertionError(f"Test server exited {code} after graceful shutdown")

    def cleanup(self):
        try:
            self.stop()
        finally:
            if self.process is not None:
                if self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait(timeout=5)
                self.process = None
            if self.log is not None:
                self.log.close()
                self.log = None


class BridgeProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dotnet = shutil.which("dotnet")
        if dotnet is None:
            raise unittest.SkipTest("Python/C# integration needs dotnet and the built Release server")
        if not SERVER_DLL.is_file():
            raise unittest.SkipTest("Build first: dotnet build CommunityPlatform.slnx --configuration Release")
        runtimes = subprocess.run([dotnet, "--list-runtimes"], capture_output=True, text=True,
                                  timeout=10, check=True).stdout.splitlines()
        if not any(line.startswith("Microsoft.AspNetCore.App 10.") for line in runtimes):
            raise unittest.SkipTest("Python/C# integration needs the ASP.NET Core 10 runtime")

    def setUp(self):
        evidence_root = REPOSITORY / "local/t04-4/tests"
        evidence_root.mkdir(parents=True, exist_ok=True)
        self.directory = Path(tempfile.mkdtemp(prefix=self._testMethodName + "-", dir=evidence_root))
        self.servers = []
        self.clients = []
        self.bridges = []
        self.events = []
        self.tokens = []

    def tearDown(self):
        try:
            for bridge in self.bridges:
                bridge.handle(b"/community off")
                bridge._thread.join(5)
                self.assertFalse(bridge._thread.is_alive(), "Real client bridge worker leaked")
            for client in self.clients:
                client.close()
        finally:
            try:
                for server in self.servers:
                    server.cleanup()
            finally:
                (self.directory / "adapter-events.json").write_text(
                    json.dumps(self.events, indent=2), encoding="utf-8")

    def server(self, community, message):
        server = ServerProcess(self.directory / community, community, message)
        self.servers.append(server)
        server.start()
        return server

    def client(self, server):
        client = ServiceClient(server.client_config())
        self.clients.append(client)
        return client

    @staticmethod
    def command(interaction, command):
        interaction.begin(command)
        try:
            return interaction.reply(True)
        finally:
            interaction.end()

    def action(self, interaction, command=b"/community"):
        expected = b"reading saved progress" if command == b"/community state" else b"connecting/sending"
        self.assertIn(expected, self.command(interaction, command))
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            value = self.command(interaction, b"/community result")
            if b"connecting or waiting" not in value and b"busy" not in value:
                return value
            threading.Event().wait(0.01)
        self.fail(f"Real service bridge did not finish; evidence: {self.directory}")

    def test_five_actions_changed_configuration_restart_unavailable_and_reconnect(self):
        server = self.server("bridge-process", "Original operator rule.")
        client = self.client(server)
        emit = lambda name, **fields: self.events.append({"event": name, **fields})
        bridge = Bridge(client.config, emit, client=client)
        self.bridges.append(bridge)
        interaction = Interaction(emit, bridge)
        for revision in range(1, 6):
            self.assertEqual(self.action(interaction),
                             f"[bridge-process #{revision} progress {revision}] Original operator rule.".encode())
            self.assertIn(b"No community result", self.command(interaction, b"/community result"))
        self.tokens.append(client.token)
        # Progress belongs to the stable member, independently of session/native save.
        state = client.state()
        self.assertEqual((state["revision"], state["progress"], state["status"]), (5, 5, "available"))
        server.stop()
        unavailable = self.action(interaction)
        self.assertIn(b"unavailable or timed out", unavailable)
        self.assertNotIn(b"Original operator rule", unavailable)
        server.config["completionMessage"] = "Changed operator rule after restart."
        server.start()
        # Recover read-only before taking another action; config changes affect new commands only.
        self.assertEqual(self.action(interaction, b"/community state"),
                         b"[bridge-process #5 progress 5] Original operator rule.")
        self.assertEqual(client.state(), state)
        # The invalid old session was replaced; no failed mutation was retried.
        self.assertEqual(self.action(interaction),
                         b"[bridge-process #6 progress 6] Changed operator rule after restart.")
        self.assertNotEqual(client.token, self.tokens[0])
        self.tokens.append(client.token)
        self.assertIn(b"disconnected", self.command(interaction, b"/community leave"))
        deadline = time.monotonic() + 5
        while client.token is not None:
            self.assertLess(time.monotonic(), deadline)
            threading.Event().wait(0.01)
        self.assertEqual(self.action(interaction, b"/community state"),
                         b"[bridge-process #6 progress 6] Changed operator rule after restart.")
        self.assertEqual(self.action(interaction),
                         b"[bridge-process #7 progress 7] Changed operator rule after restart.")
        queued = [event["request_id"] for event in self.events if event["event"] == "server_request_queued"]
        answered = [event["request_id"] for event in self.events if event["event"] == "server_response"]
        presented = [event["request_id"] for event in self.events if event["event"] == "server_presentation"]
        self.assertEqual(len(queued), 10)
        self.assertEqual(len(set(queued)), 10)
        self.assertEqual(len(answered), 9)
        self.assertEqual(presented, queued)
        self.assertTrue(set(answered).issubset(queued))
        responses = [event for event in self.events if event["event"] == "server_response"]
        self.assertEqual({event["member_id"] for event in responses}, {state["memberId"]})
        self.assertEqual({event["interaction_id"] for event in responses}, {state["interactionId"]})
        self.assertEqual([event["progress"] for event in responses], [1, 2, 3, 4, 5, 5, 6, 6, 7])
        bridge.handle(b"/community off")
        bridge._thread.join(5)
        self.assertFalse(bridge._thread.is_alive())
        server.stop()
        all_logs = repr(self.events) + "".join(path.read_text(encoding="utf-8") for path in server.log_paths)
        for secret in [server.config["adminKey"], client.config.key, *self.tokens]:
            self.assertNotIn(secret, all_logs)

    def test_new_client_recovers_committed_state_and_identical_replay_after_empty_server_restart(self):
        server = self.server("persisted-client", "Persisted operator response.")
        client = self.client(server)
        before = client.state()
        request_id = str(uuid.uuid4())
        committed = client.probe(request_id)
        replay = {"protocolVersion": 2, "communityId": client.config.community, "requestId": request_id,
                  "expectedRevision": before["revision"], "commandType": "probe",
                  "payload": {"interactionId": before["interactionId"]}}
        original = client._http("POST", "/commands", replay)
        self.assertEqual(original["state"], committed)
        client.close()
        server.stop()
        server.start()
        returning = self.client(server)
        self.assertEqual(returning.state(), committed)
        self.assertEqual(returning._http("POST", "/commands", replay), original)
        self.assertEqual(returning.state(), committed)
        continued = returning.probe(str(uuid.uuid4()))
        self.assertEqual((continued["revision"], continued["progress"]), (2, 2))
        self.assertEqual(continued["memberId"], before["memberId"])
        self.assertEqual(continued["interactionId"], before["interactionId"])

    def test_two_endpoints_preserve_community_identity_messages_and_independent_state(self):
        first = self.server("community-first", "First operator's response.")
        second = self.server("community-second", "Second operator's response.")
        self.assertNotEqual(first.config["port"], second.config["port"])
        first_client, second_client = self.client(first), self.client(second)
        first_state = first_client.probe(str(uuid.uuid4()))
        second_state = second_client.probe(str(uuid.uuid4()))
        self.assertEqual((first_state["message"], first_state["revision"], first_state["progress"]),
                         ("First operator's response.", 1, 1))
        self.assertEqual((second_state["message"], second_state["revision"], second_state["progress"]),
                         ("Second operator's response.", 1, 1))
        self.assertNotEqual(first_state["memberId"], second_state["memberId"])
        continued = first_client.probe(str(uuid.uuid4()))
        self.assertEqual((continued["message"], continued["revision"], continued["progress"]),
                         ("First operator's response.", 2, 2))
        self.assertEqual(second_client.state(), second_state)
        selected = second_client.config
        wrong_community = ServiceClient(ClientConfig(selected.port, "community-first", selected.principal,
                                                     selected.key))
        self.clients.append(wrong_community)
        with self.assertRaisesRegex(ServiceError, "^wrong_community$"):
            wrong_community.probe(str(uuid.uuid4()))
        self.assertIsNone(wrong_community.token)
        self.assertEqual(second_client.state(), second_state)


if __name__ == "__main__":
    unittest.main()
