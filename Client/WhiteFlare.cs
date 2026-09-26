using System.Runtime.CompilerServices;
using BepInEx.Configuration;
using EFT;
using EFT.PrefabSettings;
using HarmonyLib;
using Systems.Effects;
using UnityEngine;

namespace TweakboxClient;

// Turns the white (illumination) flare into a slow parachute-style flare: after ignition it
// brakes smoothly and drifts down, and its light becomes a wide spotlight pointing straight
// down instead of a short-range point light.
//
// Everything here is simulated locally on each client (the flare is a client-side physics
// object and light), so it only shows for players who have this plugin installed.
// The values are read every time a flare is fired, so they can be tuned live in the F12 menu.
internal static class WhiteFlare
{
    internal static ConfigEntry<bool> SlowDescent;
    internal static ConfigEntry<float> DescentSpeed;
    internal static ConfigEntry<float> SlowDownTime;

    internal static ConfigEntry<bool> DownwardSpot;
    internal static ConfigEntry<float> SpotAngle;
    internal static ConfigEntry<float> SpotRange;
    internal static ConfigEntry<float> Brightness;
    internal static ConfigEntry<float> VisibleDistance;
    internal static ConfigEntry<bool> CastShadows;
    internal static ConfigEntry<float> ShadowDistance;
    internal static ConfigEntry<float> LandedRange;

    internal static void Bind(ConfigFile config)
    {
        const string fall = "White Flare - Descent";
        SlowDescent = config.Bind(fall, "Slow Descent", true,
            "After ignition the flare brakes and drifts down like a parachute flare. Off = vanilla fall (about 7 m/s).");
        DescentSpeed = config.Bind(fall, "Descent Speed (m/s)", 1.5f,
            new ConfigDescription("How fast it sinks once it has slowed down. Lower = hangs in the air longer.", new AcceptableValueRange<float>(0.3f, 8f)));
        SlowDownTime = config.Bind(fall, "Slow-Down Time (s)", 1.5f,
            new ConfigDescription("How long the braking takes after ignition. Higher = it carries on further before it starts to drift.", new AcceptableValueRange<float>(0.1f, 6f)));

        const string light = "White Flare - Light";
        DownwardSpot = config.Bind(light, "Downward Spotlight", true,
            "Replace the flare's short-range point light with a wide spotlight pointing straight down. Off = vanilla light.");
        SpotAngle = config.Bind(light, "Spot Angle (degrees)", 110f,
            new ConfigDescription("Width of the light cone. Wider lights a bigger area but thinner.", new AcceptableValueRange<float>(20f, 170f)));
        SpotRange = config.Bind(light, "Spot Range (m)", 150f,
            new ConfigDescription("How far down the light reaches. Should be at least the height the flare is fired to.", new AcceptableValueRange<float>(30f, 500f)));
        Brightness = config.Bind(light, "Brightness", 2.5f,
            new ConfigDescription("Light strength. 2.5 is the vanilla value; it is spread over a much larger area now, so raise it if the ground looks dim.", new AcceptableValueRange<float>(0.1f, 10f)));
        VisibleDistance = config.Bind(light, "Light Visible Distance (m)", 250f,
            new ConfigDescription("The game switches a flare's light off beyond about 30 m from the camera, which is why a flare overhead lights nothing. This raises that limit.", new AcceptableValueRange<float>(30f, 600f)));
        CastShadows = config.Bind(light, "Cast Shadows", true,
            "Buildings and trees block the light. Turn off if frame rate drops while a flare is up (the light then shines through roofs).");
        ShadowDistance = config.Bind(light, "Shadow Distance (m)", 100f,
            new ConfigDescription("Beyond this distance from the camera the light stops casting shadows.", new AcceptableValueRange<float>(20f, 300f)));
        LandedRange = config.Bind(light, "Landed Light Range (m)", 30f,
            new ConfigDescription("Once the flare hits something it turns back into a normal point light with this range, since a downward spot would light nothing.", new AcceptableValueRange<float>(5f, 100f)));
    }

    internal static bool IsWhite(FlareCartridgeSettings settings)
    {
        return settings != null && settings.FlareColorType == FlareColorType.LightFlare;
    }
}

// The effect prefab (light, smoke, particles) is created in FlareCartridge.Init and configured
// by SetFlareEffect, then switched off until ignition - so anything set here lands before the
// game's culling system registers the light on first activation.
[HarmonyPatch(typeof(FlareShotEffectSelector), nameof(FlareShotEffectSelector.SetFlareEffect))]
internal static class WhiteFlareLightPatch
{
    private static void Postfix(FlareShotEffectSelector __instance, FlareColorType flareColorType)
    {
        if (flareColorType != FlareColorType.LightFlare || !WhiteFlare.DownwardSpot.Value)
        {
            return;
        }

        Light light = __instance._flareLight;
        if (light == null)
        {
            return;
        }

        light.type = LightType.Spot;
        light.spotAngle = WhiteFlare.SpotAngle.Value;
        light.range = WhiteFlare.SpotRange.Value;

        // The effect root is forced upright every frame by FlareShotEffectAnimator, but the light
        // is a child of it, so its own rotation is free: pitch it to look straight down.
        light.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);

