using System.Runtime.CompilerServices;
using BepInEx.Configuration;
using EFT;
using EFT.InventoryLogic;
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

    internal static ConfigEntry<bool> FillLight;
    internal static ConfigEntry<float> FillStrength;
    internal static ConfigEntry<float> FillRange;
    internal static ConfigEntry<bool> FillShadows;

    internal static ConfigEntry<float> FlickerStrength;
    internal static ConfigEntry<float> FlickerSpeed;

    internal static ConfigEntry<float> GlowTolerance;

    internal static void Bind(ConfigFile config)
    {
        const string fall = "White Flare - Descent";
        SlowDescent = config.Bind(fall, "Slow Descent", true,
            "After ignition the flare brakes and drifts down like a parachute flare. Off = vanilla fall (about 7 m/s).");
        DescentSpeed = config.Bind(fall, "Descent Speed (m/s)", 1.0f,
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

        const string fill = "White Flare - Fill Light";
        FillLight = config.Bind(fill, "Fill Light", true,
            "Adds a wide point light next to the downward spotlight, so trees and walls to the sides light up as the flare drops below them, like a real flare lighting up 360 degrees. Off = spotlight only.");
        FillStrength = config.Bind(fill, "Fill Strength", 0.35f,
            new ConfigDescription("Fill light brightness as a fraction of the spotlight's (it follows the same fade in and out and flicker). 0.35 = about a third.", new AcceptableValueRange<float>(0.05f, 2f)));
        FillRange = config.Bind(fill, "Fill Range (m)", 70f,
            new ConfigDescription("How far the fill light reaches in every direction.", new AcceptableValueRange<float>(10f, 250f)));
        FillShadows = config.Bind(fill, "Fill Shadows", false,
            "Let the fill light cast shadows. Costs noticeably more frame rate (a point light renders six shadow maps), so it is off by default; without it the fill light shines through walls a little.");

        const string flicker = "White Flare - Flicker";
        FlickerStrength = config.Bind(flicker, "Flicker Strength", 0.15f,
            new ConfigDescription("How much the flare's light wavers, like a burning flare. Roughly the size of the brightness swings as a fraction of normal (0.15 = about 15% either way). 0 = steady light. Applies to the spotlight, the fill light and, once landed, the ground light. Takes effect live.", new AcceptableValueRange<float>(0f, 0.6f)));
        FlickerSpeed = config.Bind(flicker, "Flicker Speed", 1f,
            new ConfigDescription("How fast the flicker is. Higher = more nervous. Takes effect live.", new AcceptableValueRange<float>(0.2f, 4f)));

        GlowTolerance = config.Bind("White Flare - Glow", "Glow Occlusion Tolerance (m)", 0.2f,
            new ConfigDescription("The bright star glare fades whenever something (branches, wires, rain) is in front of it. 0.2 is the vanilla value. Raise it in steps (2, 20, 200) if the glare drops out now and then; a very high value makes it show through everything.", new AcceptableValueRange<float>(0.2f, 1000f)));
    }

    internal static bool IsWhite(FlareCartridgeSettings settings)
    {
        return settings != null && settings.FlareColorType == FlareColorType.LightFlare;
    }
}

// Sets the burn time on the settings object just before FlareCartridge.Init reads it.
//
// This deliberately does NOT patch the FlareCartridgeSettings.FlareLifetime getter. That getter is a
// one-line property (`=> _flareLifetime`), which the Mono JIT inlines into FlareCartridge.Update and
// Init, so a Harmony patch on it is silently bypassed and the flare dies at the baked 20 s.
// Writing the field means every read - inlined or not - sees the configured value, and it also
// feeds the effect's particle duration, fade curve and sound fade, which all take the lifetime.
[HarmonyPatch(typeof(FlareCartridge), "Init", new[] { typeof(FlareCartridgeSettings), typeof(IPlayer), typeof(Ammo), typeof(Weapon) })]
internal static class WhiteFlareLifetimePatch
{
    private static readonly AccessTools.FieldRef<FlareCartridgeSettings, float> LifetimeRef =
        AccessTools.FieldRefAccess<FlareCartridgeSettings, float>("_flareLifetime");

