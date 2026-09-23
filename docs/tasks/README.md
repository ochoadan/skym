# Task documents

[STEPS](../STEPS.md) owns delivery status. This index links existing detailed records by task ID; implementation paths are included when code exists.

| Task / roadmap | Documents | Architecture and code |
| --- | --- | --- |
| T-03.1 / R-011 — Native baseline | [Plan and E-01a procedure](T-03.1/README.md) · [Sources](T-03.1/sources.md) · [Evidence](T-03.1/evidence-2026-09-21.md) | [Client/recovery boundaries](../ARCHITECTURE.md#5-client-and-resource-boundaries); no product code introduced |
| T-04.1 / R-001–R-010 — Standalone server | [Implementation and commands](T-04.1/README.md) · [Protocol](T-04.1/protocol.md) · [Sources](T-04.1/sources.md) · [Evidence](T-04.1/evidence-2026-09-23.md) | [Transport/authority](../ARCHITECTURE.md#4-protocol-and-persistence); [server](../../src/Community.Server/Program.cs), [client](../../src/Community.Client/Program.cs), [tests](../../tests/Community.Tests/Program.cs) |
| T-04.2 / R-012–R-020 — Minimal adapter | [Operation, commands and lab procedure](T-04.2/README.md) · [Sources](T-04.2/sources.md) · [Evidence](T-04.2/evidence-2026-09-23.md) | [Client boundaries](../ARCHITECTURE.md#5-client-and-resource-boundaries); [preflight](../../src/Community.AdapterLab/preflight.py), [probe](../../src/Community.AdapterLab/probe.py) |
| T-04.3 / R-021–R-030 — One-player service connection | [Operation, commands, sources and E-10 procedure](T-04.3/README.md) · [Evidence](T-04.3/evidence-2026-09-23.md) | [First game connection](../ARCHITECTURE.md#3-first-game-connection-and-the-later-gameplay-slice); [worker](../../src/Community.AdapterLab/bridge.py), [typed client](../../src/Community.AdapterLab/service_client.py) |
