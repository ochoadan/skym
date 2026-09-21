# Decisions

## D-001 — Follow the Agent Project Playbook

Date: 2026-09-20. The project uses a small Markdown file map with one owner per fact and evidence-backed delivery status. `AGENTS.md` owns instructions and `CLAUDE.md` links to it. This establishes the initial structure; it replaces no prior system.

## D-002 — Preserve the user's FiveM-style objective

Date: 2026-09-20. The goal is community-controlled, game-integrated multiplayer. Mod distribution and a companion roleplay service are possible components or alternatives, not proof the goal is achieved. Applied in [PRODUCT](docs/PRODUCT.md). This supersedes the initial broad interpretation of a generic modding platform.

## D-003 — Establish authority before committing to platform implementation (superseded by D-006)

Date: 2026-09-20. The initial recommendation emphasized feasibility before implementation. The user clarified that this obscured the construction path and undervalued a one-player server. D-006 replaces this sequencing. Existing technical findings remain in RESEARCH.

## D-004 — Keep external progress distinct from official game state

Date: 2026-09-20. The proposed first contract uses a platform-owned ledger. Official currencies, inventory, discoveries, and cloud saves are not assumed to be server-authoritative or available through an API. Any later bridge needs separate trust and recovery evidence. Applied in PRODUCT and ARCHITECTURE.

## D-005 — Evaluate dependencies during implementation planning

Date: 2026-09-20. Windows/Steam is the initial lab assumption, not a promise of platform coverage. Hosting vendor, scripting engine, client technology, public license, and brand remain unselected. Reusing FiveM source or community libraries requires the actual selected license review. The research includes alternatives without freezing speculative dependencies.

## D-006 — Build incrementally from one player to the full community platform

Date: 2026-09-20. In response to the user's correction, a runnable service and a one-player game/server loop are explicit completed outcomes when verified. Persistence, two-player synchronization, admission, scripting, and stronger game authority follow as distinct capabilities. Experiments support engineering decisions rather than imposing a general stop/pivot checkpoint. Dedicated/listen hosting, player count, and simulation scope are evaluated separately. This supersedes D-003 and is applied in PRODUCT, ARCHITECTURE, and EXPERIMENTS.

## D-007 — Show the full roadmap and keep a small active queue

Date: 2026-09-20. ROADMAP owns the long-range engineering breakdown; STEPS owns progress and the next five executable tasks. The original five tasks were broad work packages and are retained as parent records with stable IDs. Detailed child tasks no longer hide the full construction path. This clarifies the playbook structure without treating five as the total project size.

## D-008 — Make the first build independent of game access and future hosting

Date: 2026-09-20. Start implementation at T-04.1 / R-001–R-010 with a local service, diagnostic client, and in-memory state. Choose and pin the toolchain in that task. Game integration can proceed alongside it when the installation is available. The loopback lab transport policy is separate from remote encryption requirements. First persisted progression is community-member-owned with stable server IDs; later character ownership is explicit. These rules are applied in AGENTS, STEPS, ARCHITECTURE, and ROADMAP to prevent handoff ambiguity and unnecessary early dependencies.
