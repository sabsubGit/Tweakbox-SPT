# Tweakbox

A small collection of fun, low-grind tweaks for SPT (single-player Tarkov) and Fika co-op.
Works with SPT 4.1.

## What it adds and changes

### New stuff
- **IDEA ISKUB lingonberry soda** – a brand new drink (+80 hydration). Find it wherever you'd
  find water bottles and kvass: loose on shelves, in containers, and on scavs and PMCs. It's also
  on the flea market, and Therapist trades one for a medical bloodset (loyalty level 3).
- **Ammo penetration at a glance** – when you right-click a magazine and choose *Load ammo*,
  each round shows its penetration value, coloured by how strong an armour it can beat:
  red (weak), orange, yellow, green, blue, purple (goes through almost anything).

### Better flares
- **White flares burn much longer** – 65 seconds from the flare gun and 80 seconds for the
  handheld flare, instead of 20. The coloured signal flares are unchanged.
- **White flares are now parachute flares** – they drift down slowly and light up a wide area
  below them like a real illumination flare, with a slight flicker. You can actually use them
  to light up a night raid now.

### Traders and flea market
- **Jaeger** sells white flare cartridges and white handheld flares for cash, and the green
  flare cartridge (used for flare extracts) at loyalty level 2.
- **Peacekeeper** sells the Peltor TEP-300 earplugs for dollars at loyalty level 3 (normally
  Ref only sells them for GP coins).
- **KS-23M shotgun** can be bought on the flea market.
- Cheaper white flares on the flea, and white flare cartridges stack up to 5.

### Loot
- **Thermal scopes and top-tier armour and helmets** can (rarely) be found in weapon crates,
  safes and on PMC bodies, instead of never.

## Installing

1. Download the latest zip from the [Releases](https://github.com/sabsubGit/Tweakbox-SPT/releases) page.
2. Copy the `BepInEx` and `SPT` folders from the zip into your SPT game folder and allow it to
   merge/replace.
3. **Everyone** in your group needs the `BepInEx` part. **Only the person hosting the server**
   needs the `SPT` part – the soda's model and textures are sent to everyone else automatically.

Most things can be tweaked: flare settings in-game with **F12**, everything else in
`SPT/user/mods/Tweakbox/config.json`.

Uninstalling: sell or throw away any Iskub sodas first, then delete the two Tweakbox folders.

---

<sub>For modders: `./package.sh` builds the release zip. The client compiles against game
assemblies that are not in this repo; point the `Assembly-CSharp` reference in
`Client/TweakboxClient.csproj` at your own `EscapeFromTarkov_Data/Managed` first.</sub>
