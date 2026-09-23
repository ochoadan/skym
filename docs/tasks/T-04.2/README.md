# T-04.2 — Minimal game adapter

Scope: R-012–R-020, required subset of E-02/E-03. Started 2026-09-23 at the user's request to begin the next step. [STEPS](../../STEPS.md) owns status. [Sources and licenses](sources.md) distinguish upstream claims from verified behavior; [evidence](evidence-2026-09-23.md) records local checks and game observations.

## Selected operation and boundary

The first experiment uses the native text-chat input: the player submits exactly `/community` while using the disposable save with Multiplayer off. The proposed observable result is a native chat response, `Community adapter ready. Local probe #N.` The probe observes `ParseTextForCommands` and replaces at most one system `Say` response synchronously within that call on the same thread. Whether the native invalid-command response takes that path must be observed; unique signatures do not establish it.

This is an exploratory Python adapter alongside the existing C# service. It has no server connection, credentials, economy, save editing, or game-session control. T-04.3 owns the network round trip. This initial operation does not establish a custom world object or authoritative physical action.

Only two hooks are selected, using declarations from NMS.py at the revision in the source review. No NMS.py runtime, internal singleton loader, GUI extra, or HTTP extra is installed. The optional state-change signature was rejected by the stricter entry-point check and excluded; it may be a leaf function, but that has not been validated. Playable/menu state callbacks, travel, location access, live unloading and long-duration overhead remain separate work.

## Setup, build and verify

Selected toolchain: Windows x64 CPython 3.13.14, isolated venv, pyMHF 0.2.4. The initial Store-Python attachment failed; the working attachment uses the official Python NuGet package under ignored local storage and the loader corrections described below. Several changes were made before the successful attachment, so the failure is not attributed solely to Store Python. The service remains C#/.NET 10. Source-only tests need no dependencies or game files:

```powershell
py -3.13 -m unittest discover -s tests/Community.AdapterLab.Tests -v
```

Install the exact reviewed runtime wheels into ignored local storage:

```powershell
Invoke-WebRequest 'https://api.nuget.org/v3-flatcontainer/python/3.13.14/python.3.13.14.nupkg' -OutFile local/t04-2/python.3.13.14.zip
Get-FileHash local/t04-2/python.3.13.14.zip -Algorithm SHA256
Expand-Archive -LiteralPath local/t04-2/python.3.13.14.zip -DestinationPath local/t04-2/python-3.13.14
.\local\t04-2\python-3.13.14\tools\python.exe -m venv local/t04-2/venv-native
.\local\t04-2\venv-native\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r src/Community.AdapterLab/requirements.txt
.\local\t04-2\venv-native\Scripts\python.exe -m pip check
```

Create `local/t04-2` first if absent. For this selected artifact the archive hash must be `9AC15CFA6CAB1115C83D48F2AF55C554EFA4D1BB044BBC4AB1C9D17AD426E16C`; stop on mismatch before extraction/execution. Skip download/extraction/venv creation if already set up. The task evidence records the Python executable's valid PSF Authenticode signature. These commands do not change global Python registration or PATH.

[requirements.txt](../../../src/Community.AdapterLab/requirements.txt) pins all 19 runtime packages and Windows x64 wheel hashes. [dependencies.json](../../../src/Community.AdapterLab/dependencies.json) supplies the corresponding launch-time version allowlist. Do not install other packages in this environment; the launcher rejects extra distributions except pip and any pyMHF runtime/library entry points. Installed binary hashes are not a client anti-cheat claim. This code is an interpreted lab component; there is no native build step.

Read-only file preflight (exact local path from T-03.1):

```powershell
py -3.13 src/Community.AdapterLab/preflight.py --exe "D:\SteamLibrary\steamapps\common\No Man's Sky\Binaries\NMS.exe"
```

Exit 0 means eligible for this candidate experiment; exit 2 means refused. The allowlist covers executable SHA-256 `B7913F268DFC62386B6B68F524BFC8ADE4A44A9F4FBAD39085B7BF51BE3680CB`. PE layout, mapped-section bounds, signature uniqueness, executable section membership and x64 runtime-function starts are checked. No switch bypasses these checks. A new game release requires review; do not just replace the expected hash.

## Lab procedure and restoration

