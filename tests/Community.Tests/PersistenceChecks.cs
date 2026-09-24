using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Community.Protocol;
using Community.Server;
using Microsoft.Data.Sqlite;

internal sealed partial class IntegrationSuite
{
    private async Task ExercisePersistence()
    {
        await Check("simultaneous exact duplicate probes acknowledge one durable mutation", async () =>
        {
            var server = CreateServer("duplicate-race");
            await server.Start();
            var session = await Connect(server, 0, AdapterCompatibility.Supported);
            var initial = (await Get<StateResponse>(server, "/state", session.AccessToken)).State;
            var request = Command(server, initial, "probe");
            var replies = await Task.WhenAll(Enumerable.Range(0, 8).Select(_ => Post(server, "/commands", request, session.AccessToken)));
            Require(replies.All(reply => reply.Status == 200 && reply.Body == replies[0].Body),
                "Concurrent exact duplicates did not return the same acknowledged response.");
            var state = (await Get<StateResponse>(server, "/state", session.AccessToken)).State;
            Require(state.Progress == 1 && state.Revision == 1 && state.MemberId == initial.MemberId,
                "Concurrent duplicates minted additional progress or changed identity.");
            Require((await Get<EventsResponse>(server, "/events?after=0", session.AccessToken)).Events.Length == 1,
                "Concurrent duplicates appended multiple events.");
            await server.Stop();
        });

        await Check("acknowledged state, event and exact response survive abrupt child-process termination", async () =>
        {
            var server = CreateServer("abrupt-stop");
            await server.Start();
            var session = await Connect(server, 0, AdapterCompatibility.Supported);
            var initial = (await Get<StateResponse>(server, "/state", session.AccessToken)).State;
            var request = Command(server, initial, "probe");
            var acknowledged = await Post(server, "/commands", request, session.AccessToken);
            Require(acknowledged.Status == 200, "Mutation was not acknowledged before termination.");
            var expected = acknowledged.As<CommandResponse>();
            await server.Kill();
            RequirePortAvailable(server.Config.Port);
            var recovered = CreateServer("abrupt-recovery", server.Config, server.ConfigurationPath);
            await recovered.Start();
            await ExpectError(recovered, "GET", "/state", null, session.AccessToken, 401, "invalid_session", null);
            var reconnected = await Connect(recovered, 0, AdapterCompatibility.Supported);
            Require((await Get<StateResponse>(recovered, "/state", reconnected.AccessToken)).State == expected.State,
                "Acknowledged state did not survive process termination.");
            var events = await Get<EventsResponse>(recovered, "/events?after=0", reconnected.AccessToken);
            Require(events.Events.SequenceEqual([expected.Event]), "Acknowledged event did not survive process termination.");
            var replay = await Post(recovered, "/commands", request, reconnected.AccessToken);
            Require(replay.Status == 200 && replay.Body == acknowledged.Body, "Exact response did not survive process termination.");
            await recovered.Stop();
        });

        await Check("rotated credentials and temporarily removed principals preserve the durable member mapping", async () =>
        {
            var server = CreateServer("identity");
            await server.Start();
            var alice = await Connect(server, 0, AdapterCompatibility.Supported);
            var before = (await Get<StateResponse>(server, "/state", alice.AccessToken)).State;
            var request = Command(server, before, "probe");
            var acknowledged = await Post(server, "/commands", request, alice.AccessToken);
            var expected = acknowledged.As<CommandResponse>().State;
            await server.Stop();

            var withoutAlice = CreateServer("identity-removed", server.Config with { Principals = [server.Config.Principals[1]] }, server.ConfigurationPath);
            await withoutAlice.Start();
            var removedCredentials = Session(server, 0);
            await ExpectError(withoutAlice, "POST", "/sessions", removedCredentials, null, 401, "invalid_credentials", removedCredentials.RequestId);
            await withoutAlice.Stop();

            var principals = server.Config.Principals.Select(principal => principal with { Key = NewSecret() }).ToArray();
            var rotated = CreateServer("identity-rotated", server.Config with { Principals = principals }, server.ConfigurationPath);
            await rotated.Start();
            var oldCredentials = Session(server, 0);
            await ExpectError(rotated, "POST", "/sessions", oldCredentials, null, 401, "invalid_credentials", oldCredentials.RequestId);
            var current = await Connect(rotated, 0, AdapterCompatibility.Supported);
            Require((await Get<StateResponse>(rotated, "/state", current.AccessToken)).State == expected,
                "Credential rotation or temporary removal changed the member or its state.");
            var replay = await Post(rotated, "/commands", request, current.AccessToken);
            Require(replay.Body == acknowledged.Body && replay.Status == 200, "Credential rotation lost durable replay.");
            await rotated.Stop();
        });

        await Check("failure before transaction commit rolls back state, event and replay together", () =>
        {
            var config = NewConfig();
            var path = DirectDatabase("before-commit");
            var fail = true;
            using var store = new PersistentStore(config, path, checkpoint: stage =>
            {
                if (stage == "before_commit" && fail) throw new InjectedStorageFailure();
            });
            var runtime = new LabRuntime(config, store);
            var session = DirectSession(runtime, config);
            var initial = runtime.State(session.AccessToken).State;
            var request = DirectCommand(config, initial);
            ExpectInjected(() => runtime.Command(session.AccessToken, request));
            Require(runtime.State(session.AccessToken).State == initial && runtime.Events(session.AccessToken, 0).Events.Length == 0,
                "Uncommitted transaction left partial state or events.");
            fail = false;
            var retry = runtime.Command(session.AccessToken, request);
            Require(retry.State.Progress == 1 && retry.State.Revision == 1 && runtime.Events(session.AccessToken, 0).Events.Length == 1,
                "Retry after rollback was poisoned by a partial replay record.");
            return Task.CompletedTask;
        });

        await Check("response loss after commit recovers one state and event through exact replay", () =>
        {
            var config = NewConfig();
            var path = DirectDatabase("after-commit");
            CommandRequest request;
            InteractionState committed;
            StateEvent durableEvent;
            using (var store = new PersistentStore(config, path, checkpoint: stage =>
            {
                if (stage == "after_commit") throw new InjectedStorageFailure();
            }))
            {
                var runtime = new LabRuntime(config, store);
                var session = DirectSession(runtime, config);
                request = DirectCommand(config, runtime.State(session.AccessToken).State);
                ExpectInjected(() => runtime.Command(session.AccessToken, request));
                committed = runtime.State(session.AccessToken).State;
                durableEvent = runtime.Events(session.AccessToken, 0).Events.Single();
            }
            using (var reopened = new PersistentStore(config, path))
            {
                var runtime = new LabRuntime(config, reopened);
                var session = DirectSession(runtime, config);
                var replay = runtime.Command(session.AccessToken, request);
                Require(committed.Progress == 1 && committed.Revision == 1 && replay.State == committed && replay.Event == durableEvent,
                    "Recovery from a lost response did not replay the committed outcome.");
                Require(runtime.Events(session.AccessToken, 0).Events.Length == 1 && runtime.State(session.AccessToken).State == committed,
                    "Lost-response replay applied a second mutation.");
            }
            return Task.CompletedTask;
        });

        await Check("expired replay responses are pruned and the exact old request remains stale after restart", () =>
        {
            var config = NewConfig();
            var path = DirectDatabase("retention");
            var clock = new TestClock(DateTimeOffset.UtcNow);
            CommandRequest first;
            CommandResponse acknowledged;
            using (var store = new PersistentStore(config, path, clock))
            {
                var runtime = new LabRuntime(config, store);
                var session = DirectSession(runtime, config);
                first = DirectCommand(config, runtime.State(session.AccessToken).State);
                acknowledged = runtime.Command(session.AccessToken, first);
                clock.Advance(TimeSpan.FromHours(23));
                Require(runtime.Command(session.AccessToken, first) == acknowledged, "Replay expired before the 24-hour retention window.");
                clock.Advance(TimeSpan.FromHours(2));
                var next = runtime.Command(session.AccessToken, DirectCommand(config, acknowledged.State));
                Require(next.State.Progress == 2, "Retention maintenance blocked a new valid action.");
                ExpectFault(() => runtime.Command(session.AccessToken, first), 409, "stale_revision");
                Require(runtime.State(session.AccessToken).State == next.State && runtime.Events(session.AccessToken, 0).Events.Length == 2,
                    "Expired exact replay duplicated progress or erased durable events.");
                Require(Scalar(path, "SELECT count(*) FROM replays;") == 1,
                    "Expired replay remained stored after the next successful mutation.");
            }
            clock.Advance(TimeSpan.FromHours(25));
            using (var reopened = new PersistentStore(config, path, clock))
            {
                var runtime = new LabRuntime(config, reopened);
                var session = DirectSession(runtime, config);
                ExpectFault(() => runtime.Command(session.AccessToken, first), 409, "stale_revision");
                Require(runtime.State(session.AccessToken).State.Progress == 2, "Restart allowed an expired request to mint progress.");
                Require(Scalar(path, "SELECT count(*) FROM replays;") == 0 && runtime.Events(session.AccessToken, 0).Events.Length == 2,
                    "Startup failed to prune expired responses independently of the durable audit history.");
            }
            return Task.CompletedTask;
        });

        await ExerciseStorageRecovery();
    }

