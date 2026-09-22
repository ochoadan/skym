# T-03.1 — Owned installation and repeatable baseline

Type: task plan and E-01a procedure. Roadmap: R-011. Prepared: 2026-09-21. [STEPS](../../STEPS.md) owns delivery status.

[Task index](../README.md) · [Source review](sources.md) · [Run evidence](evidence-2026-09-21.md)

Architecture context: [client and recovery boundaries](../../ARCHITECTURE.md#5-client-and-resource-boundaries), [build compatibility](../../ARCHITECTURE.md#8-updates-operations-and-launch). This step adds no product code; [local lab helper paths and commands](evidence-2026-09-21.md#local-artifacts-and-commands) are recorded with the run.

## Purpose and authorized scope

Establish a known game installation, a repeatable native interaction, and a demonstrated way to restore the declared lab setup. This supports the [product's](../../PRODUCT.md) game-compatibility and recovery requirements. It establishes only the tested native baseline.

The user first authorized preparation and read-only metadata inspection, then authorized executing this plan after moving the detailed preparation out of STEPS. Execution is limited to T-03.1 / R-011 and E-01a. Work on another step requires an explicit user instruction. Mod installation, adapter selection, hook experiments, service implementation, and multiplayer experiments are outside this step.

Preparation itself changed no game files, saves, settings, cloud options, or running processes. The user's already-running game and the metadata below are not an E-01a result.

## User choices and working defaults

The user has no stated tooling or time constraints and no preferred success criteria or native action. The proposed action is entering and exiting the player's own ordinary landed starship, observing its native behavior and the declared saved state after reload. This does not select an adapter operation.

The user requested both a complete checklist and guidance through individual in-game actions, using judgment about how much guidance is needed. Use E-01a as the complete checklist and guide the user through its interactive checkpoints. An explicitly disposable existing save can be used if it fits the starting conditions; otherwise create a labelled Creative-mode lab save. The proposed final state retains that labelled checkpoint for repeat runs, with backups in ignored local storage.

## Initial setup and evidence limits

Recorded during preparation on 2026-09-21. These are initial observations to recheck during execution. Local readings identify files and processes; user statements identify their intended use. Neither establishes an unmodified executable against a publisher reference or game compatibility with an adapter.

| Item | Initial record | Basis |
| --- | --- | --- |
| Availability and storefront | Owned Steam installation, already running on this PC | User report; `Get-Process` found `NMS` |
| Existing content and saves | Raw/unmodified, no custom launch options, nothing requiring save preservation | User report; mod inventory and save/cloud state were not inspected during preparation |
| Game screen and input | Main menu/save selection; ordinary monitor, keyboard and mouse | User report; no disposable lab save was selected or created by preparation |
| Cloud and cross-device state | User uses this NMS account only on this PC and expects sync to be enabled because no contrary notification appeared; individual settings were unconfirmed | User report, not a settings observation; check Steam Cloud and NMS Cross-Save separately during preflight |
| Install root | `D:\SteamLibrary\steamapps\common\No Man's Sky` | Running process executable path |
| Executable | `Binaries\NMS.exe`; 88,480,328 bytes; file/product version `179666` | File metadata; this version was not mapped to a public patch label |
| Executable SHA-256 | `B7913F268DFC62386B6B68F524BFC8ADE4A44A9F4FBAD39085B7BF51BE3680CB` | `Get-FileHash -Algorithm SHA256` |
| Steam installation | AppID `275850`; build ID `25442159` | Selected fields from `appmanifest_275850.acf`; account fields were not printed |
| Build branch | Unconfirmed; no `BetaKey` appeared in the selected manifest fields | Confirm the Steam branch before the experiment; absence of this field does not establish a branch |
| OS and memory | Windows 10 Pro, 64-bit, build `19045`; 95.77 GiB RAM reported | `Get-CimInstance` |
| CPU and graphics | i9-12900K; RTX 3080 and Intel UHD Graphics 770 reported | `Get-CimInstance`; active renderer and game settings were unconfirmed |

The publisher release label is source context in [the source review](sources.md#release-context). Do not assign it to the installed binary from the release date alone. Recheck the installed build/hash at the beginning and end of the actual baseline.

## E-01a procedure and acceptance

This is the E-01a procedure for T-03.1 / R-011. The criteria below define the check; observed results are in the [run evidence](evidence-2026-09-21.md).

The proposed action is to enter and exit the player's own ordinary landed starship. Start on foot nearby; record the interaction prompt, transition into the cockpit, return to on-foot control, and save feedback. The historical saving documentation supporting this candidate is in [the dated source review](sources.md#native-procedure-sources); the actual build must be observed. Choosing this native baseline action does not select an adapter route or promise that a future integration can intercept it.

1. **Identify the environment.** Record storefront, install path, branch, build ID, executable file version and SHA-256, date, OS, CPU/GPU/RAM, display/input mode, and relevant launch/mod settings. Distinguish user-reported absence of modifications from inspected content. Record the in-game version label if exposed without extra tooling. Preserve the configuration used for each run.
2. **Define the disposable setup and restoration boundary.** Identify a suitable disposable save or create a labelled lab save; Creative mode is the proposed default if a new save is needed. Record mode/difficulty, save selection, relevant local paths, and exactly which settings/files the lab may change. Record Steam Cloud, NMS Cross-Save, and other-device use separately. Establish a sequence for backup and restoration that accounts for the observed sync settings; do not infer isolation from a save slot or multiplayer toggle. No personal-save preservation need should be invented when the user reports none, but the test checkpoint and settings still need a restoration record.
3. **Create the reference checkpoint.** Reach the starting condition using ordinary gameplay and record a recognizable saved state A, the exact save slot/type and load operation, and its expected reload behavior. A native save label such as `T-03.1 checkpoint A` is a proposed marker if supported on this build. Close the game normally. Capture the declared lab files, including the metadata needed for that marker, into ignored local storage only after the relevant writes/sync have settled; verify the backup manifest and hashes. List files whose routine changes are expected, such as logs or timestamps. A backup's existence alone does not prove recovery. Record exact source/destination paths before later restoration.
4. **Run three complete cycles.** Launch through the recorded storefront flow, load the specified save, enter/exit the ship, observe the declared result and save feedback, exit the game process normally, relaunch, and check the saved state. Each cycle includes a full process restart. Record every attempt, prompts, save/reload results, launch/load durations, and failures. Three successful cycles on matching conditions are the proposed repeatability criterion; an earlier failure remains in the evidence even if a documented correction succeeds later.
5. **Keep conditions comparable.** Record scene, resolution, graphics preset and relevant overrides, upscaling, frame cap, input/display mode, background tools, and visible stutter. Note any available frame-time observations and their collection method. No minimum FPS, two-hour run, load test, or new profiler is required for this baseline. Recheck build ID/hash after the cycles; if the build or relevant configuration changes, retain the observations and establish a new comparable set. Do not assume the retail build can be rolled back.
6. **Demonstrate restoration.** First make a harmless, recognizable change to the disposable state through the native UI, such as changing its label to `T-03.1 checkpoint B`, and verify B survives a reload of the same slot/type. Record the difference from backed-up state A; repeating an unchanged visible state would not demonstrate recovery. Recheck the build/hash before restoration; a changed build requires a new compatible baseline plan. With the game closed and the documented sync sequence followed, restore A and any deliberately changed lab settings. Check the restored files against their recorded hashes before launching, then use the recorded load operation and verify A has returned in place of B. Confirm the game fingerprint still matches after this final run. Compare immutable inputs separately from files expected to change during a normal launch. Record the final cloud/settings state and whether the labelled lab save is retained. If a sync conflict or uncertain replacement target appears, preserve the available versions and leave restoration unresolved until a specific recovery action is defined; do not guess which copy to overwrite.
7. **Record the result.** Write a sanitized E-01a report using the [shared evidence format](../../EXPERIMENTS.md#lab-prerequisites-and-evidence), including repetitions, exact manual actions/commands, limitations, failures, and restoration observations. Adapter/resource fields are `not used` for this native baseline. Keep saves, account identifiers, binaries, backups, and raw captures in ignored local storage; create no completed-run report before a real run exists.

**Acceptance:** The report identifies the exact tested build and configuration; another run can follow its instructions; three complete action/reload cycles reproduce the declared visible and saved results; and a separate restoration check recovers the declared checkpoint/settings and loads successfully. Unresolved failures affecting these criteria prevent a passing result; corrected failures remain in the report with their correction and retest evidence. Known unrelated native quirks can be documented without expanding this step into fixing the game. The result establishes the tested local baseline and recovery boundary only; cloud isolation, reversible mod installation, adapter behavior, and multiplayer require their own evidence.

## Preparation record — 2026-09-21

Read-only commands used for the initial installation record (PowerShell):

```powershell
Get-Process -Name NMS -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, Path, StartTime | Format-List
$baselineExePath = Get-Process -Name NMS -ErrorAction Stop | Select-Object -First 1 -ExpandProperty Path
$baselineExeFile = Get-Item -LiteralPath $baselineExePath
$baselineInstallRoot = [System.IO.Path]::GetDirectoryName([System.IO.Path]::GetDirectoryName($baselineExePath))
$baselineSteamAppsPath = [System.IO.Path]::GetDirectoryName([System.IO.Path]::GetDirectoryName($baselineInstallRoot))
$baselineManifestPath = Join-Path $baselineSteamAppsPath 'appmanifest_275850.acf'
Get-FileHash -LiteralPath $baselineExePath -Algorithm SHA256 | Format-List Algorithm, Hash
rg -n '^\s*"(appid|buildid|installdir|StateFlags|LastUpdated|BetaKey)"' -- $baselineManifestPath
```

Hardware queries used `Get-CimInstance Win32_OperatingSystem`, `Get-CimInstance Win32_ComputerSystem`, `Get-CimInstance Win32_Processor`, and `Get-CimInstance Win32_VideoController`. Only OS/build, RAM, CPU/core counts, GPU names, and driver versions were displayed. These checks succeeded; they do not test launch/load, frame times, save integrity, or restoration.

The preparation expanded E-01a's proposed action/repeat/recovery criteria and refreshed only its baseline sources in RESEARCH. Independent review corrections were incorporated. At that preparation checkpoint, `git diff --check` passed and PowerShell Markdown validation checked 11 files, 48 relative links, five anchors, balanced fences, 140 roadmap IDs, five queue tasks, and ten experiment IDs. Forty-seven relative targets and all five anchors resolved. One pre-existing README link to `../../../Desktop/Agent%20Project%20Playbook.md` had no target; the same link exists in `HEAD`, and its repair remains outside this step.

`git check-ignore --no-index -- local/t03-1/save-backups/probe.dat artifacts/t03-1/probe.txt` confirmed both proposed raw-artifact paths are ignored. Scope verification compared the other four queued task blocks and E-01b onward with `HEAD`; all were unchanged. `git diff --exit-code -- docs/ROADMAP.md` also passed. Preparation changed only EXPERIMENTS, PRODUCT, RESEARCH, and STEPS. No E-01a run, backup, restoration, game modification, application test, or other-step implementation occurred during that preparation. Subsequent observations and verification are in the run evidence; STEPS links the delivery result.
