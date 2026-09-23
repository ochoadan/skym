using System.Diagnostics;
using System.Net;
using System.Net.Http.Headers;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Community.Protocol;

await using var suite = new IntegrationSuite();
return await suite.Run();

internal sealed class IntegrationSuite : IAsyncDisposable
{
    private readonly string repository = Directory.GetCurrentDirectory();
    private readonly List<TestServer> servers = [];
    private readonly HashSet<string> secrets = new(StringComparer.Ordinal);
    private readonly string runDirectory;
    private int passed;
    private string currentCheck = "initialization";

    public IntegrationSuite()
    {
        runDirectory = Path.Combine(repository, "local", "t04-1", $"tests-{DateTime.UtcNow:yyyyMMdd-HHmmss-fff}-{Guid.NewGuid():N}");
    }

    public async Task<int> Run()
    {
        try
        {
            Require(File.Exists(Path.Combine(repository, "src", "Community.Server", "bin", "Release", "net10.0", "Community.Server.dll")),
                "Run from the repository root after building Release.");
            Directory.CreateDirectory(runDirectory);
            Console.WriteLine($"Integration evidence: {Path.GetRelativePath(repository, runDirectory)}");
            await ExerciseInitialization();
            await ExerciseService();
            await ExerciseAdapter();
            await ExerciseExpiry();
            await ExerciseConfiguration();
            await ExerciseDiagnosticClient();
            await Check("all child logs exclude credentials and tokens", () =>
            {
                foreach (var server in servers)
                    foreach (var secret in secrets)
                        Require(!server.LogText.Contains(secret, StringComparison.Ordinal), "A credential appeared in a child log.");
                return Task.CompletedTask;
            });
            Console.WriteLine($"PASS: {passed} integration checks; real child processes stopped.");
            return 0;
        }
        catch (Exception exception)
        {
            Console.Error.WriteLine($"FAIL: {currentCheck}: {exception.GetType().Name}: {exception.Message}");
            Console.Error.WriteLine($"Completed {passed} checks. Evidence: {Path.GetRelativePath(repository, runDirectory)}");
            return 1;
        }
    }

    private async Task ExerciseInitialization()
    {
        await Check("server initializes usable private configuration without overwriting an existing file", async () =>
        {
            var configPath = Path.Combine(runDirectory, "initialization", "server.json");
            var first = await TestServer.InitializeConfiguration(repository, configPath);
            Require(first.ExitCode == 0, "Configuration initialization failed.");
            var original = await File.ReadAllBytesAsync(configPath);
            var config = Wire.Parse<ServerConfig>(original);
            var keys = config.Principals.Select(principal => principal.Key).Append(config.AdminKey).ToArray();
            Require(keys.Length == 3 && keys.Distinct(StringComparer.Ordinal).Count() == keys.Length &&
                keys.All(key => key.Length == 64), "Initialization did not generate distinct lab keys.");
            foreach (var key in keys) Require(!first.Output.Contains(key, StringComparison.Ordinal), "Initialization exposed a key.");

            var repeated = await TestServer.InitializeConfiguration(repository, configPath);
            var retained = await File.ReadAllBytesAsync(configPath);
            Require(repeated.ExitCode == 2 && original.SequenceEqual(retained),
                "Repeated initialization must refuse to overwrite existing configuration.");
            var anotherPath = Path.Combine(runDirectory, "initialization", "another.json");
            Require((await TestServer.InitializeConfiguration(repository, anotherPath)).ExitCode == 0, "Second new configuration failed.");
            var another = Wire.Parse<ServerConfig>(await File.ReadAllBytesAsync(anotherPath));
            Require(!another.Principals.Select(principal => principal.Key).Append(another.AdminKey).Intersect(keys).Any(),
                "Separate initializations reused keys.");

            var server = CreateServer("initialized-service", config with { Port = FreePort() });
            await server.Start();
            var session = await Connect(server, 0);
            Require((await Get<StateResponse>(server, "/state", session.AccessToken)).State.Status == "available",
                "Generated configuration could not authenticate a working session.");
            await server.Stop();
        });
    }

