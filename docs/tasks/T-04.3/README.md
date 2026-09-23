# T-04.3 — One player connected to their server

Scope: R-021–R-030 / E-10 initial loop, with the required subset of R-018/R-019. Started 2026-09-23 at the user's request. [STEPS](../../STEPS.md) owns status; [evidence](evidence-2026-09-23.md) separates software checks from actual game observations.

## Selected action and visible result

In the disposable NMS save, submit `/community`, then `/community result` within 20 seconds. The first command queues one request; the second displays the server-selected response, for example `[local-lab #1] Server rule A: welcome to the community.` Change the server's `completionMessage`, restart it, and repeat: the new text must appear inside the same running game. The revision counts server interactions, not physical gameplay progress.

This first operation deliberately uses two native submissions. Network work runs asynchronously; presentation occurs only through a fresh, correlated native system-chat callback. There is no automatic push notification, game-thread network wait, cached native pointer, native function invocation from a worker, save mutation, or physical-action/economy authority claim. A successful synthetic run alone cannot complete M-02.

## Setup, build and verify

Use the existing [.NET service toolchain](../T-04.1/README.md#setup-build-and-verify) and [isolated adapter runtime](../T-04.2/README.md#setup-build-and-verify). No new dependencies were added. The reviewed game/tool hashes and licenses remain in [T-04.2 sources](../T-04.2/sources.md); the original notices remain applicable. Adapter capability version is `0.2.0`, operation `native-chat-poll-v1`. These values and the verified executable hash live only in [adapter-compatibility.json](../../../config/adapter-compatibility.json), shared by service admission and the adapter. After a game update, change that file only once the new build's signatures and behavior are verified; it is not an operator setting.

From the repository root:

```powershell
dotnet run --project tests/Community.Tests --configuration Release
py -3.13 -m unittest discover -s tests/Community.AdapterLab.Tests -v
```

The second command includes actual Python-to-C# process checks when the Release server artifact and .NET runtime exist; those cases explicitly skip in a Python-only environment. Run in this order for full verification. The existing Windows CI workflow uses the same order; it needs no game files or installed hook framework. Hosted execution is recorded separately.

Create a separate local configuration once (initialization refuses an existing file):

```powershell
dotnet src/Community.Server/bin/Release/net10.0/Community.Server.dll --init --config local/t04-3/server.json
py -3.13 src/Community.AdapterLab/service_client.py --server-config local/t04-3/server.json --principal alice --out local/t04-3/adapter.json
```

The provisioner copies only endpoint, community, principal and that principal's lab key. The adapter never receives the operator key or other principals' keys. Both files must remain ignored. The credential is a cooperative lab bootstrap key, not an entitlement token or anti-cheat secret. The server issues a bounded, expiring bearer session; adapter sessions may use only `probe` mutations. Principal-key possession can still create diagnostic sessions; session scope is not a stronger key privilege boundary.

Edit `completionMessage` in the private server config to a short, plain-text rule and start the server:

```powershell
dotnet src/Community.Server/bin/Release/net10.0/Community.Server.dll --config local/t04-3/server.json
```

Endpoint selection is explicit in the adapter config: `{host:"127.0.0.1", port, communityId, principalId, key}`. All five fields are required; extra fields are refused. Only numeric loopback is supported, without DNS, redirects, environment proxies or remote HTTP. Change endpoints only between adapter process runs. Separate configurations can select different loopback communities.

After the disposable-save preparation below, run:

```powershell
Get-Process NMS | Select-Object Id,Path
.\local\t04-2\venv-native\Scripts\python.exe -u src/Community.AdapterLab/launch.py --pid <NMS-PID> --run-dir local/t04-3/run-001 --service-config local/t04-3/adapter.json
```

Choose a new run directory on every attachment. The launcher writes executable preflight and source-hash manifests before injection and passes only the config path to pyMHF. The guard repeats executable/live signatures and Multiplayer/Cross-Save checks. Existing loader corrections remain unchanged. Omit `--service-config` to run the original T-04.2 local probe under `local/t04-2`.

## Command and lifecycle contract

| Native chat command | Observable behavior |
| --- | --- |
| `/community` | Queue one real server `probe`; immediately explain connecting/sending and result retrieval |
| `/community result` | Show pending, consume one result/error, or report nothing pending; never creates another mutation |
| `/community reconnect` | Invalidate pending/results and queue session closure; a subsequent `/community` connects again |
| `/community leave` | Same invalidation/closure with disconnected feedback; later explicit input may reconnect |
| `/community off` | Invalidate/close and disable behavior until process restart; detours remain installed |

Commands match exactly and only replace their own first nested system response. If no system response occurs, no request is sent, result consumed, or disable applied. Unrelated chat is left alone. A busy callback uses a nonblocking lock attempt and asks the player to try again; it never waits for worker completion.

One worker owns the HTTP client and session. One queued work item and one outstanding request/result bound retained work. Requests and results have a 20-second monotonic validity period; an expired record may remain stored until another command. Generation IDs and cancellation discard late replies after leave/reconnect/off. Each HTTP exchange has a three-second deadline including response reading, a 4,096-byte body limit and strict field/type/correlation checks. Native output uses at most 640 ASCII bytes from a restricted plain-text alphabet; formatting/control/non-ASCII characters are replaced with `?`. This is an English lab UI, not localization support.

The worker checks cancellation before sending a mutation. A command already sent may commit even after cancellation or a lost response. No automatic mutation retry is performed. Timeout feedback says the outcome is unknown; a later deliberate request has a new ID. Server deduplication handles exact replays within one service process. Reauthentication after an expired or restarted session occurs before a new mutation; revisions and interaction IDs are fetched anew. State and deduplication remain memory-only.

Menu and save-load transitions are **not observed**. The result belongs to the configured community principal, independently of the native save. It may be read after a quick menu/reload within its lifetime using a new callback; no native object survives the transition. Use leave/off to cancel before leaving the community. Broader R-015 and E-03 lifecycle/travel/overhead work remains open. Normal game exit removes the hooks; there is no live unload claim. If the game exits without leave/off, the session expires or is removed with server shutdown.

The loopback HTTP path is the bounded typed service boundary for this experiment. The upstream unauthenticated Python developer listener on `127.0.0.1:6770` still exists; no platform traffic uses it. This developer environment is not a distribution-ready resource sandbox.

## Attended E-10 procedure and recovery

1. Follow [T-04.2 preparation and restoration](../T-04.2/README.md#lab-procedure-and-restoration): close NMS, finish Steam sync, disable NMS-only Steam Cloud, preserve Cross-Save off, and take a fresh hash-verified backup of the four disposable save files and four settings references. Keep old saves outside the replacement set.
2. Start the local server with rule A. Launch through Steam, load `T-03.1 checkpoint A`, disable Multiplayer in the native UI, and recheck the executable hash after launch. Attach only after those checks pass. Retain server output, adapter events and source/config manifests in ignored `local/t04-3` storage; do not commit credentials or game captures.
3. Submit `/community`, then `/community result` promptly. Match the displayed rule and revision to the adapter request ID and successful server command log. Repeat for five visible round trips. Repeated input while pending must not create another mutation; repeated result retrieval must not display the same success twice.
4. Stop the service with the command below. Submit a new `/community` and retrieve the result: expect an understandable unavailable/timeout error, without a fabricated success or blocked game input. Change only `completionMessage` to rule B, restart on the same endpoint, then submit and retrieve again. Confirm rule B appears and a fresh service revision is reported.
5. Exercise `/community leave` then reconnect through `/community`. Exercise menu/reload with the declared save-independent lifetime behavior. Run the diagnostic malformed request check against the same lab service; it must reject without changing state. Submit `/community off`, verify ordinary native behavior returns, and exit normally.
6. Stop the service, launch the game normally without attachment, verify checkpoint A and native chat behavior, restore Multiplayer on, exit, restore NMS-only Steam Cloud on and finish sync. Check the old saves and settings against the fresh receipt; restore disposable files only if recovery actually requires it. Record all failures and distinguish user-visible observations from log writes.

```powershell
dotnet src/Community.Client/bin/Release/net10.0/Community.Client.dll --config local/t04-3/server.json --mode malformed
dotnet src/Community.Client/bin/Release/net10.0/Community.Client.dll --config local/t04-3/server.json --mode stop
```

## Source review and implementation

Reviewed 2026-09-23: the pinned pyMHF [hook dispatch](https://github.com/monkeyman192/pyMHF/blob/0c8ebc1c29074c5bc35207e0aff36d4035e20bac/pymhf/core/hooking.py) invokes before/original/after functions inline. It supplies neither engine-thread marshalling nor object lifetime tracking. This source finding motivates explicit result polling; it is not proof of the new game path. [Python HTTP documentation](https://docs.python.org/3.13/library/http.client.html) documents blocking-operation timeouts; the client adds an absolute socket shutdown deadline. [Queue documentation](https://docs.python.org/3.13/library/queue.html) documents bounded queues and nonblocking operations. The [publisher release log](https://www.nomanssky.com/release-log/) was refreshed; compatibility remains tied to the measured executable hash, not an inferred patch name. The same day's [scoped publisher/terms and license review](../T-04.2/sources.md#publisher-freshness-and-scoped-lab-assessment) remains applicable to this owned-client/local-service UI experiment.

| Component | Code and contract |
| --- | --- |
| Service compatibility, session scope and replay | [Wire.cs](../../../src/Community.Protocol/Wire.cs), [LabRuntime.cs](../../../src/Community.Server/LabRuntime.cs), [protocol extension](../T-04.1/protocol.md) |
| Principal-only configuration and strict HTTP client | [service_client.py](../../../src/Community.AdapterLab/service_client.py) |
| Worker, cancellation and plain-text presentation | [bridge.py](../../../src/Community.AdapterLab/bridge.py) |
| Fresh native callback correlation and loader | [interaction.py](../../../src/Community.AdapterLab/interaction.py), [probe.py](../../../src/Community.AdapterLab/probe.py), [launch.py](../../../src/Community.AdapterLab/launch.py) |

Design context: [first game connection](../../ARCHITECTURE.md#3-first-game-connection-and-the-later-gameplay-slice), [transport](../../ARCHITECTURE.md#4-protocol-and-persistence), [client boundaries](../../ARCHITECTURE.md#5-client-and-resource-boundaries), [E-10](../../EXPERIMENTS.md#e-10--connect-one-real-player-to-their-own-server).
