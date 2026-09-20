using BepInEx;
using BepInEx.Configuration;
using EFT.PrefabSettings;
using HarmonyLib;

namespace TweakboxClient;

[BepInPlugin("com.local.tweakbox.client", "Tweakbox Client", "1.0.0")]
public class TweakboxClientPlugin : BaseUnityPlugin
{
    // FlareCartridgeSettings.FlareLifetime is read live every frame in
    // FlareCartridge.Update() rather than cached at launch, so a postfix on the
    // getter is enough - no need to touch the AssetBundle. Baked value for both
    // white flares (SP-81 pistol round and the RSP-30 handheld) is 20s.
    // FlareColorType.LightFlare (0) is what both white flares report; the
    // signal colours (red/green/yellow/acid green) use different values, so
    // gating on it leaves them untouched.
    private static ConfigEntry<float> _whiteFlareSeconds;

    private void Awake()
    {
        _whiteFlareSeconds = Config.Bind(
            "Flares",
            "White Flare Burn Time (seconds)",
            120f,
            new ConfigDescription(
                "How long white/illumination flares (SP-81 pistol cartridge and the RSP-30 handheld) stay lit. Vanilla is 20 seconds. Red, green, yellow and acid green signal flares are unaffected.",
                new AcceptableValueRange<float>(5f, 600f)
            )
        );

        new Harmony("com.local.tweakbox.client").PatchAll();
    }

    [HarmonyPatch(typeof(FlareCartridgeSettings), nameof(FlareCartridgeSettings.FlareLifetime), MethodType.Getter)]
    private static class FlareLifetimePatch
    {
        private static void Postfix(FlareCartridgeSettings __instance, ref float __result)
        {
            if (__instance.FlareColorType == FlareColorType.LightFlare)
            {
                __result = _whiteFlareSeconds.Value;
            }
        }
    }
}
