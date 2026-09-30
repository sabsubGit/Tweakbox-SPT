using System.Reflection;
using System.Text.Json;
using SPTarkov.Common.Models.Logging;
using SPTarkov.DI.Annotations;
using SPTarkov.Server.Core.DI;
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

    private void ApplyCustomItems(CustomItemsConfig config)
    {
        if (!config.Enabled || config.Items.Count == 0)
        {
            return;
        }

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
                string name = details.Locales.TryGetValue("en", out var en) ? en.Name ?? details.NewItemName : details.NewItemName;
                logger.Success($"Tweakbox: custom items - added {name} ({details.NewId}).");
            }
            else
            {
                logger.Warning($"Tweakbox: custom items - {details.NewItemName} not added: {string.Join("; ", result.Errors ?? [])}");
            }
        }
    }
}
