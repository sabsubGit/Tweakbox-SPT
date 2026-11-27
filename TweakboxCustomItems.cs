using System.Reflection;
using System.Text.Json;
using SPTarkov.Common.Models.Logging;
using SPTarkov.DI.Annotations;
using SPTarkov.Server.Core.DI;
using SPTarkov.Server.Core.Models.Common;
using SPTarkov.Server.Core.Models.Eft.Common.Tables;
using SPTarkov.Server.Core.Models.Spt.Mod;
using SPTarkov.Server.Core.Models.Spt.Tables;
using SPTarkov.Server.Core.Services.Modding.Custom;
using SPTarkov.Server.Core.Utils;

namespace Tweakbox;

// Custom items must exist before SaveCallbacks loads the profiles: the profile validator marks any profile holding an
// unknown item template as invalid. The other tweaks stay in TweakboxOnLoad, which has to run later (before the flea).
[Injectable(TypePriority = OnLoadOrder.SaveCallbacks - 1)]
public sealed class TweakboxCustomItems(
    TemplateTable templateTable,
    GlobalTable globalTable,
    LocaleTable localeTable,
    CustomItemService customItemService,
    JsonUtil jsonUtil,
    ISptLogger<TweakboxCustomItems> logger
) : IOnLoad
{
    public Task OnLoadAsync(CancellationToken cancellationToken)
    {
        try
        {
            ApplyCustomItems(TweakboxOnLoad.ReadConfig()?.CustomItems ?? new CustomItemsConfig { Enabled = false });
        }
        catch (Exception ex)
        {
            logger.Error($"Tweakbox: custom items failed and were skipped - the rest of the server is unaffected. {ex.Message}");
        }
        return Task.CompletedTask;
    }

    private void AddToSlotsLike(MongoId newId, MongoId like)
    {
        int slots = 0, conflicts = 0;
        foreach (TemplateItem item in templateTable.Items.Values)
        {
            TemplateItemProperties? props = item.Properties;
            if (props == null || item.Id == newId)
            {
                continue;
            }

            foreach (Slot slot in props.Slots ?? [])
            {
                foreach (SlotFilter filter in slot.Properties?.Filters ?? [])
                {
                    if (filter.Filter != null && filter.Filter.Contains(like) && filter.Filter.Add(newId))
                    {
                        slots++;
                    }
                }
            }

            if (props.ConflictingItems != null && props.ConflictingItems.Contains(like) && props.ConflictingItems.Add(newId))
            {
                conflicts++;
            }
        }

        logger.Info($"Tweakbox: custom items - {newId} fits like {like}: added to {slots} slots and {conflicts} conflict lists.");
    }

    private void ApplyCustomItems(CustomItemsConfig config)
    {
        if (!config.Enabled || config.Items.Count == 0)
        {
            return;
        }

        List<(MongoId Id, JsonElement Raw)> created = [];
        foreach (JsonElement raw in config.Items)
        {
            NewItemFromCloneDetails? details;
            try
            {
                details = jsonUtil.Deserialize<NewItemFromCloneDetails>(raw.GetRawText());
            }
            catch (Exception ex)
            {
                logger.Warning($"Tweakbox: custom items - an entry could not be read, skipping it. {ex.Message}");
                continue;
            }

            if (details == null)
            {
                continue;
            }

            if (!templateTable.Items.ContainsKey(details.ItemTplToClone))
            {
                logger.Warning($"Tweakbox: custom items - {details.NewItemName}: base item {details.ItemTplToClone} not found, skipping.");
                continue;
            }

            CreateItemResult result = customItemService.CreateItemFromClone(details, Assembly.GetExecutingAssembly());
            if (result.Success == true)
            {
                // Optional: let the new item go wherever an existing item goes (slot filters and conflict lists),
                // e.g. a new pistol grip fits every rifle that takes the grip it was copied from.
                if (raw.TryGetProperty("addToSlotsLike", out JsonElement like) && like.ValueKind == JsonValueKind.String)
                {
                    AddToSlotsLike(details.NewId, new MongoId(like.GetString()!));
                }

                string name = details.Locales.TryGetValue("en", out var en) ? en.Name ?? details.NewItemName : details.NewItemName;
                logger.Success($"Tweakbox: custom items - added {name} ({details.NewId}).");
                created.Add((details.NewId, raw));
            }
            else
            {
                logger.Warning($"Tweakbox: custom items - {details.NewItemName} not added: {string.Join("; ", result.Errors ?? [])}");
            }
        }

        // Second pass, once every custom item exists: slot edits and ready-made presets may refer to each other.
        foreach ((MongoId id, JsonElement raw) in created)
        {
            if (raw.TryGetProperty("slots", out JsonElement slots) && slots.ValueKind == JsonValueKind.Object)
            {
                EditSlots(id, slots);
            }

            if (raw.TryGetProperty("presets", out JsonElement presets) && presets.ValueKind == JsonValueKind.Array)
            {
                foreach (JsonElement preset in presets.EnumerateArray())
                {
                    AddPreset(id, preset);
                }
            }
        }
    }

    // "slots": { "mod_x": { "filter": [ids] } | { "add": [ids] } | { "remove": true } } - edits the new item's own slots.
    private void EditSlots(MongoId id, JsonElement edits)
    {
        TemplateItemProperties? props = templateTable.Items[id].Properties;
        if (props == null)
        {
            return;
        }

        List<Slot> slots = (props.Slots ?? []).ToList();
        foreach (JsonProperty edit in edits.EnumerateObject())
        {
            Slot? slot = slots.FirstOrDefault(s => s.Name == edit.Name);
            if (slot == null)
            {
                logger.Warning($"Tweakbox: custom items - {id} has no slot '{edit.Name}' to edit.");
                continue;
            }

            if (edit.Value.TryGetProperty("remove", out JsonElement remove) && remove.ValueKind == JsonValueKind.True)
            {
                slots.Remove(slot);
                continue;
            }

            HashSet<MongoId>? filter = slot.Properties?.Filters?.FirstOrDefault()?.Filter;
            if (filter == null)
            {
                continue;
            }

            if (edit.Value.TryGetProperty("filter", out JsonElement set))
            {
                filter.Clear();
            }

            foreach (string key in new[] { "filter", "add" })
            {
                if (edit.Value.TryGetProperty(key, out JsonElement list) && list.ValueKind == JsonValueKind.Array)
                {
                    foreach (JsonElement tpl in list.EnumerateArray())
                    {
                        filter.Add(new MongoId(tpl.GetString()));
                    }
                }
            }
        }

        props.Slots = slots;
        logger.Info($"Tweakbox: custom items - {id}: {edits.EnumerateObject().Count()} slot edit(s) applied.");
    }

    // "presets": [ { "id", "name", "default": true, "label", "items": [ { "id", "tpl", "parent", "slot" } ] } ] - the first
    // item is the root. "label" is what the game prints after the weapon's name for a non-default build (vanilla e.g.
    // "Magpul", "Saboteur"); the game looks it up in the locales under the preset id and shows the raw id if it's missing.
    // Leave "label" out to keep the plain weapon name.
    private void AddPreset(MongoId id, JsonElement json)
    {
        List<Item> items = [];
        foreach (JsonElement e in json.GetProperty("items").EnumerateArray())
        {
            Item item = new() { Id = new MongoId(e.GetProperty("id").GetString()), Template = new MongoId(e.GetProperty("tpl").GetString()) };
            if (e.TryGetProperty("parent", out JsonElement parent))
            {
                item.ParentId = parent.GetString();
                item.SlotId = e.GetProperty("slot").GetString();
            }

            items.Add(item);
        }

        MongoId presetId = new(json.GetProperty("id").GetString());
        bool isDefault = !json.TryGetProperty("default", out JsonElement d) || d.ValueKind != JsonValueKind.False;
        string label = json.TryGetProperty("label", out JsonElement l) ? l.GetString() ?? "" : "";
        globalTable.ItemPresets[presetId] = new Preset
        {
            Id = presetId,
            Type = "Preset",
            // Vanilla: every non-default preset renames the weapon (adds its label), default ones don't. A build
            // without a label keeps the plain weapon name.
            ChangeWeaponName = !isDefault && label.Length > 0,
            Name = json.GetProperty("name").GetString() ?? "preset",
            Parent = items[0].Id,
            Items = items,
            // Only default presets carry _encyclopedia. Must stay a real null (the field is left out): a plain
            // "isDefault ? id : null" becomes an EMPTY MongoId, sent as "" - the game then dies on load with
            // "Critical MongoId error: incorrect length".
            Encyclopedia = isDefault ? id : (MongoId?)null,
        };

        // Same for every language, like vanilla's default presets (which all have "").
        string presetKey = presetId.ToString();
        foreach (var language in localeTable.Global.Values)
        {
            language.AddTransformer(localeData =>
            {
                if (localeData != null)
                {
                    localeData[presetKey] = label;
                }

                return localeData;
            });
        }

        logger.Info(
            $"Tweakbox: custom items - preset '{json.GetProperty("name").GetString()}' added ({items.Count} parts"
                + (label.Length > 0 ? $", shown as \"{label}\"" : "")
                + ")."
        );
    }
}
