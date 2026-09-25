Tweakbox @VERSION@
Small quality-of-life tweaks for SPT 4.1.x, built for low-grind Fika co-op.
Source and issues: https://github.com/sabsubGit/Tweakbox-SPT   (MIT licence)

WHAT IT DOES
  Server
    - KS-23M shotgun can be bought on the flea market at any level.
    - Jaeger sells the white 26x75mm flare-gun cartridge and the white RSP-30
      handheld flare for cash (loyalty level 1), and the green 26x75mm cartridge
      (loyalty level 2). Flea prices for the two whites are lowered to match.
    - The white flare-gun cartridge stacks to 5 and is found in packs of 1-5.
    - Thermal optics and top-tier armour/helmets can rarely be found in weapon
      crates, safes and PMC bodies.
  Client
    - White (illumination) flares burn for 120 seconds instead of 20.
      Red, green, yellow and acid-green signal flares are unchanged.

INSTALL (drag and drop)
  1. Copy the BepInEx and SPT folders from this zip into your SPT game folder
     (the one containing EscapeFromTarkov.exe). Accept "merge" / "replace".
  2. EVERY player needs the client plugin:  BepInEx/plugins/TweakboxClient
     Without it that player's white flares just burn the normal 20 seconds.
  3. ONLY the person running the server (the Fika host) needs the server mod:
     SPT/user/mods/Tweakbox
     Players who only join a host do not need it - the host's server sends them
     the trader stock, prices and loot.
  4. Start the server once, then the game.
  If your server folder is not called "SPT" (for example "SPT_Runtime"), put the
  Tweakbox folder in the user/mods folder inside it.

SETTINGS
  Server: SPT/user/mods/Tweakbox/config.json - every feature has an "enabled"
          switch, and a bad entry is skipped with a warning in the server log
          instead of stopping the server. Back this file up before upgrading.
  Client: BepInEx/config/com.local.tweakbox.client.cfg (created on first launch)
          - "White Flare Burn Time (seconds)".

UNINSTALL
  Delete BepInEx/plugins/TweakboxClient and SPT/user/mods/Tweakbox.
