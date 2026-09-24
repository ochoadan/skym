# Local service protocol version 2

Implemented contract for the loopback lab, including T-04.3's scoped adapter admission and `probe` command. [Wire.cs](../../../src/Community.Protocol/Wire.cs) defines field types; [task runbook](README.md) covers service commands/configuration. All examples/fixtures are original project data. T-04.4 adds durable member progress; version 2 deliberately refuses older strict clients. See [persistence and recovery](../T-04.4/README.md). The adapter's HTTP work and response storage run outside native callbacks; game presentation requires a subsequent supported callback and separate game evidence. This protocol provides no unsolicited native presentation operation.

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
| `GET /events?after=N` | Session bearer token; at most 32 events after revision N; `revision` is the last returned cursor (N if empty); reject negative or future cursors |
| `POST /commands` | Session bearer token; return `{protocolVersion, requestId, communityId, state, event}` |
| `POST /admin/stop` | Separate operator bearer key; `{status:"stopping"}`, then graceful host shutdown |

Bearer format is `Authorization: Bearer <accessToken>`; no cookies, query credentials or proxy-forwarded identities are supported. Every session belongs to the configured community and a server-configured principal. The private diagnostic client obtains keys from the lab configuration. Session creation is not idempotent; retrying it creates another bounded session. Maximum active sessions: 64; expired entries are reclaimed on new admission. All are invalid on process restart.

Session creation body:

```json
{
  "protocolVersion": 2,
  "communityId": "local-lab",
  "requestId": "11111111-1111-4111-8111-111111111111",
  "principalId": "alice",
  "key": "<private generated lab key>"
}
```

Omitting `adapter`, or setting it to null, creates a diagnostic session with the existing `accept`, `complete`, and `reset` command scope. To request an adapter session, add this object to the session body:

```json
"adapter": {
  "adapterVersion": "0.3.0",
  "gameSha256": "B7913F268DFC62386B6B68F524BFC8ADE4A44A9F4FBAD39085B7BF51BE3680CB",
  "storefront": "steam",
  "operation": "native-chat-poll-v2"
}
```

All four strings must match exactly, including case, the single supported pairing in [adapter-compatibility.json](../../../config/adapter-compatibility.json). The service embeds that file at build time and the Python adapter reads it at startup. Credential/envelope checks still apply. A different adapter version returns `unsupported_adapter`; a different executable hash or storefront returns `unsupported_game`; a different operation returns `unsupported_operation` (all HTTP 409). Missing or incorrectly typed object fields fail strict JSON parsing; null field values fail compatibility checks. The declared values are a **self-report of compatibility**, not evidence of a genuine game client, current loaded content, an in-game action, or entitlement. The exact executable selection is documented in the [adapter lab runbook](../T-04.2/README.md#setup-build-and-verify).

An admitted adapter session can read its principal's state/events, close its own session, and send `probe`. Sending any of the three diagnostic commands returns HTTP 403 `session_scope`. A diagnostic session sending `probe` receives HTTP 403 `adapter_required`. Scope is checked before replay lookup, so changing session scope cannot retrieve a cached response for a forbidden command. Both session types retain the existing lifetime/revocation/bounds; state and request deduplication belong to the principal rather than a particular session. The same lab principal key can request either scope; this separation limits accidental commands from an adapter bearer token and does not resist a caller holding the principal key.

Command body (use the interaction ID returned by `/state`):

```json
{
  "protocolVersion": 2,
  "communityId": "local-lab",
  "requestId": "22222222-2222-4222-8222-222222222222",
  "expectedRevision": 0,
  "commandType": "accept",
  "payload": { "interactionId": "33333333-3333-4333-8333-333333333333" }
}
```

No actor, reward amount, game identity or arbitrary script/event name is accepted. Requests use nonempty UUIDs. The actor is taken from the bearer session. Identity ownership does not change when the session changes.

## State, replay and notifications

One persisted interaction per community member: `{interactionId, revision, status, message, memberId, progress}`. Server-generated member and interaction UUIDs survive reconnect, restart and diagnostic reset. The configured lab principal maps to the member independently of session, credential rotation or native save. Progress starts at 0 and counts successful `probe` commands only. Revision starts at 0 and counts every successful mutation. Both are integers bounded by `9007199254740991`; diagnostic reset never decreases either value.

Diagnostic transitions are `available --accept--> accepted --complete--> completed --reset--> available`. `complete` includes the server-configured message; `accept`/`reset` use an empty message. Adapter `probe` preserves status, adds one progress and one revision, and sets the configured message. The progress amount is a server rule: the adapter verifies only that revision advances by one and progress does not decrease. It does not accept or complete a salvage contract. The client cannot supply progress or a reward.

Events are `{eventId, requestId, eventType, state}` with `interaction.changed` for diagnostics or `interaction.probed` for probes. State, event and replay response commit in one SQLite transaction before acknowledgement. Read `/state` for current state; read `/events?after=N` for up to 32 subsequent events and continue using the returned `revision` cursor until an empty page. Every read is member-scoped. Durable event history repairs missed delivery; there is no push dispatcher. Sessions alone are discarded on restart.

Successful requests are retained for 24 hours of server commit time under `(memberId, requestId)` in the community-bound database. Exact semantic replay returns the original response/event even after restart. Changed command/revision/payload under a retained ID returns `request_id_conflict`; authentication, envelope and scope checks precede replay. Invalid requests are not cached. Expired replay records are pruned during startup and successful writes; an exact old body still fails `stale_revision` after pruning because interaction IDs and revisions never reset. Reusing an expired ID with an updated revision/body is outside the guarantee and may execute as a new command. New actions must have new UUIDs. The adapter does not retry mutations automatically; it can query saved progress after an uncertain result.

The old 256-request cap is removed. Empty-server state idles. Restore of an older backup is an explicit rollback to that checkpoint, not recovery of later acknowledgements. Storage schema, maintenance and limits are in [T-04.4](../T-04.4/README.md#storage-identity-and-recovery-contract).

## Errors and diagnostics

Application errors have `{protocolVersion:2, requestId:<UUID or null>, error:<code>}`. The ID is available after successful envelope parsing; malformed input and body/transport rejection can have null. Revision conflicts leave state unchanged; retrieve `/state` before deciding whether to issue a new request. Within 24 hours an uncertain response can be retried with its original ID/body; otherwise query state/history before choosing a new action.

| HTTP status | Codes |
| --- | --- |
| 400 | `invalid_json`, `unsupported_protocol`, `invalid_request_id`, `invalid_command`, `invalid_cursor`, `invalid_host`, `invalid_http_body` |
| 401 | `invalid_credentials`, `invalid_session`, `expired_session` |
| 403 | `wrong_community`, `browser_not_allowed`, `session_scope`, `adapter_required` |
| 404 | `unknown_interaction` |
| 408 | `body_timeout` |
| 409 | `stale_revision`, `invalid_transition`, `request_id_conflict`, `unsupported_adapter`, `unsupported_game`, `unsupported_operation`, `counter_exhausted` |
| 413 | `body_too_large` or `invalid_http_body` |
| 415 | `json_required` |
| 429 | `rate_limited`, `session_capacity` |
| 503 | `storage_unavailable` |

Unknown routes and methods use framework 404/405 responses, which need not have the application envelope. Logs contain startup/shutdown, session lifecycle and request/rejection records with trace/request IDs, statuses and stable error codes. They omit credential values, bodies, query strings and untrusted request paths. stdout is the log sink; redirect only into ignored local storage when retaining it.
