using System.Text;
using System.Text.Json;
using Community.Protocol;
using Microsoft.Data.Sqlite;

namespace Community.Server;

internal sealed class StorageFault(string code) : Exception(code)
{
    public string Code { get; } = code;
}

// One owner and one connection per database. Sessions and all credentials remain outside storage.
internal sealed class PersistentStore : IDisposable
{
    internal const int SchemaVersion = 1;
    internal const int ApplicationId = 0x4e4d5343;
    internal const long CounterLimit = 9007199254740991;
    internal const int EventPageSize = 32;
    internal static readonly TimeSpan ReplayRetention = TimeSpan.FromHours(24);

    private readonly ServerConfig config;
    private readonly TimeProvider clock;
    private readonly Action<string>? checkpoint;
    private readonly FileStream ownership;
    private readonly SqliteConnection connection;

    internal PersistentStore(ServerConfig config, string databasePath, TimeProvider? clock = null, Action<string>? checkpoint = null)
    {
        this.config = config;
        this.clock = clock ?? TimeProvider.System;
        this.checkpoint = checkpoint;
        databasePath = Path.GetFullPath(databasePath);
        ownership = AcquireOwnership(databasePath);
        var existed = File.Exists(databasePath);
        try { connection = Open(databasePath, existed ? SqliteOpenMode.ReadWrite : SqliteOpenMode.ReadWriteCreate); }
        catch { ownership.Dispose(); throw; }
        try
        {
            if (!existed) Initialize();
            Validate(connection, config.CommunityId);
            // DELETE journal makes offline backup/restore a single committed database. FULL sync
            // waits for durable commit before an HTTP success can be constructed.
            Execute(connection, null, "PRAGMA journal_mode=DELETE; PRAGMA synchronous=FULL; PRAGMA foreign_keys=ON;");
            using var transaction = connection.BeginTransaction();
            foreach (var principal in config.Principals)
            {
                Execute(connection, transaction, """
                    INSERT INTO members(principal_id, member_id, interaction_id, revision, progress, status, message)
                    VALUES($principal, $member, $interaction, 0, 0, 'available', '')
                    ON CONFLICT(principal_id) DO NOTHING;
                    """, ("$principal", principal.Id), ("$member", Guid.NewGuid().ToString()), ("$interaction", Guid.NewGuid().ToString()));
            }
            Prune(transaction);
            transaction.Commit();
        }
        catch
        {
            connection.Dispose();
            ownership.Dispose();
            throw;
        }
    }

