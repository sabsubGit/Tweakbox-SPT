using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using SPTarkov.Common.Models.Logging;
using SPTarkov.DI.Annotations;
using SPTarkov.Server.Core.DI;
using SPTarkov.Server.Core.Models.Common;
using SPTarkov.Server.Core.Models.Eft.Common;
using SPTarkov.Server.Core.Models.Eft.Common.Tables;
using SPTarkov.Server.Core.Models.Spt.Mod;
using SPTarkov.Server.Core.Models.Spt.Tables;
using SPTarkov.Server.Core.Services.Modding.Custom;
using SPTarkov.Server.Core.Utils;

// Eft.Common.Tables also defines a Path type, which would otherwise shadow System.IO.Path.
using Path = System.IO.Path;

namespace Tweakbox;

// Grab-bag of small server-side tweaks that SVM can't express. Everything is
// applied to the in-memory database after the checksummed load completes, so no
// files under SPT_Data/database are ever touched (editing those breaks their
// integrity check and stops the server booting).
//
// Runs before OnLoadOrder.RagfairCallbacks: the flea builds its offer pool during
// that stage, so item/price edits made any later (e.g. at PostLoad) are silently
// ignored until the next offer refresh.
[Injectable(TypePriority = OnLoadOrder.PresetCallbacks + 1)]
public sealed class TweakboxOnLoad(
    TemplateTable templateTable,
    LocationTable locationTable,
    TradersTable tradersTable,
    BotTable botTable,
    ISptLogger<TweakboxOnLoad> logger
) : IOnLoad
{
    private static readonly MongoId Roubles = new("5449016a4bdc2d6f028b456f");
    private static readonly MongoId Dollars = new("5696686a4bdc2da3298b456a");
    private static readonly MongoId Euros = new("569668774bdc2da2298b4568");

    public Task OnLoadAsync(CancellationToken cancellationToken)
    {
        TweakboxConfig config = LoadConfig();

        // A cosmetic tweak mod must never be able to take the server down over a
        // bad config entry, so each feature is isolated.
        RunSafely("flea unban", () => ApplyFleaUnban(config.FleaUnban));
        RunSafely("loot injection", () => ApplyLootInjection(config.LootInjection));
        RunSafely("spawn like", () => ApplySpawnLike(config.SpawnLike));
        RunSafely("flea price", () => ApplyFleaPrice(config.FleaPrice));
        RunSafely("stack size", () => ApplyStackSize(config.StackSize));
        RunSafely("trader stock", () => ApplyTraderStock(config.TraderStock));
        return Task.CompletedTask;
    }

    private void RunSafely(string feature, Action action)
    {
        try
        {
            action();
        }
        catch (Exception ex)
        {
            logger.Error($"Tweakbox: {feature} failed and was skipped - the rest of the server is unaffected. {ex.Message}");
        }
    }

    private TweakboxConfig LoadConfig()
    {
        TweakboxConfig? config = ReadConfig();
        if (config != null)
        {
            return config;
        }

        logger.Warning("Tweakbox: no config.json next to the mod, no tweaks applied.");
        return new TweakboxConfig
        {
            FleaUnban = { Enabled = false },
            LootInjection = { Enabled = false },
            FleaPrice = { Enabled = false },
            StackSize = { Enabled = false },
            TraderStock = { Enabled = false },
            CustomItems = { Enabled = false },
            SpawnLike = { Enabled = false },
        };
    }

    internal static TweakboxConfig? ReadConfig()
    {
        string modDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location)!;
        string configPath = Path.Combine(modDir, "config.json");
        if (!File.Exists(configPath))
        {
            return null;
        }

        JsonSerializerOptions options = new()
        {
            PropertyNameCaseInsensitive = true,
            ReadCommentHandling = JsonCommentHandling.Skip,
            AllowTrailingCommas = true,
        };
        return JsonSerializer.Deserialize<TweakboxConfig>(File.ReadAllText(configPath), options) ?? new TweakboxConfig();
    }

    private void ApplyFleaUnban(FleaUnbanConfig config)
    {
        if (!config.Enabled || config.Items.Count == 0)
        {
            return;
        }

        foreach (FleaUnbanItem entry in config.Items)
        {
            MongoId tpl = new(entry.Id);

            if (!templateTable.Items.TryGetValue(tpl, out var item) || item.Properties == null)
            {
                logger.Warning($"Tweakbox: flea unban - item {entry.Id} not found in database, skipping.");
                continue;
            }

            item.Properties.CanSellOnRagfair = true;
            item.Properties.CanRequireOnRagfair = true;

            double? price = entry.FleaPrice ?? GetHandbookPrice(tpl);
            if (price is null or <= 0)
            {
                logger.Warning(
                    $"Tweakbox: flea unban - {item.Name} unbanned, but it has no flea price and no handbook price to fall back on, "
                        + "so no dynamic offers will generate. Set \"fleaPrice\" for it in config.json."
                );
                continue;
            }

            templateTable.Prices[tpl] = price.Value;
            logger.Success($"Tweakbox: flea unban - {item.Name} is now tradeable on the flea at a base price of {price.Value:N0} RUB.");
        }
    }

    private void ApplyLootInjection(LootInjectionConfig config)
    {
        if (!config.Enabled || config.Entries.Count == 0)
        {
            return;
        }

        // Resolve container names once; the transformer runs per map, per load.
        List<(LootInjectionEntry Entry, MongoId Tpl, List<MongoId> Containers)> resolved = [];
        foreach (LootInjectionEntry entry in config.Entries)
        {
            MongoId tpl = new(entry.Id);
            if (!templateTable.Items.TryGetValue(tpl, out var item))
            {
                logger.Warning($"Tweakbox: loot injection - item {entry.Id} not in database, skipping.");
                continue;
            }

            List<MongoId> containers = [];
            foreach (string name in entry.Containers)
            {
                MongoId? found = ResolveContainer(name);
                if (found is null)
                {
                    logger.Warning($"Tweakbox: loot injection - container '{name}' not found, skipping it for {item.Name}.");
                    continue;
                }
                containers.Add(found.Value);
            }

            if (containers.Count > 0)
            {
                resolved.Add((entry, tpl, containers));
                logger.Success(
                    $"Tweakbox: loot injection - {entry.Comment ?? item.Name} -> {containers.Count} container type(s) at ~{entry.SharePercent:0.##}% of pool."
                );
            }
        }

        if (resolved.Count == 0)
        {
            return;
        }

        // StaticLoot is a LazyLoad: its value is re-deserialised from disk on every
        // access, so mutating the returned dictionary would be thrown away. A
        // transformer is re-applied each time it loads, which is the supported hook.
        foreach (Location? location in EnumerateLocations())
        {
            location?.StaticLoot?.AddTransformer(staticLoot =>
            {
                // The transformer runs at map-load time, outside RunSafely's reach,
                // so it has to guard its own input rather than throw there.
                if (staticLoot is null)
                {
                    return staticLoot!;
                }

                foreach (var (entry, tpl, containers) in resolved)
                {
                    foreach (MongoId container in containers)
                    {
                        if (!staticLoot.TryGetValue(container, out StaticLootDetails? details) || details is null)
                        {
                            continue;
                        }

                        IEnumerable<ItemDistribution>? existing = details.ItemDistribution;
                        if (existing == null)
                        {
                            continue;
                        }

                        List<ItemDistribution> pool = existing.ToList();
                        if (pool.Any(x => x.Tpl == tpl))
                        {
                            continue; // already present - don't stack on repeat loads
                        }

                        double total = pool.Sum(x => (double)(x.RelativeProbability ?? 0));
                        if (total <= 0)
                        {
                            continue;
                        }

                        double share = Math.Clamp(entry.SharePercent, 0.001, 50) / 100d;
                        double weight = share / (1 - share) * total;

                        pool.Add(new ItemDistribution { Tpl = tpl, RelativeProbability = (float)weight });
                        details.ItemDistribution = pool;
                    }
                }

                return staticLoot;
            });
        }
    }

    private void ApplySpawnLike(SpawnLikeConfig config)
    {
        if (!config.Enabled || config.Entries.Count == 0)
        {
            return;
        }

        List<(SpawnLikeEntry Entry, MongoId Tpl, HashSet<MongoId> Like)> resolved = [];
        foreach (SpawnLikeEntry entry in config.Entries)
        {
            MongoId tpl = new(entry.Id);
            if (!templateTable.Items.TryGetValue(tpl, out var item))
            {
                logger.Warning($"Tweakbox: spawn like - item {entry.Id} not in database, skipping.");
                continue;
            }

            HashSet<MongoId> like = entry.LikeItems.Where(LooksLikeMongoId).Select(x => new MongoId(x)).ToHashSet();
            if (like.Count == 0)
            {
                logger.Warning($"Tweakbox: spawn like - {item.Name} has no valid likeItems, skipping.");
                continue;
            }
            resolved.Add((entry, tpl, like));
        }

        foreach (var (entry, tpl, like) in resolved)
        {
            string label = entry.Comment ?? templateTable.Items[tpl].Name ?? entry.Id;
            if (entry.Bots)
            {
                int pools = AddToBotPools(entry, tpl, like);
                logger.Success($"Tweakbox: spawn like - {label} added to {pools} bot inventory pool(s).");
            }
        }

        foreach (Location? location in EnumerateLocations())
        {
            if (location == null)
            {
                continue;
            }

            if (resolved.Any(r => r.Entry.LooseLoot))
            {
                location.LooseLoot?.AddTransformer(looseLoot =>
                {
                    if (looseLoot?.Spawnpoints == null)
                    {
                        return looseLoot!;
                    }
                    foreach (Spawnpoint spawnpoint in looseLoot.Spawnpoints)
                    {
                        foreach (var (entry, tpl, like) in resolved.Where(r => r.Entry.LooseLoot))
                        {
                            AddToSpawnpoint(spawnpoint, entry, tpl, like);
                        }
                    }
                    return looseLoot;
                });
            }

            if (resolved.Any(r => r.Entry.Containers))
            {
                location.StaticLoot?.AddTransformer(staticLoot =>
                {
                    if (staticLoot == null)
                    {
                        return staticLoot!;
                    }
                    foreach (StaticLootDetails? details in staticLoot.Values)
                    {
                        if (details?.ItemDistribution == null)
                        {
                            continue;
                        }
                        foreach (var (entry, tpl, like) in resolved.Where(r => r.Entry.Containers))
                        {
                            List<ItemDistribution> pool = details.ItemDistribution.ToList();
                            if (pool.Any(x => x.Tpl == tpl))
                            {
                                continue;
                            }
                            List<double> weights = pool.Where(x => like.Contains(x.Tpl)).Select(x => (double)(x.RelativeProbability ?? 0)).Where(w => w > 0).ToList();
                            if (weights.Count == 0)
                            {
                                continue;
                            }
                            pool.Add(new ItemDistribution { Tpl = tpl, RelativeProbability = (float)Math.Max(weights.Min() * entry.WeightFactor, 1) });
                            details.ItemDistribution = pool;
                        }
                    }
                    return staticLoot;
                });
            }
        }
    }

    private int AddToBotPools(SpawnLikeEntry entry, MongoId tpl, HashSet<MongoId> like)
    {
        int added = 0;
        foreach (var (role, bot) in botTable.Types)
        {
            if (bot?.BotInventory?.Items == null || entry.ExcludeBots.Contains(role, StringComparer.OrdinalIgnoreCase))
            {
                continue;
            }
            ItemPools items = bot.BotInventory.Items;
            foreach (Dictionary<MongoId, double>? pool in new[] { items.Backpack, items.Pockets, items.TacticalVest, items.SecuredContainer })
            {
                if (pool == null || pool.ContainsKey(tpl))
                {
                    continue;
                }
                List<double> weights = pool.Where(kv => like.Contains(kv.Key) && kv.Value > 0).Select(kv => kv.Value).ToList();
                if (weights.Count == 0)
                {
                    continue;
                }
                pool[tpl] = Math.Max(Math.Round(weights.Min() * entry.WeightFactor), 1);
                added++;
            }
        }
        return added;
    }

    private static void AddToSpawnpoint(Spawnpoint spawnpoint, SpawnLikeEntry entry, MongoId tpl, HashSet<MongoId> like)
    {
        List<SptLootItem>? items = spawnpoint.Template?.Items?.ToList();
        if (items == null || spawnpoint.ItemDistribution == null || items.Any(i => i.Template == tpl))
        {
            return;
        }

        HashSet<string> likeKeys = items.Where(i => i.ComposedKey != null && like.Contains(i.Template)).Select(i => i.ComposedKey!).ToHashSet();
        if (likeKeys.Count == 0)
        {
            return;
        }
        List<LooseLootItemDistribution> dist = spawnpoint.ItemDistribution.ToList();
        List<double> weights = dist.Where(d => d.ComposedKey?.Key != null && likeKeys.Contains(d.ComposedKey.Key)).Select(d => d.RelativeProbability ?? 0).Where(w => w > 0).ToList();
        if (weights.Count == 0)
        {
            return;
        }

        string key = $"tweakbox_{tpl}_{spawnpoint.Template!.Id}";
        byte[] hash = SHA256.HashData(Encoding.UTF8.GetBytes(key));
        items.Add(new SptLootItem
        {
            Id = new MongoId(Convert.ToHexStringLower(hash)[..24]),
            Template = tpl,
            ComposedKey = key,
            Upd = new Upd { StackObjectsCount = 1 },
        });
        dist.Add(new LooseLootItemDistribution
        {
            ComposedKey = new ComposedKey { Key = key },
            RelativeProbability = weights.Min() * entry.WeightFactor,
        });
        spawnpoint.Template.Items = items;
        spawnpoint.ItemDistribution = dist;
    }

    private void ApplyFleaPrice(FleaPriceConfig config)
    {
        if (!config.Enabled || config.Entries.Count == 0)
        {
            return;
        }

        foreach (FleaPriceEntry entry in config.Entries)
        {
            MongoId tpl = new(entry.Id);
            if (!templateTable.Items.TryGetValue(tpl, out var item))
            {
                logger.Warning($"Tweakbox: flea price - item {entry.Id} not in database, skipping.");
                continue;
            }

            if (entry.PriceRub <= 0)
            {
                logger.Warning($"Tweakbox: flea price - {item.Name} has no usable priceRub, skipping.");
                continue;
            }

            templateTable.Prices.TryGetValue(tpl, out double old);
            templateTable.Prices[tpl] = entry.PriceRub;
            logger.Success(
                $"Tweakbox: flea price - {entry.Comment ?? item.Name} base price {old:N0} -> {entry.PriceRub:N0} RUB."
            );
        }
    }

    private void ApplyStackSize(StackSizeConfig config)
    {
        if (!config.Enabled || config.Entries.Count == 0)
        {
            return;
        }

        foreach (StackSizeEntry entry in config.Entries)
        {
            MongoId tpl = new(entry.Id);
            if (!templateTable.Items.TryGetValue(tpl, out var item) || item.Properties == null)
            {
                logger.Warning($"Tweakbox: stack size - item {entry.Id} not in database, skipping.");
                continue;
            }

            if (entry.MaxStack < 1)
            {
                logger.Warning($"Tweakbox: stack size - {item.Name} has maxStack {entry.MaxStack}, must be at least 1, skipping.");
                continue;
            }

            var props = item.Properties;
            var old = props.StackMaxSize;
            props.StackMaxSize = entry.MaxStack;

            // Keep the loot roll inside the new cap - see StackSizeEntry.FoundMin.
            int foundMax = Math.Clamp((int)(entry.FoundMax ?? props.StackMaxRandom ?? 1), 1, entry.MaxStack);
            int foundMin = Math.Clamp((int)(entry.FoundMin ?? props.StackMinRandom ?? 1), 1, foundMax);
            props.StackMaxRandom = foundMax;
            props.StackMinRandom = foundMin;

            logger.Success(
                $"Tweakbox: stack size - {entry.Comment ?? item.Name} now stacks to {entry.MaxStack} (was {old}); "
                    + $"found in loot as {foundMin}-{foundMax}."
            );
        }
    }

    private void ApplyTraderStock(TraderStockConfig config)
    {
        if (!config.Enabled || config.Entries.Count == 0)
        {
            return;
        }

        foreach (TraderStockEntry entry in config.Entries)
        {
            MongoId tpl = new(entry.Id);
            if (!templateTable.Items.TryGetValue(tpl, out var item))
            {
                logger.Warning($"Tweakbox: trader stock - item {entry.Id} not in database, skipping.");
                continue;
            }

            Trader? trader = ResolveTrader(entry.Trader);
            if (trader?.Assort == null)
            {
                logger.Warning($"Tweakbox: trader stock - trader '{entry.Trader}' not found (or has no assort), skipping {item.Name}.");
                continue;
            }

            TraderAssort assort = trader.Assort;
            assort.Items ??= [];
            assort.BarterScheme ??= [];
            assort.LoyalLevelItems ??= [];

            // Derive the offer id from trader+item so it is identical on every
            // boot: a random id would stack a duplicate offer each restart.
            List<BarterScheme> cost = [];
            if (entry.Barter is { Count: > 0 })
            {
                foreach (BarterCost barter in entry.Barter)
                {
                    MongoId costTpl = new(barter.Id);
                    if (!templateTable.Items.ContainsKey(costTpl))
                    {
                        cost.Clear();
                        break;
                    }
                    cost.Add(new BarterScheme { Count = barter.Count, Template = costTpl });
                }
                if (cost.Count == 0)
                {
                    logger.Warning($"Tweakbox: trader stock - barter for {item.Name} names an unknown item, skipping.");
                    continue;
                }
            }
            else
            {
                MongoId? money = entry.Currency.ToUpperInvariant() switch
                {
                    "RUB" => Roubles,
                    "USD" => Dollars,
                    "EUR" => Euros,
                    _ => null,
                };
                if (money == null)
                {
                    logger.Warning($"Tweakbox: trader stock - unknown currency '{entry.Currency}' for {item.Name}, skipping.");
                    continue;
                }
                cost.Add(new BarterScheme { Count = entry.Price ?? entry.PriceRub, Template = money.Value });
            }

            // Cash offers keep their original id; barters get their own so both can coexist.
            string salt = entry.Barter is { Count: > 0 } ? "barter:" + string.Join(",", entry.Barter.Select(b => $"{b.Id}x{b.Count}")) : "";
            MongoId offerId = StableId(trader.Base!.Id, tpl, salt);
            if (assort.Items.Any(i => i.Id == offerId))
            {
                continue;
            }

            assort.Items.Add(new Item
            {
                Id = offerId,
                Template = tpl,
                ParentId = "hideout",
                SlotId = "hideout",
                Upd = new Upd
                {
                    UnlimitedCount = true,
                    StackObjectsCount = 999999,
                    BuyRestrictionMax = entry.BuyRestrictionMax,
                    BuyRestrictionCurrent = entry.BuyRestrictionMax is null ? null : 0,
                },
            });

            assort.BarterScheme[offerId] = [cost];
            assort.LoyalLevelItems[offerId] = entry.LoyaltyLevel;

            string price = entry.Barter is { Count: > 0 }
                ? string.Join(" + ", entry.Barter.Select(b => $"{b.Count:0.##}x {templateTable.Items[new MongoId(b.Id)].Name}"))
                : $"{entry.Price ?? entry.PriceRub:N0} {entry.Currency.ToUpperInvariant()}";
            logger.Success(
                $"Tweakbox: trader stock - {trader.Base.Nickname} now sells {entry.Comment ?? item.Name} "
                    + $"at LL{entry.LoyaltyLevel} for {price}."
            );
        }
    }

    private Trader? ResolveTrader(string nameOrId)
    {
        if (LooksLikeMongoId(nameOrId) && tradersTable.TryGetValue(new MongoId(nameOrId), out Trader? byId))
        {
            return byId;
        }

        foreach (Trader trader in tradersTable.Values)
        {
            if (string.Equals(trader.Base?.Nickname, nameOrId, StringComparison.OrdinalIgnoreCase))
            {
                return trader;
            }
        }

        return null;
    }

    /// A MongoId has to be exactly 24 hex characters, so hash the inputs and take
    /// the first 24 - same inputs always yield the same id.
    private static MongoId StableId(MongoId traderId, MongoId tpl, string salt = "")
    {
        string seed = salt.Length == 0 ? $"tweakbox:{traderId}:{tpl}" : $"tweakbox:{traderId}:{tpl}:{salt}";
        byte[] hash = SHA256.HashData(Encoding.UTF8.GetBytes(seed));
        return new MongoId(Convert.ToHexStringLower(hash)[..24]);
    }

    private MongoId? ResolveContainer(string nameOrId)
    {
        // MongoId's constructor throws on anything that isn't 24 hex chars, so the
        // id form has to be validated before we try it - a friendly container name
        // like "WeaponCrate" must never reach it.
        if (LooksLikeMongoId(nameOrId))
        {
            MongoId asId = new(nameOrId);
            if (templateTable.Items.ContainsKey(asId))
            {
                return asId;
            }
        }

        foreach (var (tpl, item) in templateTable.Items)
        {
            if (string.Equals(item.Name, nameOrId, StringComparison.OrdinalIgnoreCase))
            {
                return tpl;
            }
        }

        return null;
    }

    private static bool LooksLikeMongoId(string value)
    {
        return value.Length == 24 && value.All(Uri.IsHexDigit);
    }

    private IEnumerable<Location?> EnumerateLocations()
    {
        yield return locationTable.Bigmap;
        yield return locationTable.Woods;
        yield return locationTable.Shoreline;
        yield return locationTable.RezervBase;
        yield return locationTable.Lighthouse;
        yield return locationTable.TarkovStreets;
        yield return locationTable.Interchange;
        yield return locationTable.Sandbox;
        yield return locationTable.SandboxHigh;
        yield return locationTable.Laboratory;
        yield return locationTable.Factory4Day;
        yield return locationTable.Factory4Night;
    }

    private double? GetHandbookPrice(MongoId tpl)
    {
        return templateTable.Handbook?.Items?.FirstOrDefault(i => i.Id == tpl)?.Price;
    }
}