    private async Task ExerciseStorageRecovery()
    {
        var source = CreateServer("backup-source");
        InteractionState savedState = null!;
        CommandRequest savedRequest = null!;
        Reply savedReply = null!;
        var backupPath = Path.Combine(runDirectory, "backup.sqlite3");

        await Check("exclusive storage ownership refuses a second host and live maintenance", async () =>
        {
            await source.Start();
            var session = await Connect(source, 0, AdapterCompatibility.Supported);
            var initial = (await Get<StateResponse>(source, "/state", session.AccessToken)).State;
            savedRequest = Command(source, initial, "probe");
            savedReply = await Post(source, "/commands", savedRequest, session.AccessToken);
            Require(savedReply.Status == 200, "Backup source action failed.");
            savedState = savedReply.As<CommandResponse>().State;
            var duplicate = CreateServer("second-storage-owner", source.Config with { Port = FreePort() }, source.ConfigurationPath);
            await duplicate.StartRejected();
            Require(duplicate.ExitCode == 2 && duplicate.LogText.Contains("storage_in_use", StringComparison.Ordinal),
                "Second host did not refuse already-owned storage.");
            var maintenance = await source.RunManagement("--backup", backupPath);
            Require(maintenance.ExitCode == 2 && maintenance.Output.Contains("storage_in_use", StringComparison.Ordinal) && !File.Exists(backupPath),
                "Live maintenance did not refuse owned storage before producing an output.");
            Require((await Get<StateResponse>(source, "/state", session.AccessToken)).State == savedState,
                "Rejected maintenance changed live state.");
            await source.Stop();
        });

        await Check("offline backup preserves state and existing backup destinations are never overwritten", async () =>
        {
            var result = await source.RunManagement("--backup", backupPath);
            Require(result.ExitCode == 0 && File.Exists(backupPath), "Offline backup failed.");
            var originalHash = SHA256.HashData(await File.ReadAllBytesAsync(backupPath));
            var repeated = await source.RunManagement("--backup", backupPath);
            var repeatedHash = SHA256.HashData(await File.ReadAllBytesAsync(backupPath));
            Require(repeated.ExitCode == 2 && originalHash.SequenceEqual(repeatedHash),
                "Backup overwrote an existing destination.");
            foreach (var path in new[] { source.DatabasePath, backupPath })
            {
                var stored = Encoding.UTF8.GetString(await File.ReadAllBytesAsync(path));
                foreach (var secret in secrets)
                    Require(!stored.Contains(secret, StringComparison.Ordinal), "A database or backup stored a configured credential or session token.");
            }
        });

        await Check("restore into a fresh destination recovers member, state, events and exact replay", async () =>
        {
            var restored = CreateServer("restored", source.Config with { Port = FreePort() });
            var strayJournal = restored.DatabasePath + "-journal";
            Directory.CreateDirectory(Path.GetDirectoryName(strayJournal)!);
            await File.WriteAllBytesAsync(strayJournal, [1]);
            var blocked = await restored.RunManagement("--restore", backupPath);
            Require(blocked.ExitCode == 2 && blocked.Output.Contains("restore_destination_exists", StringComparison.Ordinal) &&
                !File.Exists(restored.DatabasePath), "Restore accepted a destination holding a leftover journal.");
            File.Delete(strayJournal);
            var result = await restored.RunManagement("--restore", backupPath);
            Require(result.ExitCode == 0, "Restore into a fresh destination failed.");
            await restored.Start();
            var session = await Connect(restored, 0, AdapterCompatibility.Supported);
            Require((await Get<StateResponse>(restored, "/state", session.AccessToken)).State == savedState,
                "Backup/restore changed persisted member or progress.");
            var replay = await Post(restored, "/commands", savedRequest, session.AccessToken);
            Require(replay.Status == 200 && replay.Body == savedReply.Body, "Backup/restore lost the exact replay response.");
            var events = await Get<EventsResponse>(restored, "/events?after=0", session.AccessToken);
            Require(events.Events.SequenceEqual([savedReply.As<CommandResponse>().Event]), "Backup/restore lost the committed event.");
            await restored.Stop();
            var repeated = await restored.RunManagement("--restore", backupPath);
            Require(repeated.ExitCode == 2 && repeated.Output.Contains("restore_destination_exists", StringComparison.Ordinal),
                "Restore did not refuse an existing database.");
        });

        await Check("community mismatch, unsupported schemas, corruption and existing empty files refuse startup", async () =>
        {
            var variants = new (string Name, Action<string> Modify, ServerConfig Config)[]
            {
                ("wrong-community", _ => { }, source.Config with { Port = FreePort(), CommunityId = "different-community" }),
                ("newer-schema", path => Sql(path, "PRAGMA user_version = 999;"), source.Config with { Port = FreePort() }),
                ("unsupported-old-schema", path => Sql(path, "PRAGMA user_version = 0;"), source.Config with { Port = FreePort() }),
                ("corrupt-file", path => File.WriteAllText(path, "Original test data: deliberately not a SQLite database."), source.Config with { Port = FreePort() }),
                ("empty-file", path => File.WriteAllBytes(path, []), source.Config with { Port = FreePort() })
            };
            foreach (var variant in variants)
            {
                var server = CreateServer(variant.Name, variant.Config);
                Directory.CreateDirectory(Path.GetDirectoryName(server.DatabasePath)!);
                File.Copy(backupPath, server.DatabasePath);
                variant.Modify(server.DatabasePath);
                var before = SHA256.HashData(await File.ReadAllBytesAsync(server.DatabasePath));
                await server.StartRejected();
                Require(server.ExitCode == 2, $"Unsafe storage {variant.Name} was accepted.");
                RequirePortAvailable(server.Config.Port);
                var refusedHash = SHA256.HashData(await File.ReadAllBytesAsync(server.DatabasePath));
                Require(before.SequenceEqual(refusedHash),
                    $"Refused storage {variant.Name} was rewritten.");
                var migration = await server.RunManagement("--migrate");
                Require(migration.ExitCode == 2, $"Explicit migrate silently reset or downgraded {variant.Name}.");
                var migrationHash = SHA256.HashData(await File.ReadAllBytesAsync(server.DatabasePath));
                Require(before.SequenceEqual(migrationHash),
                    $"Refused migration rewrote {variant.Name}.");
            }
        });

        await Check("failed schema creation rolls back metadata and a fresh explicit migration recovers", async () =>
        {
            var config = NewConfig();
            var failedPath = DirectDatabase("failed-migration");
            ExpectInjected(() =>
            {
                using var rejected = new PersistentStore(config, failedPath, checkpoint: stage =>
                {
                    if (stage == "migration_before_commit") throw new InjectedStorageFailure();
                });
            });
            using (var connection = new SqliteConnection($"Data Source={failedPath};Pooling=False"))
            {
                connection.Open();
                using var command = connection.CreateCommand();
                command.CommandText = "SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name = 'community_metadata';";
                Require(Convert.ToInt64(command.ExecuteScalar()) == 0, "Failed schema creation committed partial metadata.");
            }
            try
            {
                using var unexpected = new PersistentStore(config, failedPath);
                throw new InvalidOperationException("Failed migration was silently reset on reopening.");
            }
            catch (StorageFault fault) when (fault.Code == "foreign_database") { }
            var recovered = CreateServer("fresh-migration", config);
            Require((await recovered.RunManagement("--migrate")).ExitCode == 0, "Explicit migration did not initialize a fresh destination.");
            Require((await recovered.RunManagement("--migrate")).ExitCode == 0, "Current schema validation was not repeatable.");
            await recovered.Start();
            var session = await Connect(recovered, 0, AdapterCompatibility.Supported);
            var state = (await Get<StateResponse>(recovered, "/state", session.AccessToken)).State;
            Require(state.Progress == 0 && state.Revision == 0 && state.MemberId != Guid.Empty,
                "Fresh migration did not produce a valid empty community member.");
            await recovered.Stop();
        });
    }

