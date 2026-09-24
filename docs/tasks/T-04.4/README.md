# T-04.4 — Persistent community progress

Scope: R-031–R-040 / E-10 persistence extension. Started 2026-09-23 at the user's request. [STEPS](../../STEPS.md) owns delivery status; [evidence](evidence-2026-09-23.md) separates software checks from attended game observations. [Sources](sources.md) records the storage selection and exact dependencies.

## Selected action and observable result

Submit `/community`, then `/community result` within 20 seconds. Each successful server `probe` increments the configured member's `progress` by one. Read it without mutation using `/community state`, then `/community result`. Close the game, restart the now-empty service, launch and attach again, and read the same value before performing another action. The next action must increase it exactly once. This count represents accepted community chat interactions, not salvage, native inventory, currency, or proof of a physical game action.

The adapter still uses the two native chat hooks and fresh-callback presentation established by [T-04.3](../T-04.3/README.md). Network work and storage remain outside native callbacks. Adapter version `0.3.0`, operation `native-chat-poll-v2`, and protocol version 2 are a coordinated upgrade; older clients are refused. The game fingerprint remains unchanged.

## Storage, identity and recovery contract

One local SQLite database lives at `<server-config-parent>/<dataDirectory>/community.sqlite3`. A process ownership lock prevents two services or maintenance commands from opening the same data directory concurrently. This is a single-process local-disk lab design, not a network filesystem or multi-writer deployment.

The database binds itself to one community and schema version. It stores a server-generated member UUID mapped to the configured lab principal ID, a stable interaction UUID, monotonic revision, progress, status/message, committed events and replay outcomes. Credentials and sessions are not persisted. Rotating a principal key preserves ownership; renaming a principal creates a distinct mapping. Removing a principal prevents login but does not delete its records. Native save IDs and display names never select an owner. Public account/entitlement verification is separate work.

State, event and successful request/response commit atomically before acknowledgement. A lost reply can be recovered from the snapshot, durable event history or an exact request replay. Within **24 hours of server commit time**, an exact replay returns its original response and a changed body under the same member/request ID is refused. Retention is longer than the adapter's 20-second work lifetime; it does not retry mutations automatically. Old replay records are pruned during startup and successful writes. After pruning, replaying the original body still fails its old expected revision, so it cannot increment progress again. Reusing an expired ID with a changed current revision is a new command, outside the replay guarantee; clients must generate fresh UUIDs for new actions.

Revisions never reset, including diagnostic `reset`; progress increments only for `probe`. Both have a maximum of `9007199254740991`. The old 256-action lifetime cap is removed. Events remain durable; `/events?after=N` returns at most 32 events and a page cursor in `revision`. Continue from that cursor until an empty page; use `/state` for the current snapshot. A snapshot may skip history intentionally when only current progress matters. Events are the durable delivery source; there is no background push dispatcher or exactly-once delivery claim.

When empty, progress idles. There are no timers, passive rewards or catch-up calculations. The service remains operable without a game process. Session tokens expire or disappear on service restart; a returning client authenticates again before reading its member's state.

## Setup, build and verify

