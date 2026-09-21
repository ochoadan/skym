# NMS Community Platform

Research and project foundation for a FiveM-style multiplayer platform for **No Man's Sky**: independently operated communities, custom game rules, creator scripting, persistent progression, and server administration.

The working name describes the project; it is not a cleared public brand. This is an independent project, with no claimed affiliation with Hello Games or Cfx.re.

Start with [the engineering roadmap](docs/ROADMAP.md) for the complete path from a runnable server to a released community platform. The first game-integrated milestone is one player connecting to a server and receiving a meaningful server-controlled response. [The research](docs/RESEARCH.md) explains existing tools, technical unknowns, costs, and external constraints. Experiments accompany construction and guide the next implementation choice.

| Document | Purpose |
| --- | --- |
| [PRODUCT](docs/PRODUCT.md) | Intended users, experience, scope, and success criteria |
| [ROADMAP](docs/ROADMAP.md) | Full engineering path, milestone outcomes, and dependencies |
| [RESEARCH](docs/RESEARCH.md) | Dated findings, sources, alternatives, economics, and uncertainties |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | Proposed components, authority boundaries, security, and operations |
| [EXPERIMENTS](docs/EXPERIMENTS.md) | Reproducible engineering tests for implemented capabilities |
| [STEPS](docs/STEPS.md) | Actual status, evidence, and the next five executable tasks |
| [BACKLOG](docs/BACKLOG.md) | Conditional later work |
| [DECISIONS](DECISIONS.md) | Choices future work should preserve |
| [AGENTS](AGENTS.md) | Working instructions and document ownership |

There is no application to install or start yet. Implementation and release status belong to STEPS. No game executable, proprietary asset, save file, or third-party mod binary is included.

For local review, open this directory in an editor, read the documents above, and run `git diff --check` for whitespace issues. Game experiments require the separately listed lab prerequisites; reading this repository does not require No Man's Sky.

## Start the first implementation session

Open this repository as the working directory. The immediate entry point is T-04.1 / R-001–R-010: a local standalone server and diagnostic client. It can proceed without a game installation. T-03.1 / R-011 records the game baseline in parallel when that installation is available. Stack selection is part of the first implementation task, not unfinished product planning.

Use this instruction when starting the build:

> Read AGENTS.md, docs/PRODUCT.md, docs/STEPS.md, and the relevant ROADMAP rows. Begin implementing T-04.1 toward M-01: a standalone loopback server with one configurable interaction and a diagnostic client. Choose and record a minimal suitable toolchain, build and verify the complete local behavior, and update STEPS with exact commands, evidence, remaining work, and the next action. Advance the one-player NMS adapter path when the game environment is available. Keep the existing product direction and distinguish synthetic-client results from real game integration.

Session-to-session progress belongs in STEPS, including the active R-IDs, changed files, tests actually run, specific failures, and the next runnable action. See AGENTS for the handoff requirements. The saved Git checkpoint preserves the plan; remote-backup status belongs in STEPS.

Project organization follows the user's [Agent Project Playbook](../../../Desktop/Agent%20Project%20Playbook.md).