    private static void Prefix(FlareCartridgeSettings flareCartridgeSettings, Weapon weapon)
    {
        if (!WhiteFlare.IsWhite(flareCartridgeSettings))
        {
            return;
        }

        // The single-use handheld flare (RSP-30 / ROP-30) is a "one-off" weapon; the SP-81 flare gun is not.
        bool handheld = weapon != null && weapon.IsOneOff;
        LifetimeRef(flareCartridgeSettings) = handheld
            ? TweakboxClientPlugin.HandheldBurnSeconds.Value
            : TweakboxClientPlugin.GunBurnSeconds.Value;
    }
}

// The effect prefab (light, smoke, particles) is created in FlareCartridge.Init and configured
// by SetFlareEffect, then switched off until ignition - so anything set here lands before the
// game's culling system registers the light on first activation.
[HarmonyPatch(typeof(FlareShotEffectSelector), nameof(FlareShotEffectSelector.SetFlareEffect))]
internal static class WhiteFlareLightPatch
{
    private static void Postfix(FlareShotEffectSelector __instance, FlareColorType flareColorType, float lifetime)
    {
        if (flareColorType != FlareColorType.LightFlare)
        {
            return;
        }

        Light light = __instance._flareLight;
        Light fill = ExtraEffects(__instance, light);
        AddFlicker(light, fill);
        RestretchEmission(__instance._flareParticleSystem, lifetime);

        if (!WhiteFlare.DownwardSpot.Value || light == null)
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

    // SetFlareEffect (vanilla) already stretches the particle system's own Main.duration and
    // startLifetime to the new lifetime, so the glow itself lives exactly as long as it should. What
    // it never touches is the Emission module's bursts: a handful of repeating flashes baked in the
    // prefab, timed for the vanilla 20 s flare. At our much longer burn time they keep firing on their
    // original ~20 s cadence, which looks like the whole glow switching off and back on every 20 s.
    // Rescaling each burst's time and repeat interval by how much we stretched the lifetime spreads
    // the same flashes across the new duration instead - whatever the original count and spacing were,
    // this works without needing to know their baked values.
    private static void RestretchEmission(ParticleSystem flareParticles, float lifetime)
    {
        if (flareParticles == null || lifetime <= 0.001f)
        {
            return;
        }

        ParticleSystem.EmissionModule emission = flareParticles.emission;
        int count = emission.burstCount;
        if (count == 0)
        {
            return;
        }

        float scale = lifetime / 20f; // vanilla's baked assumption
        ParticleSystem.Burst[] bursts = new ParticleSystem.Burst[count];
        emission.GetBursts(bursts);
        for (int i = 0; i < count; i++)
        {
            bursts[i].time *= scale;
            bursts[i].repeatInterval *= scale;
        }

        emission.SetBursts(bursts);
    }

    // Runs for every white flare, whatever the spotlight setting. Returns the fill light, if one was made.
    private static Light ExtraEffects(FlareShotEffectSelector selector, Light light)
    {
        Light fill = null;
        if (WhiteFlare.FillLight.Value && WhiteFlare.DownwardSpot.Value && light != null)
        {
            GameObject go = new GameObject("TweakboxFillLight");
            go.transform.SetParent(light.transform.parent, false);
            go.transform.localPosition = light.transform.localPosition;

            fill = go.AddComponent<Light>();
            fill.type = LightType.Point;
            fill.range = WhiteFlare.FillRange.Value;
            fill.color = light.color;
            fill.intensity = 0f;
            fill.shadows = WhiteFlare.FillShadows.Value ? LightShadows.Soft : LightShadows.None;
        }

        // The glare material has a depth check: anything nearer than the flare (minus this offset) hides it.
        float tolerance = WhiteFlare.GlowTolerance.Value;
        if (tolerance > 0.201f && selector._flareParticleSystem != null)
        {
            ParticleSystemRenderer glare = selector._flareParticleSystem.GetComponent<ParticleSystemRenderer>();
            if (glare != null)
            {
                Material material = glare.material; // per-flare copy, so other flares keep the vanilla values
                if (material.HasProperty("_DepthOffset"))
                {
                    material.SetFloat("_DepthOffset", tolerance);
                }

                if (material.HasProperty("_FadeDepthOffset"))
                {
                    material.SetFloat("_FadeDepthOffset", tolerance * 1.5f); // vanilla ratio 0.3 : 0.2
                }
            }
        }

        return fill;
    }

    // One component drives the flare's light (flicker) and the fill light (follows it), so the two can
    // never disagree about order within a frame.
    private static void AddFlicker(Light light, Light fill)
    {
        if (light == null)
        {
            return;
        }

        FlareLightFlicker flicker = light.gameObject.AddComponent<FlareLightFlicker>();
        flicker.Main = light;
        flicker.Fill = fill;
        flicker.FillStrength = WhiteFlare.FillStrength.Value;
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

        // The main light is an ordinary point light again, so the extra fill light would just double it.
        FlareLightFlicker flicker = light.GetComponent<FlareLightFlicker>();
        if (flicker != null && flicker.Fill != null)
        {
            Object.Destroy(flicker.Fill.gameObject);
        }
    }
}

// Makes the flare's light waver like a burning flare, and keeps the fill light locked to it.
//
// The game sets the flare light's intensity only when its fade envelope or distance fade changes, and only
// once every ~20 frames (CullingLightObject.CustomUpdate, called from CullingManager.Update). Between those
// writes the light just holds its value. So each frame this reads the intensity back: if it still equals what
// this component wrote last frame the game has not touched it, and the baseline stays as it was; if it differs
// the game wrote a fresh baseline and that is picked up. Either way the flicker is applied to a baseline, never
// stacked on top of itself. It runs in LateUpdate, i.e. after the game's Update-time write.
public sealed class FlareLightFlicker : MonoBehaviour
{
    public Light Main;
    public Light Fill;
    public float FillStrength;