    private async Task ExerciseService()
    {
        var server = CreateServer("primary");
        await Check("start configured process and report health", async () =>
        {
            await server.Start();
            var health = await Get<HealthResponse>(server, "/health");
            Require(health.ProtocolVersion == Wire.Version && health.CommunityId == server.Config.CommunityId && health.Status == "ready", "Health response differs from configuration.");
        });

        SessionResponse alice = null!;
        SessionResponse bob = null!;
        InteractionState aliceState = null!;
        InteractionState bobState = null!;
        await Check("two configured identities receive distinct sessions and contracts", async () =>
        {
            alice = await Connect(server, 0);
            bob = await Connect(server, 1);
            Require(alice.SessionId != bob.SessionId && alice.AccessToken != bob.AccessToken, "Sessions are not distinct.");
            aliceState = (await Get<StateResponse>(server, "/state", alice.AccessToken)).State;
            bobState = (await Get<StateResponse>(server, "/state", bob.AccessToken)).State;
            Require(aliceState.InteractionId != bobState.InteractionId, "Principals share an interaction ID.");
            Require(aliceState.Status == "available" && aliceState.Revision == 0 && bobState.Revision == 0, "Initial contract is not empty.");
        });

        await Check("session admission rejects credentials, community, version, and empty request ID", async () =>
        {
            var baseline = Session(server, 0);
            await ExpectError(server, "POST", "/sessions", baseline with { Key = NewSecret() }, null, 401, "invalid_credentials", baseline.RequestId);
            await ExpectError(server, "POST", "/sessions", baseline with { PrincipalId = "unknown" }, null, 401, "invalid_credentials", baseline.RequestId);
            await ExpectError(server, "POST", "/sessions", baseline with { CommunityId = "other-community" }, null, 403, "wrong_community", baseline.RequestId);
            await ExpectError(server, "POST", "/sessions", baseline with { ProtocolVersion = Wire.Version + 1 }, null, 400, "unsupported_protocol", baseline.RequestId);
            await ExpectError(server, "POST", "/sessions", baseline with { RequestId = Guid.Empty }, null, 400, "invalid_request_id", Guid.Empty);
            await ExpectError(server, "GET", "/state", null, null, 401, "invalid_credentials", null);
            await ExpectError(server, "GET", "/state", null, "unknown-token", 401, "invalid_session", null);
            await ExpectError(server, "POST", "/admin/stop", null, alice.AccessToken, 401, "invalid_credentials", null);
        });

        await Check("browser origin, fetch metadata, and unexpected Host are rejected", async () =>
        {
            await ExpectRawError(server, "GET", "/health", null, null, 403, "browser_not_allowed", null, headers: new() { ["Origin"] = "http://example.test" });
            await ExpectRawError(server, "GET", "/health", null, null, 403, "browser_not_allowed", null, headers: new() { ["Sec-Fetch-Site"] = "same-origin" });
            await ExpectRawError(server, "GET", "/health", null, null, 400, "invalid_host", null, headers: new() { ["Host"] = $"localhost:{server.Config.Port}" });
        });

        var accept = Command(server, aliceState, "accept");
        await Check("original fixture parses and malformed or client-owned fields fail before mutation", async () =>
        {
            var valid = Fixture("accept.json", server, accept);
            Require(Wire.Parse<CommandRequest>(Encoding.UTF8.GetBytes(valid)) == accept, "Valid fixture differs from command.");
            var malicious = Fixture("reject-client-reward.json", server, accept);
            var json = JsonSerializer.Serialize(accept, Wire.Json);
            string[] bodies =
            [
                "{", "null", "[]", "{}", json[..^1] + ",\"actor\":\"bob\"}",
                json[..^1] + ",\"reward\":1000000}", json[..^1] + ",\"protocolVersion\":1}",
                json.Replace("\"protocolVersion\":1", "\"protocolVersion\":\"1\"", StringComparison.Ordinal),
                json.Replace("\"expectedRevision\":0", "\"expectedRevision\":\"0\"", StringComparison.Ordinal),
                malicious
            ];
            foreach (var body in bodies)
                await ExpectRawError(server, "POST", "/commands", body, alice.AccessToken, 400, "invalid_json", null);
            var state = (await Get<StateResponse>(server, "/state", alice.AccessToken)).State;
            Require(state == aliceState, "Rejected JSON mutated the contract.");
        });

        await Check("media type and declared oversized body are rejected", async () =>
        {
            var body = JsonSerializer.Serialize(accept, Wire.Json);
            await ExpectRawError(server, "POST", "/commands", body, alice.AccessToken, 415, "json_required", null, "text/plain");
            await ExpectRawError(server, "POST", "/commands", body, alice.AccessToken, 415, "json_required", null, "application/json; charset=iso-8859-1");
            var result = await Send(server, "POST", "/commands", new string(' ', Wire.BodyLimit + 1), alice.AccessToken);
            Require(result.Status == 413, "Oversized body did not return HTTP 413.");
            var error = result.As<ApiError>();
            Require(error.RequestId is null && error.Error is "invalid_http_body" or "body_too_large", "Oversized error envelope differs.");
        });

        await Check("unfinished HTTP body expires within the configured timeout", async () =>
        {
            using var client = new TcpClient();
            await client.ConnectAsync(IPAddress.Loopback, server.Config.Port);
            using var stream = client.GetStream();
            var request = $"POST /sessions HTTP/1.1\r\nHost: 127.0.0.1:{server.Config.Port}\r\nContent-Type: application/json\r\nContent-Length: 100\r\nConnection: close\r\n\r\n{{";
            var watch = Stopwatch.StartNew();
            await stream.WriteAsync(Encoding.ASCII.GetBytes(request));
            using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(8));
            var received = new StringBuilder();
            var buffer = new byte[2048];
            while (!received.ToString().Contains("body_timeout", StringComparison.Ordinal))
            {
                var count = await stream.ReadAsync(buffer, deadline.Token);
                if (count == 0) break;
                received.Append(Encoding.UTF8.GetString(buffer, 0, count));
            }
            Require(received.ToString().StartsWith("HTTP/1.1 408", StringComparison.Ordinal) && received.ToString().Contains("body_timeout", StringComparison.Ordinal), "Unfinished body did not return body_timeout/408.");
            Require(watch.Elapsed >= TimeSpan.FromSeconds(2) && watch.Elapsed < TimeSpan.FromSeconds(8), "Body timeout was outside the expected bound.");
            Require((await Get<HealthResponse>(server, "/health")).Status == "ready", "Service did not recover after incomplete body.");
        });

        await Check("command envelope, transition, revision, and actor boundaries reject invalid requests", async () =>
        {
            await ExpectError(server, "POST", "/commands", accept with { ProtocolVersion = 99 }, alice.AccessToken, 400, "unsupported_protocol", accept.RequestId);
            await ExpectError(server, "POST", "/commands", accept with { CommunityId = "wrong-community" }, alice.AccessToken, 403, "wrong_community", accept.RequestId);
            await ExpectError(server, "POST", "/commands", accept with { RequestId = Guid.Empty }, alice.AccessToken, 400, "invalid_request_id", Guid.Empty);
            await ExpectError(server, "POST", "/commands", accept with { CommandType = "complete" }, alice.AccessToken, 409, "invalid_transition", accept.RequestId);
            await ExpectError(server, "POST", "/commands", accept with { ExpectedRevision = 1 }, alice.AccessToken, 409, "stale_revision", accept.RequestId);
            await ExpectError(server, "POST", "/commands", accept with { CommandType = "mint" }, alice.AccessToken, 400, "invalid_command", accept.RequestId);
            await ExpectError(server, "POST", "/commands", accept with { ExpectedRevision = -1 }, alice.AccessToken, 400, "invalid_command", accept.RequestId);
            await ExpectError(server, "POST", "/commands", accept with { Payload = new(Guid.NewGuid()) }, alice.AccessToken, 404, "unknown_interaction", accept.RequestId);
            await ExpectError(server, "POST", "/commands", accept with { Payload = new(bobState.InteractionId) }, alice.AccessToken, 404, "unknown_interaction", accept.RequestId);
        });