1. Close NMS normally, wait for Steam synchronization, then turn off Steam Cloud for NMS only. Leave NMS Cross-Save off. With the game closed, take a hash-verified backup of the four disposable files identified in [T-03.1](../T-03.1/evidence-2026-09-21.md) and reference copies of the four settings files. Preserve old saves, shared account/cache files and prior backups. The dated evidence records private receipt locations.
2. Launch through Steam, load `T-03.1 checkpoint A`, and disable Multiplayer through Options → Network. Recheck the executable after launch because Steam can update it. Confirm the ordinary `/community` response before attaching. One owned client only; no other players are test subjects.
3. Run the guarded launcher, substituting the single observed PID and a **new** run directory:

   ```powershell
   Get-Process NMS | Select-Object Id,Path
   .\local\t04-2\venv-native\Scripts\python.exe src/Community.AdapterLab/launch.py --pid <NMS-PID> --run-dir local/t04-2/run-003
   ```

   The launcher does not start the game. It verifies the exact process, dependencies, Multiplayer/Cross-Save settings and live signature counts before calling the injector; the mod repeats process/signature checks before registering hooks. Diagnostics, offset cache and events stay in the selected ignored run directory. Parent process output should also be retained in ignored lab storage. A public dummy prompt-toolkit session permits headless pyMHF imports in both processes. The launcher adapts the injector in memory, without editing installed upstream files: it resolves each loaded DLL by its exact path in the target and checks the native entry point against its file before execution. Upstream Pymem's local-module-handle return is not used as a remote address.
4. After logs confirm both hooks enabled, submit `/community` once and inspect the actual native response. If successful, repeat five times; correlate typed `interaction`, `presentation_requested` and `presentation_written` events with the observed display. A buffer write is not proof that the user saw a response. Record missing callbacks, `no_system_reply`, crashes and duplicate messages as failures rather than inventing success.
5. Return to menu and load the disposable slot again; repeat the action. Submit `/community off`; it should display the disabled message, and subsequent `/community` should retain native behavior. This disables the probe's behavior, **not** the installed detours. Exit the game normally. Do not use Ctrl+C to unload: upstream cleanup can terminate the game. Restart NMS normally without the launcher and verify the ordinary response and playable save. Repeat an attached process cycle only after the first succeeds.
6. Restore Multiplayer to its original on setting via the native UI, exit normally, restore per-game Steam Cloud to on, wait for sync, and verify a normal native load/exit. Restore backed-up save files only if needed, using the closed-game, sync-aware allowlist from T-03.1; do not overwrite ordinary save changes merely to obtain matching hashes. Record settings/hash comparisons and any new game-managed files.

Keep NMS open only while an attended test is active. If input is unavailable with Multiplayer off or the proposed nested reply never occurs, preserve that result and choose a different local operation. Enabling public multiplayer is not a substitute for proving a local presentation path.

## Code and lifecycle rules

| File | Responsibility |
| --- | --- |
| [preflight.py](../../../src/Community.AdapterLab/preflight.py) | Read-only file/PE allowlist and signature checks |
| [runtime_guard.py](../../../src/Community.AdapterLab/runtime_guard.py) | Verify selected PID and live module matches against file RVAs |
| [launch.py](../../../src/Community.AdapterLab/launch.py) | Dependency/entry-point checks, new local run directory, exact-PID attachment |
| [injection.py](../../../src/Community.AdapterLab/injection.py) | Actual remote module bases, native export validation, headless import bootstrap |
| [interaction.py](../../../src/Community.AdapterLab/interaction.py) | Pointer-free per-thread call correlation, exact commands, one response, disable behavior |
| [probe.py](../../../src/Community.AdapterLab/probe.py) | Two native hooks, transient bounded string access, bounded event queue |
| [tests](../../../tests/Community.AdapterLab.Tests/test_preflight.py) | Original synthetic PE fixtures and rejection cases |
| [interaction tests](../../../tests/Community.AdapterLab.Tests/test_interaction.py) | Unrelated/nested/cross-thread messages, no-response and disable cases |

Game pointers are used only inside their originating callback. No network requests, disk writes, or deferred game-object access occur in callbacks. A maximum 128-entry queue sends primitive diagnostic records to a worker; overflow drops diagnostics and increments a counter. Thread IDs and timestamps are observations, not a declared engine-thread guarantee. Ordinary chat text and object addresses are not logged.

The upstream developer execution console still listens on `127.0.0.1:6770`; disabling its interactive UI does not remove that unauthenticated Python interface. This is temporary trusted local lab tooling, not the proposed platform IPC interface. R-019 requires a bounded typed communication boundary; this console does not satisfy it. Restart-based removal is the initial cleanup mechanism. No live reload/unload claim is made. Upstream launcher cleanup terminates its own process even after normal game exit, so its exit code 1 alone is not evidence of a game crash; correlate with game observations, process state and fault logs.

Architecture context: [client/resource boundaries](../../ARCHITECTURE.md#5-client-and-resource-boundaries), [authority](../../ARCHITECTURE.md#2-authority-contract), [game compatibility](../../ARCHITECTURE.md#8-updates-operations-and-launch). Full [E-02](../../EXPERIMENTS.md#e-02--prove-reversible-mod-installation) and [E-03](../../EXPERIMENTS.md#e-03--prove-minimal-runtime-access-on-the-target-build) remain broader than this first probe.
