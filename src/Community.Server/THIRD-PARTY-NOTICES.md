# Service dependency notices

The service uses unmodified `Microsoft.Data.Sqlite` / `.Core` 10.0.12 (Microsoft, MIT) and SQLitePCLRaw bundle/core/provider/native packages 2.1.12 (SourceGear, Apache-2.0). SQLite's core is public domain. Exact versions, source identities and artifact hashes are recorded in [T-04.4 sources](../../docs/tasks/T-04.4/sources.md) and [packages.lock.json](packages.lock.json).

Retain these notices with distributed service artifacts:

- [Microsoft MIT license](licenses/Microsoft-MIT.txt).
- [SQLitePCLRaw Apache-2.0 license](licenses/SQLitePCLRaw-Apache-2.0.txt).
- [SQLitePCLRaw upstream notices, including SQLite](licenses/SQLitePCLRaw-NOTICE.txt). The broad upstream notice covers optional components as well; this selection uses `e_sqlite3`, not SQLCipher.

The project does not redistribute proprietary No Man's Sky files. The native adapter has its own [dependency notices](../Community.AdapterLab/THIRD-PARTY-NOTICES.md).
