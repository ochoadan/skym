# T-04.1 protocol version 1

Implemented contract for the loopback lab. [Wire.cs](../../../src/Community.Protocol/Wire.cs) defines field types; [task runbook](README.md) covers commands/configuration. All examples/fixtures are original project data. There is no game-adapter operation in this protocol yet.

## Transport and bounds

HTTP/1.1 at `http://127.0.0.1:<configured-port>`. Require that exact Host and reject any `Origin` or `Sec-Fetch-Site` header. Sessions/commands require `Content-Type: application/json` with no charset or UTF-8. JSON is case-sensitive, depth limited to 8, and rejects duplicate, unknown, missing required or incorrectly typed fields. Semantic validation also rejects nulls where a value is needed.

Body limit: 4,096 bytes; absolute body-read deadline: 3 seconds; header deadline: 5 seconds; headers: 8,192 bytes; request line: 1,024 bytes; idle keepalive: 10 seconds; concurrent connections: 32. A global fixed window permits 100 requests/second without a queue. This bounds lab resource use; it is not a measured load/capacity result. Kestrel may terminate malformed HTTP at its transport layer without a JSON error.

## Endpoints

| Method / path | Authentication and result |
| --- | --- |
| `GET /health` | Public local readiness: `{protocolVersion, communityId, status:"ready"}` |
| `POST /sessions` | Body credential; returns `{protocolVersion, requestId, communityId, sessionId, accessToken, expiresAt}` |
| `DELETE /session` | Session bearer token; revoke this session, return 204 |
| `GET /state` | Session bearer token; return `{protocolVersion, communityId, state}` for its principal |
| `GET /events?after=N` | Session bearer token; events after revision N, plus current revision; reject negative or future cursors |
| `POST /commands` | Session bearer token; return `{protocolVersion, requestId, communityId, state, event}` |
| `POST /admin/stop` | Separate operator bearer key; `{status:"stopping"}`, then graceful host shutdown |

Bearer format is `Authorization: Bearer <accessToken>`; no cookies, query credentials or proxy-forwarded identities are supported. Every session belongs to the configured community and a server-configured principal. The private diagnostic client obtains keys from the lab configuration. Session creation is not idempotent; retrying it creates another bounded session. Maximum active sessions: 64; expired entries are reclaimed on new admission. All are invalid on process restart.

Session creation body:

```json
{
  "protocolVersion": 1,
  "communityId": "local-lab",
  "requestId": "11111111-1111-4111-8111-111111111111",
  "principalId": "alice",
  "key": "<private generated lab key>"
}
```

Command body (use the interaction ID returned by `/state`):

```json
{
  "protocolVersion": 1,
  "communityId": "local-lab",
  "requestId": "22222222-2222-4222-8222-222222222222",
  "expectedRevision": 0,
  "commandType": "accept",
  "payload": { "interactionId": "33333333-3333-4333-8333-333333333333" }
}
```

No actor, reward amount, game identity or arbitrary script/event name is accepted. Requests use nonempty UUIDs. The actor is taken from the bearer session. Identity ownership does not change when the session changes.

## State, replay and notifications

One interaction per configured principal: `{interactionId, revision, status, message}`. The server assigns its UUID and revision 0. Legal transitions are `available --accept--> accepted --complete--> completed --reset--> available`. Every transition increments revision once. Only `completed` includes the server-configured completion message; other states use an empty message. The UUID remains stable within a process, including reset.

The event is `{eventId, requestId, eventType:"interaction.changed", state}`. It represents a committed **in-memory** change, not a durable transaction. The command reply and polling endpoint expose the same event ID and revision. Poll using the last observed revision; use `/state` to reconcile. Each principal sees only its own events. A reconnect should query state before choosing a cursor because a restart replaces the interaction and clears history.

Successful commands are retained by `(principal, requestId)` for the process lifetime, bounded to 256 per principal. An exact semantic replay returns the original response/event without another transition, including from another valid session of that principal. Reuse with changed community/version is rejected by envelope validation; reuse with changed command/revision/payload is `request_id_conflict`. Invalid requests are not cached and may be retried after correction. Deduplication does not survive restart. Reject new transitions at capacity; do not evict remembered successes.

## Errors and diagnostics

Application errors have `{protocolVersion:1, requestId:<UUID or null>, error:<code>}`. The ID is available after successful envelope parsing; malformed input and body/transport rejection can have null. Revision conflicts leave state unchanged; retrieve `/state` before deciding whether to issue a new request. An uncertain successful response should be retried with its original ID/body.

| HTTP status | Codes |
| --- | --- |
| 400 | `invalid_json`, `unsupported_protocol`, `invalid_request_id`, `invalid_command`, `invalid_cursor`, `invalid_host`, `invalid_http_body` |
| 401 | `invalid_credentials`, `invalid_session`, `expired_session` |
| 403 | `wrong_community`, `browser_not_allowed` |
| 404 | `unknown_interaction` |
| 408 | `body_timeout` |
| 409 | `stale_revision`, `invalid_transition`, `request_id_conflict` |
| 413 | `body_too_large` or `invalid_http_body` |
| 415 | `json_required` |
| 429 | `rate_limited`, `session_capacity`, `interaction_capacity` |

Unknown routes and methods use framework 404/405 responses, which need not have the application envelope. Logs contain startup/shutdown, session lifecycle and request/rejection records with trace/request IDs, statuses and stable error codes. They omit credential values, bodies, query strings and untrusted request paths. stdout is the log sink; redirect only into ignored local storage when retaining it.
