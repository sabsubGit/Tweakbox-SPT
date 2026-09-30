# Tweakbox

Small, targeted tweaks for an SPT 4.1.2 Fika co-op wipe, aimed at cutting grind without
touching the checksummed database files. Two parts: a server mod and a matching BepInEx
client plugin.

## Server — `Tweakbox.dll` → `user/mods/Tweakbox/`

- **Custom items** — new items cloned from existing ones in SPT's own clone format, with
  their own models/textures shipped as bundles in `bundles/` (the server sends them to every
  connecting client). Created before SPT loads profiles, so a profile holding one never fails
  validation. Currently: IDEA ISKUB lingonberry soda (+80 hydration), a re-skinned water bottle;
  `tools/rebuild_iskub.sh` rebuilds its bundles from the Blender/Painter exports.
- **Spawn like** — makes an item spawn wherever given look-alike items can: loose loot spots,
  static containers and scav/boss/follower inventory pools, weighted like the rarest look-alike
  present. Currently: the Iskub spawns like water bottles and kvass.
- **Flea unban** — clears BSG's flea-market ban on specific items and seeds a base price
  for them, since a banned item has no scraped flea price to generate offers from.
  Currently: the KS-23M shotgun.
- **Trader stock** — adds offers to a trader's permanent stock, for roubles, dollars, euros or
  a barter. Currently: Jaeger sells the white 26x75mm flare-gun cartridge, the white ROP-30
  handheld flare, and the green 26x75mm cartridge (flare-gun extract trigger) — none
  purchasable for cash in vanilla; Peacekeeper sells the Peltor TEP-300 earplug for $315 at
  LL3; Therapist trades an Iskub for a medical bloodset at LL3.
- **Flea price override** — replaces an item's base flea price. Currently: the two white
  flares, down from their default valuation to something sane.
- **Stack size** — changes how many of an item fit in one stack, keeping the item's loot
  roll inside the new cap (the server does not clamp it). Currently: the white 26x75mm
  flare-gun cartridge stacks to 5.
- **Loot injection** — adds items that never spawn in vanilla loot into static container
  pools (weapon crates, safes, PMC bodies, etc.) at a tuned rarity. Currently: 6 thermal
  optics and 6 top-tier armour/helmet pieces.

All features are independently toggleable in `config.json` and fail in isolation — a
bad entry in one logs a warning and skips, it never stops the server from booting.

## Client — `TweakboxClient.dll` → `BepInEx/plugins/TweakboxClient/`

- **Flare burn time** — white/illumination flares burn longer than vanilla's 20s: 65s from the
  SP-81 flare gun and 80s for the single-use RSP-30 handheld, each configurable. Red, green,
  yellow and acid-green signal flares are untouched.
- **Parachute flare** — after ignition a white flare brakes and drifts down slowly (1 m/s
  instead of about 7), and its light becomes a wide spotlight pointing straight down. The game
  normally switches a flare's light off beyond ~30 m from the camera, so a flare overhead lit
  nothing; that limit is raised for these flares only. Once it lands it turns back into a normal
  point light. A wide point "fill" light next to the spotlight lights trees and walls to the sides as it
  drops. The light also flickers slightly, like a burning flare. Angle, range, brightness, descent speed,
  flicker, fill light and shadows are all tunable in the F12 menu. The bright glow itself no longer
  cycles off and on every 20 seconds - a handful of flashes baked into the effect for vanilla's short
  burn time now spread across however long the flare actually burns.

- **Ammo penetration labels** — a magazine's *Load ammo* menu shows each round's penetration
  in brackets after its name, coloured by the armour class it beats (red <20, orange 20+,
  yellow 30+, green 40+, blue 50+, purple 60+). Toggle under "Ammo Labels" in F12.

Client-side, so it needs installing on every machine in the raid to look consistent —
unlike the server half, it has no effect on its own.

## Config

Server tuning lives in `config.json` next to the DLL (comments and trailing commas are
fine). Client tuning lives in the BepInEx-generated `.cfg` after first launch. Neither
needs a rebuild to retune.

## Install

Download the release zip and copy its `BepInEx` and `SPT` folders into your SPT game folder.
Requires SPT 4.1.x. Every player needs the client plugin (`BepInEx/plugins/TweakboxClient`);
only the person running the server needs `SPT/user/mods/Tweakbox`.

## Building a release

`./package.sh` builds both projects and writes `dist/Tweakbox-<version>.zip`. The client project
compiles against game assemblies that are not in this repo - point the `Assembly-CSharp`
`HintPath` in `Client/TweakboxClient.csproj` at your own `EscapeFromTarkov_Data/Managed` first.
