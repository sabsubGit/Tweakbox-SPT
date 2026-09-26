#if TWEAKBOX_DEBUG
// Testing build only (dotnet build -c Testing). None of this is compiled into the release package.
//
// Lets the client's F12 debug buttons mail a test item to whichever profile is logged in, using the same
// item-building and mail delivery as SPT's own "spt give" chat command.
using System.Text.Json.Serialization;
using SPTarkov.Common.Models.Logging;
using SPTarkov.DI.Annotations;
using SPTarkov.Server.Core.DI;
using SPTarkov.Server.Core.Extensions;
using SPTarkov.Server.Core.Helpers.Items;
using SPTarkov.Server.Core.Models.Common;
using SPTarkov.Server.Core.Models.Eft.Common.Tables;
using SPTarkov.Server.Core.Models.Spt.Tables;
using SPTarkov.Server.Core.Models.Utils;
using SPTarkov.Server.Core.Services.Commerce;
using SPTarkov.Server.Core.Utils;
using SPTarkov.Server.Core.Utils.Cloners;

namespace Tweakbox;

public sealed class TweakboxGiveRequest : IRequestData
{
    [JsonPropertyName("tpl")]
    public string Tpl { get; set; } = string.Empty;

    [JsonPropertyName("count")]
    public int Count { get; set; } = 1;
}

[Injectable(InjectionType.Singleton)]
public sealed class TweakboxDebugGive(
    TemplateTable templateTable,
    ItemHelper itemHelper,
    PresetHelper presetHelper,
    MailSendService mailSendService,
    ICloner cloner,
    ISptLogger<TweakboxDebugGive> logger
)
{
    public void Send(MongoId sessionId, TweakboxGiveRequest request)
    {
        if (request.Tpl.Length != 24 || !request.Tpl.All(Uri.IsHexDigit))
        {
            logger.Warning($"Tweakbox debug give: '{request.Tpl}' is not an item id, ignoring.");
            return;
        }

        MongoId tpl = new(request.Tpl);
        if (!templateTable.Items.TryGetValue(tpl, out TemplateItem? template))
        {
            logger.Warning($"Tweakbox debug give: item {request.Tpl} is not in the database, ignoring.");
            return;
        }

        int count = Math.Clamp(request.Count, 1, 100);
        List<Item> items = [];

        // Same three cases SPT's give command handles: a default preset (weapons with their parts),
        // single-item templates, and stackable items.
        Preset? preset = presetHelper.GetDefaultPreset(tpl);
        if (preset is not null)
        {
            for (int i = 0; i < count; i++)
            {
                items.AddRange((cloner.Clone(preset.Items) ?? []).ReplaceIDs());
            }
        }
        else if (template.Properties?.StackMaxSize == 1)
        {
            for (int i = 0; i < count; i++)
            {
                items.Add(new Item { Id = new MongoId(), Template = tpl, Upd = itemHelper.GenerateUpdForItem(template) });
            }
        }
        else
        {
            Item stack = new() { Id = new MongoId(), Template = tpl, Upd = itemHelper.GenerateUpdForItem(template) };
            stack.Upd!.StackObjectsCount = count;
            items.AddRange(itemHelper.SplitStack(stack));
        }

        itemHelper.SetFoundInRaid(items);
        mailSendService.SendSystemMessageToPlayer(sessionId, $"TWEAKBOX TEST DELIVERY: {count}x {template.Name}", items, 172800L);
        logger.Success($"Tweakbox debug give: mailed {count}x {template.Name} to {sessionId}.");
    }
}

[Injectable(InjectionType.Transient, int.MaxValue, TypePriority = 400000)]
public sealed class TweakboxDebugRouter : StaticRouter
{
    public TweakboxDebugRouter(JsonUtil jsonUtil, HttpResponseUtil http, TweakboxDebugGive give)
        : base(
            jsonUtil,
            new RouteAction[]
            {
                new RouteAction<TweakboxGiveRequest>(
                    "/tweakbox/debug/give",
                    (url, info, sessionId, output, cancellationToken) =>
                    {
                        give.Send(sessionId, info);
                        return new ValueTask<string>(http.NullResponse());
                    }
                ),
            }
        ) { }
}
#endif
