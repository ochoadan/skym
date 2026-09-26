# Working task references

[STEPS](../STEPS.md#next-five-tasks) holds the next five task plans and current capability status. This page links procedures and contracts still used by that work; it is not an index of every completed task.

| Working reference | Documents to use | Implementation |
| --- | --- | --- |
| Server and wire contract | [T-04.1 setup and verification](T-04.1/README.md#setup-build-and-verify) · [Protocol](T-04.1/protocol.md) | [Server](../../src/Community.Server/Program.cs), [diagnostic client](../../src/Community.Client/Program.cs), [service checks](../../tests/Community.Tests/Program.cs) |
| Native lab setup and recovery | [T-04.2 adapter setup](T-04.2/README.md#setup-build-and-verify) · [Disposable-save procedure](T-04.2/README.md#lab-procedure-and-restoration) · [T-03.1 native baseline](T-03.1/README.md) | [Preflight](../../src/Community.AdapterLab/preflight.py), [guarded launcher](../../src/Community.AdapterLab/launch.py) |
| Connected chat fallback | [T-04.3 operation and E-10 procedure](T-04.3/README.md) | [Worker](../../src/Community.AdapterLab/bridge.py), [typed client](../../src/Community.AdapterLab/service_client.py) |
| Persistent member state and maintenance | [T-04.4 storage/identity contract](T-04.4/README.md#storage-identity-and-recovery-contract) · [Build and verify](T-04.4/README.md#setup-build-and-verify) · [Backup and restore](T-04.4/README.md#maintenance-and-restore) | [Storage](../../src/Community.Server/PersistentStore.cs), [persistence checks](../../tests/Community.Tests/PersistenceChecks.cs) |
| Automatic input and presentation | [T-04.5 receiver and callback contract](T-04.5/README.md#receiver-validation-and-selected-automatic-operation) · [Automatic setup and verification](T-04.5/README.md#setup-build-and-verify) | [Native hooks](../../src/Community.AdapterLab/probe.py), [fresh state](../../src/Community.AdapterLab/native_state.py), [scheduler](../../src/Community.AdapterLab/world_runtime.py) |

Each task reference links its own relevant sources and dated evidence. Keep those reports at their existing paths while capability claims, recovery, or future work depend on them. Replace this page's entries when the operational entry point changes; do not add a row merely because another task finished. Superseded, unreferenced plans and routine chronology can leave the working tree once their useful constraints have an owner; Git retains their history.

Shared design references: [authority](../ARCHITECTURE.md#2-authority-contract), [transport and persistence](../ARCHITECTURE.md#4-protocol-and-persistence), [client boundaries](../ARCHITECTURE.md#5-client-and-resource-boundaries), and [experiment catalog](../EXPERIMENTS.md). Retention and handoff rules belong to [AGENTS](../../AGENTS.md#fact-ownership).
