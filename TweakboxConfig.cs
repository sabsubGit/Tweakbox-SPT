using System.Text.Json.Serialization;

namespace Tweakbox;

public sealed class TweakboxConfig
{
    [JsonPropertyName("fleaUnban")]
    public FleaUnbanConfig FleaUnban { get; set; } = new();

    [JsonPropertyName("lootInjection")]
    public LootInjectionConfig LootInjection { get; set; } = new();

    [JsonPropertyName("fleaPrice")]
    public FleaPriceConfig FleaPrice { get; set; } = new();

    [JsonPropertyName("stackSize")]
    public StackSizeConfig StackSize { get; set; } = new();

    [JsonPropertyName("traderStock")]
    public TraderStockConfig TraderStock { get; set; } = new();
}

public sealed class FleaUnbanConfig
{
    [JsonPropertyName("enabled")]
    public bool Enabled { get; set; } = true;

    [JsonPropertyName("items")]
    public List<FleaUnbanItem> Items { get; set; } = [];
}

public sealed class FleaUnbanItem
{
    /// Item template id to clear BSG's flea-market ban from.
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    /// Rouble price used to seed the dynamic flea price list. Items that are
    /// flea-banned in live Tarkov have no scraped flea price, and SPT only
    /// generates dynamic offers for items that have one - so without this the
    /// item stays invisible on the flea even once unbanned.
    /// Null falls back to the item's handbook price.
    [JsonPropertyName("fleaPrice")]
    public double? FleaPrice { get; set; }
}

/// Adds items to static loot container pools. Unlike a loot multiplier - which
/// scales an item's weight inside pools it already belongs to - this can place
/// items that never spawn at all, which is the only way to make things like
/// thermal optics findable by looting.
public sealed class LootInjectionConfig
{
    [JsonPropertyName("enabled")]
    public bool Enabled { get; set; } = true;

    [JsonPropertyName("entries")]
    public List<LootInjectionEntry> Entries { get; set; } = [];
}

public sealed class LootInjectionEntry
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    /// Free-text label; ignored by the loader, purely so the config stays readable.
    [JsonPropertyName("comment")]
    public string? Comment { get; set; }

    /// Roughly what percentage of each target container's loot pool this item
    /// should occupy. Weights are recomputed per map from that map's actual pool
    /// total, so the odds stay consistent regardless of how big the pool is or
    /// what other mods have added to it.
    [JsonPropertyName("sharePercent")]
    public double SharePercent { get; set; } = 0.25;

    /// Container template ids, or their internal names (e.g. "Safe", "WeaponCrate",
    /// "Jacket", "PMC_dead", "ToolBox", "terraWBoxLong").
    [JsonPropertyName("containers")]
    public List<string> Containers { get; set; } = [];
}

/// Overrides an item's base flea price. SPT generates dynamic offers around this
/// number, so lowering it lowers what the flea actually asks for the item.
/// Unlike FleaUnban this touches nothing but the price - use it for items that
/// are already tradeable and merely overpriced.
public sealed class FleaPriceConfig
{
    [JsonPropertyName("enabled")]
    public bool Enabled { get; set; } = true;

    [JsonPropertyName("entries")]
    public List<FleaPriceEntry> Entries { get; set; } = [];
}

public sealed class FleaPriceEntry
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("comment")]
    public string? Comment { get; set; }

    [JsonPropertyName("priceRub")]
    public double PriceRub { get; set; }
}

/// Adds items to a trader's permanent stock. A trader offer is steadier than the
/// flea - fixed price, always in stock, no bidding against dynamic offers - which
/// makes it the better way to guarantee something stays affordable.
public sealed class TraderStockConfig
{
    [JsonPropertyName("enabled")]
    public bool Enabled { get; set; } = true;

    [JsonPropertyName("entries")]
    public List<TraderStockEntry> Entries { get; set; } = [];
}

public sealed class TraderStockEntry
{
    /// Trader nickname ("Jaeger", "Prapor", ...) or their MongoId.
    [JsonPropertyName("trader")]
    public string Trader { get; set; } = string.Empty;

    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("comment")]
    public string? Comment { get; set; }

    [JsonPropertyName("priceRub")]
    public double PriceRub { get; set; }

    /// Loyalty level the offer unlocks at. Jaeger's LL1 needs nothing at all.
    [JsonPropertyName("loyaltyLevel")]
    public int LoyaltyLevel { get; set; } = 1;

    /// Purchases allowed per restock. Null means unlimited.
    [JsonPropertyName("buyRestrictionMax")]
    public int? BuyRestrictionMax { get; set; }
}

/// Changes how many of an item fit in one inventory stack. The change is made to
/// the in-memory item template, which the server sends to every client on login,
/// so nothing needs installing on the players' side.
public sealed class StackSizeConfig
{
    [JsonPropertyName("enabled")]
    public bool Enabled { get; set; } = true;

    [JsonPropertyName("entries")]
    public List<StackSizeEntry> Entries { get; set; } = [];
}

public sealed class StackSizeEntry
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("comment")]
    public string? Comment { get; set; }

    /// Largest stack the item can form.
    [JsonPropertyName("maxStack")]
    public int MaxStack { get; set; } = 1;

    /// Optional size range for copies that spawn as loot. Falls back to the item's
    /// existing range when left out. Either way the result is clamped to maxStack:
    /// the loot generators only skip their roll while the cap is exactly 1 and never
    /// clamp it themselves, so an item whose range was written for a cap of 1 would
    /// otherwise start spawning in over-full stacks the moment the cap is raised.
    [JsonPropertyName("foundMin")]
    public int? FoundMin { get; set; }

    [JsonPropertyName("foundMax")]
    public int? FoundMax { get; set; }
}
