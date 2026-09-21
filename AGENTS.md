# Working instructions

Read this file, `docs/PRODUCT.md`, and `docs/STEPS.md` before work. Read `docs/RESEARCH.md` and relevant experiment or architecture sections for technical changes. `CLAUDE.md` points here; this is the authoritative instruction file.

## Scope

The founding request is to create a new project and research, end to end, a FiveM-style platform for No Man's Sky. Research and documentation are authorized. A planned task does not by itself authorize building, publishing, contacting people, or purchasing services. Follow the latest user request when scope expands; do not request permission again for already authorized work.

Preserve the distinction between independent game servers, servers that own only platform data, and community websites. Do not silently replace the requested game-integrated platform with a companion product. Do not advertise a larger player limit, enforced economy, crossplay mod support, or independent hosting without matching evidence.

## Fact ownership

| File | Owns |
| --- | --- |
| `README.md` | Orientation and navigation |
| `AGENTS.md` | Workflow and verification rules |
| `docs/PRODUCT.md` | Users, intent, scope, product boundaries |
| `docs/STEPS.md` | Delivery status, dependencies, next tasks, completion evidence |
| `docs/ROADMAP.md` | End-to-end engineering decomposition and milestone acceptance; no competing status ledger |
| `docs/RESEARCH.md` | External findings, source freshness, alternatives, cost assumptions |
| `docs/ARCHITECTURE.md` | Proposed technical design and operational requirements |
| `docs/EXPERIMENTS.md` | Test procedures, acceptance thresholds, evidence format |
| `docs/BACKLOG.md` | Conditional later ideas |
| `DECISIONS.md` | Lasting decisions and reasons |

Update the owner of a changed fact and link to it elsewhere. Rewrite outdated claims. Keep completion records concise. Keep the next five executable tasks detailed in STEPS and the full engineering path in ROADMAP. The playbook's five-task working queue is not a limit on the size of the project plan.

## Engineering approach

The user clarified that the project should progress through construction and problem-solving, starting with a server and one connected player. Count a runnable service, a real one-player game connection, persistent reconnect, two-player synchronization, and stronger game control as separate useful milestones. Server player count, dedicated/listen hosting mode, and simulation authority are separate dimensions. Do not require full native-engine simulation, multiple players, or an always-running world before acknowledging an earlier milestone.

Use experiments to implement and debug the next capability. When an approach fails, record the specific failure, alternatives, and next bounded change. Do not automatically stop the whole project, demand interviews before technical work, or pivot to a companion app. Escalate a constraint when concrete evidence requires a product/budget/rights decision; do not promise that engineering can guarantee every desired outcome.

## Research and implementation

- Separate verified source statements, maintainer claims, engineering inferences, proposals, and unresolved questions. A README is evidence of what a tool promises, not proof it works on an installed game build.
- Cite primary publisher/vendor/maintainer sources with exact URLs and review dates. Recheck game releases, dependency licenses, service prices, and terms before relying on them. Avoid unqualified claims based on historical player counts.
- Treat absence of a discovered API as an unresolved dependency, not proof of impossibility. Generic networking middleware does not provide No Man's Sky's simulation or permission to use its backend.
- Define the user action and observable result before implementing. A UI mock or two clients exchanging arbitrary messages does not verify in-game behavior.
- Keep proprietary game files, real saves, credentials, account tickets, and mod binaries out of Git. Use owned test installations and disposable saves for lab work; document changes and verify restoration.
- Record permissions and licenses for each dependency at the exact selected commit. Do not assume source-visible code can be redistributed. The architecture and research contain scoped permission questions; a proposed public launch is distinct from local documentation work.
- End-to-end game evidence records build/storefront, mod hashes, configuration, client count, steps, observed state, logs, and failures. Never fabricate a lab result.

## Setup and verification

This foundation contains Markdown and Git configuration; it has no runtime dependencies, package manager, test runner, or deployment target. Do not invent setup or passing application tests.

Use `rg --files` to inspect the file map and `git diff --check` for tracked changes. For new files, include them in a Git comparison before relying on that command. Check that relative Markdown links resolve, STEPS matches actual artifacts, and research claims link to supporting sources. Record what was checked and what was not in STEPS.

When code is introduced, add exact install, run, and verification commands here in the same change. Select tests for observable behavior and risks, not mechanical copies of the implementation.

## First build and handoff

Start authorized implementation with T-04.1 / R-001–R-010. Select the minimal service toolchain from the local environment, pin its SDK/dependency versions, and record the choice. M-01 can use in-memory state; persistence belongs to the next milestone's work. Keep the service, protocol contract/fixtures, diagnostic client, and later game adapter separated so the service can be developed without game access. Introduce exact paths with the scaffold rather than pre-creating empty projects.

Add a repeatable local build/test command with the first runnable code. Run ordinary protocol and service tests without proprietary game files; native integration evidence requires the actual game environment. Add an automated build/test workflow when the repository's hosting is configured, reusing the same local commands. Check dependency/license changes when selecting packages rather than freezing an arbitrary stack in the planning documents.

At a handoff, update STEPS with active task and R-IDs, implementation state, exact commands/results, unresolved failures, game/build requirements if relevant, and the next concrete action. Record partial row completion without marking the parent milestone complete. Put only original/sanitized fixtures in Git; keep runtime databases, credentials, save backups, captures, and downloaded game-derived material under ignored local storage.

Use independent agents for clearly assigned files/components when useful. Agree the shared protocol before parallel server and adapter edits; avoid two agents editing its contract simultaneously. Integrate and verify their changes before recording completion.
