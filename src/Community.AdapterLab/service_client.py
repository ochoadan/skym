"""Strict loopback client for the native-chat lab; no game imports or pointers."""

import argparse
from dataclasses import dataclass
from datetime import datetime
import http.client
import json
from pathlib import Path
import re
import socket
import threading
import time
import uuid

from preflight import COMPATIBILITY


ADAPTER = dict(COMPATIBILITY)
PROTOCOL_VERSION = 2
MAX_REVISION = 9007199254740991
LIMIT = 4096
TIMEOUT = 3.0


class ServiceError(Exception):
    """Only fixed diagnostic codes cross the game/log boundary."""


def strict_json(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate")
            value[key] = item
        return value

    def depth(value, level=0):
        if level > 8:
            raise ValueError("depth")
        if isinstance(value, dict):
            for item in value.values():
                depth(item, level + 1)
        elif isinstance(value, list):
            for item in value:
                depth(item, level + 1)

    if len(raw) > LIMIT:
        raise ValueError("size")
    value = json.loads(raw, object_pairs_hook=unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constant")))
    depth(value)
    return value


def fields(value, names):
    if type(value) is not dict or set(value) != set(names.split()):
        raise ValueError("fields")


def identifier(value):
    return type(value) is str and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", value) is not None


def guid(value):
    if type(value) is not str or str(uuid.UUID(value)) != value or uuid.UUID(value).int == 0:
        raise ValueError("uuid")


@dataclass(frozen=True)
class ClientConfig:
    port: int
    community: str
    principal: str
    key: str

    @classmethod
    def load(cls, path):
        with Path(path).open("rb") as source:
            value = strict_json(source.read(LIMIT + 1))
        fields(value, "host port communityId principalId key")
        if (value["host"] != "127.0.0.1" or type(value["port"]) is not int or
                not 1024 <= value["port"] <= 65535 or
                not identifier(value["communityId"]) or not identifier(value["principalId"]) or
                type(value["key"]) is not str or not 32 <= len(value["key"]) <= 128 or
                any(not "!" <= c <= "~" for c in value["key"])):
            raise ValueError("Invalid loopback client configuration")
        return cls(value["port"], value["communityId"], value["principalId"], value["key"])


class ServiceClient:
    """Owned exclusively by one background worker. No automatic mutation retry."""

    def __init__(self, config):
        self.config = config
        self.token = None

    def _http(self, method, path, body=None, authenticated=True):
        connection = http.client.HTTPConnection("127.0.0.1", self.config.port, timeout=TIMEOUT)
        response = None
        timer = None
        started = time.monotonic()
        try:
            connection.connect()  # Numeric loopback: no DNS, proxy or redirect handling.
            transport = connection.sock

            def expire():
                try:
                    transport.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

            remaining = TIMEOUT - (time.monotonic() - started)
            if remaining <= 0:
                raise TimeoutError()
            timer = threading.Timer(remaining, expire)
            timer.daemon = True
            timer.start()
            headers = {"Content-Type": "application/json"}
            if authenticated:
                if self.token is None:
                    raise ServiceError("invalid_session")
                headers["Authorization"] = "Bearer " + self.token
            raw = None if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
            connection.request(method, path, body=raw, headers=headers)
            response = connection.getresponse()
            data = response.read(LIMIT + 1)
            if time.monotonic() - started >= TIMEOUT:
                raise TimeoutError()
            if response.status == 204 and method == "DELETE" and not data:
                return None
            if response.getheader("Content-Type", "").split(";", 1)[0] != "application/json":
                raise ValueError("content type")
            value = strict_json(data)
            if response.status != 200:
                fields(value, "protocolVersion requestId error")
                expected_id = body.get("requestId") if body else None
                if (type(value["protocolVersion"]) is not int or value["protocolVersion"] != PROTOCOL_VERSION or
                        value["requestId"] not in (None, expected_id)):
                    raise ValueError("error envelope")
                known = {"invalid_credentials", "invalid_session", "expired_session", "wrong_community",
                         "unsupported_protocol", "unsupported_adapter", "unsupported_game", "unsupported_operation",
                         "session_scope", "adapter_required", "stale_revision", "unknown_interaction",
                         "counter_exhausted", "storage_unavailable", "session_capacity",
                         "request_id_conflict", "rate_limited"}
                code = value["error"]
                raise ServiceError(code if type(code) is str and code in known else "server_rejected")
            return value
        except ServiceError:
            raise
        except (TimeoutError, ConnectionError, OSError, http.client.HTTPException):
            raise ServiceError("unavailable") from None
        except (ValueError, TypeError, KeyError, RecursionError):
            raise ServiceError("invalid_response") from None
        finally:
            if timer:
                timer.cancel()
            if response:
                response.close()
            connection.close()

    def _envelope(self, value):
        if (type(value["protocolVersion"]) is not int or value["protocolVersion"] != PROTOCOL_VERSION or
                value["communityId"] != self.config.community):
            raise ValueError("envelope")

    @staticmethod
    def _state(value):
        fields(value, "memberId interactionId revision progress status message")
        guid(value["memberId"])
        guid(value["interactionId"])
        if (type(value["revision"]) is not int or not 0 <= value["revision"] <= MAX_REVISION or
                type(value["progress"]) is not int or not 0 <= value["progress"] <= value["revision"] or
                value["status"] not in ("available", "accepted", "completed") or
                type(value["message"]) is not str or len(value["message"]) > 512):
            raise ValueError("state")

    def connect(self):
        request_id = str(uuid.uuid4())
        value = self._http("POST", "/sessions", {
            "protocolVersion": PROTOCOL_VERSION, "communityId": self.config.community, "requestId": request_id,
            "principalId": self.config.principal, "key": self.config.key, "adapter": ADAPTER}, False)
        fields(value, "protocolVersion requestId communityId sessionId accessToken expiresAt")
        self._envelope(value)
        guid(value["sessionId"])
        if (value["requestId"] != request_id or type(value["accessToken"]) is not str or
                re.fullmatch(r"[A-F0-9]{64}", value["accessToken"]) is None or
                type(value["expiresAt"]) is not str or
                datetime.fromisoformat(value["expiresAt"]).utcoffset() is None):
            raise ValueError("session")
        self.token = value["accessToken"]

    def state(self, cancelled=lambda: False):
        """Read persisted member state, renewing only an invalid/expired session."""
        try:
            if cancelled():
                raise ServiceError("cancelled")
            if self.token is None:
                self.connect()
            if cancelled():
                raise ServiceError("cancelled")
            try:
                snapshot = self._http("GET", "/state")
            except ServiceError as error:
                if str(error) not in ("invalid_session", "expired_session"):
                    raise
                self.token = None
                if cancelled():
                    raise ServiceError("cancelled")
                self.connect()
                if cancelled():
                    raise ServiceError("cancelled")
                snapshot = self._http("GET", "/state")
            fields(snapshot, "protocolVersion communityId state")
            self._envelope(snapshot)
            self._state(snapshot["state"])
            if cancelled():
                raise ServiceError("cancelled")
            return snapshot["state"]
        except (ValueError, TypeError, KeyError, RecursionError):
            raise ServiceError("invalid_response") from None

    def probe(self, request_id, cancelled=lambda: False):
        try:
            state = self.state(cancelled)
            if cancelled():
                raise ServiceError("cancelled")
            value = self._http("POST", "/commands", {
                "protocolVersion": PROTOCOL_VERSION, "communityId": self.config.community, "requestId": request_id,
                "expectedRevision": state["revision"], "commandType": "probe",
                "payload": {"interactionId": state["interactionId"]}})
            fields(value, "protocolVersion requestId communityId state event")
            self._envelope(value)
            self._state(value["state"])
            event = value["event"]
            fields(event, "eventId requestId eventType state")
            guid(event["eventId"])
            self._state(event["state"])
            if (value["requestId"] != request_id or event["requestId"] != request_id or
                    event["eventType"] != "interaction.probed" or event["state"] != value["state"] or
                    value["state"]["memberId"] != state["memberId"] or
                    value["state"]["interactionId"] != state["interactionId"] or
                    value["state"]["revision"] != state["revision"] + 1 or
                    # The server decides how much progress an action earns; the client only
                    # refuses a reply that would move saved progress backwards.
                    value["state"]["progress"] < state["progress"] or
                    value["state"]["status"] != state["status"]):
                raise ValueError("command")
            return value["state"]
        except (ValueError, TypeError, KeyError, RecursionError):
            raise ServiceError("invalid_response") from None

    def close(self):
        if self.token:
            try:
                self._http("DELETE", "/session")
            except ServiceError:
                pass  # Unreachable sessions expire server-side; never block a callback.
            finally:
                self.token = None


def main():
    parser = argparse.ArgumentParser(description="Provision a principal-only adapter config; never copy the admin key.")
    parser.add_argument("--server-config", type=Path, required=True)
    parser.add_argument("--principal", default="alice")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    destination = args.out.resolve()
    local = Path(__file__).resolve().parents[2] / "local"
    if not any(destination.is_relative_to(local / task) and destination != local / task
               for task in ("t04-3", "t04-4")):
        raise ValueError("Output must be a new file under local/t04-3 or local/t04-4")
    source = json.loads(args.server_config.read_text(encoding="utf-8-sig"))
    principal = next(p for p in source["principals"] if p["id"] == args.principal)
    value = {"host": source["bindAddress"], "port": source["port"], "communityId": source["communityId"],
             "principalId": principal["id"], "key": principal["key"]}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as output:
        json.dump(value, output, indent=2)
    print("Created private principal-only adapter configuration.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, StopIteration, TypeError):
        raise SystemExit("Provisioning refused; check paths/principal/configuration. Existing output is never overwritten.")
