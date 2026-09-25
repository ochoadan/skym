# T-04.5 — Candidate source review

Reviewed **2026-09-24**. Source inspection and read-only executable checks are distinct from game observations in [evidence](evidence-2026-09-24.md).

## Selected sources and licenses

NMS.py remains pinned at `b41bf9e6fdff1c833b77d805bb0c8da555c4ced4`; the local checkout is clean and remote HEAD matched on review. Its [types](https://github.com/monkeyman192/NMS.py/blob/b41bf9e6fdff1c833b77d805bb0c8da555c4ced4/nmspy/data/types.py) supply the declarations below. The exact-revision [MIT license](https://raw.githubusercontent.com/monkeyman192/NMS.py/b41bf9e6fdff1c833b77d805bb0c8da555c4ced4/LICENSE) was rechecked; the existing [adapter notice](../../../src/Community.AdapterLab/THIRD-PARTY-NOTICES.md) is retained and extended to the observation module. NMS.py is still a source reference, not an installed runtime.

pyMHF remains the selected 0.2.4 wheel/source tag commit `0c8ebc1c29074c5bc35207e0aff36d4035e20bac`. Its [MIT license](https://raw.githubusercontent.com/monkeyman192/pyMHF/0c8ebc1c29074c5bc35207e0aff36d4035e20bac/LICENSE) was rechecked. Its [manual hook implementation](https://github.com/monkeyman192/pyMHF/blob/0c8ebc1c29074c5bc35207e0aff36d4035e20bac/pymhf/core/hooking.py) combines before/after detours sharing a name and function offset. No package, version or binary is added. Exact runtime dependency artifacts and notice obligations remain in [T-04.2](../T-04.2/sources.md#selected-dependency-artifacts-and-licenses).

## Maintainer declarations and selection

| Candidate | Declared interface | Decision |
| --- | --- | --- |
| `cGcApplication.Update` | `void(this*)` | Observe callback nesting/thread; no game object fields read |
| `cGcPlayer.Update` | `void(this*, float)` | Observe scheduling relative to application update |
| `cGcPlayer.OnEnteredCockpit` | `void(this*)` | Selected narrow non-chat candidate: native landed-ship entry |
| `cTkFSM.StateChange` | `void(this*, uint64, uint64, bool)` | Observe transition counts only; no pointer-to-string inference |
| `cTkFSMState.StateChange` | `void(this*, fixedchar16*, void*, bool)` | Rejected by current function-entry gate |
| `cGcSimpleInteractionComponent.DoAction` | `void(this*)` | Rejected by current function-entry gate |
| `cGcTextChatManager.Say` | `void(this*, fixedchar1023*, bool)` | Retain synchronous hook; investigate the exact-build fresh receiver below, with subsequent native evidence linked separately |
| `cGcPlayerNotifications.AddTimedMessage` | Ten parameters including two marked unknown | Exclude direct calls; upstream explicitly warns about changed arguments |

These are declarations, not verified ABIs for the installed build. Source offers broader interaction hooks, but cockpit entry needs no unknown extra argument or component dereference. Constructor/Say declarations alone do not prove chat-manager lifetime. No fresh accessor is declared in this inspected source.

The upstream [singleton module](https://github.com/monkeyman192/NMS.py/blob/b41bf9e6fdff1c833b77d805bb0c8da555c4ced4/nmspy/_internal_mods/singletons.py) forwards application updates to custom callbacks. It caches the first parent-FSM receiver, and its `game_loaded` flag is set at mode selection without being reset. The [decorator](https://github.com/monkeyman192/NMS.py/blob/b41bf9e6fdff1c833b77d805bb0c8da555c4ced4/nmspy/decorators.py) calls that state fully booted, not save loaded. These mechanisms are not imported. The [state enum](https://github.com/monkeyman192/NMS.py/blob/b41bf9e6fdff1c833b77d805bb0c8da555c4ced4/nmspy/data/enums/internal_enums.py) supplies names, but neither names nor generic transitions prove application ownership.

## Engineering findings and remaining dependency

All eleven reviewed patterns had one match in the installed executable. Two failed the required runtime-function-entry/prefix check; rejection does not prove the functions absent or unusable under a separately validated method. The four selected additional hooks pass that gate together with the two existing chat hooks. [Evidence](evidence-2026-09-24.md) records counts, RVAs and exact fingerprint.

Inference: an update callback could schedule delayed presentation, but it cannot by itself establish receiver lifetime. Read-only investigation of the owned executable subsequently identified the candidate below. Retaining the last chat pointer or assuming old application-field offsets is not selected. Native observations come before connecting cockpit callbacks to persistent progress: entry can potentially occur during load, and an event is a cooperative report rather than gameplay authority.

## Local static receiver investigation

**Observed instruction relationships, with inferred semantics; not a native-call result.** The analysis used the already installed pefile/iced-x86 tools against the exact allowed executable and rechecked its SHA-256. Private scripts, disassembly and decoded tables remain under ignored `local/t04-5/receiver-research`; they are not Git content. `findings.md` has SHA-256 `6E94316BBF2F5647ED145B0DA0B6EDCDE98651B176654BF974F9C9A1A2F36D2A`; `artifact-hashes.json` records 40 private analysis artifacts.

The ordinary chat path at RVA `0xB14284` and the system-message branch at `0xB151A3` compute a receiver from the current owner global before calling the selected `Say`. Constructor/reset callsites agree with that receiver offset. The candidate is specific to this executable:

| Value | Candidate derivation relative to the **actual loaded module base** |
| --- | --- |
| Application singleton | RVA `0x6E7AAB0` |
| Current owner pointer | Read pointer at RVA `0x6E7AAE8` (singleton + `0x38`) |
| Chat receiver | Current owner + `0x932AB0` |
| Current state pointer | Read pointer at RVA `0x6E7AAC0` |
| Expected `APPVIEW` state object | Module base + RVA `0x6E7C520` |
| Pending transition | 16 bytes at RVA `0x6E7AAC8`; native queue/updater use all-zero as no pending transition |

The enclosing main routine calls initialization before entering the application-update loop, then exits that loop before an apparent owner release and clearing the global. Allocation precedes constructor completion, so non-null alone is insufficient. Direct-store analysis is not exhaustive proof against alias writes. Application.Update also reaches native queued-chat code using the same receiver, which supports investigating that phase; it does not establish injected-call safety.

**Do not use `Application.Update.this` as an application object.** Its inspected direct caller does not supply the singleton in that register and the function uses image globals instead. The current observer ignores its arguments, so this finding does not invalidate the recorded callback observations.

The current-state/pending-state candidates were derived from the exact initialization table and FSM read/write instructions, not imported structure offsets. State-pointer equality can be tested without dereferencing an arbitrary state-name pointer. `APPVIEW` alone does not establish focus, pause state or receiver validity.

**Validation required before native calls:** use an explicitly selected read-only profile that validates the relevant file/live instruction relationships; compare the freshly computed receiver with the actual `Say.this` in its native callback; emit only equality and state classification. Observe current/pending state at application-update after callbacks across menu, reload, focus/pause, cockpit entry and disable. Compare the FSM receiver with the fixed application singleton if assigning application ownership. Preserve source hashes and exact-build refusal. Any disagreement must keep automatic presentation disabled. Use application-update scheduling rather than player-update: [the initial run](evidence-2026-09-24.md#run-001-observed-input-and-scheduling) placed the latter on a different thread. The subsequent [validation evidence](evidence-automatic-2026-09-24.md#read-only-validation-passed) records this procedure's outcome separately from the static findings.

## Native message ownership and system presentation

Additional exact-build static inspection found that the selected `Say` path copies the entire 1023-byte caller buffer into manager-owned storage before returning. A caller must allocate the full zero-filled buffer, even for a short message, and retain it through the call. The reviewed system-message branch bypasses recipient transport dispatch and continues local UI enqueue. This supports the narrow local presentation candidate; it is not a claim that the game makes no network traffic. The internal ten-slot queue can refuse an enqueue while the public function returns void, so a returned call is submission evidence only.

Private decoded evidence remains in `local/t04-5/receiver-research/say-lifetime-and-system-scope.md`, SHA-256 `F6D33409B601225675ABD475DEE415B4585ED4547EEF22C793C90930FBCB4649`. The private artifact index now covers 51 files. These findings do not replace live receiver/state validation or attended visible results.

## Publisher freshness

The [release log](https://www.nomanssky.com/release-log/) still lists Cosmos 7.04 first at review; that marketing label is not assigned to executable `179666`. The [EULA](https://www.nomanssky.com/end-user-licence-agreement/) still labels its last update 25 January 2019. The scoped local-lab assessment and unresolved rights questions from [T-04.2](../T-04.2/sources.md#publisher-freshness-and-scoped-lab-assessment) remain; no publisher grant, public distribution or service redirection is inferred.
