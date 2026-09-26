# Delivery status and next work

Updated: 2026-09-26.

[PRODUCT](PRODUCT.md) owns the goal; [ROADMAP](ROADMAP.md) owns the longer-range plan. This file keeps the current capability baseline and the next five tasks. Detailed work lives in the linked task plans; [working references](tasks/README.md) hold reusable procedures and supporting evidence.

## Current status

M-01–M-03 and T-03.1 / T-04.1–T-04.5 are complete within their recorded scopes. **Next: M-04, two real clients interacting with the same community-owned state.** The existing progress value belongs to one member; sharing an endpoint does not make it shared gameplay state.

| Capability available to the next tasks | Supporting reference and boundary |
| --- | --- |
| Standalone community runtime / M-01 | [T-04.1](tasks/T-04.1/README.md): local service, scoped lab credentials and synthetic-client verification |
| One real game connection / M-02 | [Chat loop](tasks/T-04.3/evidence-2026-09-23.md#result-and-limits), extended by [automatic cockpit-report replies](tasks/T-04.5/evidence-automatic-2026-09-24.md#recovery-result-and-limits): one client, exact Windows Steam build, cooperative reports |
| Persistent reconnect and restart / M-03 | [T-04.4](tasks/T-04.4/evidence-2026-09-23.md#result-and-limits): member-owned progress, atomic state/event/replay writes and idle empty-server recovery |

M-04 is planned; M-05–M-08 remain planned in ROADMAP. Parent IDs remain stable: T-01 research foundation complete; T-02 discovery/release questions prepared; T-03 baselines partially complete; T-04 implementation partially complete; T-05 reusable platform/pilot/release not started. A completed child does not complete its parent or every roadmap item it draws on.

Recorded verification for T-04.3–T-04.5 is local. T-04.1/T-04.2 also have recorded hosted CI passes; no later push or hosted result is established by these records.

## Next five tasks

All five are **planned**. Start with T-04.6's shared-action contract and lab inventory. Service and transport work can then advance while the second game installation is being arranged; actual two-client results require both clients.

- [ ] **T-04.6 — Define the shared interaction and establish the two-client lab.**

  R-041–R-042; selected E-01b/E-04 checks. [Detailed tasks](tasks/T-04.6/README.md).
  Specify one community-owned activity driven by armed cockpit reports, distinct from member progress; choose identities, transitions, scope and conflict policy. Inventory two separately licensed installations, disposable saves and the connection topology.

  Done when the contract is implementable and paired native baseline observations establish the selected join/leave/late-join boundary. Record unavailable prerequisites and untested location/entity behavior explicitly.

- [ ] **T-04.7 — Implement shared persistent state and its protocol.**

  Scoped R-042–R-043, R-045–R-046 and R-031–R-039 recovery work. Needs T-04.6's contract; no game required for service implementation. [Detailed tasks](tasks/T-04.7/README.md).
  Add a community-owned activity with stable IDs, revisions, member authorization, atomic events and replay handling, preserving existing member progress. Supply snapshots and a recoverable event feed.

  Done when two synthetic members converge under concurrent actions, duplicate/stale requests, missed events and service restart. This is service proof; native entity spawning and M-04 remain open.

- [ ] **T-04.8 — Connect the second machine securely.**

  Scoped R-089 plus R-021–R-024 compatibility/session work. Needs T-04.6's topology; can proceed beside T-04.7. [Detailed tasks](tasks/T-04.8/README.md).
  Implement and document authenticated encryption and server-identity verification for the selected cross-machine route, with separate lab credentials and failure feedback. Current server and adapter code accept loopback HTTP only.

  Done when both hosts reach the same service through the verified route and reject wrong identity, credentials and insecure fallback. A same-machine alternative needs actual feasibility evidence; it is not assumed available.

- [ ] **T-04.9 — Present and update shared state through both adapters.**

  Scoped R-044–R-049 and E-03/E-04. Needs T-04.7's protocol, T-04.5's guarded callbacks and T-04.8 for cross-machine operation. [Detailed tasks](tasks/T-04.9/README.md).
  Add bounded shared-state subscriptions and armed input; automatically present the other member's committed changes. Repair revision gaps with snapshots and clear stale work on leave, reconnect, menu transitions or disable.

  Done when game-free fault checks and a real-client integration check pass, including passive receipt of another member's service change. Two real game views are verified in T-04.10; text presentation does not establish a spawned world object.

- [ ] **T-04.10 — Prove the shared loop with two real clients.**

  Scoped R-041–R-050 / M-04, E-01b/E-04 and relevant persistence checks. Needs the preceding capabilities and both prepared clients. [Detailed tasks](tasks/T-04.10/README.md).
  Exercise each player's action and the other player's automatic observation, simultaneous input, late join, missed events, disconnect, empty-server restart and both clients' return. Compare native and community ownership and restore both installations.

  Done when paired observations match the authoritative shared revisions and acknowledged state survives the tested recovery cases. Retain one scoped result with failures/limits; mark M-04 only for demonstrated shared behavior.

## Dependencies and limits that affect this queue

- Availability of a second account, supported installation, machine and consenting participant is not recorded. T-04.6 establishes those facts; it does not authorize purchases or outreach.
- Existing cockpit input is a cooperative client report. General engine lifecycle access, extended E-03/R-015–R-020 hardening, native location/reference frames, world-object lifecycle, admission and gameplay enforcement remain open. Compatibility self-report is not attestation; existing two-endpoint selection has synthetic evidence only.
- The proposed first shared activity uses in-game text presentation and historical cockpit reports. It does not claim co-location, native object replication, official rewards, crossplay or independence from native multiplayer. [ARCHITECTURE](ARCHITECTURE.md#2-authority-contract) owns those trust boundaries.
- A remote lab needs the [encrypted transport and server-identity boundary](ARCHITECTURE.md#4-protocol-and-persistence). Opening the current HTTP listener to the LAN is not a supported shortcut.
- Keep concrete license, build and release restrictions attached to the operation they affect. Broader publication/commercialization work remains separate from local service development.

Completed entries leave this queue. Keep only evidence and references needed by current capabilities, unresolved failures or future work; routine completion/check history belongs in Git and CI, under the [retention rules](../AGENTS.md#fact-ownership).
