"""Original protocol fixtures and a loopback HTTP peer; no game dependencies."""

from copy import deepcopy
from dataclasses import dataclass, field
import http.server
import http.client
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "Community.AdapterLab"))
import service_client
from service_client import ClientConfig, ServiceClient, ServiceError, strict_json


REQUEST = "11111111-1111-4111-8111-111111111111"
INTERACTION = "22222222-2222-4222-8222-222222222222"
SESSION = "33333333-3333-4333-8333-333333333333"
EVENT = "44444444-4444-4444-8444-444444444444"
TOKEN = "A" * 64
KEY = "original-test-key-" * 3
COMMUNITY = "test-community"
MESSAGE = "Response selected by the test server."


def state(revision=0, message=""):
    return {"interactionId": INTERACTION, "revision": revision,
            "status": "available", "message": message}


def fixture(path, body):
    if path == "/sessions":
        return {"protocolVersion": 1, "requestId": body["requestId"],
                "communityId": COMMUNITY, "sessionId": SESSION, "accessToken": TOKEN,
                "expiresAt": "2030-01-01T00:00:00+00:00"}
    if path == "/state":
        return {"protocolVersion": 1, "communityId": COMMUNITY, "state": state()}
    if path == "/commands":
        result = state(1, MESSAGE)
        return {"protocolVersion": 1, "requestId": body["requestId"],
                "communityId": COMMUNITY, "state": result,
                "event": {"eventId": EVENT, "requestId": body["requestId"],
                          "eventType": "interaction.probed", "state": deepcopy(result)}}
    raise AssertionError(f"Unexpected test request: {path}")


def set_value(value, path, replacement):
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = replacement


@dataclass
class Reply:
    value: object = None
    status: int = 200
    raw: bytes | None = None
    headers: dict = field(default_factory=dict)
    drip_interval: float = 0
    header_wait: threading.Event | None = None


class Peer:
    """HTTP peer with observable requests and controllable response faults."""

    def __init__(self, respond=None):
        self.requests = []
        self.respond = respond or (lambda method, path, body: Reply(fixture(path, body)))
        peer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def handle_request(self):
                raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                body = json.loads(raw) if raw else None
                peer.requests.append((self.command, self.path, body, dict(self.headers)))
                reply = peer.respond(self.command, self.path, body)
                data = reply.raw if reply.raw is not None else json.dumps(reply.value).encode("utf-8")
                try:
                    if reply.header_wait:
                        reply.header_wait.wait(2)
                    self.send_response(reply.status)
                    headers = {"Content-Type": "application/json", "Content-Length": str(len(data))}
                    headers.update(reply.headers)
                    for name, value in headers.items():
                        self.send_header(name, value)
                    self.end_headers()
                    if reply.drip_interval:
                        for byte in data:
                            self.wfile.write(bytes([byte]))
                            self.wfile.flush()
                            time.sleep(reply.drip_interval)
                    else:
                        self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass  # Expected when the bounded client abandons a slow response.

            do_POST = do_GET = do_DELETE = handle_request

            def log_message(self, *_):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": 0.01}, daemon=True)
        self.port = self.server.server_address[1]

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def client(self):
        return ServiceClient(ClientConfig(self.port, COMMUNITY, "alice", KEY))


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "client.json"
        self.value = {"host": "127.0.0.1", "port": 18181, "communityId": COMMUNITY,
                      "principalId": "alice", "key": KEY}

    def load(self, value):
        self.path.write_text(json.dumps(value), encoding="utf-8")
        return ClientConfig.load(self.path)

    def test_exact_loopback_principal_configuration(self):
        self.assertEqual(self.load(self.value), ClientConfig(18181, COMMUNITY, "alice", KEY))

    def test_rejects_unscoped_or_malformed_configuration(self):
        cases = [("host", "localhost"), ("host", "127.0.0.2"), ("host", "0.0.0.0"),
                 ("host", "https://127.0.0.1"), ("host", "::1"), ("port", True),
                 ("port", 1023), ("port", 65536), ("port", "18181"),
                 ("communityId", "Other"), ("communityId", "a" * 49),
                 ("principalId", ""), ("principalId", "alice\n"),
                 ("key", "x" * 31), ("key", "x" * 129), ("key", " " * 64),
                 ("key", "x" * 32 + "\r\n"), ("key", 123),
                 ("adminKey", "must-not-be-in-client-config")]
        for name, value in cases:
            with self.subTest(field=name, value=value), self.assertRaises(ValueError):
                self.load({**self.value, name: value})
        for name in self.value:
            with self.subTest(missing=name), self.assertRaises(ValueError):
                self.load({key: value for key, value in self.value.items() if key != name})

    def test_configuration_read_is_bounded_and_rejects_duplicate_fields(self):
        for raw in (b" " * (service_client.LIMIT + 1),
                    b'{"host":"127.0.0.1","host":"127.0.0.1"}'):
            self.path.write_bytes(raw)
            with self.assertRaises(ValueError):
                ClientConfig.load(self.path)

    def test_provisioning_copies_only_selected_principal_and_preserves_existing_output(self):
        source = self.root / "server.json"
        source.write_text(json.dumps({"bindAddress": "127.0.0.1", "port": 18181,
                                      "communityId": COMMUNITY, "adminKey": "operator-only-key",
                                      "principals": [{"id": "alice", "key": KEY},
                                                     {"id": "bob", "key": "other-key"}]}),
                          encoding="utf-8")
        output = self.root / "local" / "t04-3" / "client.json"
        # Reproduce the repository directory layout under the isolated test directory.
        module_path = self.root / "src" / "Community.AdapterLab" / "service_client.py"
        arguments = ["service_client.py", "--server-config", str(source), "--out", str(output)]
        with patch.object(service_client, "__file__", str(module_path)), \
                patch.object(sys, "argv", arguments), patch("sys.stdout", new_callable=io.StringIO):
            service_client.main()
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), self.value)
            original = output.read_bytes()
            with self.assertRaises(FileExistsError):
                service_client.main()
            self.assertEqual(output.read_bytes(), original)
        outside = self.root / "outside.json"
        arguments[-1] = str(outside)
        with patch.object(service_client, "__file__", str(module_path)), \
                patch.object(sys, "argv", arguments), self.assertRaises(ValueError):
            service_client.main()
        self.assertFalse(outside.exists())