    private float _seed;
    private float _baseline;
    private float _lastWritten = float.NaN;

    private void Awake()
    {
        // Each flare wavers differently, so several in the air do not pulse in step.
        _seed = Random.value * 200f + 5f;
    }

    private void OnEnable()
    {
        _lastWritten = float.NaN;
    }

    private void LateUpdate()
    {
        if (Main == null)
        {
            return;
        }

        bool live = Main.enabled;
        if (Fill != null)
        {
            Fill.enabled = live;
        }

        if (!live)
        {
            _lastWritten = float.NaN;
            return;
        }

        float current = Main.intensity;
        if (!Mathf.Approximately(current, _lastWritten))
        {
            _baseline = current;
        }

        float factor = Factor();
        Main.intensity = _baseline * factor;
        _lastWritten = Main.intensity;

        if (Fill != null)
        {
            Fill.intensity = _baseline * FillStrength * factor;
        }
    }

    // Three layers of smooth noise: a quick flutter, a slower wobble and a lazy drift, so it never looks like a loop.
    private float Factor()
    {
        float strength = WhiteFlare.FlickerStrength.Value;
        if (strength <= 0f)
        {
            return 1f;
        }

        float t = Time.time * WhiteFlare.FlickerSpeed.Value;
        float offset = 0.5f * Noise(t * 8f, _seed)
                     + 0.35f * Noise(t * 2.3f, _seed + 31f)
                     + 0.15f * Noise(t * 0.6f, _seed + 67f);

        // Perlin noise rarely reaches its extremes, so the x2 makes the strength setting roughly the peak swing.
        return Mathf.Clamp(1f + strength * 2f * offset, 0.2f, 2f);
    }

    private static float Noise(float x, float y)
    {
        return Mathf.PerlinNoise(x, y) * 2f - 1f;
    }
}
