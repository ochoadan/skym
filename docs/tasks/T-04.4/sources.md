# T-04.4 — Storage and dependency review

Reviewed 2026-09-23. This file separates vendor documentation, artifact observations and engineering choices. Game/tool ownership and native-hook restrictions remain those in [T-04.2 sources](../T-04.2/sources.md); this task adds service storage and a read-only use of the existing chat bridge.

## Selected storage

**Vendor statements:** Microsoft documents explicit [SQLite transactions](https://learn.microsoft.com/en-us/dotnet/standard/data/sqlite/transactions) and the [online backup API](https://learn.microsoft.com/en-us/dotnet/standard/data/sqlite/backup). SQLite describes its [atomic commit mechanism](https://www.sqlite.org/atomiccommit.html), [synchronous settings](https://sqlite.org/pragma.html#pragma_synchronous), and [corruption hazards](https://www.sqlite.org/howtocorrupt.html). These describe intended storage behavior, not results from this application or hardware.

**Engineering selection:** Use SQLite for the single service/local disk lab. It supplies transactions and recoverable storage without operating another daemon. PostgreSQL remains a candidate for later concurrent/remote operational needs; it adds deployment work without improving this one-player acceptance check. A JSON snapshot or ad hoc append log would require us to implement crash recovery and atomic consistency between state, events and replays. No benchmark or production-scale conclusion is inferred from this choice.

Commit state, event and replay outcome in one transaction and retain durable events as the notification recovery source. Use full synchronization and exclude multi-process/network-filesystem operation. Ordinary restart/process-interruption checks do not certify power-loss durability on every disk/controller.

## Exact dependency artifacts and permissions

Restore uses NuGet's official v3 endpoint, package SHA-512 hashes in the committed lock files, and `--locked-mode` in verification/CI. The package `.nuspec` metadata was inspected locally after restore. No game-derived dependency is added.

| Artifact | Exact source identity and review | Selected license |
| --- | --- | --- |
| `Microsoft.Data.Sqlite` and `Microsoft.Data.Sqlite.Core` **10.0.12** | [Package](https://www.nuget.org/packages/Microsoft.Data.Sqlite/10.0.12); both restored nuspecs identify `dotnet/dotnet` commit [`95017c711e6afc1085133d440e42b4bd78155701`](https://github.com/dotnet/dotnet/tree/95017c711e6afc1085133d440e42b4bd78155701) | MIT; [license at that commit](https://github.com/dotnet/dotnet/blob/95017c711e6afc1085133d440e42b4bd78155701/LICENSE.TXT) |
| `SQLitePCLRaw.bundle_e_sqlite3`, `.core`, `.provider.e_sqlite3`, `.lib.e_sqlite3` **2.1.12** | [Release](https://github.com/ericsink/SQLitePCL.raw/releases/tag/v2.1.12); tag resolved through the maintainer GitHub API to [`ca835d21508bff43121c65081035840ac5006c4c`](https://github.com/ericsink/SQLitePCL.raw/tree/ca835d21508bff43121c65081035840ac5006c4c). Nuspecs identify the repository but omit commit; the lock pins the published artifacts, not a claimed locally reproduced build | Apache-2.0 per package metadata; [license](https://github.com/ericsink/SQLitePCL.raw/blob/ca835d21508bff43121c65081035840ac5006c4c/LICENSE.TXT), [upstream notices](https://github.com/ericsink/SQLitePCL.raw/blob/ca835d21508bff43121c65081035840ac5006c4c/NOTICE.TXT) |
| Native SQLite in selected Windows x64 `e_sqlite3.dll` | Direct `sqlite3_libversion()` / `sqlite3_sourceid()` artifact query returned **3.53.3**, `2026-06-26 20:14:12 d4c0e51e4aeb96955b99185ab9cde75c339e2c29c3f3f12428d364a10d782c62`; [source ID](https://sqlite.org/src/info/d4c0e51e4aeb96955b99185ab9cde75c339e2c29c3f3f12428d364a10d782c62). This is the artifact's own identity report, not a reproducibility audit | SQLite's [public-domain statement](https://www.sqlite.org/copyright.html); the selected NuGet distribution also carries SQLitePCLRaw package notices |

MIT permits use and redistribution subject to retaining its copyright/license notice. Apache-2.0 permits use and distribution subject to its license/notice and modification requirements; its patent/trademark terms still apply. Original licenses and upstream notices are retained under [server licenses](../../../src/Community.Server/licenses/Microsoft-MIT.txt) and linked from [THIRD-PARTY-NOTICES](../../../src/Community.Server/THIRD-PARTY-NOTICES.md). No dependency source was modified. The broad upstream NOTICE includes optional components; retaining it does not claim this application uses SQLCipher or OpenSSL.

## Game freshness and unchanged boundary

The publisher [release log](https://www.nomanssky.com/release-log/) was refreshed on 2026-09-23. Compatibility still requires the exact executable fingerprint and live checks in [adapter compatibility](../../../config/adapter-compatibility.json); a release name alone cannot admit an executable. The same-day [scoped publisher/terms review](../T-04.2/sources.md#publisher-freshness-and-scoped-lab-assessment) remains applicable to the owned-client local chat experiment. This storage selection grants no permission or capability to replace the game backend, distribute a public adapter or claim a secure economy.
