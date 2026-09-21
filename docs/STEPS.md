# Delivery status and next work

Updated: 2026-09-21.

## Current status

The local research project exists. [PRODUCT](PRODUCT.md) records the selected experience and the context behind the user's request for a visible construction path and a useful one-player outcome.

[ROADMAP](ROADMAP.md) contains the provisional engineering breakdown and its uncertainty by workstream. This file owns actual progress and the next five detailed tasks. The original T-01 through T-05 were broad work packages, not five implementation steps; they remain stable parent records below. Experiments supply proposed checks for those tasks.

No launcher, adapter, runtime, or game integration has been implemented or run. No interviews, publisher outreach, deployment, purchase, or public release have occurred. Implementation has not started. The proposed build entry point is T-04.1, with T-03.1 in parallel when the owned game installation is available. The 2026-09-21 revision concerns planning documents only.

The handoff is stored in this local Git repository; Git history owns checkpoint hashes and commit state. No remote repository is configured, so there is no verified remote backup. Game installation path/build and the actual development SDK versions have not been recorded; neither is needed to preserve this documentation checkpoint. Select and verify the service toolchain at R-001, and record the game environment at R-011.

## Milestone status

Acceptance definitions live in ROADMAP; this table records status only.

| Milestone | Status |
| --- | --- |
| M-01 — Runnable server lifecycle | Planned |
| M-02 — One real player and in-game server response | Planned |
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
| T-03 | Local game, content, and later multiplayer baselines | Not started; T-03.1 supplies the first single-player baseline, later children add content and multiple clients |
| T-04 | Implement server, game integration, persistence, synchronization, and operator control | Not started; split into children and ROADMAP work. Adapter route and achievable control remain unverified |
| T-05 | Reusable creator/operator platform, pilot, and release | Not started; follows the capabilities it actually uses. Detailed future decomposition is in ROADMAP |

These parent IDs supersede the original coarse queue without renumbering its references. Completing a child completes that child only. The remaining core work is visible in ROADMAP and is not hidden in the optional backlog.

## Next five executable tasks

Queue-to-roadmap mapping: T-03.1 covers R-011; T-04.1 covers the bounded R-001–R-010 service outcome; T-04.2 draws on R-012–R-020; T-04.3 covers R-021–R-030; T-04.4 covers R-031–R-040. These are the current proposed increments. The service has a concrete local verification path; the game-dependent tasks still need a supported operation and adapter route. Their build details may change with those findings.

- [ ] **T-03.1 — Establish one owned game installation and a repeatable local baseline.**
  Needs: Access to one owned Windows NMS installation and a disposable save. A second player is not required.
  Build: Record storefront/build/hash, local files and settings, startup/save behavior, a reversible restoration plan, and the game interaction to use first. Run E-01a; inspect current mod/adapter integration requirements.
  Verify: Launch, load, perform the intended action, exit, and return; retain the baseline and restoration observations. If installation access is unavailable, document it while T-04.1 proceeds independently.
  Completed: Not started.

- [ ] **T-04.1 — Start and operate the first standalone community server.**
  Needs: Local development tools and an explicit choice of service language for this bounded increment. In-memory state is sufficient for M-01; durable storage selection can wait for R-031. No game installation, multiplayer tester, paid hosting, or operator interview is needed.
  Build: A separate local service process with configuration, start/stop, health, protocol version, request IDs, one configurable interaction response, and a synthetic protocol client. Choose loopback binding initially; keep original test data separate from game files.
  Verify: Start on a configured local port, send a request, receive the configured result, change configuration, reject malformed input, and shut down cleanly. Run the reproducible service/contract tests and record exact install/run/test commands in AGENTS. This completes service behavior, not yet the game connection.
  Completed: Not started.

- [ ] **T-04.2 — Expose one game interaction through a minimal adapter.**
  Needs: T-03.1, the selected adapter/tool's actual capabilities and license, and an appropriate scope for the chosen game operation. The standalone server can be developed in parallel.
  Build: Observe one interaction and present/apply one reversible response inside the running game. Isolate build detection, lifecycle, and thread handling. Use the required subset of E-02/E-03; diagnose and replace an unsupported hook path if necessary.
  Verify: Trigger the real interaction, observe the callback and in-game response, unload/restart safely, and refuse unsupported signatures. Record the supported operation and its limitations without requiring complete game authority.
  Completed: Not started.

- [ ] **T-04.3 — Connect one real player to their own server.**
  Needs: T-04.1 and T-04.2.
  Build: Send the real game interaction through the adapter to the local server, let server configuration determine the result, and display/apply the response in the same game client. Add scoped local session credentials and useful connection errors.
  Verify: E-10 initial loop: five actual in-game round trips, a changed server rule producing a changed result, stopped-service handling, and reconnect. One real player is sufficient to complete M-02. No second player or full economy is required.
  Completed: Not started.

- [ ] **T-04.4 — Preserve that player's community state across restart.**
  Needs: T-04.3 for the full game-connected result; storage/protocol work can begin alongside T-04.2.
  Build: Persist one server-owned progression value using transactional storage and request deduplication. Associate it with a stable community-member ID mapped to the configured lab principal, independently of connection/session and native save IDs. Define empty-server behavior; it may idle. Persisted lab identity is not a public entitlement-verification claim.
  Verify: E-10 persistence extension: complete an action, acknowledge it, close the game, restart the empty server, reconnect, recover the same value, and reject a duplicate mutation. This completes M-03; two-player synchronization is the next capability.
  Completed: Not started.

## Parallel work and real constraints

Server software, protocol fixtures, data models, and tests with original data can advance without game access. Adapter work needs the actual supported game environment. Multiple-client tests need the corresponding accounts/testers only when those tasks are reached.

Keep relevant code/content licenses and any concrete restrictions attached to the operation they affect. Publisher clarification, public entitlement access, interviews, naming, privacy responsibilities, distribution, hosting, and commercialization are distinct workstreams. Resolve required release conditions before the affected release. Do not require a commercial-launch agreement merely to write an original local server or document native game behavior. Outreach still needs a user instruction to contact people.

No failed implementation has been observed yet. The main open technical questions are which interaction can be exposed safely, what state the external runtime can control, and how that control relates to native sessions. These findings may change the task breakdown, dependencies, or proposed architecture.

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
