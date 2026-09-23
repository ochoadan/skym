using System.Security.Cryptography;
using System.Text;
using Community.Protocol;

namespace Community.Server;

internal sealed class ApiFault(int status, string code) : Exception(code)
{
    public int Status { get; } = status;
    public string Code { get; } = code;
}

internal sealed class LabRuntime(ServerConfig config)
{
    private sealed record Session(Guid Id, string PrincipalId, DateTimeOffset ExpiresAt, bool Adapter);
    private sealed class Contract
    {
        public InteractionState State { get; set; } = new(Guid.NewGuid(), 0, "available", "");
        public Dictionary<Guid, (CommandRequest Request, CommandResponse Response)> Requests { get; } = [];
        public List<StateEvent> Events { get; } = [];
    }

    private readonly object gate = new();
    private readonly Dictionary<string, Session> sessions = new(StringComparer.Ordinal);
    private readonly Dictionary<string, Contract> contracts = config.Principals.ToDictionary(p => p.Id, _ => new Contract());

    public static bool SecretEquals(string? candidate, string expected) => candidate is { Length: <= 128 } &&
        CryptographicOperations.FixedTimeEquals(SHA256.HashData(Encoding.UTF8.GetBytes(candidate)), SHA256.HashData(Encoding.UTF8.GetBytes(expected)));

    private void Envelope(int version, string? community, Guid requestId)
    {
        if (version != Wire.Version) throw new ApiFault(400, "unsupported_protocol");
        if (community != config.CommunityId) throw new ApiFault(403, "wrong_community");
        if (requestId == Guid.Empty) throw new ApiFault(400, "invalid_request_id");
    }

    public SessionResponse Connect(SessionRequest request)
    {
        Envelope(request.ProtocolVersion, request.CommunityId, request.RequestId);
        var principal = config.Principals.FirstOrDefault(p => p.Id == request.PrincipalId);
        if (principal is null || !SecretEquals(request.Key, principal.Key)) throw new ApiFault(401, "invalid_credentials");
        if (request.Adapter is { } adapter)
        {
            // Compatibility self-report only; a caller holding a lab key can fabricate these fields.
            var supported = AdapterCompatibility.Supported;
            if (adapter.AdapterVersion != supported.AdapterVersion) throw new ApiFault(409, "unsupported_adapter");
            if (adapter.GameSha256 != supported.GameSha256 || adapter.Storefront != supported.Storefront)
                throw new ApiFault(409, "unsupported_game");
            if (adapter.Operation != supported.Operation) throw new ApiFault(409, "unsupported_operation");
        }
        lock (gate)
        {
            var now = DateTimeOffset.UtcNow;
            foreach (var key in sessions.Where(pair => pair.Value.ExpiresAt <= now).Select(pair => pair.Key).ToArray()) sessions.Remove(key);
            if (sessions.Count >= 64) throw new ApiFault(429, "session_capacity");
            var token = Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
            var session = new Session(Guid.NewGuid(), principal.Id, now.AddSeconds(config.SessionLifetimeSeconds), request.Adapter is not null);
            sessions.Add(token, session);
            return new(Wire.Version, request.RequestId, config.CommunityId, session.Id, token, session.ExpiresAt);
        }
    }

    private Session Authenticate(string token)
    {
        if (!sessions.TryGetValue(token, out var session)) throw new ApiFault(401, "invalid_session");
        if (session.ExpiresAt <= DateTimeOffset.UtcNow)
        {
            sessions.Remove(token);
            throw new ApiFault(401, "expired_session");
        }
        return session;
    }

    public void Disconnect(string token)
    {
        lock (gate) { Authenticate(token); sessions.Remove(token); }
    }

    public StateResponse State(string token)
    {
        lock (gate) return new(Wire.Version, config.CommunityId, contracts[Authenticate(token).PrincipalId].State);
    }

    public EventsResponse Events(string token, long after)
    {
        lock (gate)
        {
            var contract = contracts[Authenticate(token).PrincipalId];
            if (after < 0 || after > contract.State.Revision) throw new ApiFault(400, "invalid_cursor");
            return new(Wire.Version, config.CommunityId, contract.Events.Where(e => e.State.Revision > after).ToArray(), contract.State.Revision);
        }
    }

    public CommandResponse Command(string token, CommandRequest request)
    {
        lock (gate)
        {
            var session = Authenticate(token);
            Envelope(request.ProtocolVersion, request.CommunityId, request.RequestId);
            if (request.Payload is null || request.Payload.InteractionId == Guid.Empty || request.ExpectedRevision < 0 ||
                request.CommandType is not ("accept" or "complete" or "reset" or "probe")) throw new ApiFault(400, "invalid_command");
            var probe = request.CommandType == "probe";
            // Scope precedes replay lookup, so a differently scoped session cannot replay a privileged command.
            if (session.Adapter && !probe) throw new ApiFault(403, "session_scope");
            if (!session.Adapter && probe) throw new ApiFault(403, "adapter_required");
            var contract = contracts[session.PrincipalId];
            if (contract.Requests.TryGetValue(request.RequestId, out var prior))
            {
                if (prior.Request != request) throw new ApiFault(409, "request_id_conflict");
                return prior.Response;
            }
            if (request.Payload.InteractionId != contract.State.InteractionId) throw new ApiFault(404, "unknown_interaction");
            if (request.ExpectedRevision != contract.State.Revision) throw new ApiFault(409, "stale_revision");
            var next = (contract.State.Status, request.CommandType) switch
            {
                (_, "probe") => contract.State.Status,
                ("available", "accept") => "accepted",
                ("accepted", "complete") => "completed",
                ("completed", "reset") => "available",
                _ => throw new ApiFault(409, "invalid_transition")
            };
            // Never evict deduplication entries and accidentally execute an old request twice.
            if (contract.Requests.Count >= 256) throw new ApiFault(429, "interaction_capacity");
            contract.State = new(contract.State.InteractionId, contract.State.Revision + 1, next,
                probe || next == "completed" ? config.CompletionMessage : "");
            var change = new StateEvent(Guid.NewGuid(), request.RequestId, probe ? "interaction.probed" : "interaction.changed", contract.State);
            var response = new CommandResponse(Wire.Version, request.RequestId, config.CommunityId, contract.State, change);
            contract.Requests.Add(request.RequestId, (request, response));
            contract.Events.Add(change);
            return response;
        }
    }
}
