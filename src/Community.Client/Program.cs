using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using Community.Protocol;

try
{
    var options = new Dictionary<string, string>(StringComparer.Ordinal);
    if (args.Length % 2 != 0) throw new ArgumentException();
    for (var i = 0; i < args.Length; i += 2)
        if (args[i] is not ("--config" or "--principal" or "--mode") || !options.TryAdd(args[i], args[i + 1])) throw new ArgumentException();
    if (!options.TryGetValue("--config", out var path)) throw new ArgumentException();
    var mode = options.GetValueOrDefault("--mode", "demo");
    var principalId = options.GetValueOrDefault("--principal", "alice");
    var config = Wire.Parse<ServerConfig>(File.ReadAllBytes(path));
    if (config.BindAddress != "127.0.0.1" || config.Port is < 1024 or > 65535) throw new ArgumentException();
    using var handler = new HttpClientHandler { UseProxy = false, AllowAutoRedirect = false };
    using var client = new HttpClient(handler) { BaseAddress = new Uri($"http://127.0.0.1:{config.Port}"), Timeout = TimeSpan.FromSeconds(6) };
    if (mode == "health")
    {
        Print(await Get<HealthResponse>(client, "/health"));
        return 0;
    }
    if (mode == "stop")
    {
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", config.AdminKey);
        using var stop = await client.PostAsync("/admin/stop", null);
        stop.EnsureSuccessStatusCode();
        Console.WriteLine("Server accepted graceful shutdown.");
        return 0;
    }
    if (mode is not ("demo" or "duplicate" or "malformed" or "state" or "events")) throw new ArgumentException();
    var principal = config.Principals.Single(p => p.Id == principalId);
    var session = await Post<SessionRequest, SessionResponse>(client, "/sessions",
        new(Wire.Version, config.CommunityId, Guid.NewGuid(), principal.Id, principal.Key));
    client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", session.AccessToken);
    try
    {
        var snapshot = await Get<StateResponse>(client, "/state");
        if (mode == "state") Print(snapshot);
        else if (mode == "events") Print(await Get<EventsResponse>(client, "/events?after=0"));
        else if (mode == "malformed")
        {
            using var response = await client.PostAsync("/commands", new StringContent("{", Encoding.UTF8, "application/json"));
            if (response.StatusCode != HttpStatusCode.BadRequest) throw new InvalidOperationException("Expected 400.");
            Print(await response.Content.ReadFromJsonAsync<ApiError>(Wire.Json) ?? throw new JsonException());
        }
        else if (mode == "duplicate")
        {
            var command = Command(config, snapshot.State, snapshot.State.Status switch { "available" => "accept", "accepted" => "complete", _ => "reset" });
            var first = await Post<CommandRequest, CommandResponse>(client, "/commands", command);
            var replay = await Post<CommandRequest, CommandResponse>(client, "/commands", command);
            if (first != replay) throw new InvalidOperationException("Replay changed the response.");
            Print(replay);
            Console.WriteLine("Duplicate returned the same event and revision.");
        }
        else
        {
            var state = snapshot.State;
            if (state.Status == "completed") state = (await Send("reset", state)).State;
            if (state.Status == "available") state = (await Send("accept", state)).State;
            var completed = await Send("complete", state);
            if (completed.State.Status != "completed" || completed.State.Message != config.CompletionMessage)
                throw new InvalidOperationException("Unexpected server result.");
            Print(await Get<EventsResponse>(client, $"/events?after={snapshot.State.Revision}"));
            Print(await Get<StateResponse>(client, "/state"));

            async Task<CommandResponse> Send(string type, InteractionState current)
            {
                var response = await Post<CommandRequest, CommandResponse>(client, "/commands", Command(config, current, type));
                Print(response);
                return response;
            }
        }
    }
    finally
    {
        using var disconnected = await client.DeleteAsync("/session");
        disconnected.EnsureSuccessStatusCode();
    }
    return 0;
}
catch (Exception exception) when (exception is HttpRequestException or TaskCanceledException or IOException or JsonException or ArgumentException or InvalidOperationException)
{
    Console.Error.WriteLine($"Diagnostic failed ({exception.GetType().Name}). Check that the server is running and the local config matches it.");
    Console.Error.WriteLine("Usage: Community.Client --config <server.json> [--principal alice|bob] [--mode demo|state|events|duplicate|malformed|health|stop]");
    return 1;
}

static CommandRequest Command(ServerConfig config, InteractionState state, string type) =>
    new(Wire.Version, config.CommunityId, Guid.NewGuid(), state.Revision, type, new(state.InteractionId));
static void Print<T>(T value) => Console.WriteLine(JsonSerializer.Serialize(value, Wire.Json));
static async Task<T> Get<T>(HttpClient client, string path)
{
    using var response = await client.GetAsync(path);
    response.EnsureSuccessStatusCode();
    return await response.Content.ReadFromJsonAsync<T>(Wire.Json) ?? throw new JsonException();
}
static async Task<TResponse> Post<TRequest, TResponse>(HttpClient client, string path, TRequest body)
{
    using var response = await client.PostAsJsonAsync(path, body, Wire.Json);
    response.EnsureSuccessStatusCode();
    return await response.Content.ReadFromJsonAsync<TResponse>(Wire.Json) ?? throw new JsonException();
}
