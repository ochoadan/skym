# Decisions

## D-001 — Follow the Agent Project Playbook

Date: 2026-09-20. The project uses a small Markdown file map with one owner per fact and evidence-backed delivery status. `AGENTS.md` owns instructions and `CLAUDE.md` links to it. This establishes the initial structure; it replaces no prior system.

## D-002 — Preserve the user's FiveM-style objective

Date: 2026-09-20. The goal is community-controlled, game-integrated multiplayer. Mod distribution and a companion roleplay service are possible components or alternatives, not proof the goal is achieved. Applied in [PRODUCT](docs/PRODUCT.md). This supersedes the initial broad interpretation of a generic modding platform.

## D-003 — Establish authority before committing to platform implementation (superseded by D-006)

Date: 2026-09-20. The initial recommendation emphasized feasibility before implementation. The user clarified that this obscured the construction path and undervalued a one-player server. D-006 replaces this planning approach. Existing technical findings remain in RESEARCH.

## D-004 — Keep external progress distinct from official game state

Date: 2026-09-20. The proposed first contract uses a platform-owned ledger. Official currencies, inventory, discoveries, and cloud saves are not assumed to be server-authoritative or available through an API. Any later bridge needs separate trust and recovery evidence. Applied in PRODUCT and ARCHITECTURE.

## D-005 — Evaluate dependencies during implementation planning

Date: 2026-09-20. Windows/Steam is the initial lab assumption, not a promise of platform coverage. Hosting vendor, scripting engine, client technology, public license, and brand remain unselected. Reusing FiveM source or community libraries requires the actual selected license review. The research includes alternatives without freezing speculative dependencies.

## D-006 — Recognize useful increments toward the community platform

Date: 2026-09-20; framing clarified 2026-09-21. A runnable service and a one-player game/server loop have explicit acceptance definitions because the initial plan undervalued those outcomes. Persistence, synchronization, admission, scripting, and stronger authority are distinct capabilities. Hosting mode, player count, and simulation scope describe different properties. This supersedes D-003; it does not select an unchangeable implementation order or settle how to respond to future failures. The context is recorded in PRODUCT and the proposed milestones in ROADMAP.

## D-007 — Show the longer-range roadmap and keep a small active queue

Date: 2026-09-20; framing clarified 2026-09-21. ROADMAP owns the long-range engineering breakdown; STEPS owns progress and the next few detailed tasks, currently five. The original broad work packages remain parent records with stable IDs. The 140 rows make anticipated work visible; they are neither proof of completeness nor a required count. ROADMAP records which parts have concrete local checks and which depend on untested integration assumptions.

## D-008 — Propose a local service as the first build increment

Date: 2026-09-20; framing clarified 2026-09-21. A local service, diagnostic client, and in-memory state provide an initial software outcome independent of game access and future hosting. T-04.1 / R-001–R-010 is therefore the proposed entry point in STEPS, with tooling selected during that work. The loopback lab policy, encrypted remote transport, and stable community-member ownership remain technical requirements in ARCHITECTURE. The user's note, *Expressing Intent Without Prescribing Behavior*, prompted removal of duplicated sequencing and failure-response instructions; it did not supply a replacement behavioral formula.

## D-009 — Persist member progress with local SQLite transactions

Date: 2026-09-23. T-04.4 uses SQLite for one locally operated service, with stable member ownership, atomic state/event/replay writes and durable polling recovery. This avoids a separate database daemon while supplying transactions and backup support. PostgreSQL remains an option for broader deployment needs. Protocol version 2 explicitly carries member/progress data; sessions remain ephemeral, and progression counts cooperative chat interactions. [Task contract](docs/tasks/T-04.4/README.md), [alternatives and dependency review](docs/tasks/T-04.4/sources.md).
