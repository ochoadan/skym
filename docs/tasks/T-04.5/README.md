# T-04.5 — Investigate automatic presentation and an in-world interaction

Started 2026-09-24 at the user's request to begin the next step. [STEPS](../../STEPS.md) owns status. [Source review](sources.md) separates upstream declarations from local findings; [initial observations](evidence-2026-09-24.md) and [receiver/automatic evidence](evidence-automatic-2026-09-24.md) record the successive passes. This is the adapter investigation required before M-04/M-05 build gameplay on the chat bridge.

## Intended observable outcome

One deliberate in-game action beyond chat produces a typed observation, and a delayed server result is presented inside the running game without a second chat command, within the validated callback/state constraints. The selected action is a one-use armed entry into the landed ship; its contract is below. Do not infer gameplay authority merely from observing a callback.

The existing [T-04.4 loop](../T-04.4/README.md) supplies persistent service state and a verified chat baseline. This investigation addresses the game boundary needed to make later interactions practical. It draws on R-015–R-020 / E-03 and informs R-042–R-044; it does not complete those broader roadmap items by association.

## First work

1. Review the selected dependency source revisions, installed executable and [existing adapter findings](../T-04.2/sources.md). Refresh changed sources/licenses before selecting another dependency. Identify candidate engine-thread callbacks, lifecycle signals and one reversible interaction beyond chat.
2. Write the operation contract: user action, visible result, allowed game states/thread, transient data, cancellation and failure feedback. Establish how delayed work is delivered using valid native state; an arbitrary worker calling a native function or reusing a stale pointer is not a valid presentation path.
3. Implement only the selected bounded experiment, preserving the existing supported-build gate, disposable-save workflow and restoration receipts. Keep pure protocol/queue/lifecycle checks game-free.
4. Run an attended one-client proof: real input, delayed response without a result command, cancellation on leave/disable, menu/reload and normal recovery. Record missing callbacks, rejected signatures, crashes and unsupported lifecycle behavior as findings.

## Acceptance and resulting decision

Record evidence for automatic presentation and the chosen non-chat action separately. Each needs actual native observations and user-visible results, exact build/source hashes, thread/lifetime constraints and successful recovery. If one is unavailable, preserve the working chat path and identify the concrete missing operation or candidate alternative. A server-only message exchange cannot satisfy either native result.

The findings decide the next game-integrated synchronization slice. A second player, independent simulation, economy enforcement and game-session admission require their own later evidence. No additional account or tester is needed merely to investigate this one-client boundary.

## Selected first experiment: observe cockpit entry and scheduling

**User action:** enter the player's landed starship on the disposable checkpoint, remain landed, then exit. **Visible native result:** the normal cockpit view appears and the player can return on foot. **Adapter result to measure:** one `cockpit_entered` observation per deliberate entry, with callback thread and nesting relative to application updates. Menu/reload observations determine whether the same callback also occurs without deliberate input. No observed callback is yet connected to progression.

The optional `--observe-world` mode adds four native hooks: application update (before/after), player update, cockpit entry and the parent FSM transition. It retains the existing two chat hooks for a visible `/community` smoke check and `/community off`. It refuses a service configuration. All native functions continue normally; the new hooks neither dereference nor retain their arguments. The FSM record deliberately contains no state ID or object identity: its upstream arguments do not establish a readable string or application ownership. Observations during loading/menu are allowed for diagnosis and are never treated as permission to present a reply.

Only scalar counts, timestamps, thread IDs and per-thread update nesting enter the diagnostic queue. At most 64 detailed observations are emitted, plus a summary at most every two seconds while callbacks occur. Contended diagnostic updates are dropped; the count is approximate under contention. An emitter failure stops observation. These limits bound logging, not measured frame cost. `/community off` stops observation and local chat behavior; installed detours remain until process exit. No live unload claim is made.