        Reply accepted = null!;
        CommandResponse acceptedValue = null!;
        await Check("accept creates one correlated event and exact duplicate returns the original reply", async () =>
        {
            accepted = await Send(server, "POST", "/commands", Fixture("accept.json", server, accept), alice.AccessToken);
            Require(accepted.Status == 200, "Accept failed.");
            acceptedValue = accepted.As<CommandResponse>();
            Require(acceptedValue.State.Status == "accepted" && acceptedValue.State.Revision == 1, "Accept returned wrong state.");
            Require(acceptedValue.ProtocolVersion == Wire.Version && acceptedValue.CommunityId == server.Config.CommunityId && acceptedValue.RequestId == accept.RequestId, "Response lost envelope correlation.");
            Require(acceptedValue.Event.RequestId == accept.RequestId && acceptedValue.Event.EventId != Guid.Empty && acceptedValue.Event.EventType == "interaction.changed" && acceptedValue.Event.State == acceptedValue.State, "Event differs from acknowledged state.");
            var duplicate = await Post(server, "/commands", accept, alice.AccessToken);
            Require(duplicate.Status == 200 && duplicate.Body == accepted.Body, "Duplicate did not return exactly the original event and reply.");
            await ExpectError(server, "POST", "/commands", accept with { ExpectedRevision = 1 }, alice.AccessToken, 409, "request_id_conflict", accept.RequestId);
        });

        SessionResponse reconnected = null!;
        await Check("same principal reconnect preserves state and request deduplication", async () =>
        {
            reconnected = await Connect(server, 0);
            Require(reconnected.SessionId != alice.SessionId, "Reconnect reused the session ID.");
            Require((await Get<StateResponse>(server, "/state", reconnected.AccessToken)).State == acceptedValue.State, "Reconnect lost principal-owned state.");
            var duplicate = await Post(server, "/commands", accept, reconnected.AccessToken);
            Require(duplicate.Status == 200 && duplicate.Body == accepted.Body, "Reconnect lost deduplication.");
        });

        CommandResponse completed = null!;
        await Check("complete returns only the configured message and event polling repairs state", async () =>
        {
            var complete = Command(server, acceptedValue.State, "complete");
            completed = (await SuccessfulPost<CommandResponse>(server, "/commands", complete, alice.AccessToken));
            Require(completed.State.Status == "completed" && completed.State.Revision == 2 && completed.State.Message == server.Config.CompletionMessage, "Completion did not use configured message.");
            var all = await Get<EventsResponse>(server, "/events?after=0", alice.AccessToken);
            Require(all.ProtocolVersion == Wire.Version && all.CommunityId == server.Config.CommunityId && all.Revision == 2 && all.Events.Length == 2, "Event list has wrong envelope, count, or revision.");
            Require(all.Events[0] == acceptedValue.Event && all.Events[1] == completed.Event, "Event ordering or identity changed.");
            var later = await Get<EventsResponse>(server, "/events?after=1", reconnected.AccessToken);
            Require(later.Events.Length == 1 && later.Events[0] == completed.Event, "Event cursor did not resume correctly.");
            Require((await Get<EventsResponse>(server, "/events?after=2", alice.AccessToken)).Events.Length == 0, "Current cursor returned old events.");
            Require((await Get<StateResponse>(server, "/state", alice.AccessToken)).State == completed.State, "Snapshot differs from acknowledged event.");
            Require((await Get<EventsResponse>(server, "/events?after=0", bob.AccessToken)).Events.Length == 0, "One principal received another's events.");
            Require((await Get<StateResponse>(server, "/state", bob.AccessToken)).State == bobState, "One principal mutated another's state.");
            foreach (var path in new[] { "/events", "/events?after=-1", "/events?after=3", "/events?after=x", "/events?after=0&after=1", "/events?after=0&other=1" })
                await ExpectError(server, "GET", path, null, alice.AccessToken, 400, "invalid_cursor", null);
        });

        InteractionState reset = null!;
        await Check("reset clears completion message and preserves interaction identity", async () =>
        {
            reset = (await SuccessfulPost<CommandResponse>(server, "/commands", Command(server, completed.State, "reset"), alice.AccessToken)).State;
            Require(reset.Status == "available" && reset.Revision == 3 && reset.Message == "" && reset.InteractionId == aliceState.InteractionId, "Reset state differs from contract.");
        });

        await Check("concurrent commands at one revision produce exactly one mutation", async () =>
        {
            var commands = Enumerable.Range(0, 8).Select(_ => Command(server, reset, "accept")).ToArray();
            var replies = await Task.WhenAll(commands.Select(command => Post(server, "/commands", command, alice.AccessToken)));
            Require(replies.Count(reply => reply.Status == 200) == 1, "Concurrent commands did not produce exactly one success.");
            foreach (var reply in replies.Where(reply => reply.Status != 200))
                Require(reply.Status == 409 && reply.As<ApiError>().Error == "stale_revision", "Concurrent loser did not receive stale_revision.");
            var state = (await Get<StateResponse>(server, "/state", alice.AccessToken)).State;
            Require(state.Revision == 4 && state.Status == "accepted", "Concurrent commands created multiple revisions.");
            Require((await Get<EventsResponse>(server, "/events?after=3", alice.AccessToken)).Events.Length == 1, "Concurrent commands created multiple events.");
        });

        await Check("disconnect revokes only that session", async () =>
        {
            Require((await Send(server, "DELETE", "/session", null, alice.AccessToken)).Status == 204, "Disconnect failed.");
            await ExpectError(server, "GET", "/state", null, alice.AccessToken, 401, "invalid_session", null);
            Require((await Get<StateResponse>(server, "/state", reconnected.AccessToken)).State.Revision == 4, "Disconnect revoked a separate session.");
        });

        await Check("authenticated shutdown releases the port and records lifecycle/correlation", async () =>
        {
            await server.Stop();
            Require(server.ExitCode == 0, "Graceful server exit was nonzero.");
            RequirePortAvailable(server.Config.Port);
            Require(server.LogText.Contains("server_started", StringComparison.Ordinal) && server.LogText.Contains("server_stopping", StringComparison.Ordinal) && server.LogText.Contains("server_stopped", StringComparison.Ordinal), "Lifecycle log is incomplete.");
            Require(server.LogText.Contains(accept.RequestId.ToString(), StringComparison.OrdinalIgnoreCase) && server.LogText.Contains("TraceId", StringComparison.Ordinal), "Logs lack request/transport correlation.");
        });

