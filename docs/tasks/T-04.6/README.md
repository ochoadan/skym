# T-04.6 — Define the shared interaction and prepare two real clients

**Planned.** [STEPS](../../STEPS.md) owns delivery status. This task selects the bounded M-04 interaction and prepares its actual game environment. It draws on R-041–R-044 and supplies initial observations for R-049/R-051; it does not complete their broader native-entity requirements.

## Outcome

A written shared-state contract, an identified way for two legitimate game clients to reach one service, and paired native baseline observations for the chosen scene. The contract can be completed before the second game client becomes available, allowing service and transport work to proceed.

**Proposed first interaction:** one community-owned boarding activity receives at most one cooperative cockpit-entry report from each participating member. Both players automatically see its accepted-report count and server-decided pending/completed state. Two accepted members complete the activity. The exact wording and operation are selected here before implementation.

This is a project-owned shared activity presented through the existing in-game chat surface. A report records an accepted submission; it does not certify that a player remains aboard, control takeoff, spawn a native object, synchronize ships, or prove an action to an authoritative server. Existing member-owned progress remains separate.

## Needs

- [T-04.4](../T-04.4/README.md) for durable member identity and [T-04.5](../T-04.5/README.md) for guarded automatic presentation and the armed cockpit report.
- Two consenting participants or otherwise legitimately usable concurrent game installations, with supported builds, disposable saves and a restoration plan for each. Current evidence identifies only one real client.
- A concrete machine/account arrangement and native-session route. Concurrent retail clients on one machine are not an established capability; do not assume that this avoids a second-machine connection.

Missing lab access blocks paired observations and the final proof, not original-data protocol, storage or transport development.

## Work

1. Specify the deliberate input, visible output on both clients, allowed callback/state conditions, failure feedback and cancellation. The second player must receive the other player's change without submitting a matching command or manually fetching every update.
2. Define a server-issued activity ID, community scope, monotonic revision, participant attribution, accepted-report count, completion rule and lifecycle. These are proposed fields, not the implemented protocol. Use an explicitly nonspatial activity scope; native galaxy/system/scene coordinates remain unverified.
3. Select conflict semantics: one command can commit against a given revision; a stale competitor receives a conflict and refreshes. A later deliberate retry may contribute if still eligible. An accepted member cannot contribute twice, and exact replay cannot create another contribution.
4. Define restart/disconnect semantics: committed contributions survive; sessions and local armed actions do not. A disconnect does not retract historical reports. Define closing an activity and opening another with a fresh ID, without resetting old revisions or copying member progress.
5. Inventory the two builds, installations, principals, machines, save receipts and private configuration locations. Record the intended service host and whether transport requires [T-04.8](../T-04.8/README.md). Keep account identifiers, credentials and saves out of Git.
6. With two unmodified clients, run the selected E-01b subset: initial join, late join, leave/rejoin, each participant closing, both returning and any travel required to reach the chosen landed-ship scene. Capture paired views and failure counts. Record which native participant hosts or leaves the scene only where observed.
7. Record differences between the community connection and native group/scene membership. Full E-01b coverage, including unrelated bases, freighters, item transfers and damage, remains outside this subset unless actually exercised.

## Acceptance

- The contract names one genuinely shared record and the result each client should see. Connecting two principals to today's member-scoped `/state` does not satisfy it.
- The topology is actionable: each client has its own principal, supported adapter environment and recovery procedure; cross-machine credentials require the verified encrypted route in T-04.8 first.
- Paired baseline observations identify the selected native-session dependency and any failures. If the second client is unavailable, keep this portion pending and record that dependency in STEPS; do not substitute a synthetic client.
- The selected contract is sufficient to start T-04.7 and T-04.9 without inventing native controls. R-042 location/reference-frame work and native spawn/despawn work remain open.

## Entry points

[Shared-state roadmap](../../ROADMAP.md#stage-5--synchronize-two-players-and-shared-interactions) · [Native baseline experiment](../../EXPERIMENTS.md#e-01--establish-local-and-multiplayer-baselines) · [World identity design](../../ARCHITECTURE.md#6-independent-networking-work-if-the-bridge-permits-it).

[Existing operation and recovery](../T-04.5/README.md#receiver-validation-and-selected-automatic-operation) · [Current member storage](../../../src/Community.Server/PersistentStore.cs) · [Automatic scheduler](../../../src/Community.AdapterLab/world_runtime.py).
