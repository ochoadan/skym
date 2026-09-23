# T-04.1 protocol version 1

Implemented contract for the loopback lab, including T-04.3's scoped adapter admission and `probe` command. [Wire.cs](../../../src/Community.Protocol/Wire.cs) defines field types; [task runbook](README.md) covers service commands/configuration. All examples/fixtures are original project data. Version 1 remains provisional. The adapter's HTTP work and response storage run outside native callbacks; game presentation requires a subsequent supported callback and separate game evidence. This protocol provides no unsolicited native presentation operation.

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

Omitting `adapter`, or setting it to null, creates a diagnostic session with the existing `accept`, `complete`, and `reset` command scope. To request an adapter session, add this object to the session body:

```json
"adapter": {
  "adapterVersion": "0.2.0",
  "gameSha256": "B7913F268DFC62386B6B68F524BFC8ADE4A44A9F4FBAD39085B7BF51BE3680CB",
  "storefront": "steam",
  "operation": "native-chat-poll-v1"
}
```

All four strings must match exactly, including case, the single supported pairing in [adapter-compatibility.json](../../../config/adapter-compatibility.json). The service embeds that file at build time and the Python adapter reads it at startup. Credential/envelope checks still apply. A different adapter version returns `unsupported_adapter`; a different executable hash or storefront returns `unsupported_game`; a different operation returns `unsupported_operation` (all HTTP 409). Missing or incorrectly typed object fields fail strict JSON parsing; null field values fail compatibility checks. The declared values are a **self-report of compatibility**, not evidence of a genuine game client, current loaded content, an in-game action, or entitlement. The exact executable selection is documented in the [adapter lab runbook](../T-04.2/README.md#setup-build-and-verify).

An admitted adapter session can read its principal's state/events, close its own session, and send `probe`. Sending any of the three diagnostic commands returns HTTP 403 `session_scope`. A diagnostic session sending `probe` receives HTTP 403 `adapter_required`. Scope is checked before replay lookup, so changing session scope cannot retrieve a cached response for a forbidden command. Both session types retain the existing lifetime/revocation/bounds; state and request deduplication belong to the principal rather than a particular session. The same lab principal key can request either scope; this separation limits accidental commands from an adapter bearer token and does not resist a caller holding the principal key.

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

One interaction per configured principal: `{interactionId, revision, status, message}`. The server assigns its UUID and revision 0. Diagnostic transitions are `available --accept--> accepted --complete--> completed --reset--> available`. Every successful command increments revision once. Diagnostic `complete` includes the server-configured completion message; `accept` and `reset` use an empty message. The UUID remains stable within a process, including reset.

An adapter sends the same command body with `commandType:"probe"`; payload remains exactly `{interactionId}`. `probe` is legal at any current status, preserves that status and interaction ID, and sets `message` to the server's configured `completionMessage`. It advances revision once and emits `interaction.probed`. It does not accept or complete a salvage contract. No arbitrary text or client-selected message is accepted. The response is held for the adapter's bounded polling presentation path; receiving it over HTTP does not establish display inside NMS.

The event is `{eventId, requestId, eventType, state}` with `eventType:"interaction.changed"` for diagnostic transitions or `"interaction.probed"` for probes. It represents a committed **in-memory** change, not a durable transaction. The command reply and polling endpoint expose the same event ID and revision. Poll using the last observed revision; use `/state` to reconcile. Each principal sees only its own events. A reconnect should query state before choosing a cursor because a restart replaces the interaction and clears history.

Successful commands are retained by `(principal, requestId)` for the process lifetime, bounded to 256 per principal across both session types. An exact semantic replay returns the original response/event without another change, including from another valid session of that principal with the required command scope. Reuse with changed community/version is rejected by envelope validation; reuse with changed command/revision/payload is `request_id_conflict` when scope permits the command. Invalid requests are not cached and may be retried after correction. Deduplication does not survive restart. Reject new commands at capacity; do not evict remembered successes.

## Errors and diagnostics

Application errors have `{protocolVersion:1, requestId:<UUID or null>, error:<code>}`. The ID is available after successful envelope parsing; malformed input and body/transport rejection can have null. Revision conflicts leave state unchanged; retrieve `/state` before deciding whether to issue a new request. An uncertain successful response should be retried with its original ID/body.

| HTTP status | Codes |
| --- | --- |
| 400 | `invalid_json`, `unsupported_protocol`, `invalid_request_id`, `invalid_command`, `invalid_cursor`, `invalid_host`, `invalid_http_body` |
| 401 | `invalid_credentials`, `invalid_session`, `expired_session` |
| 403 | `wrong_community`, `browser_not_allowed`, `session_scope`, `adapter_required` |
| 404 | `unknown_interaction` |
| 408 | `body_timeout` |
| 409 | `stale_revision`, `invalid_transition`, `request_id_conflict`, `unsupported_adapter`, `unsupported_game`, `unsupported_operation` |
| 413 | `body_too_large` or `invalid_http_body` |
| 415 | `json_required` |
| 429 | `rate_limited`, `session_capacity`, `interaction_capacity` |

Unknown routes and methods use framework 404/405 responses, which need not have the application envelope. Logs contain startup/shutdown, session lifecycle and request/rejection records with trace/request IDs, statuses and stable error codes. They omit credential values, bodies, query strings and untrusted request paths. stdout is the log sink; redirect only into ignored local storage when retaining it.