        await Check("restart on the same port starts empty and applies changed configuration", async () =>
        {
            var restarted = CreateServer("restart", server.Config with { CompletionMessage = "Changed server rule observed after restart." });
            await restarted.Start();
            await ExpectError(restarted, "GET", "/state", null, reconnected.AccessToken, 401, "invalid_session", null);
            var session = await Connect(restarted, 0);
            var state = (await Get<StateResponse>(restarted, "/state", session.AccessToken)).State;
            Require(state.Revision == 0 && state.Status == "available" && state.InteractionId != aliceState.InteractionId, "Restart did not start empty memory.");
            Require((await Get<EventsResponse>(restarted, "/events?after=0", session.AccessToken)).Events.Length == 0, "Restart retained old events.");
            var next = await SuccessfulPost<CommandResponse>(restarted, "/commands", Command(restarted, state, "accept"), session.AccessToken);
            var final = await SuccessfulPost<CommandResponse>(restarted, "/commands", Command(restarted, next.State, "complete"), session.AccessToken);
            Require(final.State.Message == restarted.Config.CompletionMessage && final.State.Message != completed.State.Message, "Restart ignored changed message.");
            await restarted.Stop();
            RequirePortAvailable(restarted.Config.Port);
        });
    }

    private async Task ExerciseAdapter()
    {
        var server = CreateServer("adapter");
        var compatibility = AdapterCompatibility.Supported;
        SessionResponse adapter = null!;
        SessionResponse diagnostic = null!;
        SessionResponse bob = null!;
        InteractionState state = null!;
        await Check("compatible adapter and legacy diagnostic sessions share only their own principal state", async () =>
        {
            await server.Start();
            adapter = await Connect(server, 0, compatibility);
            diagnostic = await Connect(server, 0);
            bob = await Connect(server, 1, compatibility);
            state = (await Get<StateResponse>(server, "/state", adapter.AccessToken)).State;
            Require(state.Revision == 0 && state.Status == "available" && state.Message == "", "Adapter did not receive initial principal state.");
            Require((await Get<StateResponse>(server, "/state", diagnostic.AccessToken)).State == state,
                "Session scope created a separate principal contract.");
            // Omission remains valid, in addition to the explicit null sent by existing .NET callers.
            var legacy = Session(server, 0);
            var legacyJson = JsonSerializer.Serialize(legacy, Wire.Json).Replace(",\"adapter\":null", "", StringComparison.Ordinal);
            var admitted = await Send(server, "POST", "/sessions", legacyJson, null);
            Require(admitted.Status == 200, "Legacy session body without adapter was rejected.");
            secrets.Add(admitted.As<SessionResponse>().AccessToken);
        });

        await Check("adapter admission rejects exact version, game, storefront, and operation mismatches", async () =>
        {
            var baseline = Session(server, 0) with { Adapter = compatibility };
            var rejected = new (AdapterCompatibility Value, string Error)[]
            {
                (compatibility with { AdapterVersion = "0.1.0" }, "unsupported_adapter"),
                (compatibility with { AdapterVersion = null! }, "unsupported_adapter"),
                (compatibility with { GameSha256 = new string('0', 64) }, "unsupported_game"),
                (compatibility with { GameSha256 = compatibility.GameSha256.ToLowerInvariant() }, "unsupported_game"),
                (compatibility with { GameSha256 = null! }, "unsupported_game"),
                (compatibility with { Storefront = "Steam" }, "unsupported_game"),
                (compatibility with { Storefront = null! }, "unsupported_game"),
                (compatibility with { Operation = "arbitrary-native-call" }, "unsupported_operation"),
                (compatibility with { Operation = null! }, "unsupported_operation")
            };
            foreach (var (value, error) in rejected)
                await ExpectError(server, "POST", "/sessions", baseline with { Adapter = value }, null, 409, error, baseline.RequestId);
            await ExpectError(server, "POST", "/sessions", baseline with { Key = NewSecret() }, null,
                401, "invalid_credentials", baseline.RequestId);
            Require((await Get<StateResponse>(server, "/state", adapter.AccessToken)).State == state,
                "Rejected admissions changed existing state.");
        });

        await Check("adapter compatibility object rejects missing, duplicate, unknown, and wrongly typed fields", async () =>
        {
            var json = JsonSerializer.Serialize(Session(server, 0) with { Adapter = compatibility }, Wire.Json);
            var nested = JsonSerializer.Serialize(compatibility, Wire.Json);
            string[] malformed =
            [
                "{}", "[]", nested[..^1] + $",\"operation\":\"{compatibility.Operation}\"}}",
                nested[..^1] + ",\"actor\":\"bob\"}",
                nested.Replace($"\"adapterVersion\":\"{compatibility.AdapterVersion}\"", "\"adapterVersion\":2", StringComparison.Ordinal)
            ];
            foreach (var value in malformed)
                await ExpectRawError(server, "POST", "/sessions", json.Replace(nested, value, StringComparison.Ordinal),
                    null, 400, "invalid_json", null);
        });

        CommandRequest original = null!;
        Reply originalReply = null!;
        await Check("probe preserves contract status and emits one server-configured correlated event", async () =>
        {
            original = Command(server, state, "probe");
            originalReply = await Post(server, "/commands", original, adapter.AccessToken);
            Require(originalReply.Status == 200, "Adapter probe failed.");
            var response = originalReply.As<CommandResponse>();
            Require(response.ProtocolVersion == Wire.Version && response.RequestId == original.RequestId &&
                response.CommunityId == server.Config.CommunityId, "Probe response lost envelope correlation.");
            Require(response.State == state with { Revision = 1, Message = server.Config.CompletionMessage },
                "Probe changed status, identity, or returned the wrong configured message/revision.");
            Require(response.Event.EventId != Guid.Empty && response.Event.RequestId == original.RequestId &&
                response.Event.EventType == "interaction.probed" && response.Event.State == response.State,
                "Probe event differs from the acknowledged state.");
            var events = await Get<EventsResponse>(server, "/events?after=0", adapter.AccessToken);
            Require(events.Revision == 1 && events.Events.SequenceEqual([response.Event]), "Probe polling did not return the same single event.");
            Require((await Get<StateResponse>(server, "/state", bob.AccessToken)).State.Revision == 0,
                "Adapter mutated another principal.");
            state = response.State;
        });

        await Check("session scope is enforced before replaying either adapter or diagnostic commands", async () =>
        {
            await ExpectError(server, "POST", "/commands", original, diagnostic.AccessToken, 403, "adapter_required", original.RequestId);
            foreach (var type in new[] { "accept", "complete", "reset" })
            {
                var forbidden = Command(server, state, type);
                await ExpectError(server, "POST", "/commands", forbidden, adapter.AccessToken, 403, "session_scope", forbidden.RequestId);
            }
            var accept = Command(server, state, "accept");
            var accepted = await SuccessfulPost<CommandResponse>(server, "/commands", accept, diagnostic.AccessToken);
            Require(accepted.State.Status == "accepted" && accepted.State.Message == "" &&
                accepted.State.Revision == state.Revision + 1, "Diagnostic accept changed its existing behavior.");
            state = accepted.State;
            await ExpectError(server, "POST", "/commands", accept, adapter.AccessToken, 403, "session_scope", accept.RequestId);
            Require((await Get<StateResponse>(server, "/state", adapter.AccessToken)).State == state,
                "Rejected cross-scope replay mutated state.");
        });

        await Check("probe works in accepted and completed states without changing diagnostic transitions", async () =>
        {
            foreach (var expectedStatus in new[] { "accepted", "completed" })
            {
                var probed = await SuccessfulPost<CommandResponse>(server, "/commands", Command(server, state, "probe"), adapter.AccessToken);
                Require(probed.State == state with { Revision = state.Revision + 1, Message = server.Config.CompletionMessage } &&
                    probed.State.Status == expectedStatus && probed.Event.EventType == "interaction.probed",
                    "Probe did not preserve the current diagnostic status.");
                var transition = expectedStatus == "accepted" ? "complete" : "reset";
                var changed = await SuccessfulPost<CommandResponse>(server, "/commands", Command(server, probed.State, transition), diagnostic.AccessToken);
                Require(changed.Event.EventType == "interaction.changed" && changed.State.Revision == probed.State.Revision + 1,
                    "Diagnostic transition event changed.");
                state = changed.State;
            }
            Require(state.Status == "available" && state.Message == "", "Diagnostic reset did not clear the probe/completion message.");
        });

        await Check("probe replay, conflict, revision, and principal boundaries remain enforced", async () =>
        {
            var replay = await Post(server, "/commands", original, adapter.AccessToken);
            Require(replay.Status == 200 && replay.Body == originalReply.Body, "Probe replay changed an earlier response after subsequent commands.");
            await ExpectError(server, "POST", "/commands", original with { ExpectedRevision = state.Revision }, adapter.AccessToken,
                409, "request_id_conflict", original.RequestId);
            await ExpectError(server, "POST", "/commands", original with { Payload = new(Guid.NewGuid()) }, adapter.AccessToken,
                409, "request_id_conflict", original.RequestId);
            var stale = original with { RequestId = Guid.NewGuid() };
            await ExpectError(server, "POST", "/commands", stale, adapter.AccessToken, 409, "stale_revision", stale.RequestId);
            var invalid = Command(server, state, "probe");
            await ExpectError(server, "POST", "/commands", invalid with { ExpectedRevision = -1 }, adapter.AccessToken,
                400, "invalid_command", invalid.RequestId);
            await ExpectError(server, "POST", "/commands", invalid with { Payload = new(Guid.NewGuid()) }, adapter.AccessToken,
                404, "unknown_interaction", invalid.RequestId);
            await ExpectError(server, "POST", "/commands", invalid, bob.AccessToken, 404, "unknown_interaction", invalid.RequestId);
            Require((await Get<StateResponse>(server, "/state", adapter.AccessToken)).State == state,
                "Rejected or replayed probes mutated current state.");
        });

        await Check("concurrent probes at one revision commit exactly one response", async () =>
        {
            var attempts = Enumerable.Range(0, 8).Select(_ => Command(server, state, "probe")).ToArray();
            var replies = await Task.WhenAll(attempts.Select(command => Post(server, "/commands", command, adapter.AccessToken)));
            Require(replies.Count(reply => reply.Status == 200) == 1, "Concurrent probes produced multiple mutations.");
            foreach (var reply in replies.Where(reply => reply.Status != 200))
                Require(reply.Status == 409 && reply.As<ApiError>().Error == "stale_revision", "Concurrent probe loser did not receive stale_revision.");
            var events = await Get<EventsResponse>(server, $"/events?after={state.Revision}", adapter.AccessToken);
            Require(events.Events.Length == 1 && events.Revision == state.Revision + 1, "Concurrent probes produced the wrong event count.");
            state = events.Events[0].State;
        });

        await Check("adapter reconnect recovers current principal state and original replay while revoking only the old session", async () =>
        {
            Require((await Send(server, "DELETE", "/session", null, adapter.AccessToken)).Status == 204, "Adapter disconnect failed.");
            await ExpectError(server, "POST", "/commands", original, adapter.AccessToken, 401, "invalid_session", original.RequestId);
            adapter = await Connect(server, 0, compatibility);
            Require((await Get<StateResponse>(server, "/state", adapter.AccessToken)).State == state, "Adapter reconnect lost current principal state.");
            var replay = await Post(server, "/commands", original, adapter.AccessToken);
            Require(replay.Status == 200 && replay.Body == originalReply.Body, "Adapter reconnect lost probe deduplication.");
            Require((await Get<StateResponse>(server, "/state", diagnostic.AccessToken)).State == state, "Adapter disconnect revoked the diagnostic session.");
            var bobState = (await Get<StateResponse>(server, "/state", bob.AccessToken)).State;
            var ownRequest = Command(server, bobState, "probe") with { RequestId = original.RequestId };
            var ownReply = await SuccessfulPost<CommandResponse>(server, "/commands", ownRequest, bob.AccessToken);
            Require(ownReply.State.InteractionId == bobState.InteractionId && ownReply.State.Revision == 1 &&
                ownReply.Event.EventId != originalReply.As<CommandResponse>().Event.EventId,
                "Request deduplication leaked between principals.");
        });

        await Check("probe shares the 256-command bound and retains successful replay at capacity", async () =>
        {
            while (state.Revision < 256)
                state = (await SuccessfulPost<CommandResponse>(server, "/commands", Command(server, state, "probe"), adapter.AccessToken)).State;
            var overflow = Command(server, state, "probe");
            await ExpectError(server, "POST", "/commands", overflow, adapter.AccessToken, 429, "interaction_capacity", overflow.RequestId);
            var replay = await Post(server, "/commands", original, adapter.AccessToken);
            Require(replay.Status == 200 && replay.Body == originalReply.Body, "Capacity evicted the first successful probe.");
            var events = await Get<EventsResponse>(server, "/events?after=0", adapter.AccessToken);
            Require(events.Revision == 256 && events.Events.Length == 256 &&
                (await Get<StateResponse>(server, "/state", adapter.AccessToken)).State == state,
                "Capacity rejection changed state or event retention.");
        });

        await Check("adapter server restart invalidates sessions and interaction IDs and returns changed configuration", async () =>
        {
            await server.Stop();
            var restarted = CreateServer("adapter-restart", server.Config with { CompletionMessage = "Changed adapter response after service restart." });
            await restarted.Start();
            await ExpectError(restarted, "GET", "/state", null, adapter.AccessToken, 401, "invalid_session", null);
            var session = await Connect(restarted, 0, compatibility);
            var fresh = (await Get<StateResponse>(restarted, "/state", session.AccessToken)).State;
            Require(fresh.Revision == 0 && fresh.Message == "" && fresh.InteractionId != state.InteractionId, "Restart retained adapter memory.");
            await ExpectError(restarted, "POST", "/commands", original, session.AccessToken, 404, "unknown_interaction", original.RequestId);
            var response = await SuccessfulPost<CommandResponse>(restarted, "/commands", Command(restarted, fresh, "probe"), session.AccessToken);
            Require(response.State.Revision == 1 && response.State.Status == "available" &&
                response.State.Message == restarted.Config.CompletionMessage && response.State.Message != state.Message,
                "Adapter probe ignored changed server configuration.");
            await restarted.Stop();
        });
    }

    private async Task ExerciseExpiry()
    {
        await Check("short-lived session expires and is removed", async () =>
        {
            var server = CreateServer("expiry", NewConfig() with { SessionLifetimeSeconds = 1 });
            await server.Start();
            var session = await Connect(server, 0);
            Require((await Get<StateResponse>(server, "/state", session.AccessToken)).State.Revision == 0, "Fresh short-lived session failed.");
            var remaining = session.ExpiresAt - DateTimeOffset.UtcNow + TimeSpan.FromMilliseconds(150);
            if (remaining > TimeSpan.Zero) await Task.Delay(remaining);
            await ExpectError(server, "GET", "/state", null, session.AccessToken, 401, "expired_session", null);
            await ExpectError(server, "GET", "/state", null, session.AccessToken, 401, "invalid_session", null);
            await server.Stop();
        });
    }

    private async Task ExerciseConfiguration()
    {
        await Check("public binding and invalid startup configuration fail before listening", async () =>
        {
            var baseline = NewConfig();
            var variants = new (string Name, ServerConfig Config)[]
            {
                ("public-bind", baseline with { BindAddress = "0.0.0.0" }),
                ("privileged-port", baseline with { Port = 1 }),
                ("empty-message", baseline with { CompletionMessage = "" }),
                ("invalid-community", baseline with { CommunityId = "community\n" }),
                ("path-escape", baseline with { DataDirectory = "../outside" }),
                ("duplicate-keys", baseline with { AdminKey = baseline.Principals[0].Key })
            };
            foreach (var variant in variants)
            {
                var server = CreateServer(variant.Name, variant.Config);
                await server.StartRejected();
                Require(server.ExitCode == 2 && server.LogText.Contains("Startup failed", StringComparison.Ordinal), "Invalid startup did not fail with the documented exit.");
            }
            RequirePortAvailable(baseline.Port);
            var duplicate = CreateServer("duplicate-config", NewConfig());
            var json = JsonSerializer.Serialize(duplicate.Config, Wire.Json);
            await duplicate.StartRejected(json[..^1] + ",\"port\":12345}");
            Require(duplicate.ExitCode == 2, "Duplicate configuration field was accepted.");
        });

        await Check("ambient URL and Kestrel settings cannot change loopback binding", async () =>
        {
            var unwantedPort = FreePort();
            var server = CreateServer("environment-binding");
            while (unwantedPort == server.Config.Port) unwantedPort = FreePort();
            var unwantedUrl = $"http://0.0.0.0:{unwantedPort}";
            await server.Start(new()
            {
                ["ASPNETCORE_URLS"] = unwantedUrl,
                ["DOTNET_URLS"] = unwantedUrl,
                ["ASPNETCORE_HTTP_PORTS"] = unwantedPort.ToString(),
                ["ASPNETCORE_HTTPS_PORTS"] = unwantedPort.ToString(),
                ["Kestrel__Endpoints__Public__Url"] = unwantedUrl
            });
            var listeners = IPGlobalProperties.GetIPGlobalProperties().GetActiveTcpListeners().Where(endpoint => endpoint.Port == server.Config.Port).ToArray();
            Require(listeners.Length > 0 && listeners.All(endpoint => endpoint.Address.Equals(IPAddress.Loopback)), "Server exposed a non-loopback listener.");
            RequirePortAvailable(unwantedPort);
            Require((await Get<HealthResponse>(server, "/health")).Status == "ready", "Configured endpoint stopped responding.");
            await server.Stop();
        });
    }

    private async Task ExerciseDiagnosticClient()
    {
        await Check("diagnostic client completes, replays, and rejects malformed input against a real server", async () =>
        {
            var server = CreateServer("diagnostic");
            await server.Start();
            var modes = new (string Mode, string Expected)[]
            {
                ("demo", server.Config.CompletionMessage),
                ("duplicate", "Duplicate returned the same event and revision."),
                ("malformed", "invalid_json")
            };
            foreach (var (mode, expected) in modes)
            {
                var output = await server.RunDiagnostic(mode);
                Require(output.Contains(expected, StringComparison.Ordinal), "Diagnostic output did not report the expected behavior.");
                Require(!output.Contains("accessToken", StringComparison.OrdinalIgnoreCase), "Diagnostic output exposed the token field.");
                foreach (var secret in secrets)
                    Require(!output.Contains(secret, StringComparison.Ordinal), "Diagnostic output exposed a configured credential or known token.");
            }
            var session = await Connect(server, 0);
            var state = (await Get<StateResponse>(server, "/state", session.AccessToken)).State;
            Require(state.Revision == 3 && state.Status == "available", "Diagnostic operations produced unexpected server state.");
            await server.Stop();
        });
    }

    private async Task Check(string name, Func<Task> action)
    {
        currentCheck = name;
        await action();
        passed++;
        Console.WriteLine($"PASS {name}");
    }

    private TestServer CreateServer(string name, ServerConfig? config = null)
    {
        config ??= NewConfig();
        secrets.Add(config.AdminKey);
        foreach (var principal in config.Principals) secrets.Add(principal.Key);
        var server = new TestServer(repository, Path.Combine(runDirectory, name), config);
        servers.Add(server);
        return server;
    }

    private static ServerConfig NewConfig() => new("127.0.0.1", FreePort(), "original-test-community", "data",
        "Original configurable completion message.", 120, NewSecret(), [new("alice", NewSecret()), new("bob", NewSecret())]);

    private static string NewSecret() => Convert.ToHexString(RandomNumberGenerator.GetBytes(32));

    private static int FreePort()
    {
        var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        try { return ((IPEndPoint)listener.LocalEndpoint).Port; }
        finally { listener.Stop(); }
    }

    private static void RequirePortAvailable(int port)
    {
        var listener = new TcpListener(IPAddress.Loopback, port);
        try { listener.Start(); }
        finally { listener.Stop(); }
    }

    private static SessionRequest Session(TestServer server, int principal) => new(Wire.Version, server.Config.CommunityId,
        Guid.NewGuid(), server.Config.Principals[principal].Id, server.Config.Principals[principal].Key);

    private async Task<SessionResponse> Connect(TestServer server, int principal, AdapterCompatibility? adapter = null)
    {
        var request = Session(server, principal) with { Adapter = adapter };
        var response = await SuccessfulPost<SessionResponse>(server, "/sessions", request);
        Require(response.ProtocolVersion == Wire.Version && response.CommunityId == server.Config.CommunityId && response.RequestId == request.RequestId && response.SessionId != Guid.Empty, "Session envelope is invalid.");
        Require(response.AccessToken.Length >= 32 && response.ExpiresAt > DateTimeOffset.UtcNow, "Session token/expiry is invalid.");
        secrets.Add(response.AccessToken);
        return response;
    }

    private static CommandRequest Command(TestServer server, InteractionState state, string type) =>
        new(Wire.Version, server.Config.CommunityId, Guid.NewGuid(), state.Revision, type, new(state.InteractionId));

    private string Fixture(string file, TestServer server, CommandRequest command) =>
        File.ReadAllText(Path.Combine(repository, "fixtures", "protocol", file))
            .Replace("__COMMUNITY_ID__", server.Config.CommunityId, StringComparison.Ordinal)
            .Replace("__REQUEST_ID__", command.RequestId.ToString(), StringComparison.Ordinal)
            .Replace("__INTERACTION_ID__", command.Payload.InteractionId.ToString(), StringComparison.Ordinal);

    private static async Task<T> Get<T>(TestServer server, string path, string? token = null)
    {
        var reply = await Send(server, "GET", path, null, token);
        Require(reply.Status == 200, $"GET {path} returned HTTP {reply.Status}.");
        return reply.As<T>();
    }

    private static Task<Reply> Post(TestServer server, string path, object body, string? token = null) =>
        Send(server, "POST", path, JsonSerializer.Serialize(body, Wire.Json), token);

    private static async Task<T> SuccessfulPost<T>(TestServer server, string path, object body, string? token = null)
    {
        var reply = await Post(server, path, body, token);
        Require(reply.Status == 200, $"POST {path} returned HTTP {reply.Status}.");
        return reply.As<T>();
    }

    private static Task ExpectError(TestServer server, string method, string path, object? body, string? token,
        int status, string error, Guid? requestId) => ExpectRawError(server, method, path,
            body is null ? null : JsonSerializer.Serialize(body, Wire.Json), token, status, error, requestId);

    private static async Task ExpectRawError(TestServer server, string method, string path, string? body, string? token,
        int status, string error, Guid? requestId, string contentType = "application/json", Dictionary<string, string>? headers = null)
    {
        var reply = await Send(server, method, path, body, token, contentType, headers);
        Require(reply.Status == status, $"{method} {path}: expected HTTP {status}, received {reply.Status}.");
        var envelope = reply.As<ApiError>();
        Require(envelope.ProtocolVersion == Wire.Version && envelope.RequestId == requestId && envelope.Error == error,
            $"{method} {path}: expected error {error} with the contract request ID.");
    }

    private static async Task<Reply> Send(TestServer server, string method, string path, string? body, string? token,
        string contentType = "application/json", Dictionary<string, string>? headers = null)
    {
        // Normal sequences remain below the service's 100 requests/second budget.
        await Task.Delay(25);
        using var request = new HttpRequestMessage(new HttpMethod(method), path);
        if (token is not null) request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        if (body is not null)
        {
            request.Content = new ByteArrayContent(Encoding.UTF8.GetBytes(body));
            request.Content.Headers.ContentType = MediaTypeHeaderValue.Parse(contentType);
        }
        if (headers is not null)
            foreach (var (name, value) in headers) request.Headers.TryAddWithoutValidation(name, value);
        using var response = await server.Client.SendAsync(request);
        var text = await response.Content.ReadAsStringAsync();
        if ((int)response.StatusCode != 204)
            Require(response.Content.Headers.ContentType?.MediaType == "application/json", "API response did not declare JSON.");
        return new((int)response.StatusCode, text);
    }

    internal static void Require(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }

    public async ValueTask DisposeAsync()
    {
        foreach (var server in servers) await server.DisposeAsync();
    }

    private sealed record Reply(int Status, string Body)
    {
        public T As<T>() => Wire.Parse<T>(Encoding.UTF8.GetBytes(Body));
    }
}