**Automatic presentation uses a separate opt-in profile.** The upstream source supplies no verified fresh chat-manager accessor. The [local static investigation](sources.md#local-static-receiver-investigation) derived a current-owner receiver and state guard from this exact executable; the [read-only validation](evidence-automatic-2026-09-24.md#read-only-validation-passed) compared it with native `Say.this` and observed transitions before native calls were enabled. An application update callback does not make a saved chat pointer valid, and its own incoming `this` argument is not a valid singleton source on this build. The existing service/chat mode remains the manual fallback.

## Setup, build and verify

### Receiver validation and selected automatic operation

The next profile, `--validate-world`, uses the same six hooks but reads the guarded current-state/owner globals. It compares a freshly derived chat receiver with natural `Say.this`, records whether the FSM receiver is the application singleton, and samples state at application-update completion. It has no service and no native presentation call. Exercise normal play, pause, focus loss, mode selection and reload before selecting automatic mode. Never use the incoming application-update argument as the singleton.

**Selected automatic action:** submit `/community arm`, then enter the landed ship within 60 seconds. This consumes one arm and sends one existing typed `probe` request to the local service. The configured reply and saved community progress appear automatically, without `/community result`. Unarmed entries do nothing. This is a cooperative client report, not server proof of gameplay or an official-currency reward. `/community state` reads progress; the original chat commands remain available.

Automatic mode (`--auto-world --service-config <private-config>`) uses the outer application-update after callback on the observed engine thread. A natural chat callback must first match the freshly derived receiver in a playable state with no pending transition. Each delivery samples again and uses a full zero-initialized 1023-byte owned buffer through the synchronous native call. No game-object pointer is stored or sent to the worker. The function returns void, so logs record submission; user observation establishes visible delivery.

This is a scoped scheduling experiment. Fresh reads and cancellation checks cannot atomically prevent another native thread from replacing an object after the final read. No arbitrary-thread lifetime guarantee is claimed. `APPVIEW` classification is also not a focus/pause detector; pause/focus behavior needs observed evidence and must not be inferred from the state name.

Transitions, invalid state/reads, leave, reconnect and disable disarm the action and discard pending presentation. Cancellation contention blocks new actions and presentation until cancellation succeeds. Cancellation does not undo a service transaction that already committed; query state to reconcile it. Calibration is repeated after lifecycle changes. `/community off` ends adapter behavior until process restart; detours are removed by normal game exit. The worker retains its 20-second request/result lifetime. Optional `--delivery-delay 5` holds a completed reply for five seconds on the presentation side, making leave/disable cancellation observable without sleeping on the game thread.

For the read-only pass, substitute `--validate-world` and a fresh run directory in the attended procedure below. After that pass has established receiver/state agreement, exit normally and attach automatic mode to a fresh process. Verify repeated armed entries, automatic state reads, queued-result cancellation on leave and disable, menu/reload recalibration, service failure feedback, and final unmodified recovery. Preserve each run's source hashes and keep validation observations separate from automatic-call results.

Use the existing [isolated Python environment](../T-04.2/README.md#setup-build-and-verify). Dependencies and the service protocol are unchanged. The optional observer is identified by its launch flag and recorded Python source hashes; it is not an advertised service capability.

The shared [compatibility manifest](../../../config/adapter-compatibility.json) now selects adapter `0.4.0` and operation `native-chat-and-cockpit-v2`; rebuild the service with the [T-04.4 commands](../T-04.4/README.md#setup-build-and-verify) before using this adapter. Wire version 2, storage schema and typed `probe`/`state` operations are unchanged. This identifies the hybrid lab adapter, including manual fallback; it does not attest to a physical action. Keep older evidence's recorded versions unchanged.

```powershell
py -3.13 -W error::ResourceWarning -m unittest discover -s tests/Community.AdapterLab.Tests -v
py -3.13 src/Community.AdapterLab/preflight.py --observe-world --exe "D:\SteamLibrary\steamapps\common\No Man's Sky\Binaries\NMS.exe"
```

Provision and run a fresh service for automatic mode (private paths below are examples):

```powershell
dotnet src/Community.Server/bin/Release/net10.0/Community.Server.dll --init --config local/t04-5/finish/server.json
py -3.13 src/Community.AdapterLab/service_client.py --server-config local/t04-5/finish/server.json --principal alice --out local/t04-5/finish/adapter.json
dotnet src/Community.Server/bin/Release/net10.0/Community.Server.dll --config local/t04-5/finish/server.json
```

After the read-only validation pass and normal game restart, attach automatic mode:

```powershell
.\local\t04-2\venv-native\Scripts\python.exe -u src/Community.AdapterLab/launch.py --pid <NMS-PID> --run-dir local/t04-5/finish/automatic-001 --auto-world --delivery-delay 5 --service-config local/t04-5/finish/adapter.json
```

Stop the service using the existing authenticated diagnostic command:

```powershell
dotnet src/Community.Client/bin/Release/net10.0/Community.Client.dll --config local/t04-5/finish/server.json --mode stop
```

The process tests need the Release service artifact built by the [T-04.4 verification commands](../T-04.4/README.md#setup-build-and-verify). File preflight checks all six signatures using the same exact-build, uniqueness, section and runtime-function gates; launcher and injected module repeat the selected profile against live memory. Exit 0 permits an experiment, not a compatibility claim.

### Attended observation procedure

1. Follow the [disposable-save and restoration procedure](../T-04.2/README.md#lab-procedure-and-restoration): NMS closed, Steam synchronization complete, NMS-only Steam Cloud off, Cross-Save off, fresh verified save/settings receipts below ignored `local/t04-5`. Preserve older saves and previous receipts.
2. Launch through Steam, load `T-03.1 checkpoint A`, set Multiplayer off and stand near the landed ship. Recheck the executable after launch. Attach to the observed PID, using a new run directory:

   ```powershell
   Get-Process NMS | Select-Object Id,Path
   .\local\t04-2\venv-native\Scripts\python.exe -u src/Community.AdapterLab/launch.py --pid <NMS-PID> --run-dir local/t04-5/run-001 --observe-world
   ```

3. Confirm all six hooks enabled. Submit `/community` once to verify the existing visible local response. Leave the player idle for several seconds to establish counts, then enter/exit the landed ship three times with pauses. Record actual cockpit views, exact action count and any failures; compare diagnostic counts/nesting and thread IDs.
4. Return to menu, reload the same disposable slot and repeat one entry/exit. Record load-time callbacks separately. Generic FSM counts are not named application lifecycle events.
5. Submit `/community off`; confirm its visible message and the absence of subsequent observation. Enter/exit once more, verify ordinary `/community` behavior, then exit normally. Do not terminate the launcher to unload the hooks.
6. Relaunch through Steam without attachment. Verify normal checkpoint/chat behavior, restore Multiplayer on, exit, restore NMS-only Steam Cloud on and finish synchronization. Compare older saves, settings and executable to the fresh receipt. Preserve ordinary disposable-save changes; restore files only if recovery requires it.

This pass can establish native observation and recovery. It cannot complete T-04.5's automatic server-result acceptance.

## Entry points

[Architecture: client boundaries](../../ARCHITECTURE.md#5-client-and-resource-boundaries) · [E-03](../../EXPERIMENTS.md#e-03--prove-minimal-runtime-access-on-the-target-build) · [existing hooks](../../../src/Community.AdapterLab/probe.py) · [callback correlation](../../../src/Community.AdapterLab/interaction.py) · [asynchronous worker](../../../src/Community.AdapterLab/bridge.py) · [guarded launcher](../../../src/Community.AdapterLab/launch.py).

[Observation state and signatures](../../../src/Community.AdapterLab/world_observation.py) · [observation tests](../../../tests/Community.AdapterLab.Tests/test_world_observation.py). Native execution and remaining work are recorded in [evidence](evidence-2026-09-24.md).

[Fresh state reads and guards](../../../src/Community.AdapterLab/native_state.py) · [callback scheduler](../../../src/Community.AdapterLab/world_runtime.py) · [state tests](../../../tests/Community.AdapterLab.Tests/test_native_state.py) · [scheduler tests](../../../tests/Community.AdapterLab.Tests/test_world_runtime.py).
