using BepInEx;
using BepInEx.Configuration;
using HarmonyLib;

namespace TweakboxClient;

[BepInPlugin("com.local.tweakbox.client", "Tweakbox Client", "1.2.1")]
public class TweakboxClientPlugin : BaseUnityPlugin
{
    // How long white flares burn. Applied in WhiteFlareLifetimePatch (see WhiteFlare.cs).
    internal static ConfigEntry<float> GunBurnSeconds;
    internal static ConfigEntry<float> HandheldBurnSeconds;
    internal static BepInEx.Logging.ManualLogSource Log;

    private void Awake()
    {
        Log = Logger;

        GunBurnSeconds = Config.Bind(
            "Flares",
            "Flare Gun Burn Time (seconds)",
            65f,
            new ConfigDescription(
                "How long a white flare fired from the SP-81 flare gun burns. Vanilla is 20 seconds. Red, green, yellow and acid green signal flares are unaffected.",
                new AcceptableValueRange<float>(5f, 600f)
            )
        );
        HandheldBurnSeconds = Config.Bind(
            "Flares",
            "Handheld Flare Burn Time (seconds)",
            80f,
            new ConfigDescription(
                "How long the single-use white handheld flare (RSP-30 / ROP-30) burns. Vanilla is 20 seconds.",
                new AcceptableValueRange<float>(5f, 600f)
            )
        );

        WhiteFlare.Bind(Config);
#if TWEAKBOX_DEBUG
        DebugTools.Bind(Config);
#endif

        new Harmony("com.local.tweakbox.client").PatchAll();
    }
}
