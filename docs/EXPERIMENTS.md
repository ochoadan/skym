# Engineering experiments and verification

These are **proposed procedures for testing capabilities**, not recorded results. [STEPS](STEPS.md) owns status, and [ROADMAP](ROADMAP.md) owns the provisional construction plan. All thresholds below are proposed acceptance targets, not measured performance. Results provide evidence about a specific approach and may affect its implementation, the architecture, or the planned scope.

IDs are stable references. The current queue uses E-01a, the needed parts of E-02/E-03, and the one-player loop E-10. E-05 includes checks that can use original data without a game client. E-01b/E-04 need multiple game clients. Later tests cover enforcement, independent rule behavior, and broader operation; their prerequisites differ by the claim being tested.

## Lab prerequisites and evidence

Begin with one owned Windows game installation, an exact storefront build, and a disposable save. A separate server process may run on that same PC. Record CPU/GPU/RAM, network path, game settings, mods, and executable/tool hashes. Add a second separately licensed account/installation for real multi-client tests; a third consenting tester becomes relevant for interference tests. Keep paid equipment and account requirements separate from technical task dependencies.

Review the intended scope and applicable terms before invasive integration experiments. Publisher clarification is a separate workstream; it does not block reading documentation or preparing a simulation with original data. Do not use public players or live economies as test subjects. Network-condition changes must affect only the lab clients and be restored afterwards.

A completed experiment produces a dated, redacted `evidence-<date>.md` in its `docs/tasks/<T-ID>/` folder with this format:

```text
Experiment ID and run date:
Tester and review owner:
Claim tested:
Storefront / game build / executable hash:
Tool and adapter versions / commit hashes / resource manifest hash:
OS / hardware / network and latency conditions:
Save/profile setup and restoration plan:
Permission/scope assessment reference where applicable:
Exact procedure and sample size:
Expected result:
Observed result and failure counts:
Logs/video/capture locations and redaction notes:
Conclusion: passed / failed / inconclusive:
Scope of the conclusion and remaining unknowns:
Restoration result:
```

Keep raw dumps, credentials, account identifiers, and save files in ignored local storage. An evidence report may link to a controlled artifact location; do not commit those artifacts blindly. Create an evidence report only after a real run.

## E-01 — Establish local and multiplayer baselines

**Question:** What happens without our integration, and which behaviors already work?

