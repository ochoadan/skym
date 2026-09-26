# T-04.10 — Prove shared state with two real game clients

**Planned.** [STEPS](../../STEPS.md) owns delivery status. This is the attended R-050 / M-04 proof, drawing on the selected E-01b/E-04 scope and R-045–R-049. Its observations also establish the initial R-051 dependency record for later M-05 work.

## Outcome

Two real No Man's Sky clients interact with the same persisted community activity and automatically observe consistent results through the tested presentation surface. The run covers late join, conflict, participant loss and an empty-service restart, with restoration verified on both installations.

M-04 may be completed only for that observed shared-activity scope. This does not prove spawned world objects, synchronized native ships/positions, enforced physical actions, game admission, independent native-session hosting or capacity above the tested two clients.

## Needs

- Completed applicable lab/baseline work in [T-04.6](../T-04.6/README.md), [shared service](../T-04.7/README.md), [transport](../T-04.8/README.md) and [adapter integration](../T-04.9/README.md).
- Two actual supported game clients, separate community principals and disposable-save/restoration receipts for both. Both participants must be available for paired observations.
- Current build/mod/configuration hashes, service backup location, a selected native-session arrangement and a way to record user-visible outcomes from each client. Raw saves, credentials and captures stay in ignored local storage.

## Work

1. Record both build/storefront environments, adapter/service revisions, transport route, native host/group/scene conditions and starting save/settings receipts. Recheck compatibility before attachment. Restore the selected native baseline if an update or configuration change invalidates it.
2. Start a fresh shared activity through its implemented operator procedure. Connect both principals and confirm that both games display the same activity ID, revision and state. Record existing member progress to check that shared contributions do not alter it.
3. Player A arms the shared operation and enters their landed ship. Observe the server-decided result automatically in both games while B performs no matching action or manual state retrieval. Then have B contribute and observe the completed shared result in both views.
4. Exercise late join on a new activity: A changes state before B connects; B must display the current snapshot without replaying obsolete effects. Repeat after B has missed at least one change while disconnected. Compare activity identity, accepted count and authoritative revision.
5. Exercise a real two-player conflict against one prior revision. Coordinate both deliberate actions and verify from correlated requests that they used that revision. If ordinary timing does not produce contention, use a documented bounded lab barrier outside native callbacks; label the induced timing. One accepted command and one stale result must converge, and a permitted fresh action must follow the selected rules.
6. Close each game process in turn using the declared test procedure. Verify that the other participant can continue appropriately, historical contributions remain and no callback/ownership lock requires the departed player. Record native-session disruption separately from community-service behavior.
7. Close both games, confirm the service is empty, restart it using the same data, then reconnect both clients. Verify the same acknowledged activity revision/contributions, renewed sessions, discarded old armed input and consistent automatic presentation. Exercise exact replay as a diagnostic check without calling it another in-game action.
8. Test service loss/recovery and the selected late-event/duplicate presentation cases. Record outcomes from both clients, including failures and any native overwrite or duplicate native-chat replication. If native networking duplicates or replaces the presentation, keep that integration defect open until the selected fix is actually re-run.
9. Leave/disable, exit normally, run unmodified recovery and compare each installation's receipts. Preserve ordinary disposable-save changes as declared; restore relevant native/cloud settings and report every unresolved difference.

## Acceptance

- Both real clients see the same shared activity and server-decided revision after each accepted action; the passive observer receives changes automatically.
- Late join, a verified same-revision conflict, participant departure and empty-service restart produce the selected consistent result. A timing attempt that never conflicted is not conflict evidence.
- Correlated service/adapter records and paired user observations establish what was visible. A submitted native call or matching backend logs alone do not establish both visible results.
- Both recovery checks pass before this task or M-04 is marked complete. If restoration remains unresolved, retain a partial result with the problem explicit. Failures are retained as findings; no milestone completion is inferred from synthetic tests.
- A dated task-local report records the actual experiment, dependency/ownership table and scope. STEPS links the result and updates M-04 only when all scoped acceptance is met; no central per-run evidence ledger is appended.

## Follow-on boundary

Use observed dependencies to select M-05 work from R-051–R-060. The shared record belongs to the community service; observed native scene hosting, admission and ship behavior keep their actual owners. Native reference frames, world-entity lifecycle and authority/enforcement remain distinct tasks wherever unimplemented.

## Entry points

[M-04 acceptance](../../ROADMAP.md#milestones) · [Shared-state roadmap](../../ROADMAP.md#stage-5--synchronize-two-players-and-shared-interactions) · [Replication experiment](../../EXPERIMENTS.md#e-04--map-native-and-custom-replication) · [Evidence format](../../EXPERIMENTS.md#lab-prerequisites-and-evidence).

[Native operation and recovery](../T-04.5/README.md) · [Persistence and maintenance](../T-04.4/README.md) · [Product outcome](../../PRODUCT.md#intended-experience).