    private static void Sql(string path, string sql)
    {
        using var connection = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = path, Pooling = false }.ToString());
        connection.Open();
        using var command = connection.CreateCommand();
        command.CommandText = sql;
        command.ExecuteNonQuery();
    }

    private static long Scalar(string path, string sql)
    {
        using var connection = new SqliteConnection(new SqliteConnectionStringBuilder
        {
            DataSource = path, Pooling = false, Mode = SqliteOpenMode.ReadOnly
        }.ToString());
        connection.Open();
        using var command = connection.CreateCommand();
        command.CommandText = sql;
        return Convert.ToInt64(command.ExecuteScalar());
    }

    private async Task<List<StateEvent>> ReadAllEvents(TestServer server, string token, long expectedRevision)
    {
        var events = new List<StateEvent>();
        long cursor = 0;
        while (true)
        {
            var page = await Get<EventsResponse>(server, $"/events?after={cursor}", token);
            Require(page.Events.Length <= 32, "Event page exceeded its 32-event bound.");
            if (page.Events.Length == 0)
            {
                Require(page.Revision == cursor && cursor == expectedRevision, "Empty page did not finish at the expected revision.");
                return events;
            }
            Require(page.Events[0].State.Revision == cursor + 1 && page.Revision == page.Events[^1].State.Revision &&
                page.Revision <= expectedRevision, "Event page cursor did not resume from its last delivered event.");
            events.AddRange(page.Events);
            cursor = page.Revision;
        }
    }

    private string DirectDatabase(string name)
    {
        var directory = Path.Combine(runDirectory, "storage", name);
        Directory.CreateDirectory(directory);
        return Path.Combine(directory, "community.sqlite3");
    }

    private static SessionResponse DirectSession(LabRuntime runtime, ServerConfig config) => runtime.Connect(
        new(Wire.Version, config.CommunityId, Guid.NewGuid(), config.Principals[0].Id, config.Principals[0].Key, AdapterCompatibility.Supported));

    private static CommandRequest DirectCommand(ServerConfig config, InteractionState state) =>
        new(Wire.Version, config.CommunityId, Guid.NewGuid(), state.Revision, "probe", new(state.InteractionId));

    private static void ExpectInjected(Action action)
    {
        try { action(); }
        catch (InjectedStorageFailure) { return; }
        throw new InvalidOperationException("The requested transaction failure checkpoint was not reached.");
    }

    private static void ExpectFault(Action action, int status, string code)
    {
        try { action(); }
        catch (ApiFault fault)
        {
            Require(fault.Status == status && fault.Code == code, $"Expected {code}/{status}, received {fault.Code}/{fault.Status}.");
            return;
        }
        throw new InvalidOperationException($"Expected rejection {code}.");
    }

    private sealed class InjectedStorageFailure : Exception { }
    private sealed class TestClock(DateTimeOffset now) : TimeProvider
    {
        public override DateTimeOffset GetUtcNow() => now;
        public void Advance(TimeSpan duration) => now += duration;
    }
}
