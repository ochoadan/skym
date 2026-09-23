# T-04.1 — First standalone community server

Scope: R-001–R-010 / M-01. The user requested the next step on 2026-09-22 and selected C#/.NET. [STEPS](../../STEPS.md) owns completion status; this file owns the implementation and verification procedure. [Observed evidence](evidence-2026-09-23.md) records the completed runs and their limits.

## Observable result

An operator starts a separate local process. A synthetic client connects as a configured lab principal, accepts and completes an original salvage contract, and receives the server's configured message. Editing that message and restarting changes the returned result. The client can query state/events, reconnect, deliberately send malformed or duplicate input, and request an authenticated graceful stop.

This is the service component of [M-01](../../ROADMAP.md#milestones). It uses no NMS files or game APIs. The in-game interaction remains T-04.2/T-04.3; persistence remains T-04.4. No reward amount or official currency is implemented.

## Tooling decision — R-001

Selected C# 14 / .NET 10, framework-dependent. [global.json](../../../global.json) requires any stable .NET 10 SDK (`10.0.100` or later, `rollForward: latestFeature`); the apps target `net10.0` and use the default runtime roll-forward, so they run on the latest installed .NET 10 patch. Exact pins were dropped on 2026-09-23 because they broke builds on every monthly patch and would have held operators' servers on an unpatched runtime. Evidence records the SDK/runtime actually used for each run.

| Option considered | Fit for this increment |
| --- | --- |
| C#/.NET, selected by user | Typed service contract, built-in HTTP server/JSON tooling, Windows development tools already present, transport independent of a future adapter language |
| TypeScript/Node.js | Installed and viable for HTTP services; would add a TypeScript build dependency if selected |
| Rust | Installed and viable; native control is not required by this service-only increment, so its ownership/tooling costs do not yet buy a needed game capability |

This is an engineering choice for the service, not a selection of a C# NMS hook. SDK/runtime and GitHub action commits, licenses, notices and reviewed primary sources are in [sources](sources.md). There are **no external application NuGet packages**. [NuGet.Config](../../../NuGet.Config) clears package sources; the SDK supplies the framework reference packs. The test executable uses the standard library, actual child processes and HTTP/TCP assertions; it is run by the command below, not discovered by `dotnet test`.

## Setup, build and verify

Install any stable **.NET 10 SDK** from [Microsoft's .NET 10 downloads](https://dotnet.microsoft.com/en-us/download/dotnet/10.0); it includes the required runtimes. From the repository root:

```powershell
dotnet --version
dotnet run --project tests/Community.Tests --configuration Release
```

The version command must report 10.0.100 or later. `dotnet run` builds the test project and its server/client references, then runs all process-level checks; build or assertion failures return nonzero. For a build without execution, use `dotnet build CommunityPlatform.slnx --configuration Release`. No custom build/run script or C# command wrapper is needed. Other operating systems have not been exercised.

After building, create the lab configuration through the server itself:

```powershell
dotnet src/Community.Server/bin/Release/net10.0/Community.Server.dll --init --config local/lab/server.json
```

Initialization generates distinct random operator/principal keys from the embedded [example](../../../config/server.example.json), creates parent directories, writes the configuration, and exits without listening. It refuses an existing file with exit 2 and preserves its bytes; skip initialization if you already have the configuration. The defaults are embedded in the binary, so initialization does not depend on the current working directory. The example's blank keys intentionally fail ordinary startup validation. Never commit a populated configuration. Generated test configurations and process logs stay under ignored `local/t04-1/`.

## Operate the demonstration

Start the server in one terminal:

```powershell
dotnet src/Community.Server/bin/Release/net10.0/Community.Server.dll --config local/lab/server.json
```

Use a second terminal in the repository root:

```powershell
dotnet src/Community.Client/bin/Release/net10.0/Community.Client.dll --config local/lab/server.json --mode demo
dotnet src/Community.Client/bin/Release/net10.0/Community.Client.dll --config local/lab/server.json --mode duplicate
dotnet src/Community.Client/bin/Release/net10.0/Community.Client.dll --config local/lab/server.json --mode malformed
dotnet src/Community.Client/bin/Release/net10.0/Community.Client.dll --config local/lab/server.json --mode stop
```

The server prints JSON diagnostics to stdout. `demo` completes the selected principal's contract; another invocation resets a completed contract before accepting/completing it again. `duplicate` executes the next legal transition twice with the same request ID and verifies identical replies. `malformed` expects a 400 error and succeeds only if the server rejects the body. Other modes are `health`, `state` and `events`; add `--principal bob` to use the second identity (default: `alice`). Each ordinary client invocation authenticates and explicitly closes its session. The diagnostic client reads the private operator configuration for convenience; this is not the future player/adapter credential-distribution mechanism.

With the server stopped, edit **only `completionMessage`** in `local/lab/server.json`, restart, and rerun `demo`. The returned completed state must contain the new message. Configuration reload is restart-based. Ctrl+C uses the host's normal shutdown; `stop` uses the operator key and is the reproducible automated shutdown path. The service does not keep running after the demonstration tests finish.

Configuration controls the community ID, numeric loopback bind (`127.0.0.1` only), port (1024–65535), message (1–512 characters), session lifetime (1–3600 seconds), operator key and 1–8 lab principals. IDs use lowercase letters/digits/hyphens, maximum 48 characters. Keys must be distinct printable strings of 32–128 characters; initialization generates 256-bit random values. `dataDirectory` is a child path relative to the configuration; it is created as a reserved location and contains no durable state in this increment. Keep the configuration under ignored local storage.

Startup returns exit 2 for invalid config or an unavailable port without printing secrets; verify the config against the example, ensure keys were initialized, check port conflicts, and confirm `dotnet --version` reports a .NET 10 SDK. The client returns exit 1 for connection/protocol failures. Run `health` to check availability. A stopped service produces a diagnostic failure; it does not fabricate a successful interaction.

## Implementation and boundaries

| Responsibility | Entry point |
| --- | --- |
| Wire records and strict JSON parsing | [Community.Protocol](../../../src/Community.Protocol/Wire.cs), [protocol reference](protocol.md) |
| Configuration initialization and validation | [Configuration.cs](../../../src/Community.Server/Configuration.cs) |
| In-memory sessions, interaction state and replay cache | [LabRuntime.cs](../../../src/Community.Server/LabRuntime.cs) |
| HTTP host, bounds, logs and shutdown | [Server Program.cs](../../../src/Community.Server/Program.cs) |
| Synthetic diagnostic client | [Client Program.cs](../../../src/Community.Client/Program.cs) |
| Process-level verification | [Community.Tests](../../../tests/Community.Tests/Program.cs) |
| GitHub build/test workflow | [verify.yml](../../../.github/workflows/verify.yml) |

HTTP/1.1 JSON is selected for these low-frequency commands. Event notifications are retrieved through a revision-based polling endpoint; no WebSocket or movement-replication transport is selected. The scoped bearer session supplies the actor; client-supplied actor/reward fields are rejected. The server owns each principal's original contract ID, transition rules and completion message. This proves authority over synthetic service records only.

State, sessions, deduplication and events are memory-only. A same-principal reconnect within the process recovers state. A restart invalidates sessions and creates new interaction IDs at revision 0. At 256 successful transitions per principal the service refuses new changes until restart, retaining all successful request IDs and events instead of silently evicting replay protection. This is a bounded lab implementation, not a durable ledger. Time does not advance contracts while nobody is connected.

The local transport enforces numeric Host matching, rejects browser-origin/fetch metadata, limits bodies/headers/connections and request rate, and does not expose remote binding through web-host environment variables. Local keys authenticate cooperative lab callers; possession is not NMS entitlement, game-action evidence or an anti-cheat root. Administrator access to the config grants shutdown and lab impersonation by design.

Relevant design: [authority](../../ARCHITECTURE.md#2-authority-contract), [transport and persistence](../../ARCHITECTURE.md#4-protocol-and-persistence), [game boundaries](../../ARCHITECTURE.md#5-client-and-resource-boundaries). Game procedures remain [E-03](../../EXPERIMENTS.md#e-03--prove-minimal-runtime-access-on-the-target-build) and [E-10](../../EXPERIMENTS.md#e-10--connect-one-real-player-to-their-own-server). This task does not run either experiment.

## Verification procedure — R-002–R-010

The executable suite exercises configuration initialization, usable generated credentials and preservation of existing files, then a real server over loopback: configured health and version; two principals; credentials, community and expiry checks; transitions and revision conflicts; exact replay and altered-ID rejection; concurrent attempts; snapshot/event recovery; malformed/oversized/incomplete input; origin/Host and startup binding defenses; log redaction; diagnostic client behavior; graceful shutdown and same-port restart with a changed message and empty memory.

The [workflow](../../../.github/workflows/verify.yml) runs the same `dotnet run --project tests/Community.Tests --configuration Release` command on a Windows GitHub runner with exact action commits and read-only repository permissions. Whether GitHub executed it is recorded separately from local test results.