class StrictJsonTests(unittest.TestCase):
    def test_rejects_duplicate_fields_constants_depth_and_oversize(self):
        nested = 0
        for _ in range(9):
            nested = [nested]
        cases = [b'{"a":1,"a":2}', b'{"a":{"b":1,"b":2}}', b'NaN',
                 b'Infinity', b'-Infinity', json.dumps(nested).encode(),
                 b" " * (service_client.LIMIT + 1)]
        for raw in cases:
            with self.subTest(raw=raw[:80]), self.assertRaises(ValueError):
                strict_json(raw)


class ServiceClientTests(unittest.TestCase):
    def assert_error(self, code, callback):
        with self.assertRaises(ServiceError) as result:
            callback()
        self.assertEqual(str(result.exception), code)

    def test_real_http_round_trip_binds_scope_and_correlation(self):
        with Peer() as peer:
            self.assertEqual(peer.client().probe(REQUEST), (MESSAGE, 1))
        self.assertEqual([(method, path) for method, path, _, _ in peer.requests],
                         [("POST", "/sessions"), ("GET", "/state"), ("POST", "/commands")])
        session = peer.requests[0]
        self.assertNotIn("Authorization", session[3])
        self.assertEqual(session[2]["adapter"], service_client.ADAPTER)
        self.assertEqual(session[2]["principalId"], "alice")
        self.assertEqual(session[2]["communityId"], COMMUNITY)
        self.assertEqual(peer.requests[-1][2], {
            "protocolVersion": 1, "communityId": COMMUNITY, "requestId": REQUEST,
            "expectedRevision": 0, "commandType": "probe", "payload": {"interactionId": INTERACTION}})
        for _, _, _, headers in peer.requests[1:]:
            self.assertEqual(headers["Authorization"], "Bearer " + TOKEN)
        self.assertNotIn("reward", peer.requests[-1][2])

    def assert_invalid_at(self, target, transform):
        def respond(method, path, body):
            value = fixture(path, body)
            if path == target:
                transform(value)
            return Reply(value)

        with Peer(respond) as peer:
            self.assert_error("invalid_response", lambda: peer.client().probe(REQUEST))
        self.assertEqual(peer.requests[-1][1], target)

    def test_session_schema_and_correlation_mismatches_stop_before_mutation(self):
        cases = [(("protocolVersion",), True), (("protocolVersion",), 2),
                 (("requestId",), INTERACTION), (("communityId",), "other-community"),
                 (("sessionId",), "00000000-0000-0000-0000-000000000000"),
                 (("sessionId",), "not-a-uuid"), (("accessToken",), "a" * 64),
                 (("sessionId",), True), (("sessionId",), None), (("sessionId",), {}),
                 (("accessToken",), "A" * 63), (("accessToken",), 123),
                 (("expiresAt",), "2030-01-01T00:00:00"), (("expiresAt",), "invalid"),
                 (("unexpected",), 1)]
        for path, value in cases:
            with self.subTest(field=path, value=value):
                self.assert_invalid_at("/sessions", lambda reply: set_value(reply, path, value))
        self.assert_invalid_at("/sessions", lambda reply: reply.pop("sessionId"))

    def test_state_schema_rejection_prevents_command(self):
        cases = [(("protocolVersion",), True), (("communityId",), "other-community"),
                 (("state", "interactionId"), "00000000-0000-0000-0000-000000000000"),
                 (("state", "interactionId"), True), (("state", "interactionId"), []),
                 (("state", "revision"), True), (("state", "revision"), -1),
                 (("state", "revision"), 257), (("state", "revision"), 0.0),
                 (("state", "status"), "unknown"), (("state", "message"), {}),
                 (("state", "message"), "x" * 513), (("state", "unexpected"), 1),
                 (("state",), []), (("unexpected",), 1)]
        for path, value in cases:
            with self.subTest(field=path, value=value):
                self.assert_invalid_at("/state", lambda reply: set_value(reply, path, value))
        self.assert_invalid_at("/state", lambda reply: reply["state"].pop("message"))

    def test_reply_and_event_must_match_exact_request_and_next_state(self):
        cases = [(("protocolVersion",), True), (("communityId",), "other-community"),
                 (("requestId",), INTERACTION), (("event", "requestId"), INTERACTION),
                 (("event", "eventType"), "interaction.changed"),
                 (("event", "eventId"), "00000000-0000-0000-0000-000000000000"),
                 (("event", "eventId"), True), (("event", "eventId"), None),
                 (("event", "state", "message"), "different"),
                 (("event", "state", "revision"), True),
                 (("event", "state", "revision"), 1.0),
                 (("state", "revision"), True), (("state", "unexpected"), 1),
                 (("event", "unexpected"), 1), (("unexpected",), 1)]
        for path, value in cases:
            with self.subTest(field=path, value=value):
                self.assert_invalid_at("/commands", lambda reply: set_value(reply, path, value))
        for name, value in (("revision", 0), ("revision", 2), ("status", "completed"),
                            ("interactionId", REQUEST)):
            def change_both(reply):
                reply["state"][name] = value
                reply["event"]["state"][name] = value
            with self.subTest(matching_but_wrong_state=name, value=value):
                self.assert_invalid_at("/commands", change_both)
        self.assert_invalid_at("/commands", lambda reply: reply["event"].pop("state"))

    def test_wire_rejections_are_bounded_and_do_not_expose_server_strings(self):
        cases = [(Reply(raw=b"{}" * service_client.LIMIT), "invalid_response"),
                 (Reply(raw=b'{"a":1,"a":2}'), "invalid_response"),
                 (Reply(raw=b"NaN"), "invalid_response"),
                 (Reply(raw=b"\xff"), "invalid_response"),
                 (Reply({}, headers={"Content-Type": "text/html"}), "invalid_response"),
                 (Reply({"protocolVersion": 1, "requestId": None,
                         "error": "untrusted secret from peer"}, status=500), "server_rejected"),
                 (Reply({"protocolVersion": 1, "requestId": None,
                         "error": "invalid_credentials"}, status=401), "invalid_credentials"),
                 (Reply({"protocolVersion": True, "requestId": None,
                         "error": "invalid_credentials"}, status=401), "invalid_response"),
                 (Reply({"protocolVersion": 1, "requestId": INTERACTION,
                         "error": "invalid_credentials"}, status=401), "invalid_response")]
        for reply, expected in cases:
            with self.subTest(expected=expected, status=reply.status), \
                    Peer(lambda *_: reply) as peer:
                self.assert_error(expected, lambda: peer.client().probe(REQUEST))
                self.assertEqual(len(peer.requests), 1)

    def test_oversized_response_closes_its_partially_read_stream(self):
        responses = []

        class ObservedResponse(http.client.HTTPResponse):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                responses.append(self)

        with Peer(lambda *_: Reply(raw=b" " * (service_client.LIMIT * 2))) as peer, \
                patch.object(http.client.HTTPConnection, "response_class", ObservedResponse):
            self.assert_error("invalid_response", lambda: peer.client().probe(REQUEST))
            self.assertEqual(len(responses), 1)
            try:
                self.assertTrue(responses[0].isclosed())
            finally:
                responses[0].close()

    def test_http_redirect_is_never_followed(self):
        with Peer() as target:
            redirect = Reply({"protocolVersion": 1, "requestId": None, "error": "redirect"},
                             status=307, headers={"Location": f"http://127.0.0.1:{target.port}/sessions"})
            with Peer(lambda *_: redirect) as peer:
                self.assert_error("server_rejected", lambda: peer.client().probe(REQUEST))
                self.assertEqual(len(peer.requests), 1)
            self.assertEqual(target.requests, [])

    def test_proxy_environment_cannot_redirect_credentials(self):
        with Peer() as proxy, Peer() as peer:
            endpoint = f"http://127.0.0.1:{proxy.port}"
            environment = {"http_proxy": endpoint, "HTTP_PROXY": endpoint,
                           "https_proxy": endpoint, "HTTPS_PROXY": endpoint,
                           "all_proxy": endpoint, "ALL_PROXY": endpoint,
                           "no_proxy": "", "NO_PROXY": ""}
            with patch.dict(os.environ, environment):
                self.assertEqual(peer.client().probe(REQUEST), (MESSAGE, 1))
            self.assertEqual(proxy.requests, [])

    def test_slow_drip_has_absolute_deadline_even_when_each_byte_arrives_in_time(self):
        reply = Reply(raw=b" " * 100, drip_interval=0.025)
        with Peer(lambda *_: reply) as peer, patch.object(service_client, "TIMEOUT", 0.2):
            started = time.monotonic()
            self.assert_error("unavailable", lambda: peer.client().probe(REQUEST))
            self.assertLess(time.monotonic() - started, 1.2)
            self.assertEqual(len(peer.requests), 1)

    def test_header_stall_also_obeys_deadline(self):
        release = threading.Event()
        with Peer(lambda *_: Reply({}, header_wait=release)) as peer, \
                patch.object(service_client, "TIMEOUT", 0.2):
            try:
                started = time.monotonic()
                self.assert_error("unavailable", lambda: peer.client().probe(REQUEST))
                self.assertLess(time.monotonic() - started, 1.2)
            finally:
                release.set()

    def test_initial_cancellation_makes_no_http_request(self):
        with Peer() as peer:
            self.assert_error("cancelled", lambda: peer.client().probe(REQUEST, lambda: True))
            self.assertEqual(peer.requests, [])

    def test_cancellation_during_snapshot_prevents_mutation(self):
        cancelled = threading.Event()

        def respond(method, path, body):
            if path == "/state":
                cancelled.set()
            return Reply(fixture(path, body))

        with Peer(respond) as peer:
            self.assert_error("cancelled", lambda: peer.client().probe(REQUEST, cancelled.is_set))
        self.assertEqual([request[1] for request in peer.requests], ["/sessions", "/state"])

    def test_expired_session_is_renewed_before_one_command(self):
        snapshots = 0

        def respond(method, path, body):
            nonlocal snapshots
            if path == "/state":
                snapshots += 1
                if snapshots == 1:
                    return Reply({"protocolVersion": 1, "requestId": None,
                                  "error": "expired_session"}, status=401)
            return Reply(fixture(path, body))

        with Peer(respond) as peer:
            self.assertEqual(peer.client().probe(REQUEST), (MESSAGE, 1))
        self.assertEqual([request[1] for request in peer.requests],
                         ["/sessions", "/state", "/sessions", "/state", "/commands"])

    def test_cancellation_after_expiry_prevents_reauthentication(self):
        cancelled = threading.Event()

        def respond(method, path, body):
            if path == "/state":
                cancelled.set()
                return Reply({"protocolVersion": 1, "requestId": None,
                              "error": "expired_session"}, status=401)
            return Reply(fixture(path, body))

        with Peer(respond) as peer:
            self.assert_error("cancelled", lambda: peer.client().probe(REQUEST, cancelled.is_set))
        self.assertEqual([request[1] for request in peer.requests], ["/sessions", "/state"])

    def test_command_error_is_not_automatically_retried(self):
        def respond(method, path, body):
            if path == "/commands":
                return Reply({"protocolVersion": 1, "requestId": body["requestId"],
                              "error": "invalid_session"}, status=401)
            return Reply(fixture(path, body))

        with Peer(respond) as peer:
            self.assert_error("invalid_session", lambda: peer.client().probe(REQUEST))
        self.assertEqual([request[1] for request in peer.requests], ["/sessions", "/state", "/commands"])

    def test_close_revokes_session_and_clears_local_token(self):
        with Peer(lambda *_: Reply(status=204, raw=b"")) as peer:
            client = peer.client()
            client.token = TOKEN
            client.close()
            client.close()
            self.assertIsNone(client.token)
        self.assertEqual([(method, path) for method, path, _, _ in peer.requests], [("DELETE", "/session")])

    def test_failed_close_still_clears_local_token(self):
        with Peer(lambda *_: Reply(raw=b"unavailable", status=503)) as peer:
            client = peer.client()
            client.token = TOKEN
            client.close()
            self.assertIsNone(client.token)


if __name__ == "__main__":
    unittest.main()
