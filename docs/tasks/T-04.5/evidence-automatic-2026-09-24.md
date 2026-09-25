# T-04.5 — Receiver validation and automatic interaction evidence

Started 2026-09-24 (local time; some artifact timestamps are 2026-09-25 UTC). This continues the [first observation pass](evidence-2026-09-24.md). [STEPS](../../STEPS.md) owns completion status; [the task contract](README.md#receiver-validation-and-selected-automatic-operation) defines the action and cancellation behavior.

## Environment and preparation

One owned Steam client, executable version `179666`, Steam build `25442159`, SHA-256 `B7913F268DFC62386B6B68F524BFC8ADE4A44A9F4FBAD39085B7BF51BE3680CB`. The same pinned Python/pyMHF environment and disposable `T-03.1 checkpoint A` are used. No new dependency was selected. Adapter compatibility is now `0.4.0` / `native-chat-and-cockpit-v2`; protocol version 2 and SQLite schema v1 are unchanged.

The user confirmed NMS closed, synchronization finished and NMS-only Steam Cloud disabled. A fresh ignored receipt at `local/t04-5/finish-20260924/snapshot-before-game/receipt-private.json` records eight verified copies: four disposable-save files and four settings references. Older-save hashes were recorded separately. Prior receipts were preserved. Initial Multiplayer was true, Cross-Save false and Cross-Save auto-upload true.

The first attempted read-only process check refused because Multiplayer still read true on disk; no attachment occurred. The user returned through mode select and reloaded. The settings then read Multiplayer=false and CrossSaves=false. Exact file and live preflight passed all six hook signatures and 12 receiver/state guard spans in PID `22624`. Private report: `finish-20260924/live-validation-preflight.json`.

## Software verification before attachment

- Locked .NET restore succeeded; the Release service passed all 44 integration checks. Private process evidence: `local/t04-4/tests-20260925-012226-539-b76109d6f4df4228b3dcf85ba1459887`.
- The adapter suite passed 119 tests before the new scheduler tests were added, including 22 fresh-state tests and the extended bridge lifecycle tests. Command: `py -3.13 -W error::ResourceWarning -m unittest discover -s tests/Community.AdapterLab.Tests -v`. Output: `finish-20260924/python-validation-tests.txt`.
- Exact file validation matched all 12 span hashes. Synthetic tests cover tampering, relocated module bases, invalid pointers, partial reads and state changes during sampling. This establishes refusal behavior, not native lifetime.
- Static review established the full 1023-byte message-copy requirement and the narrow system-message path; [source findings](sources.md#native-message-ownership-and-system-presentation) retain the limits. Independent review found no must-fix issue in the launcher, native reads, guard integration or buffer construction before scheduler integration.
- First principal-config provisioning refused the new T-04.5 directory. The allowed ignored task paths were extended, then provisioning succeeded; no credentials are in this record or Git.

## Attended result

### Read-only validation, passed

The combined suite passed **137 tests** before attachment, including 18 scheduler tests. Output: `finish-20260924/python-pre-attachment-tests.txt`. Independent review also verified the validation scheduler cannot reach a native presentation call with `bridge=None` / `present=None`.

`validation-001` attached to PID `22624`; pyMHF logged one mod and six hooks. Source hashes are recorded in that run directory. Application update ran on thread `13512`. Initial update samples were readable, `APPVIEW`, no pending transition and a valid owner. Player update was again observed separately, on thread `27132`, outside application-update nesting.

The user confirmed `/community` showed the normal ready message, one ship entry/exit worked, and pause/unpause plus focus loss/return worked normally. Natural Say matched the freshly derived receiver on thread `13512`, at update depth 1. The cockpit sample had the same thread/nesting and all valid state flags. No automatic native call or service request was possible in this profile. `APPVIEW` remained classified as playable across these tested pause/focus actions; it does not distinguish them.

The user then confirmed mode-select/reload, a second ready message, a second landed-ship entry/exit, `/community off` and normal exit to desktop. The three FSM observations were on thread `13512` within the outer update; the recorded ownership classification matched the fixed application singleton. Update samples changed from playable/no pending to nonplayable with pending work, to nonplayable/no pending, then back to playable/no pending on reload. No receiver mismatch, read failure or owner-invalid record occurred. Repeated equal classifications are deduplicated, so this is not a per-frame trace of every pointer comparison.

Disable totals: 9,468 application updates, 2,644 player updates, two cockpit entries, three FSM transitions and three natural Say callbacks; zero dropped diagnostics. The game process and port 6770 were absent after exit, and no NMS Application Error 1000 was found for the run window. All 11 recorded Python source hashes remained unchanged through exit (`validation-001/source-unchanged.json`). The user supplied the visible-result evidence; logs separately establish scheduling and guard behavior.

### Automatic profile

Before this pass, controller review added guards against continuing after diagnostic failure/reentrant invalidation, repeated calibration logging, fixed-code bridge error containment and explicit submission-event naming. The full suite then passed **145 tests**, including 25 controller tests and an opt-in arm-command correlation check. Output: `finish-20260924/python-pre-automatic-tests.txt`. The shared service was already rebuilt and its 44 checks passed; no server source/dependency changed afterward.

The fresh service baseline is revision 0/progress 0, community `local-lab`, principal `alice`, member `456289f9-dff0-4e92-9d1d-3313b9b7a869`, interaction `90991b77-3c94-4a7a-a982-04537f484528`. The private server configuration selects `T-04.5 ship entry recorded by your local server.` as the response message. This text is operator configuration, not server verification of native gameplay.

The user relaunched through Steam and confirmed checkpoint A, Multiplayer off and the landed-ship starting position. Live guards passed in PID `15132`. Attachment uses `--auto-world --delivery-delay 5`, the private principal-only adapter configuration and fresh run directory `finish-20260924/automatic-001`.

The user confirmed the initial state reply appeared automatically at progress 0 without `/community result`. Three subsequent armed, deliberate landed-ship entries each produced the configured message automatically, with progress 1, 2 and 3 and normal cockpit behavior. The user explicitly noted that arming was needed each time; this is the selected one-use lab action contract.

| Input | Request ID | Revision / progress | Reply delay after worker response |
| --- | --- | --- | --- |
| State query | `f6817c6c-fca3-4d47-9e21-4e1fcb372de6` | 0 / 0 | 5.009 s |
| Armed ship entry 1 | `28724ef9-5803-4617-a386-97e67908f061` | 1 / 1 | 5.011 s |
| Armed ship entry 2 | `fa8011bc-24e1-4852-b176-2eecd672074e` | 2 / 2 | 5.013 s |
| Armed ship entry 3 | `c608bec1-7aaf-4572-84e0-904c4b5989ba` | 3 / 3 | 5.002 s |

Requests and native submissions ran on application-update thread `2056`; service responses ran on worker thread `27124`. Each entry also queued an immediate owned connecting notice for a following update. These notices are distinct from the final server reply. The injected native-call wrapper and scheduler record submission, and user confirmation establishes visible output.

The user then queued a state read and immediately submitted `/community leave`. Request `6b035beb-f716-4f74-a004-c463bdab7159` was cancelled before presentation; the user confirmed the disconnect message and no delayed progress reply after eight seconds. This tested cancellation of a queued state result, not rollback of a mutation.

An unarmed entry produced no mutation; state request `e03930b4-f6c5-49ef-8283-ee3e853502a9` returned 3/3. The next armed entry, request `5df6f9fe-9861-41f0-aa10-db035946e6c4`, returned 4/4. Both replies were confirmed visible. Although this prompt also requested mode select/reload, the log contained no FSM transition or nonplayable sample, so this portion was not accepted as automatic-mode menu evidence.

The service was stopped gracefully. State request `9f800b5a-a6e5-458d-b985-9c8628203656` failed with the fixed `unavailable` code, and the user confirmed the delayed automatic failure message and responsive gameplay. The service restarted against the same database.

The user then explicitly returned to the save-selection screen and paused there. This time the log captured a pending transition, an application-owned FSM transition and a nonplayable update sample; the controller invalidated its work/calibration. No automatic native submission occurred in the nonplayable interval.

After the explicit menu reload, natural chat recalibrated the receiver. State request `2a684db5-cad7-484c-947c-75d57260b31a` recovered revision/progress 4/4 under generation 8. Armed entry request `13c29c14-7455-47af-a087-06f75332fce8` advanced to 5/5. The user confirmed both automatic replies after the menu cycle and service restart. Member and interaction IDs remained unchanged.

For disable cancellation, state request `e95520a4-803b-476f-b3a1-09451f40ee9c` returned 5/5 to the worker, then `/community off` advanced the bridge to disabled generation 9 before its presentation deadline. The request has no presentation record. The user confirmed the disabled message, no delayed reply after eight seconds, another normal ship entry/exit and normal game exit. The latter entry occurred after observation was disabled and is user evidence only.

At disable, counters recorded 27,846 application updates, 11,061 player updates, seven cockpit entries, three FSM transitions and 28 Say calls, including automatic calls. Five armed entries issued exactly five successful probe requests; unarmed entries did not mutate progress. Independent log review found 14 automatic native submissions: five connecting notices and nine server outcomes (five probe results, three successful state reads and one expected unavailable error). All submissions used thread `2056`; service responses/failure used worker `27124`. Leave/off requests were not presented; no duplicates, native-call failures or dropped diagnostics were recorded.

Final diagnostic state was revision/progress 5/5 with the same member/interaction identity. Authenticated service shutdown succeeded. At `2026-09-25T01:49:28.9407147Z`, the attached process and both lab ports were absent; no NMS Application Error 1000 was found in the phase window. All 11 Python source hashes matched the attachment receipt through exit. No launcher/service helper process remained. Private checks are in `automatic-001/exit-check.json` and `source-unchanged.json`.

## Recovery, result and limits

The user confirmed an unmodified Steam launch, normal checkpoint gameplay and ordinary `/community` behavior, Multiplayer restored to Enabled, normal exit, and NMS-only Steam Cloud re-enabled with synchronization complete. The final receipt at `local/t04-5/finish-20260924/final-restoration.json`, timestamp `2026-09-25T01:50:30.9387574Z`, records:

- All four older-save files and all four settings files byte-identical to this phase's fresh backup.
- Multiplayer=true, CrossSaves=false and CrossSavesAutoUploads=true, matching the initial controls.
- Unchanged executable, no MODS directories, NMS closed, both lab listeners absent and no NMS Application Error 1000 in the phase window.

No backup restoration was needed. Ordinary changes to the disposable checkpoint and the separate community database were preserved. The first observation pass's retained catalogue history is already part of this phase's fresh baseline; this does not retroactively claim byte equality against the earlier phase's settings.

**T-04.5 is complete within the selected one-client, exact-build lab scope.** Five deliberately armed cockpit entries produced five persistent community increments and user-confirmed automatic server replies. Leave/disable cancelled queued state results; explicit menu/reload, service failure/restart, normal exit and unmodified recovery passed. The final independent log audit covers 554 events across 729.875 seconds of active observation, reports no issues, and measures outcome-to-submission delays of 5.002–5.019 seconds. `automatic-001/run-summary.json` holds the private audit; the events file SHA-256 is `FBFB237403F0FD3C252A2B75DEBF54A7C6075447A1431F8AECBA9C13609CEEE9`. User confirmations supply visible delivery and the post-disable wait; the event log itself ends at disable.

Verification: 44 service checks and 145 adapter tests passed; independent native/code/log reviews found no must-fix issue. Final repository verification passed for 33 Markdown files, 328 relative links, 98 anchor links, balanced fences and all 140 stable roadmap IDs. Git whitespace checks covered tracked changes and all nine new files through explicit no-index comparisons; no failures were found. Private report: `finish-20260924/repository-checks.json`. Verification is local; no push or hosted CI result is claimed.

Limits: this is cooperative client reporting, not proof of native gameplay or an enforced economy. Arming permits one entry for 60 seconds; no persistent activity subscription is claimed. Request/result lifetime remains 20 seconds, and the five-second delay is an optional lab setting. Native submission can be dropped by the game's queue, so only attended results establish the visible replies recorded here. Fresh reads do not make native lifetime atomic across arbitrary threads. `APPVIEW` does not identify pause/focus, and only the read-only profile exercised those states deliberately. Prolonged stability, frame overhead, travel, live unload, broader E-03/R-015–R-020 acceptance, two-client synchronization, native multiplayer admission, crossplay, independent simulation and distribution remain unverified. The parent T-04 and M-04 remain incomplete.

## Automatic-run source receipt

SHA-256 values recorded before attachment and unchanged through normal exit; dependency pins and the executable fingerprint are recorded above.

| Adapter source | SHA-256 |
| --- | --- |
| `bridge.py` | `B0B296A144B913B29DB7DCE48ADCCF06E80B2E1F640D2DE827EEFE49289F871A` |
| `injection.py` | `01ECE032E9F8E03AFB2FC4F72A4C3FC62A0C1C25A9BEACC08256AA6DEDA730DC` |
| `interaction.py` | `E1523CE1568722EDDB60B5A54B6440230CFD5EECC68A3FA8F191600885D8C07C` |
| `launch.py` | `25FDD221786CD2708A0AA8B49191B138B34BAE00A0B14163213AA2D08F82A2D7` |
| `native_state.py` | `10242207E8EE5F73EBFF670784F8B007B450B3CF0458FC23A4E9E5927DCC7A83` |
| `preflight.py` | `27065A1C2C76E0848F03B8674750D0E8FFBC9644C913B3F4367C5E065AFBF4E7` |
| `probe.py` | `1C093F79F6FFD2E71AB055D52E628E622B28D12B31EA1F1678C0F3821D052785` |
| `runtime_guard.py` | `1CDFF2045BAF351520044B2647566C8A8FF47D7B355F78714B1CE8C4AECABA82` |
| `service_client.py` | `FF511A3B006728ABE6661A075B8BE08AA50EF4EE4EF37004ECA63AB70E22202A` |
| `world_observation.py` | `98463D1BDDA613F54E639A668AF6D30DA5E119CA6F50079DABEF5AECACBDE684` |
| `world_runtime.py` | `E835EA48398A54A10132829CDDBE448EE71F5CE54737B1C14000F3505EDD4E7A` |
