# T-04.9 — Connect shared input and automatic presentation to the adapter

**Planned.** [STEPS](../../STEPS.md) owns delivery status. This task implements the scoped adapter behavior for R-044–R-048 using the selected shared activity. Final two-client integration acceptance belongs to [T-04.10](../T-04.10/README.md).

## Outcome

A real player deliberately submits the selected shared contribution through the guarded cockpit observation. Connected participants automatically receive the activity's current server revision, including another member's change, and recover the latest state after reconnect without replaying obsolete effects.

The shared input and feed are proposed additions. Today's `/community arm` submits the existing member-owned `probe`; it does not join or mutate a shared activity. Keep that behavior and member progress explicit while introducing a separate opt-in shared operation.

## Needs

- [T-04.6's selected operation contract](../T-04.6/README.md), [T-04.7's shared wire contract](../T-04.7/README.md) and [T-04.5's guarded native operation](../T-04.5/README.md#receiver-validation-and-selected-automatic-operation).
- A working service implementation for full adapter integration; fixtures allow pure protocol/scheduler work earlier. [T-04.8](../T-04.8/README.md) is required before a remote game connection.
- Actual supported-build access for native behavior. A second game client is needed for T-04.10, not every game-free or one-client check here.

## Work

1. Extend typed parsing and compatibility negotiation for the shared snapshot, event and mutation result. Refuse unsupported versions and cross-community/activity data. Keep member state and shared state in separate types/paths.
2. Define an explicit opt-in shared-activity selection and one-use arm action. Apply the existing lifetime, transition, leave and disable guards to the deliberate cockpit report. Do not send mutations from unarmed/load-time observations or infer physical authority from the callback.
3. Add a bounded background subscription/catch-up mechanism; select polling or streaming against the actual low-frequency contract. Native callbacks must not perform network work. Document polling intervals or connection behavior, queues, result lifetime, rate limits and cancellation.
4. On subscription, obtain a coherent snapshot and continue from its revision. Detect gaps, wrong activity, duplicates and older revisions; repair by query. Coalesce superseded state safely so late join displays current state rather than replaying every historical notification.
5. Present server state through fresh guarded native reads and the validated callback thread. Preserve calibration requirements and menu/reload behavior. No game-object pointers cross into the worker; a disconnected or invalid lifecycle cannot display an old queued success in a later community session.
6. On conflict, query the authoritative revision and show the outcome. Re-arm only after a new deliberate player action if contribution remains allowed. Distinguish exact request replay from a fresh mutation; lost acknowledgement is reconciled before implying that the contribution failed or succeeded.
7. On leave, disable, community/activity change or menu invalidation, cancel local input/feed/presentation and discard stale state. Reconnect obtains the current snapshot under a fresh valid session. Cancellation cannot undo a transaction that committed before the disconnect.
8. Verify parser/worker/scheduler behavior with original fixtures: remote-member change, late snapshot, missed/reordered/duplicate event, stale conflict, cancellation, timeout, session renewal, activity close and service restart. Complete a bounded attended one-client native pass before marking this task complete; label any second actor driven by diagnostics as synthetic. Game-free implementation can advance while native access is unavailable.

## Acceptance

- Synthetic service events reach the adapter's automatic presentation path without requiring a result command per event; native visibility is separately confirmed in actual game observations.
- The selected input changes the shared activity only once per permitted contribution and leaves existing member progress unchanged.
- Conflicts and missed events converge to a current revision; leave/disable/lifecycle change prevents stale native delivery. Queues and network retries remain bounded and off the game thread.
- One-client evidence states exactly which participant was real. Two real clients seeing each other's changes, late join and restart remain required in T-04.10.
- Exact commands, compatibility values, lifecycle limits and selected feed timings are recorded here when implemented; no untested arbitrary-thread or native-session control guarantee is added.

## Entry points

[Typed client](../../../src/Community.AdapterLab/service_client.py) · [Worker](../../../src/Community.AdapterLab/bridge.py) · [Native hooks](../../../src/Community.AdapterLab/probe.py) · [Guarded state](../../../src/Community.AdapterLab/native_state.py) · [Scheduler](../../../src/Community.AdapterLab/world_runtime.py).

[Client boundaries](../../ARCHITECTURE.md#5-client-and-resource-boundaries) · [Runtime experiment](../../EXPERIMENTS.md#e-03--prove-minimal-runtime-access-on-the-target-build) · [T-04.5 setup and recovery](../T-04.5/README.md#setup-build-and-verify).
