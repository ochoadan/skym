# T-04.5 — Investigate automatic presentation and an in-world interaction

Planning record, 2026-09-23. [STEPS](../../STEPS.md) owns status. This is the adapter investigation already required before M-04/M-05 build gameplay on the chat bridge; it is not a two-player result or authorization to publish anything.

## Intended observable outcome

One deliberate in-game action beyond chat produces a typed observation, and a delayed server result is presented safely inside the running game without a second chat command. Select the exact reversible action and visible result after reviewing available hooks on the supported build, before implementing or attaching. Do not infer gameplay authority merely from observing a callback.

The existing [T-04.4 loop](../T-04.4/README.md) supplies persistent service state and a verified chat baseline. This investigation addresses the game boundary needed to make later interactions practical. It draws on R-015–R-020 / E-03 and informs R-042–R-044; it does not complete those broader roadmap items by association.

## First work

1. Review the selected dependency source revisions, installed executable and [existing adapter findings](../T-04.2/sources.md). Refresh changed sources/licenses before selecting another dependency. Identify candidate engine-thread callbacks, lifecycle signals and one reversible interaction beyond chat.
2. Write the operation contract: user action, visible result, allowed game states/thread, transient data, cancellation and failure feedback. Establish how delayed work is delivered using valid native state; an arbitrary worker calling a native function or reusing a stale pointer is not a valid presentation path.
3. Implement only the selected bounded experiment, preserving the existing supported-build gate, disposable-save workflow and restoration receipts. Keep pure protocol/queue/lifecycle checks game-free.
4. Run an attended one-client proof: real input, delayed response without a result command, cancellation on leave/disable, menu/reload and normal recovery. Record missing callbacks, rejected signatures, crashes and unsupported lifecycle behavior as findings.

## Acceptance and resulting decision

Record evidence for automatic presentation and the chosen non-chat action separately. Each needs actual native observations and user-visible results, exact build/source hashes, thread/lifetime constraints and successful recovery. If one is unavailable, preserve the working chat path and identify the concrete missing operation or candidate alternative. A server-only message exchange cannot satisfy either native result.

The findings decide the next game-integrated synchronization slice. A second player, independent simulation, economy enforcement and game-session admission require their own later evidence. No additional account or tester is needed merely to investigate this one-client boundary.

## Entry points

[Architecture: client boundaries](../../ARCHITECTURE.md#5-client-and-resource-boundaries) · [E-03](../../EXPERIMENTS.md#e-03--prove-minimal-runtime-access-on-the-target-build) · [existing hooks](../../../src/Community.AdapterLab/probe.py) · [callback correlation](../../../src/Community.AdapterLab/interaction.py) · [asynchronous worker](../../../src/Community.AdapterLab/bridge.py) · [guarded launcher](../../../src/Community.AdapterLab/launch.py).

Use the established [adapter verification command and disposable-save procedure](../T-04.2/README.md#setup-build-and-verify). Exact new commands and evidence belong here once an operation is selected; this plan claims no execution.
