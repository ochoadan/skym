using System.Net;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;
using Community.Protocol;

namespace Community.Server;

internal static partial class Configuration
{
    public static void Initialize(string path)
    {
        using var template = typeof(Configuration).Assembly.GetManifestResourceStream("Community.Server.DefaultConfig")
            ?? throw new InvalidOperationException("Missing default configuration.");
        var defaults = JsonSerializer.Deserialize<ServerConfig>(template, Wire.Json) ?? throw new JsonException();
        var config = defaults with
        {
            AdminKey = NewKey(),
            Principals = defaults.Principals.Select(principal => principal with { Key = NewKey() }).ToArray()
        };
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        // CreateNew refuses an existing file atomically, preserving operator settings and keys.
        using var destination = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None);
        JsonSerializer.Serialize(destination, config, new JsonSerializerOptions(Wire.Json) { WriteIndented = true });
    }

    private static string NewKey() => Convert.ToHexString(RandomNumberGenerator.GetBytes(32));

    public static ServerConfig Load(string path)
    {
        var bytes = File.ReadAllBytes(path);
        if (bytes.Length > 16384) throw new InvalidDataException("Configuration exceeds 16 KiB.");
        var config = Wire.Parse<ServerConfig>(bytes);
        if (config.BindAddress != IPAddress.Loopback.ToString() || config.Port is < 1024 or > 65535)
            throw new InvalidDataException("Use bindAddress 127.0.0.1 and a port from 1024 to 65535.");
        if (!Identifier(config.CommunityId) || config.SessionLifetimeSeconds is < 1 or > 3600)
            throw new InvalidDataException("Invalid community ID or session lifetime (1-3600 seconds).");
        if (string.IsNullOrWhiteSpace(config.CompletionMessage) || config.CompletionMessage.Length > 512)
            throw new InvalidDataException("Completion message must contain 1-512 characters.");
        if (!Key(config.AdminKey) || config.Principals is null || config.Principals.Length is < 1 or > 8 ||
            config.Principals.Any(p => p is null || !Identifier(p.Id) || !Key(p.Key)) ||
            config.Principals.Select(p => p.Id).Distinct(StringComparer.Ordinal).Count() != config.Principals.Length ||
            config.Principals.Select(p => p.Key).Append(config.AdminKey).Distinct(StringComparer.Ordinal).Count() != config.Principals.Length + 1)
            throw new InvalidDataException("Provide 1-8 unique lab principals and distinct keys of 32-128 characters.");
        if (string.IsNullOrWhiteSpace(config.DataDirectory) || Path.IsPathRooted(config.DataDirectory) ||
            config.DataDirectory.Split('/', '\\').Any(part => part is ".." or "." or ""))
            throw new InvalidDataException("Data directory must be a child path relative to the configuration file.");
        return config;
    }

    public static string DatabasePath(string configurationPath, ServerConfig config) => Path.Combine(
        Path.GetFullPath(Path.Combine(Path.GetDirectoryName(Path.GetFullPath(configurationPath))!, config.DataDirectory)),
        "community.sqlite3");

    private static bool Identifier(string? value) => value is not null && IdPattern().IsMatch(value);
    private static bool Key(string? value) => value is { Length: >= 32 and <= 128 } && value.All(c => c is >= '!' and <= '~');
    [GeneratedRegex("^[a-z0-9][a-z0-9-]{0,47}\\z", RegexOptions.CultureInvariant)]
    private static partial Regex IdPattern();
}
