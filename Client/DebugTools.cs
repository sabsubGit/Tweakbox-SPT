#if TWEAKBOX_DEBUG
// Testing build only (dotnet build -c Testing). None of this is compiled into the release package.
//
// Adds a "Debug" section to the F12 menu with buttons that ask the (Testing-build) Tweakbox server mod
// to mail test items to your profile, using the same delivery as SPT's own "spt give" chat command.
using System;
using BepInEx.Configuration;
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
        AddButton(config, "Mail me an SP-81 flare gun", "620109578d82e67e7911abf2", 1, 3);
        AddButton(config, "Mail me 5 white flare cartridges", "62389bc9423ed1685422dc57", 5, 2);
        AddButton(config, "Mail me a white handheld flare (RSP-30)", "62178be9d0050232da3485d9", 1, 1);
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
