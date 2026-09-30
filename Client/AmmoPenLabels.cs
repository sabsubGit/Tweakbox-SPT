using System.Collections.Generic;
using System.Linq;
using BepInEx.Configuration;
using Comfort.Common;
using EFT;
using EFT.InventoryLogic;
using EFT.UI;
using HarmonyLib;

namespace TweakboxClient;

// Adds each round's penetration to the magazine "Load ammo" submenu, colour-coded by the armour class it beats
// (pen 30 = class 3, 40 = class 4, ...).
internal static class AmmoPenLabels
{
    internal static ConfigEntry<bool> Enabled;

    internal static void Bind(ConfigFile config)
    {
        Enabled = config.Bind(
            "Ammo Labels",
            "Show Penetration In Load Ammo Menu",
            true,
            "Show each round's penetration in brackets after its name in a magazine's Load Ammo menu, coloured by the armour class it beats."
        );
    }

    internal static string Colour(int pen)
    {
        return pen switch
        {
            >= 60 => "#C58CFF",
            >= 50 => "#4FC3F7",
            >= 40 => "#7BD148",
            >= 30 => "#F4D03F",
            >= 20 => "#F39C4A",
            _ => "#E0625C",
        };
    }

    internal static int? Penetration(string tpl)
    {
        ItemFactory factory = Singleton<ItemFactory>.Instance;
        if (factory?.ItemTemplates == null || !factory.ItemTemplates.TryGetValue(tpl, out ItemTemplate template))
        {
            return null;
        }
        return (template as AmmoTemplate)?.PenetrationPower;
    }
}

[HarmonyPatch(typeof(LoadMagContextInteractions), MethodType.Constructor,
    new[] { typeof(Magazine), typeof(ItemContext), typeof(ItemUiContext) })]
internal static class AmmoPenLabelsPatch
{
    // Entries are keyed by their label, so each one is re-added under the new label.
    private static void Postfix(LoadMagContextInteractions __instance)
    {
        if (!AmmoPenLabels.Enabled.Value)
        {
            return;
        }

        Dictionary<string, DynamicContextInteraction> entries = __instance._dynamicInteractions;
        foreach (DynamicContextInteraction entry in entries.Values.ToList())
        {
            int? pen = AmmoPenLabels.Penetration(entry.Id);
            if (pen == null)
            {
                continue;
            }

            string label = $"{entry.Key} <b><color={AmmoPenLabels.Colour(pen.Value)}>[{pen.Value}]</color></b>";
            entries.Remove(entry.Key);
            entries[label] = new DynamicContextInteraction(entry.Id, label, entry._callback, entry.Icon);
        }
    }
}
