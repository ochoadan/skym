using System.Text.Json;
using System.Text.Json.Serialization;

namespace Community.Protocol;

public static class Wire
{
    public const int Version = 1;
    public const int BodyLimit = 4096;
    public static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web)
    {
        PropertyNameCaseInsensitive = false,
        NumberHandling = JsonNumberHandling.Strict,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        RespectRequiredConstructorParameters = true,
        MaxDepth = 8
    };

    // System.Text.Json normally accepts duplicate fields. The contract rejects them.
    public static T Parse<T>(ReadOnlySpan<byte> bytes)
    {
        using var document = JsonDocument.Parse(bytes.ToArray(), new JsonDocumentOptions { MaxDepth = 8 });
        CheckUnique(document.RootElement);
        return JsonSerializer.Deserialize<T>(bytes, Json) ?? throw new JsonException();
    }

    private static void CheckUnique(JsonElement element)
    {
        if (element.ValueKind == JsonValueKind.Object)
        {
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (var property in element.EnumerateObject())
            {
                if (!names.Add(property.Name)) throw new JsonException("Duplicate field.");
                CheckUnique(property.Value);
            }
        }
        else if (element.ValueKind == JsonValueKind.Array)
            foreach (var item in element.EnumerateArray()) CheckUnique(item);
    }
}

public sealed record SessionRequest(int ProtocolVersion, string CommunityId, Guid RequestId, string PrincipalId, string Key,
    AdapterCompatibility? Adapter = null);
public sealed record AdapterCompatibility(string AdapterVersion, string GameSha256, string Storefront, string Operation)
{
    // The single verified adapter/build pairing; the Python adapter reads the same config/adapter-compatibility.json.
    public static AdapterCompatibility Supported { get; } = LoadSupported();

    private static AdapterCompatibility LoadSupported()
    {
        using var resource = typeof(AdapterCompatibility).Assembly.GetManifestResourceStream("Community.Protocol.AdapterCompatibility")
            ?? throw new InvalidOperationException("Missing adapter compatibility.");
        using var buffer = new MemoryStream();
        resource.CopyTo(buffer);
        return Wire.Parse<AdapterCompatibility>(buffer.ToArray());
    }
}
public sealed record SessionResponse(int ProtocolVersion, Guid RequestId, string CommunityId, Guid SessionId, string AccessToken, DateTimeOffset ExpiresAt);
public sealed record CommandRequest(int ProtocolVersion, string CommunityId, Guid RequestId, long ExpectedRevision, string CommandType, CommandPayload Payload);
public sealed record CommandPayload(Guid InteractionId);
public sealed record InteractionState(Guid InteractionId, long Revision, string Status, string Message);
public sealed record StateResponse(int ProtocolVersion, string CommunityId, InteractionState State);
public sealed record StateEvent(Guid EventId, Guid RequestId, string EventType, InteractionState State);
public sealed record EventsResponse(int ProtocolVersion, string CommunityId, StateEvent[] Events, long Revision);
public sealed record CommandResponse(int ProtocolVersion, Guid RequestId, string CommunityId, InteractionState State, StateEvent Event);
public sealed record ApiError(int ProtocolVersion, Guid? RequestId, string Error);
public sealed record HealthResponse(int ProtocolVersion, string CommunityId, string Status);

// Contains lab credentials: real instances belong only under ignored local storage.
public sealed record LabPrincipal(string Id, string Key);
public sealed record ServerConfig(string BindAddress, int Port, string CommunityId, string DataDirectory,
    string CompletionMessage, int SessionLifetimeSeconds, string AdminKey, LabPrincipal[] Principals);