**E-01a, one-client baseline — T-03.1 / R-011:** Repeat one native interaction and demonstrate recovery of a disposable checkpoint on an identified installation. [Procedure and acceptance](tasks/T-03.1/README.md#e-01a-procedure-and-acceptance).

**E-01b, later multiplayer baseline:** Add the second game installation when work reaches shared sessions.

Run ten join/leave cycles with two unmodified clients. Include initial join, late join, travel between planets/systems, entering a base, entering a freighter/corvette where available, item transfer, a consensual damage test, one client closing, and both returning. Observe which state persists and whether both clients agree. Record failures instead of removing them from the sample.

Separate matchmaking, group membership, visible scene membership, ownership, and persistence. Observe owned-client connection metadata if useful; a relay address does not reveal simulation authority. Do not infer the full protocol from endpoint names or capture other people's credentials.

**Acceptance:** A reproducible state/authority hypothesis table, observations from both clients, complete build/configuration records, and failure counts for every action. This experiment documents behavior; it need not show flawless native multiplayer to be useful. Every hypothesized authority owner remains labeled until a stronger test establishes it.

## E-02 — Prove reversible mod installation

**Question:** Can a player safely enter and leave a community content profile?

Select one harmless, licensed data modification. Confirm the current installation path/settings from the selected tool and build; do not copy a 2019 guide. Snapshot the relevant files and settings. Install, launch, observe the intended change, uninstall, and compare the restored files. Repeat five cycles. Interrupt one install before activation; repeat with an existing unrelated mod and a deliberately incompatible manifest.

**Acceptance:** The expected visual/data change occurs; platform-owned changes restore exactly; unrelated mods and saves are preserved; incomplete or incompatible installs do not activate. Document any game-managed files that legitimately change and why they are outside the exact-restore comparison. Check relevant cloud-save and native sharing writes; custom progress, discoveries, or construction must not be assumed isolated. No claim of separate save profiles unless tested with cloud-sync behavior too.

## E-03 — Prove minimal runtime access on the target build

**Question:** Can the selected adapter observe and perform the minimum needed game operation reliably?

The narrow first chat-probe procedure and its code entry points are in [T-04.2](tasks/T-04.2/README.md). The broader lifecycle, travel and duration checks below remain separate acceptance work.

Expose game lifecycle, current location/transform, one interaction event, and one reversible presentation/state operation. Demonstrate it across ten process restarts, a menu transition, travel, and clean unload. Test a deliberately unsupported build fingerprint and a missing/ambiguous signature. Record the allowed execution thread and valid object lifetime.

**Acceptance:** Each operation is observed correctly on repeat runs and lifecycle transitions; no use of invalid object references; unsupported conditions disable integration safely. Run a two-hour session and record adapter-related failures and frame-time overhead against E-01a conditions. A successful hook is a completed adapter capability; authority and synchronization are additional tests. E-10 can begin once its required operation works, while longer lifecycle hardening continues.

## E-04 — Map native and custom replication

**Question:** Which modified behaviors are local, natively replicated, divergent, or unsupported?

Compare vanilla/vanilla, identical-mod/identical-mod, and mod/vanilla pairs in consenting isolated sessions. Test a cosmetic change, a gameplay parameter, a base/scene asset, an interaction, a custom object, and a contract state transition. Exclude unproven destructive changes from ordinary saves. Check both viewpoints and repeat after late join, region travel, and the original participant leaving.

**Acceptance:** Every tested behavior has a classified result, specific build/mod hashes, expected observer behavior, observed divergence, and a retained failure case. An identical package hash is not accepted as proof of replication. Do not generalize from cosmetics to physics, NPCs, or inventory.

## E-05 — Prove a durable community transaction

**Question:** Can an operator-owned service maintain one consistent contract reward?

With original test data, accept a contract, complete its permitted state transition, and post community credits with no promised cash value or redemption. Test normal completion, duplicate delivery, stale revision, expired token, another player's contract ID, wrong community, simultaneous completion, and service termination immediately before/after commit. Service tests can use synthetic protocol clients; E-10 adds one real game client, and later shared-state work adds two. Record which clients were actually used.

Run 100 duplicate and concurrent completion attempts for the same contract. Expected result: one completion and exactly one balanced reward transaction. Confirm unauthorized requests cannot mint, transfer, or spend funds. Verify queries repair a missed event notification.

**Acceptance:** Every acknowledged transaction survives an ordinary service restart; no duplicate or unauthorized reward occurs; clients converge to the persisted revision. This establishes the ledger only. If driven by a mock client or a manually approved event, explicitly record that no in-game authority has been verified.

## E-06 — Establish game enforcement and admission

**Question:** Can the server enforce the actual rules needed for the user's RP community?

Connect the E-03 game interaction to E-05. Add a third consenting client that lacks the extension or deliberately reports an invalid action. Test forged completion, impossible interaction distance, replay after reconnect, changed local save, disabled bridge, unauthorized entry, and a revoked account. The server must either verify authoritative gameplay state or demonstrate how the action is controlled; a second cooperative client confirming a report is not an anti-cheat proof.

Evaluate at least one gameplay restriction separate from the ledger, such as access to the project-owned interaction object. Test admission mismatches in game mode, active content, adapter version, and configuration as well as package download hashes. Record what remains possible in native multiplayer. A rule on one custom object does not establish safe zones, PvP enforcement, inventory control, or building permissions.

**Acceptance:** Invalid gameplay cannot earn the claimed enforced reward; unauthorized users cannot enter/interfere with the promised controlled environment; the declared rule holds on all tested clients after reconnect. If only platform API access can be denied, classify admission as platform-only and fail the independent game-admission claim. If native behavior overrides the rule, classify the integration as cooperative/hybrid or inconclusive, not fully enforced.

## E-07 — Establish independent simulation

**Question:** Can relevant game state and rules run without a retail client hosting them?

In a permitted isolated setup, have one real game client connect to the operator-owned session and interact with one project-owned entity. Exercise spawn, state change, despawn, and reconnect. Then exit that client. The service continues a nontrivial declared rule—for example, an object progresses through timed states, consumes a server-owned resource, and changes later interaction eligibility. Restart the service before the player returns. This may be implemented through scheduled work or elapsed-time calculation with the declared semantics.

On return, the client must see the persisted state and the correct eligibility result. Test unauthorized rejoin and confirm native networking cannot create a second conflicting owner. Record every official service still needed and whether its role is identity, discovery, transport, persistence, or simulation. A second client supplies additional convergence/late-join evidence under E-04/M-04, but is not required for this independent-feature test.

**Acceptance:** The tested rule's authoritative state survives the client-free interval according to its declared timing policy; the returning game client presents the resulting entity correctly; operator admission/enforcement holds within the tested boundary; no native duplicate owner or overwritten state occurs. A timer/database demonstration without functioning in-game integration does not suffice. Scheduled database work is a valid implementation for suitable rules. One entity class passing establishes that feature; other game systems need separate work.

This checks independently advancing gameplay for the tested feature. A persistent server with idle or paused state has a different acceptance scope. An E-07 result establishes evidence about the tested ownership and timing model; it does not by itself establish or disprove every other server capability.

## E-08 — Verify operation by another creator and operator

**Question:** Is this a reusable community platform rather than a bespoke demonstration?

After the selected technical boundary is established, an independent creator follows the resource documentation to add a second contract or rule. An operator on a fresh environment installs the runtime, configures roles/resources, joins two clients, applies a sanction, backs up, restores, updates, and uninstalls without an author editing their environment.

Include a resource crash, unavailable directory, revoked package, and failed migration. Confirm the sample exposes game integration, rather than merely changing text in the launcher. Verify controller and readable UI behavior for the supported desktop mode; VR is a separate target.

**Acceptance:** The operator completes the documented lifecycle; creator changes load within their declared capability boundary; failures yield useful diagnostics and recovery; role escalation fails; restore results match the recorded recovery scope. Record assistance time and every undocumented step.

## E-09 — Measure load and update survival

**Question:** Is the integration maintainable and usable at a declared pilot size?

After correctness, grow from 2 to 4, 8, 16, and 32 real clients where the game allows, stopping at the first unsupported level. Test dense scenes separately from clients spread across systems. Synthetic service load is useful but must be reported separately from actual game-client capacity.

At each supported level run two-hour normal-condition sessions and controlled 100 ms added round-trip latency/1% packet-loss sessions. Record p50/p95 action acknowledgment, snapshot convergence, desynchronization, bandwidth, CPU/RAM, game frame time, crash count, and operator recovery time. A proposed RP target is p95 acknowledgment under 500 ms on the defined normal test network and state convergence within five seconds of reconnect; tune targets from user experience before turning them into commitments.

Repeat the narrow proof after a future update or on another legitimately available build. Measure failure detection, diagnosis and repair time, install restoration, and compatibility reporting. If no second build is available, mark update survival untested.

**Acceptance:** Publish only the observed client count and conditions, retain failing cases, and do not claim a successful mock-server load test raises NMS's game limits. A public supported-build claim requires a working game run, not just source changes or a compiler release.

## E-10 — Connect one real player to their own server

The persistence extension, read-only chat query and attended restart/replay procedure are in [T-04.4](tasks/T-04.4/README.md#attended-e-10-persistence-procedure).

**Question:** Can the operator start a server and make it control one visible response inside their running NMS game?

The selected explicit chat-polling implementation, detailed procedure and observed initial-loop results are in [T-04.3](tasks/T-04.3/README.md).

Start the standalone service on the player's PC with a small operator-configured rule. Use one owned game installation and the minimal E-03 interaction adapter. Trigger the game action, send it to the service, have the service select the result, and display/apply that result inside the game. Change the rule on the service and repeat so the outcome demonstrates the server's decision.

Use request IDs in the game and server logs to correlate the round trip. Complete five interactions, disconnect/reconnect the service, reject a malformed request, and confirm a stopped service produces an understandable failure instead of a fabricated success. A server-decided in-game interaction message is sufficient for this first loop; controlling native combat or world physics is later work. A separate web page or synthetic client alone verifies the service, not this game connection.

**M-02 acceptance:** One real game client completes the action-to-server-to-game loop, changes in server configuration affect the observed result, and disconnects behave as documented. This is a legitimate one-player server milestone even with cooperative trust, one supported build, a local server process, and unfinished multiplayer features.

**M-03 extension:** Add one server-owned progression value. Acknowledge a change, close the game, leave the service empty, restart it, and reconnect the same player. Recover the recorded value and continue the interaction. Specify whether any timers pause or catch up; the empty server may idle. Acceptance: acknowledged state survives ordinary service restart and the player sees it on return. Two players, a secure economy, and continuous simulation of the universe are not prerequisites for this persistence outcome.

## What each result establishes

| Evidence | Permissible conclusion |
| --- | --- |
| Standalone service and synthetic client | Runnable server software and its tested protocol behavior |
| E-01a/E-02 | Local baseline and reversible content distribution understood |
| E-10 initial loop | M-02: one real player interacts with their server inside the game |
| E-10 persistence extension | M-03: game-connected persistent state survives reconnect and restart |
| E-03/E-04 | Specific current-build runtime and replication capabilities demonstrated |
| E-05 only | Persistent platform records demonstrated |
| E-06 plus E-05 | The tested game rule and transaction are enforceable within the measured boundary |
| E-07 plus admission/enforcement | Narrow independent game-simulation proof, not whole-game compatibility |
| E-08/E-09 and resolved release conditions | Basis for a limited public pilot with explicit supported scope |

Technical success does not establish commercial permission, operator demand, entitlement access, or release readiness. Those questions have separate evidence. The report format above records both the observed result and its limits; an experiment alone does not determine the appropriate project-level response.
