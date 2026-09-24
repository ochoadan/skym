using System.Net;
using System.Text.Json;
using System.Threading.RateLimiting;
using Community.Protocol;
using Community.Server;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using Microsoft.Data.Sqlite;

var initialize = args is ["--init", "--config", _];
var migrate = args is ["--migrate", "--config", _];
var backup = args is ["--backup", _, "--config", _];
var restore = args is ["--restore", _, "--config", _];
if (!initialize && !migrate && !backup && !restore && args is not ["--config", _])
{
    Console.Error.WriteLine("Usage: Community.Server [--init | --migrate | --backup <new file> | --restore <backup>] --config <local server.json>");
    return 2;
}

try
{
    if (initialize)
    {
        Configuration.Initialize(args[2]);
        Console.WriteLine("Created private lab configuration with random keys. Keep this file out of Git.");
        return 0;
    }
    var configurationPath = args[^1];
    var config = Configuration.Load(configurationPath);
    var databasePath = Configuration.DatabasePath(configurationPath, config);
    if (backup || restore)
    {
        if (backup) PersistentStore.Backup(databasePath, args[1], config.CommunityId);
        else PersistentStore.Restore(databasePath, args[1], config.CommunityId);
        Console.WriteLine(backup ? "Verified offline backup created." : "Verified backup restored to a new database. Start the service to reconnect.");
        return 0;
    }
    using var store = new PersistentStore(config, databasePath);
    if (migrate)
    {
        Console.WriteLine($"Database schema {PersistentStore.SchemaVersion} is ready. Unsupported schemas are never downgraded or reset.");
        return 0;
    }
    var runtime = new LabRuntime(config, store);
    var builder = WebApplication.CreateSlimBuilder(new WebApplicationOptions { Args = [] });
    // No URLs, endpoints, or secrets can be injected through ambient web-host configuration.
    builder.Configuration.Sources.Clear();
    builder.Logging.ClearProviders();
    builder.Logging.AddJsonConsole(options =>
    {
        options.IncludeScopes = false;
        options.UseUtcTimestamp = true;
        options.TimestampFormat = "O";
    });
    builder.Logging.AddFilter("Microsoft", LogLevel.None);
    builder.Services.Configure<HostOptions>(options => options.ShutdownTimeout = TimeSpan.FromSeconds(5));
    builder.WebHost.ConfigureKestrel(options =>
    {
        options.AddServerHeader = false;
        options.Listen(IPAddress.Loopback, config.Port, listen => listen.Protocols = HttpProtocols.Http1);
        options.Limits.MaxRequestBodySize = Wire.BodyLimit;
        options.Limits.MaxRequestHeadersTotalSize = 8192;
        options.Limits.MaxRequestLineSize = 1024;
        options.Limits.MaxConcurrentConnections = 32;
        options.Limits.RequestHeadersTimeout = TimeSpan.FromSeconds(5);
        options.Limits.KeepAliveTimeout = TimeSpan.FromSeconds(10);
    });
    builder.Services.AddRateLimiter(options =>
    {
        options.GlobalLimiter = PartitionedRateLimiter.Create<HttpContext, string>(_ =>
            RateLimitPartition.GetFixedWindowLimiter("lab", _ => new FixedWindowRateLimiterOptions
            {
                PermitLimit = 100, Window = TimeSpan.FromSeconds(1), QueueLimit = 0
            }));
        options.OnRejected = async (context, cancellation) =>
        {
            context.HttpContext.Response.StatusCode = 429;
            await context.HttpContext.Response.WriteAsJsonAsync(new ApiError(Wire.Version, null, "rate_limited"), Wire.Json, cancellation);
        };
    });
    var app = builder.Build();
    var logger = app.Logger;
    app.Use(async (context, next) =>
    {
        try
        {
            if (context.Request.Host.Value != $"127.0.0.1:{config.Port}") throw new ApiFault(400, "invalid_host");
            if (context.Request.Headers.ContainsKey("Origin") || context.Request.Headers.ContainsKey("Sec-Fetch-Site"))
                throw new ApiFault(403, "browser_not_allowed");
            await next(context);
        }
        catch (ApiFault fault)
        {
            logger.LogInformation("request_rejected {TraceId} {RequestId} {Code}", context.TraceIdentifier, RequestId(context), fault.Code);
            context.Response.StatusCode = fault.Status;
            await context.Response.WriteAsJsonAsync(new ApiError(Wire.Version, RequestId(context), fault.Code), Wire.Json);
        }
        catch (Microsoft.AspNetCore.Http.BadHttpRequestException fault)
        {
            context.Response.StatusCode = fault.StatusCode;
            await context.Response.WriteAsJsonAsync(new ApiError(Wire.Version, RequestId(context), "invalid_http_body"), Wire.Json);
        }
        catch (OperationCanceledException) when (context.RequestAborted.IsCancellationRequested) { }
        catch (Exception fault) when (fault is SqliteException or StorageFault)
        {
            // An error or lost response may follow a committed mutation; query/replay it after recovery.
            // Do not serialize database paths, SQL, principal data, or raw exception messages.
            var code = fault is StorageFault storage ? storage.Code : "storage_unavailable";
            logger.LogError("storage_failure {TraceId} {RequestId} {Code}", context.TraceIdentifier, RequestId(context), code);
            context.Response.StatusCode = 503;
            await context.Response.WriteAsJsonAsync(new ApiError(Wire.Version, RequestId(context), "storage_unavailable"), Wire.Json);
        }
        finally
        {
            // Never log bodies, query strings, headers, tokens, or arbitrary paths.
            logger.LogInformation("request {TraceId} {RequestId} {StatusCode}", context.TraceIdentifier, RequestId(context), context.Response.StatusCode);
        }
    });
    app.UseRateLimiter();
    app.MapGet("/health", () => Results.Json(new HealthResponse(Wire.Version, config.CommunityId, "ready"), Wire.Json));
    app.MapPost("/sessions", async (HttpContext context) =>
    {
        var request = await Read<SessionRequest>(context);
        context.Items["requestId"] = request.RequestId;
        var response = runtime.Connect(request);
        logger.LogInformation("session_opened {SessionId} {RequestId}", response.SessionId, response.RequestId);
        return Results.Json(response, Wire.Json);
    });
    app.MapDelete("/session", (HttpContext context) =>
    {
        runtime.Disconnect(Bearer(context));
        logger.LogInformation("session_closed {TraceId}", context.TraceIdentifier);
        return Results.NoContent();
    });
    app.MapGet("/state", (HttpContext context) => Results.Json(runtime.State(Bearer(context)), Wire.Json));
    app.MapGet("/events", (HttpContext context) =>
    {
        if (context.Request.Query.Count != 1 || context.Request.Query["after"].Count != 1 ||
            !long.TryParse(context.Request.Query["after"], out var after)) throw new ApiFault(400, "invalid_cursor");
        return Results.Json(runtime.Events(Bearer(context), after), Wire.Json);
    });
    app.MapPost("/commands", async (HttpContext context) =>
    {
        var token = Bearer(context);
        var request = await Read<CommandRequest>(context);
        context.Items["requestId"] = request.RequestId;
        return Results.Json(runtime.Command(token, request), Wire.Json);
    });
    app.MapPost("/admin/stop", (HttpContext context) =>
    {
        if (!LabRuntime.SecretEquals(Bearer(context), config.AdminKey)) throw new ApiFault(401, "invalid_credentials");
        context.Response.OnCompleted(() => { app.Lifetime.StopApplication(); return Task.CompletedTask; });
        return Results.Json(new { status = "stopping" }, Wire.Json);
    });
    app.Lifetime.ApplicationStarted.Register(() => logger.LogInformation("server_started {CommunityId} {Port} {ProtocolVersion}", config.CommunityId, config.Port, Wire.Version));
    app.Lifetime.ApplicationStopping.Register(() => logger.LogInformation("server_stopping"));
    app.Lifetime.ApplicationStopped.Register(() => logger.LogInformation("server_stopped"));
    await app.RunAsync();
    await app.DisposeAsync();
    return 0;
}
catch (Exception exception) when (exception is IOException or InvalidDataException or JsonException or UnauthorizedAccessException or ArgumentException or InvalidOperationException or SqliteException or StorageFault)
{
    // Parser/startup exceptions may contain configuration values. Report only the category.
    Console.Error.WriteLine(initialize
        ? $"Initialization failed ({exception.GetType().Name}). Use a writable path to a new file; existing files are never overwritten."
        : $"Startup or storage operation failed ({(exception is StorageFault storage ? storage.Code : exception.GetType().Name)}). Check configuration, port and database ownership/schema; see the T-04.4 runbook. Existing databases are never reset.");
    return 2;
}

