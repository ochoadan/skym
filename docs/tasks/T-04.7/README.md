# T-04.7 — Implement one durable shared activity

**Planned.** [STEPS](../../STEPS.md) owns delivery status. This task implements the selected T-04.6 contract in the service. It covers scoped shared-record work from R-042/R-043/R-045/R-046/R-048, with persistence checks from R-031–R-040. Service acceptance does not complete M-04.

## Outcome

Two distinct authenticated members query and change the same community-owned activity, and recover its committed revision after service restart. The shared aggregate is separate from each member's existing progress and interaction ID.

All fields, endpoints and migrations described below are proposed work. Today's protocol and database are member-scoped; no shared activity API is currently claimed.

## Needs

- The selected interaction, revision/conflict rules and lifecycle from [T-04.6](../T-04.6/README.md).
- [T-04.4's storage and recovery contract](../T-04.4/README.md#storage-identity-and-recovery-contract), current protocol fixtures and the existing two-principal lab configuration.
- No second game installation or remote connection is required for implementation and original-data verification. [T-04.8](../T-04.8/README.md) can proceed independently once topology is selected.

## Work

1. Define the versioned shared snapshot, mutation result, conflict response and event envelope. Include stable community/activity identity and revision; derive the acting member from the session. Document bounded payloads, event page size and compatibility rejection before changing server and adapter contracts.
2. Add separate activity/contribution/event/replay storage. Commit each accepted contribution, revised activity, event and replay outcome atomically before acknowledgement. Preserve the existing member records and progress behavior.
3. Bind replay lookup to the authenticated member, community, activity, request ID and payload. Exact replay returns the original result within its declared retention window; changed payload reuse and cross-actor reuse cannot impersonate the original action.
4. Enforce the selected contribution limit and completion rule. Race two members against one revision: one commits and the other receives the documented stale result. A fresh deliberate request after reconciliation can succeed only if the member remains eligible.
5. Provide a current snapshot and bounded catch-up path. Specify cursor scope, event ordering, gap/retention handling and when a fresh snapshot replaces obsolete history. A snapshot plus subsequent changes must converge even if an event is missed during subscription startup.
6. Make activity lifecycle and participant departure explicit. Committed historical contributions persist; disconnected sessions hold no blocking ownership. Close/create activity operations receive deliberate authorization and fresh IDs; they must not masquerade as native object spawn/despawn.
7. Add an explicit schema migration and backup/recovery procedure if existing databases are supported. Verify representative original old-schema fixtures, unchanged member progress, rejected unsupported schemas and interrupted migration behavior. Do not silently reset storage or promise downgrade support.
8. Verify normal commits, duplicate and changed-body replay, stale revision, wrong community/member scope, simultaneous submissions, lost acknowledgement, event gaps, restart and selected storage-failure boundaries. Include a bounded 100-attempt duplicate/concurrency run against one activity and assert the declared committed contributions.

## Acceptance

- Two synthetic principals read the same activity ID/revision while their member-owned progress remains independently owned.
- Contributions cannot exceed the selected per-member/total rule; accepted state/event/replay outcomes agree after restart. A stale or rejected command creates no partial contribution.
- A consumer missing an event repairs from the documented snapshot/cursor path; old activity IDs and unrelated communities cannot contaminate a current view.
- Tests establish service behavior using original fixtures only. No two-game-client result, physical-action authority or game-capacity claim is recorded.
- Exact build/test commands, compatibility changes, migration and recovery instructions are added to this task when implemented. Preserve any known startup/event-history growth limits instead of claiming an unbounded service.

## Entry points

[Transport and persistence design](../../ARCHITECTURE.md#4-protocol-and-persistence) · [Current wire reference](../T-04.1/protocol.md) · [Durable transaction experiment](../../EXPERIMENTS.md#e-05--prove-a-durable-community-transaction).

[Wire types](../../../src/Community.Protocol/Wire.cs) · [Runtime authorization](../../../src/Community.Server/LabRuntime.cs) · [Storage](../../../src/Community.Server/PersistentStore.cs) · [Persistence checks](../../../tests/Community.Tests/PersistenceChecks.cs).
