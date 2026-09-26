# Working instructions

Read this file, `docs/PRODUCT.md`, and `docs/STEPS.md` before work. Read the selected task record and relevant research, experiment, and architecture sections before technical changes. `CLAUDE.md` points here; this is the authoritative instruction file.

## Scope

The founding request is to create a new project and research, end to end, a FiveM-style platform for No Man's Sky. Research and documentation are authorized. A planned task does not by itself authorize building, publishing, contacting people, or purchasing services. Follow the latest user request when scope expands; do not request permission again for already authorized work.

The selected product and the context behind it are in [PRODUCT](docs/PRODUCT.md). Match capability claims to evidence, including player limits, economy enforcement, crossplay, and independent hosting.

## Fact ownership

| File | Owns |
| --- | --- |
| `README.md` | Orientation and navigation |
| `AGENTS.md` | Workflow and verification rules |
| `docs/PRODUCT.md` | Users, intent, scope, product boundaries |
| `docs/STEPS.md` | Compact current capability status, dependencies, and the next five tasks |
| `docs/tasks/README.md` | Entry points for task documents still used by current work |
| `docs/tasks/<T-ID>/` | Task plans, detailed procedures, dated sources/evidence, and links to relevant architecture and implementation |
| `docs/ROADMAP.md` | Provisional engineering breakdown, dependencies, and milestone acceptance; no competing status ledger |
| `docs/RESEARCH.md` | Cross-cutting external findings, alternatives, costs, and links to dated source reviews |
| `docs/ARCHITECTURE.md` | Proposed technical design and operational requirements |
| `docs/EXPERIMENTS.md` | Experiment catalog, common lab rules, and evidence format; detailed task procedures are linked |
| `docs/BACKLOG.md` | Conditional later ideas |
| `DECISIONS.md` | Lasting decisions and reasons |

Update each fact's owner and link to it elsewhere. Minimize changes to core Markdown files; keep them focused on purpose, shared constraints, summaries, status, and navigation. Put step detail in `docs/tasks/<T-ID>/`; label plans, procedures, dated sources, and observed evidence clearly. Link relevant architecture sections and real code paths when they exist. Create or split files only for useful depth; update indexes and incoming links when moving or removing them. Keep task IDs stable; STEPS holds the short queue and ROADMAP the longer-range plan.

STEPS is a rolling plan: keep a compact capability baseline and five upcoming tasks. Remove completed tasks from the queue once their lasting result and remaining limitations are reflected in the appropriate reference. Do not append a completion ledger or replace it with another cumulative history table. Git history and CI retain routine change/check history; do not create a documentation row or evidence file for every edit, task, or passing test run.

Keep task procedures, contracts, source reviews, and selected evidence while current operation, a capability claim, an unresolved failure, or future work relies on them. Preserve dated evidence as the result of its actual build/run; a later result must not rewrite an earlier observation. Retire superseded, unreferenced material to Git history after updating incoming links and preserving any still-useful constraints in their owning document. The task index lists working references, not every task ever completed.

## Research and implementation

- Separate verified source statements, maintainer claims, engineering inferences, proposals, and unresolved questions. A README is evidence of what a tool promises, not proof it works on an installed game build.
- Cite primary publisher/vendor/maintainer sources with exact URLs and review dates. Recheck game releases, dependency licenses, service prices, and terms before relying on them. Avoid unqualified claims based on historical player counts.
- Treat absence of a discovered API as an unresolved dependency, not proof of impossibility. Generic networking middleware does not provide No Man's Sky's simulation or permission to use its backend.
- Define the user action and observable result before implementing. A UI mock or two clients exchanging arbitrary messages does not verify in-game behavior.
- Keep proprietary game files, real saves, credentials, account tickets, and mod binaries out of Git. Use owned test installations and disposable saves for lab work; document changes and verify restoration.
- Record permissions and licenses for each dependency at the exact selected commit. Do not assume source-visible code can be redistributed. The architecture and research contain scoped permission questions; a proposed public launch is distinct from local documentation work.
- End-to-end game evidence records build/storefront, mod hashes, configuration, client count, steps, observed state, logs, and failures. Never fabricate a lab result.

## Setup and verification

Standalone service setup, run and verification commands are in [T-04.1](docs/tasks/T-04.1/README.md#setup-build-and-verify). Do not invent passing application tests or game results.

Adapter lab setup, read-only preflight and verification commands are in [T-04.2](docs/tasks/T-04.2/README.md#setup-build-and-verify); follow its disposable-save procedure before attachment.

The connected chat adapter, service configuration and E-10 procedure are in [T-04.3](docs/tasks/T-04.3/README.md#setup-build-and-verify).

Current persistence setup, locked restore, maintenance and E-10 restart verification are in [T-04.4](docs/tasks/T-04.4/README.md#setup-build-and-verify).

The opt-in cockpit probe, receiver validation, automatic presentation and attended procedure are in [T-04.5](docs/tasks/T-04.5/README.md#setup-build-and-verify).

Use `rg --files` to inspect the file map and `git diff --check` for tracked changes. For new files, include them in a Git comparison before relying on that command. Check that relative Markdown links resolve, STEPS matches actual artifacts, and research claims link to supporting sources. Report routine checks in the handoff or CI; retain detailed results in a task/evidence record when they support a capability claim or a failure needed for future work.

When code is introduced, put exact install, run, and verification commands in its component/task documentation and link that entry point here. Select tests for observable behavior and risks, not mechanical copies of the implementation.

## Implementation and handoff

Use STEPS for the current implementation entry point and its prerequisites. Record selected tooling and pin SDK/dependency versions when introducing code. The proposed component boundaries and transport policy are in ARCHITECTURE.

Use scripts only when necessary. Implement application behavior in code and use standard toolchain commands for build and execution.

Add a repeatable local build/test command with the first runnable code. Run ordinary protocol and service tests without proprietary game files; native integration evidence requires the actual game environment. Add an automated build/test workflow when the repository's hosting is configured, reusing the same local commands. Check dependency/license changes when selecting packages rather than freezing an arbitrary stack in the planning documents.

At a handoff, refresh STEPS with the current task/R-IDs, state and next action; replace completed queue entries instead of accumulating them. Link selected supporting evidence from the capability summary or working reference that needs it. Keep reusable commands, material results/failures, and build requirements in the relevant task record. Record partial completion without marking the parent milestone complete. Put only original/sanitized fixtures in Git; keep runtime databases, credentials, save backups, captures, and downloaded game-derived material under ignored local storage.

Use independent agents for clearly assigned files/components when useful. Agree the shared protocol before parallel server and adapter edits; avoid two agents editing its contract simultaneously. Integrate and verify their changes before recording completion.