Use the [.NET SDK and local setup](../T-04.1/README.md#setup-build-and-verify) and [isolated adapter environment](../T-04.2/README.md#setup-build-and-verify). The service adds the pinned SQLite packages in [packages.lock.json](../../../src/Community.Server/packages.lock.json); the Python dependencies and native hooks are unchanged.

From the repository root:

```powershell
dotnet restore CommunityPlatform.slnx --locked-mode
dotnet run --project tests/Community.Tests --configuration Release --no-restore
py -3.13 -W error::ResourceWarning -m unittest discover -s tests/Community.AdapterLab.Tests -v
```

The Python process tests require the Release server artifact built by the preceding command. CI uses the same service build/test and Python test entry points. Hosted execution is separate evidence.

Create new private configurations (both commands refuse existing destination files):

```powershell
dotnet src/Community.Server/bin/Release/net10.0/Community.Server.dll --init --config local/t04-4/server.json
py -3.13 src/Community.AdapterLab/service_client.py --server-config local/t04-4/server.json --principal alice --out local/t04-4/adapter.json
dotnet src/Community.Server/bin/Release/net10.0/Community.Server.dll --config local/t04-4/server.json
```

The first startup creates schema v1. Pre-persistence tasks have no database to migrate; historical process memory cannot be recovered. Configuration, databases, backups and receipts stay in ignored `local/` storage. The database contains no native saves or game files.

## Maintenance and restore

Stop the service before maintenance. Backup and restore refuse to overwrite existing destinations. Preserve the matching server configuration separately; it contains credentials that the database deliberately excludes.

```powershell
dotnet src/Community.Client/bin/Release/net10.0/Community.Client.dll --config local/t04-4/server.json --mode stop
dotnet src/Community.Server/bin/Release/net10.0/Community.Server.dll --backup local/t04-4/backups/checkpoint.sqlite3 --config local/t04-4/server.json
dotnet src/Community.Server/bin/Release/net10.0/Community.Server.dll --migrate --config local/t04-4/server.json
```

To restore, copy the matching private config into a **new** directory, for example `local/t04-4/restore/server.json`, with the same community/principal IDs and relative `dataDirectory`. Leave its data directory empty; restore refuses a destination holding a database or leftover journal file. Then run:

```powershell
dotnet src/Community.Server/bin/Release/net10.0/Community.Server.dll --restore local/t04-4/backups/checkpoint.sqlite3 --config local/t04-4/restore/server.json
dotnet src/Community.Server/bin/Release/net10.0/Community.Server.dll --config local/t04-4/restore/server.json
dotnet src/Community.Client/bin/Release/net10.0/Community.Client.dll --config local/t04-4/restore/server.json --mode state
```

Compare member, interaction, revision and progress against the backup checkpoint before redirecting clients. Restoring an older backup intentionally restores older progress and replay history: commands acknowledged after that backup are outside its recovery point. Do not replay post-backup commands as if this were current state. Keep the original database for investigation. Unsupported schemas, another community, corruption and failed validation stop startup/maintenance; they never silently reset progress. `--migrate` creates/validates v1 only; no prior persistent schema or automatic downgrade is supported.

Startup and maintenance run a full integrity check and verify every member's complete event history, and events are never pruned. Cost therefore grows with total history. This is acceptable for the lab; revisit validation and event retention before any long-lived hosted deployment.

## Attended E-10 persistence procedure

1. Close NMS, finish Steam synchronization and disable NMS-only Steam Cloud; preserve Cross-Save off. Follow the [disposable-save backup and recovery procedure](../T-04.2/README.md#lab-procedure-and-restoration), with fresh receipts under `local/t04-4`. Preserve older saves and settings references.
2. Start the server; launch through Steam and load `T-03.1 checkpoint A`. Disable Multiplayer in the native UI. Recheck the executable, settings, isolated dependencies and live signatures before attachment. Attach with a new run directory:

   ```powershell
   Get-Process NMS | Select-Object Id,Path
   .\local\t04-2\venv-native\Scripts\python.exe -u src/Community.AdapterLab/launch.py --pid <NMS-PID> --run-dir local/t04-4/run-001 --service-config local/t04-4/adapter.json
   ```

3. Submit `/community state`, then `/community result` promptly. Record the initial value. Submit `/community`, then `/community result`; record acknowledged progress, revision, member/interaction IDs, request/event IDs and a user-confirmed visible response. Read the state again; the read must not increment it.
4. Use `/community leave`, then exit NMS normally. Verify the game process is gone. Record the empty service state, stop it, take a database backup, and restart it with the same configuration/data. Read back unchanged state before relaunch. Record old-session rejection and exact replay of the acknowledged game request under a fresh correctly scoped session: it must return the original response/event and leave progress unchanged. The replay is a diagnostic check, not another game action.
5. Relaunch through Steam, load the disposable save and verify Multiplayer/Cross-Save off. Recheck the build and attach into `run-002`. Submit `/community state`, then `/community result`; the user must see the same acknowledged progress. Submit one new `/community` and retrieve its result; progress must advance once. Close/disable the adapter and exit normally.
6. Stop the service. Restart NMS without attachment, verify the disposable checkpoint/native chat, restore Multiplayer on, exit normally, restore NMS-only Steam Cloud on and finish sync. Compare old saves/settings to the fresh receipt. Restore disposable files only if necessary. Record failures and the difference between service/log evidence and actual observed game output.

## Implementation and boundaries

[Storage](../../../src/Community.Server/PersistentStore.cs), [runtime](../../../src/Community.Server/LabRuntime.cs), [server/maintenance entry point](../../../src/Community.Server/Program.cs), [wire contract](../T-04.1/protocol.md), [adapter HTTP client](../../../src/Community.AdapterLab/service_client.py), [worker](../../../src/Community.AdapterLab/bridge.py), [service checks](../../../tests/Community.Tests/Program.cs).

Design context: [persistence and member ownership](../../ARCHITECTURE.md#4-protocol-and-persistence), [E-10](../../EXPERIMENTS.md#e-10--connect-one-real-player-to-their-own-server). Real storage/reconnect evidence does not establish a secure economy, game-session admission, independent simulation, two-client state synchronization or automatic native presentation.