        // Effective light strength is maxLightIntensity * distance fade * fade curve * this value.
        if (__instance._flareAnimator != null)
        {
            __instance._flareAnimator.LightIntensity = WhiteFlare.Brightness.Value;
        }

        CullingLightObject culling = light.GetComponent<CullingLightObject>();
        if (culling == null)
        {
            return;
        }

        float far = WhiteFlare.VisibleDistance.Value;
        culling._fadeStartDistance = far * 0.6f;
        culling._fadeEndDistance = far;
        culling.CullDistance = far;
        culling.CacheLightSqrDistances();

        float shadowFar = WhiteFlare.ShadowDistance.Value;
        culling._shadowsFadeStartDistance = shadowFar * 0.85f;
        culling._shadowsFadeEndDistance = shadowFar;
        culling.CacheShadowSqrDistances();

        if (!WhiteFlare.CastShadows.Value)
        {
            light.shadows = LightShadows.None;
            culling._initialShadowsMode = LightShadows.None;
        }
    }
}

[HarmonyPatch(typeof(FlareCartridge), nameof(FlareCartridge.Update))]
internal static class WhiteFlareFlightPatch
{
    private static readonly AccessTools.FieldRef<FlareCartridge, FlareCartridgeSettings> SettingsRef =
        AccessTools.FieldRefAccess<FlareCartridge, FlareCartridgeSettings>("_flareCartridgeSettings");
    private static readonly AccessTools.FieldRef<FlareCartridge, bool> StartedRef =
        AccessTools.FieldRefAccess<FlareCartridge, bool>("_flareStarted");
    private static readonly AccessTools.FieldRef<FlareCartridge, float> StartTimeRef =
        AccessTools.FieldRefAccess<FlareCartridge, float>("_startTime");
    private static readonly AccessTools.FieldRef<FlareCartridge, bool> LandedRef =
        AccessTools.FieldRefAccess<FlareCartridge, bool>("_dragDroppedAfterCollision");
    private static readonly AccessTools.FieldRef<FlareCartridge, GameObject> EffectRef =
        AccessTools.FieldRefAccess<FlareCartridge, GameObject>("_flareEffectPrefab");

    private sealed class State
    {
        public Rigidbody Body;
        public bool BackToPoint;
    }

    private static readonly ConditionalWeakTable<FlareCartridge, State> States = new();

    private static void Postfix(FlareCartridge __instance)
    {
        FlareCartridgeSettings settings = SettingsRef(__instance);
        if (!WhiteFlare.IsWhite(settings))
        {
            return;
        }

        State state = States.GetOrCreateValue(__instance);

        // Once it has hit something the game applies its own heavy ground drag and takes over.
        if (LandedRef(__instance))
        {
            if (!state.BackToPoint)
            {
                state.BackToPoint = true;
                RestorePointLight(EffectRef(__instance));
            }
            return;
        }

        if (!WhiteFlare.SlowDescent.Value || !StartedRef(__instance))
        {
            return;
        }

        state.Body ??= __instance.GetComponent<Rigidbody>();
        if (state.Body == null)
        {
            return;
        }

        // Unity drag settles a falling body at gravity / drag, so pick the drag that gives the
        // wanted sink speed, and blend to it so the flare slows down instead of stopping dead.
        float sinceIgnition = Time.time - StartTimeRef(__instance) - settings.FlareTimeAfterStart;
        float blend = Mathf.Clamp01(sinceIgnition / Mathf.Max(0.05f, WhiteFlare.SlowDownTime.Value));
        float target = Physics.gravity.magnitude / Mathf.Max(0.1f, WhiteFlare.DescentSpeed.Value);
        state.Body.drag = Mathf.Lerp(settings.RigidbodyDrag, target, blend);
    }

    // A spotlight pointing down lights nothing once the flare lies on the ground, so it goes
    // back to an ordinary point light.
    private static void RestorePointLight(GameObject effect)
    {
        if (effect == null || !WhiteFlare.DownwardSpot.Value)
        {
            return;
        }

        Light light = effect.GetComponent<FlareShotEffectSelector>()?._flareLight;
        if (light == null)
        {
            return;
        }

        light.type = LightType.Point;
        light.range = WhiteFlare.LandedRange.Value;
        light.transform.localRotation = Quaternion.identity;
    }
}