internal sealed class TestServer : IAsyncDisposable
{
    private readonly string repository;
    private readonly string directory;
    private Process? process;
    private Task<string>? standardOutput;
    private Task<string>? standardError;
    private bool logsSaved;
    public ServerConfig Config { get; }
    public HttpClient Client { get; }
    public string LogText { get; private set; } = "";
    public int? ExitCode => process is { HasExited: true } ? process.ExitCode : null;

    public TestServer(string repository, string directory, ServerConfig config)
    {
        this.repository = repository;
        this.directory = directory;
        Config = config;
        Client = new(new SocketsHttpHandler { UseProxy = false, AllowAutoRedirect = false })
        {
            BaseAddress = new Uri($"http://127.0.0.1:{config.Port}"), Timeout = TimeSpan.FromSeconds(10)
        };
    }

    public async Task Start(Dictionary<string, string>? environment = null)
    {
        await Launch(null, environment);
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(12));
        while (!deadline.IsCancellationRequested)
        {
            IntegrationSuite.Require(process is { HasExited: false }, "Child server exited before becoming healthy.");
            try
            {
                using var reply = await Client.GetAsync("/health", deadline.Token);
                if (reply.IsSuccessStatusCode) return;
            }
            catch (HttpRequestException) { }
            await Task.Delay(75, deadline.Token);
        }
        throw new TimeoutException("Child server did not become ready.");
    }

    public async Task StartRejected(string? rawConfiguration = null)
    {
        await Launch(rawConfiguration, null);
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(8));
        await process!.WaitForExitAsync(deadline.Token);
        await SaveLogs();
    }

    private async Task Launch(string? rawConfiguration, Dictionary<string, string>? environment)
    {
        Directory.CreateDirectory(directory);
        var configurationPath = Path.Combine(directory, "server.json");
        await File.WriteAllTextAsync(configurationPath, rawConfiguration ?? JsonSerializer.Serialize(Config, Wire.Json));
        var start = new ProcessStartInfo(DotnetHost())
        {
            WorkingDirectory = repository,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        start.ArgumentList.Add(Path.Combine(repository, "src", "Community.Server", "bin", "Release", "net10.0", "Community.Server.dll"));
        start.ArgumentList.Add("--config");
        start.ArgumentList.Add(configurationPath);
        if (environment is not null)
            foreach (var (name, value) in environment) start.Environment[name] = value;
        process = Process.Start(start) ?? throw new InvalidOperationException("Could not start child server.");
        standardOutput = process.StandardOutput.ReadToEndAsync();
        standardError = process.StandardError.ReadToEndAsync();
    }

    private static string DotnetHost()
    {
        var current = Environment.ProcessPath;
        return current is not null && Path.GetFileNameWithoutExtension(current).Equals("dotnet", StringComparison.OrdinalIgnoreCase)
            ? current : Environment.GetEnvironmentVariable("DOTNET_HOST_PATH") ?? "dotnet";
    }

    public static async Task<(int ExitCode, string Output)> InitializeConfiguration(string repository, string path)
    {
        var start = new ProcessStartInfo(DotnetHost())
        {
            WorkingDirectory = Path.GetTempPath(), UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardOutput = true, RedirectStandardError = true
        };
        foreach (var argument in new[]
        {
            Path.Combine(repository, "src", "Community.Server", "bin", "Release", "net10.0", "Community.Server.dll"),
            "--init", "--config", path
        }) start.ArgumentList.Add(argument);
        using var child = Process.Start(start) ?? throw new InvalidOperationException("Could not start configuration initializer.");
        var output = child.StandardOutput.ReadToEndAsync();
        var errors = child.StandardError.ReadToEndAsync();
        try
        {
            using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(10));
            await child.WaitForExitAsync(deadline.Token);
            var text = await output + await errors;
            await File.AppendAllTextAsync(Path.ChangeExtension(path, ".log"), text);
            return (child.ExitCode, text);
        }
        finally
        {
            if (!child.HasExited)
            {
                child.Kill(entireProcessTree: true);
                await child.WaitForExitAsync();
            }
        }
    }

    public async Task<string> RunDiagnostic(string mode)
    {
        var start = new ProcessStartInfo(DotnetHost())
        {
            WorkingDirectory = repository, UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardOutput = true, RedirectStandardError = true
        };
        foreach (var argument in new[]
        {
            Path.Combine(repository, "src", "Community.Client", "bin", "Release", "net10.0", "Community.Client.dll"),
            "--config", Path.Combine(directory, "server.json"), "--principal", "alice", "--mode", mode
        }) start.ArgumentList.Add(argument);
        using var child = Process.Start(start) ?? throw new InvalidOperationException("Could not start diagnostic client.");
        var output = child.StandardOutput.ReadToEndAsync();
        var errors = child.StandardError.ReadToEndAsync();
        try
        {
            using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(15));
            await child.WaitForExitAsync(deadline.Token);
            var text = await output + await errors;
            await File.WriteAllTextAsync(Path.Combine(directory, $"client-{mode}.log"), text);
            IntegrationSuite.Require(child.ExitCode == 0, "Diagnostic client returned nonzero.");
            return text;
        }
        finally
        {
            if (!child.HasExited)
            {
                child.Kill(entireProcessTree: true);
                await child.WaitForExitAsync();
            }
        }
    }

    public async Task Stop()
    {
        IntegrationSuite.Require(process is { HasExited: false }, "Server was not running before shutdown.");
        using var request = new HttpRequestMessage(HttpMethod.Post, "/admin/stop");
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", Config.AdminKey);
        using var response = await Client.SendAsync(request);
        IntegrationSuite.Require(response.StatusCode == HttpStatusCode.OK, "Authenticated shutdown request failed.");
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(8));
        await process!.WaitForExitAsync(deadline.Token);
        await SaveLogs();
    }

    private async Task SaveLogs()
    {
        if (logsSaved || standardOutput is null || standardError is null) return;
        var output = await standardOutput;
        var errors = await standardError;
        await File.WriteAllTextAsync(Path.Combine(directory, "stdout.jsonl"), output);
        await File.WriteAllTextAsync(Path.Combine(directory, "stderr.log"), errors);
        LogText = output + errors;
        logsSaved = true;
    }

    public async ValueTask DisposeAsync()
    {
        try
        {
            if (process is { HasExited: false })
            {
                try { await Stop(); }
                catch (Exception exception) when (exception is HttpRequestException or OperationCanceledException or InvalidOperationException)
                {
                    // Only terminate the specific child created by this test instance.
                    if (!process.HasExited) process.Kill(entireProcessTree: true);
                    await process.WaitForExitAsync();
                }
            }
            await SaveLogs();
        }
        finally
        {
            Client.Dispose();
            process?.Dispose();
        }
    }
}
