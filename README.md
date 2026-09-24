# NMS Community Platform

## What we're building

A FiveM-style platform for **No Man's Sky**, intended to let operators run persistent communities, creators build custom rules and activities, and players join distinct multiplayer experiences with community progression.

The working name describes the project; it is not a cleared public brand. This is an independent project, with no claimed affiliation with Hello Games or Cfx.re.

## Current state

The product scope, research foundation, and proposed architecture are documented. [T-03.1 is complete](docs/tasks/T-03.1/evidence-2026-09-21.md#result-and-limits): repeated native game actions, saving and reloading across restarts, and recovery from a backup were verified using a disposable save on one Windows Steam installation.

A local standalone server and diagnostic client are implemented in C#/.NET. An experimental Python adapter connects native chat input to the server and retrieves its response inside NMS. [STEPS](docs/STEPS.md#current-status) holds delivery status, verification limits and completion evidence.

## Implementation entry points

[T-04.4](docs/tasks/T-04.4/README.md) documents current persistent progress, read-only chat queries, database backup/restore and restart verification.

[T-04.1](docs/tasks/T-04.1/README.md) documents the local server. [T-04.2](docs/tasks/T-04.2/README.md) documents the native adapter guards and disposable-save setup. [T-04.3](docs/tasks/T-04.3/README.md) documents the connected chat operation, commands and game checks.

The first playable goal is [one player connected to their own server](docs/PRODUCT.md#proposed-first-playable-milestone-one-player-and-their-server), performing an in-game action and seeing a result determined by that server. Follow [STEPS](docs/STEPS.md) for the current implementation task and its prerequisites.

## Getting started and documentation

Open this repository in an editor to review the documents; no game installation or development toolchain is needed for that. For project work, begin with AGENTS, PRODUCT, and STEPS below, then follow the selected task's linked records for procedures, evidence, and implementation entry points as code is added.

| Document | Purpose |
| --- | --- |
| [PRODUCT](docs/PRODUCT.md) | Intended users, experience, scope, and success criteria |
| [STEPS](docs/STEPS.md) | Current delivery status and queued work |
| [ROADMAP](docs/ROADMAP.md) | Provisional engineering path, milestone outcomes, dependencies, and uncertainty |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | Proposed components, authority boundaries, security, and operations |
| [RESEARCH](docs/RESEARCH.md) | Dated findings, sources, alternatives, economics, and uncertainties |
| [EXPERIMENTS](docs/EXPERIMENTS.md) | Experiment catalog, common lab rules, and evidence format |
| [Task documents](docs/tasks/README.md) | Plans, procedures, sources, evidence, and implementation links by task ID |
| [BACKLOG](docs/BACKLOG.md) | Conditional later work |
| [DECISIONS](DECISIONS.md) | Recorded choices, reasons, and revisions |
| [AGENTS](AGENTS.md) | Working instructions and document ownership |

See [LICENSE](LICENSE) for licensing terms.
