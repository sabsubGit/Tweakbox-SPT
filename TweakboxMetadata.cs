using SPTarkov.Server.Core.Models.Spt.Mod;
using Range = SemanticVersioning.Range;
using Version = SemanticVersioning.Version;

namespace Tweakbox;

public sealed record TweakboxMetadata : IModMetadata
{
    public string ModGuid { get; init; } = "local.tweakbox";
    public string Name { get; init; } = "Tweakbox";
    public string Author { get; init; } = "local";
    public List<string>? Contributors { get; init; } = [];
    public Version Version { get; init; } = new("1.1.0");
    public Range SptVersion { get; init; } = new("~4.1.0");
    public List<string>? Incompatibilities { get; init; } = [];
    public Dictionary<string, Range>? ModDependencies { get; init; } = [];
    public string? Url { get; init; } = null;
    public bool HasPrepatcher { get; init; } = false;
    public string License { get; init; } = "MIT";
}
