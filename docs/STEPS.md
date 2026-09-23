# Delivery status and next work

Updated: 2026-09-23.

## Current status

The research foundation, T-03.1 native baseline, T-04.1 / M-01 standalone service, T-04.2's narrow native chat adapter and T-04.3 / M-02 one-player service loop are complete within their recorded scopes. T-04.4 is next: persist the player's community state across reconnect and server restart. Evidence and entry points are linked below.

[PRODUCT](PRODUCT.md) defines the goal; [ROADMAP](ROADMAP.md) defines the longer-range plan. This file owns delivery status and the short queue. Detailed records are in the [task index](tasks/README.md).

T-04.1 and T-04.2 are pushed; hosted CI passed for both commits (runs 35922543716 and 35927119404). T-04.3 changes are local and uncommitted; its expanded suites have not run on GitHub.

## Milestone status

Acceptance definitions live in ROADMAP; this table records status only.

| Milestone | Status |
| --- | --- |
| M-01 — Runnable server lifecycle | Complete; [T-04.1 evidence](tasks/T-04.1/evidence-2026-09-23.md#result-and-limits) |
| M-02 — One real player and in-game server response | Complete within explicit chat-polling scope; [T-04.3 evidence](tasks/T-04.3/evidence-2026-09-23.md#result-and-limits) |
| M-03 — Persistent reconnect and restart | Planned |
| M-04 — Two players sharing state | Planned |
| M-05 — Operator admission and selected gameplay rules | Planned |
| M-06 — Creator/operator alpha | Planned |
| M-07 — Reliable community pilot | Planned |
| M-08 — Public release | Planned |

## Parent work packages

| Stable ID | Scope | Status and relationship |
| --- | --- | --- |
| T-01 | Research-backed project foundation | Completed; evidence below. ROADMAP expansion makes the proposed construction work visible |
| T-02 | Operator discovery and scoped permissions/release work | Prepared questions only; runs alongside engineering. Interviews and monetization approval are not prerequisites for an original local service |
| T-03 | Local game, content, and later multiplayer baselines | T-03.1 / R-011 / E-01a complete; parent incomplete |
| T-04 | Implement server, game integration, persistence, synchronization, and operator control | T-04.1 / M-01, narrow T-04.2 and T-04.3 / M-02 complete; parent incomplete. Persistence, explicit engine lifecycle API and broader adapter hardening remain open |
| T-05 | Reusable creator/operator platform, pilot, and release | Not started; follows the capabilities it actually uses. Detailed future decomposition is in ROADMAP |

These parent IDs supersede the original coarse queue without renumbering its references. Completing a child completes that child only. The remaining core work is visible in ROADMAP and is not hidden in the optional backlog.

## Current detailed tasks

Queue-to-roadmap mapping: T-03.1 covers R-011; T-04.1 covers the bounded R-001–R-010 service outcome; T-04.2 draws on R-012–R-020; T-04.3 draws on R-021–R-030; T-04.4 covers R-031–R-040. T-04.3 supplies the narrow R-019 typed service path and fresh-callback retrieval of delayed replies. R-015's engine lifecycle interface and full R-020/E-03 hardening remain open. Two-endpoint selection has synthetic service evidence, not two actual game-endpoint runs; compatibility is a cooperative self-report. The task does not complete every broader roadmap acceptance item.

- [x] **T-03.1 — Owned installation and repeatable native baseline.**
  R-011 / E-01a. [Plan and procedure](tasks/T-03.1/README.md) · [Evidence](tasks/T-03.1/evidence-2026-09-21.md#result-and-limits).

- [x] **T-04.1 — Start and operate the first standalone community server.**
  R-001–R-010 / M-01 complete within the in-memory synthetic-client scope. [Implementation and commands](tasks/T-04.1/README.md) · [Evidence and limits](tasks/T-04.1/evidence-2026-09-23.md#result-and-limits).

- [x] **T-04.2 — Expose one game interaction through a minimal adapter.**
  Needs: T-03.1, the selected adapter/tool's actual capabilities and license, and an appropriate scope for the chosen game operation. The standalone server can be developed in parallel.
  Build: Observe one interaction and present/apply one reversible response inside the running game. Isolate build detection, lifecycle, and thread handling. Use the required subset of E-02/E-03; diagnose and replace an unsupported hook path if necessary.
  Verify: Trigger the real interaction, observe the callback and in-game response, unload/restart safely, and refuse unsupported signatures. Record the supported operation and its limitations without requiring complete game authority.
  Completed within the synchronous native-chat scope: real callback/response, repetitions, menu/reload, disable, restart-based removal and final recovery verified; 28 game-free tests passed. One earlier injector-startup fault is retained in evidence. Broader R-012–R-020 work is partial, as scoped above. [Operation and procedure](tasks/T-04.2/README.md) · [Sources](tasks/T-04.2/sources.md) · [Evidence and remaining work](tasks/T-04.2/evidence-2026-09-23.md#result-and-limits).

- [x] **T-04.3 — Connect one real player to their own server.**
  Needs: T-04.1 and T-04.2.
  Build: Send the real game interaction through the adapter to the local server, let server configuration determine the result, and display/apply the response in the same game client. Add scoped local session credentials and useful connection errors.
  Verify: E-10 initial loop: five actual in-game round trips, a changed server rule producing a changed result, stopped-service handling, and reconnect. One real player is sufficient to complete M-02. No second player or full economy is required.
  Completed within the explicit chat-polling scope: six visible server replies, changed server rule in the same game process, stopped-service feedback, reconnect, leave/menu/reload, disable and normal recovery. One initial reply expired before manual retrieval. Scoped compatibility, typed loopback traffic and cancellation are implemented; 33 service checks and 63 adapter tests passed. [Operation and commands](tasks/T-04.3/README.md) · [Evidence and limits](tasks/T-04.3/evidence-2026-09-23.md#result-and-limits).

- [ ] **T-04.4 — Preserve that player's community state across restart.**
  Needs: T-04.3 for the full game-connected result; storage/protocol work can begin alongside T-04.2.
  Next action: Define the persisted member/progression/replay records and transactional storage choice, then connect recovery to the proved chat operation. Keep the configured lab principal independent of session and native save identity. Replace the in-memory 256-request cap with a stated replay-retention window longer than any client retry; persisting the cap unchanged would lock a member permanently, and naive eviction would allow duplicate mutations.
  Build: Persist one server-owned progression value using transactional storage and request deduplication. Associate it with a stable community-member ID mapped to the configured lab principal, independently of connection/session and native save IDs. Define empty-server behavior; it may idle. Persisted lab identity is not a public entitlement-verification claim.
  Verify: E-10 persistence extension: complete an action, acknowledge it, close the game, restart the empty server, reconnect, recover the same value, and reject a duplicate mutation. This completes M-03; two-player synchronization is the next capability.
  Completed: Not started.

## Parallel work and real constraints

Server software, protocol fixtures, data models, and tests with original data can advance without game access. Adapter work needs the actual supported game environment. Multiple-client tests need the corresponding accounts/testers only when those tasks are reached.

Keep relevant code/content licenses and any concrete restrictions attached to the operation they affect. Publisher clarification, public entitlement access, interviews, naming, privacy responsibilities, distribution, hosting, and commercialization are distinct workstreams. Resolve required release conditions before the affected release. Do not require a commercial-launch agreement merely to write an original local server or document native game behavior. Outreach still needs a user instruction to contact people.

Before M-04/M-05 server gameplay builds on the chat bridge, run a game-side investigation: a game-thread presentation path without a second command, and one in-world interaction beyond chat. Its result decides whether those milestones remain game-integrated. The chat bridge supports asynchronous server requests and explicit native result retrieval. Automatic pushed presentation, explicit engine lifecycle signals and the relationship to native multiplayer sessions remain unverified. The 20-second result lifetime was exercised by an initially delayed manual retrieval; this remains a lab usability limit.

## Completion evidence

| Date | Item | Evidence and limits |
| --- | --- | --- |
| 2026-09-20 | Initial research foundation | Ten Markdown documents and primary-source findings; original file map and 28 relative links checked; Git whitespace check passed |
| 2026-09-20 | Initial independent review | Ecosystem, networking/authority, and licensing reviews incorporated |
| 2026-09-20 | User correction applied and verified | ROADMAP has 140 unique contiguous tasks across 14 stages; eight milestone states and five immediate queue outcomes; 11 Markdown files, 40 relative links, ten experiment IDs, balanced fences, and Git whitespace checks passed |
| 2026-09-20 | Engineering review | One-player/idle-server criteria reviewed; added explicit operational identity and encrypted remote transport work, corrected token-theft claims, and kept independent-feature testing separate from two-player synchronization |
| 2026-09-20 | Build handoff review | No missing major workstream found; first-build entry point, in-memory M-01 scope, pinned tooling/local tests, loopback/remote transport boundaries, stable member ownership, and exact next-session instructions recorded. Eleven Markdown files, 40 relative links, 140 roadmap IDs, five queue items, balanced fences, and Git whitespace checks passed before checkpointing |
| 2026-09-20 | Implementation limits | No executable platform, game run, performance result, interview, or release; engineering acceptance thresholds remain planned |
| 2026-09-21 | Intent and planning revision | Removed duplicated failure-response and fixed-order instructions; preserved product, trust, and evidence requirements. Independent review found no actionable inconsistencies. Checked 11 Markdown files, 42 relative links, balanced fences, 140 unchanged roadmap task rows across 14 stages, five queue tasks, ten experiment IDs, and Git whitespace. Documentation only; no application tests or new external-source verification |
| 2026-09-21 | T-03.1 / R-011 | Native repeatability and recovery verified; [results, limits, and document checks](tasks/T-03.1/evidence-2026-09-21.md#result-and-limits). Detailed documentation moved under the task |
| 2026-09-23 | T-04.1 / R-001–R-010 / M-01 | Standalone service and diagnostic client verified; [results, checks and limits](tasks/T-04.1/evidence-2026-09-23.md). No hosted CI or game integration run |
| 2026-09-23 | T-04.2 / scoped R-012–R-020 | Native chat adapter proof, repeated responses, menu/reload, disable, process recovery and settings restoration verified; [results, one startup failure, checks and remaining work](tasks/T-04.2/evidence-2026-09-23.md#result-and-limits). No service round trip or full E-03 completion |
| 2026-09-23 | T-04.3 / scoped R-021–R-030 / M-02 | Six visible replies, server rule change, outage/reconnect, lifecycle/recovery and 33 service + 63 adapter checks verified; [results, expired first display and remaining scope](tasks/T-04.3/evidence-2026-09-23.md#result-and-limits). No persistence or automatic pushed presentation |
