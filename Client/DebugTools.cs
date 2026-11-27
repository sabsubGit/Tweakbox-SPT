#if TWEAKBOX_DEBUG
// Testing build only (dotnet build -c Testing). None of this is compiled into the release package.
//
// Adds a "Debug" section to the F12 menu with buttons that ask the (Testing-build) Tweakbox server mod
// to mail test items to your profile, using the same delivery as SPT's own "spt give" chat command.
using System;
using System.Linq;
using BepInEx.Configuration;
using EFT;
using EFT.Interactive;
using SPT.Common.Http;
using UnityEngine;

namespace TweakboxClient;

// The F12 configuration manager looks for a class with this name (by reflection) in the tags of a setting.
internal sealed class ConfigurationManagerAttributes
{
    public Action<ConfigEntryBase> CustomDrawer;
    public bool? HideDefaultButton;
    public bool? HideSettingName;
    public int? Order;
}

internal static class DebugTools
{
    private const string Section = "Debug (testing build only)";

    internal static void Bind(ConfigFile config)
    {
        AddAction(config, "Mail me the RK 62 test kit (every new part, magazines, ammo)", () => SendKit("rk62"), 7);
        AddButton(config, "Mail me 500,000 roubles", "5449016a4bdc2d6f028b456f", 500000, 6);
        AddButton(config, "Mail me 10,000 dollars", "5696686a4bdc2da3298b456a", 10000, 5);
        AddButton(config, "Mail me 10,000 euros", "569668774bdc2da2298b4568", 10000, 4);
        AddButton(config, "Mail me an SP-81 flare gun", "620109578d82e67e7911abf2", 1, 3);
        AddButton(config, "Mail me 5 white flare cartridges", "62389bc9423ed1685422dc57", 5, 2);
        AddButton(config, "Mail me a white handheld flare (RSP-30)", "62178be9d0050232da3485d9", 1, 1);
        AddAction(config, "Report hidden caches on this map (in raid)", ReportCaches, 0);
    }

    private static void AddAction(ConfigFile config, string label, Action action, int order)
    {
        config.Bind(
            Section,
            label,
            false,
            new ConfigDescription(
                "Writes the result to BepInEx/LogOutput.log.",
                null,
                new ConfigurationManagerAttributes
                {
                    HideSettingName = true,
                    HideDefaultButton = true,
                    Order = order,
                    CustomDrawer = _ =>
                    {
                        if (GUILayout.Button(label, GUILayout.ExpandWidth(true)))
                        {
                            action();
                        }
                    },
                }
            )
        );
    }

    private const string GroundCacheTpl = "5d6d2b5486f774785c2ba8ea";
    private const string BuriedBarrelTpl = "5d6d2bb386f774785b07a77a";

    // Lists every ground cache and buried barrel container the map scene has, and which of them got loot this
    // raid (the game gives a picked container an item owner; unpicked ones stay without one).
    private static void ReportCaches()
    {
        var log = TweakboxClientPlugin.Log;
        try
        {
            GameWorld world = Comfort.Common.Singleton<GameWorld>.Instance;
            Vector3 me = world?.MainPlayer != null ? world.MainPlayer.Transform.position : Vector3.zero;
            LootableContainer[] all = UnityEngine.Object.FindObjectsOfType<LootableContainer>(true);
            log.LogInfo($"Cache report: {all.Length} lootable containers in the scene. You are at {me}.");
            foreach (var (tpl, name) in new[] { (GroundCacheTpl, "Ground cache"), (BuriedBarrelTpl, "Buried barrel") })
            {
                var found = all.Where(c => c.Template == tpl).OrderBy(c => Vector3.Distance(me, c.transform.position)).ToList();
                int spawned = found.Count(c => c.ItemOwner != null);
                log.LogInfo($"Cache report: {name}: {found.Count} in the scene, {spawned} spawned this raid.");
                foreach (LootableContainer c in found)
                {
                    Vector3 p = c.transform.position;
                    log.LogInfo($"   {(c.ItemOwner != null ? "SPAWNED" : "empty  ")} {c.Id} at {p} - {Vector3.Distance(me, p):0} m away, active={c.gameObject.activeInHierarchy}");
                }
            }
        }
        catch (Exception ex)
        {
            log.LogError("Cache report failed (are you in a raid?): " + ex);
        }
    }

    private static void AddButton(ConfigFile config, string label, string tpl, int count, int order)
    {
        // The setting itself is a dummy bool; the custom drawer replaces its widget with a button.
        config.Bind(
            Section,
            label,
            false,
            new ConfigDescription(
                "Sends the item to your in-game mail. Open the messenger in the main menu to collect it.",
                null,
                new ConfigurationManagerAttributes
                {
                    HideSettingName = true,
                    HideDefaultButton = true,
                    Order = order,
                    CustomDrawer = _ =>
                    {
                        if (GUILayout.Button(label, GUILayout.ExpandWidth(true)))
                        {
                            Send(label, tpl, count);
                        }
                    },
                }
            )
        );
    }

    private static void SendKit(string kit)
    {
        try
        {
            RequestHandler.PostJson("/tweakbox/debug/kit", "{\"kit\":\"" + kit + "\"}");
            TweakboxClientPlugin.Log.LogInfo("Debug: asked the server to mail the test kit: " + kit);
        }
        catch (Exception ex)
        {
            TweakboxClientPlugin.Log.LogError("Debug: kit request failed - is the server running the Testing build of Tweakbox? " + ex.Message);
        }
    }

    private static void Send(string label, string tpl, int count)
    {
        try
        {
            RequestHandler.PostJson("/tweakbox/debug/give", "{\"tpl\":\"" + tpl + "\",\"count\":" + count + "}");
            TweakboxClientPlugin.Log.LogInfo("Debug: asked the server to mail: " + label);
        }
        catch (Exception ex)
        {
            TweakboxClientPlugin.Log.LogError("Debug: mail request failed - is the server running the Testing build of Tweakbox? " + ex.Message);
        }
    }
}
#endif
