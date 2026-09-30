#!/usr/bin/env bash
# Rebuild the IDEA Iskub soda bundles from the current Painter/Blender exports and deploy them.
# Re-export from Painter with the same file names (IskubWithCap_DefaultMaterial_*.png), then run this.
set -euo pipefail

GAME=/mnt/nvme1tb/SPT
OBJ_DIR=/home/teemu/Blender
TEX_DIR=/mnt/seagate2tb/APainter
REPO="$(cd "$(dirname "$0")/.." && pwd)"
MOD="$GAME/SPT_Runtime/user/mods/Tweakbox"
ICONS="$GAME/SPT_Runtime/user/sptappdata/live"
ISKUB_ICON_KEY=1323672428   # EFT's icon-cache key for the Iskub item (stable, keyed to the item)

if pgrep -x EscapeFromTarko >/dev/null || pgrep -x SPT.Server.Linu >/dev/null; then
    echo "Close the game and the SPT server first (the icon cache and bundles are in use)." >&2
    exit 1
fi

OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
"$REPO/tools/.venv/bin/python" "$REPO/tools/build_iskub_bundles.py" "$GAME" "$OBJ_DIR" "$TEX_DIR" "$OUT"

rm -rf "$REPO/bundles" && cp -r "$OUT/bundles" "$REPO/bundles"
cp "$OUT/bundles.json" "$REPO/bundles.json"
rm -rf "$MOD/bundles" && cp -r "$REPO/bundles" "$MOD/bundles"
cp "$REPO/bundles.json" "$MOD/bundles.json"
echo "Deployed bundles to $MOD"

# EFT keeps rendered inventory icons on disk and never notices a changed texture, so drop the Iskub's.
python3 - "$ICONS" "$ISKUB_ICON_KEY" <<'PY'
import json, os, sys
icons, key = sys.argv[1], sys.argv[2]
idx = os.path.join(icons, "index.json")
if not os.path.exists(idx):
    sys.exit(0)
d = json.load(open(idx))
n = d.pop(key, None)
if n is None:
    print("No cached Iskub icon (already clear).")
    sys.exit(0)
json.dump(d, open(idx, "w"))
png = os.path.join(icons, f"{n}.png")
if os.path.exists(png):
    os.remove(png)
print(f"Cleared cached Iskub icon ({n}.png); it redraws on next launch.")
PY
echo "Done. Start the server and game to see the changes."