    private static FileStream AcquireOwnership(string path)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        try { return new FileStream(path + ".owner.lock", FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None); }
        catch (IOException) { throw new StorageFault("storage_in_use"); }
    }

    private static SqliteConnection Open(string path, SqliteOpenMode mode)
    {
        var result = new SqliteConnection(new SqliteConnectionStringBuilder
        {
            DataSource = path, Mode = mode, Pooling = false, DefaultTimeout = 5
        }.ToString());
        try { result.Open(); return result; }
        catch { result.Dispose(); throw; }
    }

    private void Initialize()
    {
        Execute(connection, null, "PRAGMA journal_mode=DELETE; PRAGMA synchronous=FULL; PRAGMA foreign_keys=ON;");
        using var transaction = connection.BeginTransaction();
        Execute(connection, transaction, $"""
            PRAGMA application_id={ApplicationId};
            PRAGMA user_version={SchemaVersion};
            CREATE TABLE community_metadata (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                schema_version INTEGER NOT NULL,
                community_id TEXT NOT NULL,
                created_utc_ms INTEGER NOT NULL
            ) STRICT;
            CREATE TABLE members (
                principal_id TEXT PRIMARY KEY,
                member_id TEXT NOT NULL UNIQUE,
                interaction_id TEXT NOT NULL UNIQUE,
                revision INTEGER NOT NULL CHECK(revision BETWEEN 0 AND {CounterLimit}),
                progress INTEGER NOT NULL CHECK(progress BETWEEN 0 AND revision),
                status TEXT NOT NULL CHECK(status IN ('available','accepted','completed')),
                message TEXT NOT NULL CHECK(length(message)<=512)
            ) STRICT;
            CREATE TABLE events (
                member_id TEXT NOT NULL REFERENCES members(member_id),
                revision INTEGER NOT NULL CHECK(revision BETWEEN 1 AND {CounterLimit}),
                event_id TEXT NOT NULL UNIQUE,
                request_id TEXT NOT NULL,
                event_json TEXT NOT NULL,
                committed_utc_ms INTEGER NOT NULL,
                PRIMARY KEY(member_id, revision)
            ) STRICT;
            CREATE TABLE replays (
                member_id TEXT NOT NULL REFERENCES members(member_id),
                request_id TEXT NOT NULL,
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                committed_utc_ms INTEGER NOT NULL,
                PRIMARY KEY(member_id, request_id)
            ) STRICT;
            CREATE INDEX replays_expiry ON replays(committed_utc_ms);
            """);
        Execute(connection, transaction,
            "INSERT INTO community_metadata VALUES(1, $version, $community, $now);",
            ("$version", SchemaVersion), ("$community", config.CommunityId), ("$now", Now()));
        checkpoint?.Invoke("migration_before_commit");
        transaction.Commit();
    }

    private static void Validate(SqliteConnection database, string community)
    {
        using var integrity = Command(database, null, "PRAGMA integrity_check;");
        if (!string.Equals(integrity.ExecuteScalar() as string, "ok", StringComparison.Ordinal))
            throw new StorageFault("invalid_database");
        using var application = Command(database, null, "PRAGMA application_id;");
        if (Convert.ToInt64(application.ExecuteScalar()) != ApplicationId) throw new StorageFault("foreign_database");
        using var version = Command(database, null, "PRAGMA user_version;");
        if (Convert.ToInt64(version.ExecuteScalar()) != SchemaVersion) throw new StorageFault("unsupported_schema");
        using (var metadata = Command(database, null, "SELECT singleton, schema_version, community_id FROM community_metadata;"))
        using (var reader = metadata.ExecuteReader())
        {
            if (!reader.Read() || reader.GetInt64(0) != 1 || reader.GetInt32(1) != SchemaVersion)
                throw new StorageFault("invalid_database");
            if (reader.GetString(2) != community) throw new StorageFault("wrong_database_community");
            if (reader.Read()) throw new StorageFault("invalid_database");
        }
        using var foreignKeys = Command(database, null, "PRAGMA foreign_key_check;");
        using (var reader = foreignKeys.ExecuteReader())
            if (reader.Read()) throw new StorageFault("invalid_database");
        // Detect incomplete histories and inconsistent snapshot/event ownership before admission.
        using var members = Command(database, null, """
            SELECT m.member_id, m.interaction_id, m.revision, m.progress, m.status, m.message,
                (SELECT COUNT(*) FROM events e WHERE e.member_id=m.member_id),
                (SELECT event_json FROM events e WHERE e.member_id=m.member_id ORDER BY revision DESC LIMIT 1)
            FROM members m;
            """);
        using (var reader = members.ExecuteReader())
        {
            while (reader.Read())
            {
                var state = ReadState(reader);
                if (reader.GetInt64(6) != state.Revision) throw new StorageFault("invalid_database");
                if (state.Revision > 0 && Parse<StateEvent>(reader.GetString(7)).State != state)
                    throw new StorageFault("invalid_database");
            }
        }
        // Verify required replay columns, including on an empty store. Malformed selected schema fails closed.
        using var replays = Command(database, null, "SELECT member_id, request_id, request_json, response_json, committed_utc_ms FROM replays LIMIT 0;");
        using var replayReader = replays.ExecuteReader();
    }

    internal InteractionState State(string principalId, SqliteTransaction? transaction = null)
    {
        using var command = Command(connection, transaction,
            "SELECT member_id, interaction_id, revision, progress, status, message FROM members WHERE principal_id=$principal;",
            ("$principal", principalId));
        using var reader = command.ExecuteReader();
        if (!reader.Read()) throw new StorageFault("invalid_database");
        return ReadState(reader);
    }

    private static InteractionState ReadState(SqliteDataReader reader)
    {
        if (!Guid.TryParse(reader.GetString(0), out var member) || member == Guid.Empty ||
            !Guid.TryParse(reader.GetString(1), out var interaction) || interaction == Guid.Empty)
            throw new StorageFault("invalid_database");
        var revision = reader.GetInt64(2);
        var progress = reader.GetInt64(3);
        var status = reader.GetString(4);
        var message = reader.GetString(5);
        if (revision < 0 || revision > CounterLimit || progress < 0 || progress > revision ||
            status is not ("available" or "accepted" or "completed") || message.Length > 512)
            throw new StorageFault("invalid_database");
        return new(interaction, revision, status, message, member, progress);
    }

    internal EventsResponse Events(string principalId, long after)
    {
        var state = State(principalId);
        if (after < 0 || after > state.Revision) throw new ApiFault(400, "invalid_cursor");
        using var command = Command(connection, null, """
            SELECT event_json FROM events WHERE member_id=$member AND revision>$after ORDER BY revision LIMIT $limit;
            """, ("$member", state.MemberId.ToString()), ("$after", after), ("$limit", EventPageSize));
        using var reader = command.ExecuteReader();
        var events = new List<StateEvent>();
        var cursor = after;
        while (reader.Read())
        {
            var change = Parse<StateEvent>(reader.GetString(0));
            if (change.State.MemberId != state.MemberId || change.State.InteractionId != state.InteractionId || change.State.Revision != cursor + 1)
                throw new StorageFault("invalid_database");
            events.Add(change);
            cursor = change.State.Revision;
        }
        return new(Wire.Version, config.CommunityId, events.ToArray(), cursor);
    }

    internal CommandResponse Apply(string principalId, CommandRequest request)
    {
        using var transaction = connection.BeginTransaction();
        // The service holds its gate while operating this connection; BEGIN IMMEDIATE also reserves the SQLite writer.
        var state = State(principalId, transaction);
        using (var replay = Command(connection, transaction, """
            SELECT request_json, response_json FROM replays
            WHERE member_id=$member AND request_id=$request AND committed_utc_ms>$cutoff;
            """, ("$member", state.MemberId.ToString()), ("$request", request.RequestId.ToString()), ("$cutoff", Cutoff())))
        using (var reader = replay.ExecuteReader())
        {
            if (reader.Read())
            {
                var original = Parse<CommandRequest>(reader.GetString(0));
                if (original != request) throw new ApiFault(409, "request_id_conflict");
                var originalResponse = Parse<CommandResponse>(reader.GetString(1));
                if (originalResponse.State.MemberId != state.MemberId || originalResponse.RequestId != request.RequestId ||
                    originalResponse.CommunityId != config.CommunityId || originalResponse.Event.State != originalResponse.State)
                    throw new StorageFault("invalid_database");
                return originalResponse;
            }
        }
        if (request.Payload.InteractionId != state.InteractionId) throw new ApiFault(404, "unknown_interaction");
        if (request.ExpectedRevision != state.Revision) throw new ApiFault(409, "stale_revision");
        var probe = request.CommandType == "probe";
        var next = (state.Status, request.CommandType) switch
        {
            (_, "probe") => state.Status,
            ("available", "accept") => "accepted",
            ("accepted", "complete") => "completed",
            ("completed", "reset") => "available",
            _ => throw new ApiFault(409, "invalid_transition")
        };
        if (state.Revision == CounterLimit) throw new ApiFault(409, "counter_exhausted");
        var updated = state with
        {
            Revision = state.Revision + 1, Progress = state.Progress + (probe ? 1 : 0), Status = next,
            Message = probe || next == "completed" ? config.CompletionMessage : ""
        };
        var change = new StateEvent(Guid.NewGuid(), request.RequestId, probe ? "interaction.probed" : "interaction.changed", updated);
        var response = new CommandResponse(Wire.Version, request.RequestId, config.CommunityId, updated, change);
        Execute(connection, transaction, """
            UPDATE members SET revision=$revision, progress=$progress, status=$status, message=$message
            WHERE member_id=$member AND revision=$previous;
            """, ("$revision", updated.Revision), ("$progress", updated.Progress), ("$status", updated.Status),
            ("$message", updated.Message), ("$member", updated.MemberId.ToString()), ("$previous", state.Revision));
        var now = Now();
        Execute(connection, transaction, """
            INSERT INTO events VALUES($member, $revision, $event, $request, $json, $now);
            """, ("$member", updated.MemberId.ToString()), ("$revision", updated.Revision), ("$event", change.EventId.ToString()),
            ("$request", request.RequestId.ToString()), ("$json", JsonSerializer.Serialize(change, Wire.Json)), ("$now", now));
        Prune(transaction);
        Execute(connection, transaction, """
            INSERT INTO replays VALUES($member, $request, $requestJson, $responseJson, $now);
            """, ("$member", updated.MemberId.ToString()), ("$request", request.RequestId.ToString()),
            ("$requestJson", JsonSerializer.Serialize(request, Wire.Json)), ("$responseJson", JsonSerializer.Serialize(response, Wire.Json)), ("$now", now));
        checkpoint?.Invoke("before_commit");
        transaction.Commit();
        checkpoint?.Invoke("after_commit");
        return response;
    }

    private long Now() => clock.GetUtcNow().ToUnixTimeMilliseconds();
    private long Cutoff() => clock.GetUtcNow().Subtract(ReplayRetention).ToUnixTimeMilliseconds();
    private void Prune(SqliteTransaction transaction) => Execute(connection, transaction,
        "DELETE FROM replays WHERE committed_utc_ms<=$cutoff;", ("$cutoff", Cutoff()));

    private static T Parse<T>(string json)
    {
        try { return Wire.Parse<T>(Encoding.UTF8.GetBytes(json)); }
        catch (JsonException) { throw new StorageFault("invalid_database"); }
    }

    private static SqliteCommand Command(SqliteConnection database, SqliteTransaction? transaction, string sql, params (string Name, object Value)[] parameters)
    {
        var command = database.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = sql;
        foreach (var (name, value) in parameters) command.Parameters.AddWithValue(name, value);
        return command;
    }

    private static void Execute(SqliteConnection database, SqliteTransaction? transaction, string sql, params (string Name, object Value)[] parameters)
    {
        using var command = Command(database, transaction, sql, parameters);
        command.ExecuteNonQuery();
    }

    internal static void Backup(string databasePath, string backupPath, string community)
    {
        databasePath = Path.GetFullPath(databasePath);
        backupPath = Path.GetFullPath(backupPath);
        using var owner = AcquireOwnership(databasePath);
        using var source = Open(databasePath, SqliteOpenMode.ReadOnly);
        Validate(source, community);
        CopyVerified(source, backupPath, community);
    }

    internal static void Restore(string databasePath, string backupPath, string community)
    {
        databasePath = Path.GetFullPath(databasePath);
        backupPath = Path.GetFullPath(backupPath);
        using var owner = AcquireOwnership(databasePath);
        // A leftover journal from an earlier database would be applied to the restored file on first open.
        if (new[] { "", "-journal", "-wal", "-shm" }.Any(suffix => File.Exists(databasePath + suffix)))
            throw new StorageFault("restore_destination_exists");
        using var backupOwner = AcquireOwnership(backupPath);
        using var source = Open(backupPath, SqliteOpenMode.ReadOnly);
        Validate(source, community);
        CopyVerified(source, databasePath, community);
    }

    private static void CopyVerified(SqliteConnection source, string destination, string community)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
        var temporary = destination + ".partial-" + Guid.NewGuid().ToString("N");
        try
        {
            using (var copy = Open(temporary, SqliteOpenMode.ReadWriteCreate))
            {
                Execute(copy, null, "PRAGMA journal_mode=DELETE; PRAGMA synchronous=FULL;");
                source.BackupDatabase(copy);
                Validate(copy, community);
            }
            // Publish only a verified, complete backup, never overwrite an existing destination.
            File.Move(temporary, destination, overwrite: false);
        }
        finally
        {
            if (File.Exists(temporary)) File.Delete(temporary);
        }
    }

    public void Dispose()
    {
        connection.Dispose();
        ownership.Dispose();
    }
}