static Guid? RequestId(HttpContext context) => context.Items.TryGetValue("requestId", out var value) && value is Guid id ? id : null;
static string Bearer(HttpContext context)
{
    var header = context.Request.Headers.Authorization;
    if (header.Count != 1 || header[0] is not string value || !value.StartsWith("Bearer ", StringComparison.Ordinal) || value.Length is < 8 or > 135)
        throw new ApiFault(401, "invalid_credentials");
    return value[7..];
}

static async Task<T> Read<T>(HttpContext context)
{
    Microsoft.Net.Http.Headers.MediaTypeHeaderValue? contentType;
    try { contentType = context.Request.GetTypedHeaders().ContentType; }
    catch (FormatException) { throw new ApiFault(415, "json_required"); }
    if (contentType?.MediaType.Value != "application/json" ||
        (contentType.Charset.HasValue && !contentType.Charset.Value!.Equals("utf-8", StringComparison.OrdinalIgnoreCase)))
        throw new ApiFault(415, "json_required");
    using var timeout = CancellationTokenSource.CreateLinkedTokenSource(context.RequestAborted);
    timeout.CancelAfter(TimeSpan.FromSeconds(3));
    try
    {
        using var buffer = new MemoryStream();
        var chunk = new byte[1024];
        int count;
        while ((count = await context.Request.Body.ReadAsync(chunk, timeout.Token)) != 0)
        {
            if (buffer.Length + count > Wire.BodyLimit) throw new ApiFault(413, "body_too_large");
            buffer.Write(chunk, 0, count);
        }
        return Wire.Parse<T>(buffer.ToArray());
    }
    catch (JsonException) { throw new ApiFault(400, "invalid_json"); }
    catch (OperationCanceledException) when (!context.RequestAborted.IsCancellationRequested) { throw new ApiFault(408, "body_timeout"); }
}
