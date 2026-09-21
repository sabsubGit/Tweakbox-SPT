# Tweakbox

Small, targeted tweaks for an SPT 4.1.2 Fika co-op wipe, aimed at cutting grind without
touching the checksummed database files. Two parts: a server mod and a matching BepInEx
client plugin.

## Server — `Tweakbox.dll` → `user/mods/Tweakbox/`

- **Flea unban** — clears BSG's flea-market ban on specific items and seeds a base price
  for them, since a banned item has no scraped flea price to generate offers from.
  Currently: the KS-23M shotgun.
- **Trader stock** — adds cash offers to a trader's permanent stock. Currently: Jaeger
  sells the white 26x75mm flare-gun cartridge, the white ROP-30 handheld flare, and the
  green 26x75mm cartridge (flare-gun extract trigger) — none purchasable for cash in
  vanilla.
- **Flea price override** — replaces an item's base flea price. Currently: the two white
  flares, down from their default valuation to something sane.
- **Stack size** — changes how many of an item fit in one stack, keeping the item's loot
  roll inside the new cap (the server does not clamp it). Currently: the white 26x75mm
  flare-gun cartridge stacks to 5.
- **Loot injection** — adds items that never spawn in vanilla loot into static container
  pools (weapon crates, safes, PMC bodies, etc.) at a tuned rarity. Currently: 6 thermal
  optics and 6 top-tier armour/helmet pieces.

All five features are independently toggleable in `config.json` and fail in isolation — a
bad entry in one logs a warning and skips, it never stops the server from booting.

## Client — `TweakboxClient.dll` → `BepInEx/plugins/TweakboxClient/`

- **Flare burn time** — white/illumination flares (SP-81 pistol round and RSP-30 handheld)
  burn for a configurable duration via BepInEx config (default 120s) instead of vanilla's
  20s. Red, green, yellow and acid-green signal flares are untouched.

Client-side, so it needs installing on every machine in the raid to look consistent —
unlike the server half, it has no effect on its own.

## Config

Server tuning lives in `config.json` next to the DLL (comments and trailing commas are
fine). Client tuning lives in the BepInEx-generated `.cfg` after first launch. Neither
needs a rebuild to retune.
