#!/usr/bin/env bash
# Rebuild the RK 62 part bundles from the Blender mesh export (tools/rk62/rk_export_unity.py) and the Painter
# textures, then deploy them next to the other Tweakbox bundles. Optional args: only these parts (see PARTS in
# tools/rk62/build_rk62_bundles.py), e.g.  rebuild_rk62.sh pistolgrip_rk62_black
set -euo pipefail

GAME=/mnt/nvme1tb/SPT
MESH_DIR=/home/teemu/Downloads/TarkovMods/RK62-reference/unity_meshes
REPO="$(cd "$(dirname "$0")/.." && pwd)"
MOD="$GAME/SPT_Runtime/user/mods/Tweakbox"
PREFIX=assets/content/items/mods/tweakbox_rk62/

if pgrep -x EscapeFromTarko >/dev/null || pgrep -x SPT.Server.Linu >/dev/null; then
    echo "Close the game and the SPT server first (the bundles are in use)." >&2
    exit 1
fi

OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
"$REPO/tools/.venv/bin/python" "$REPO/tools/rk62/build_rk62_v2.py" "$GAME" "$MESH_DIR" "$OUT" "$@"
for DEST in "$REPO" "$MOD"; do
    mkdir -p "$DEST/bundles/$PREFIX"
    [ $# -eq 0 ] && rm -rf "$DEST/bundles/$PREFIX"/*      # full rebuild: drop parts that no longer exist
    cp -r "$OUT/bundles/." "$DEST/bundles/"
    if [ $# -eq 0 ]; then
        python3 "$REPO/tools/merge_manifest.py" "$DEST/bundles.json" "$OUT/bundles_rk62.json" "$PREFIX"
    else   # partial rebuild: merge only the rebuilt entries, keep the other RK parts
        python3 - "$DEST/bundles.json" "$OUT/bundles_rk62.json" <<'PY'
import json, sys
t, n = sys.argv[1:3]
old = json.load(open(t))["manifest"]; new = json.load(open(n))["manifest"]
keys = {e["key"] for e in new}
json.dump({"manifest": [e for e in old if e["key"] not in keys] + new}, open(t, "w"), indent=2)
print(f"{t}: updated {len(new)} entries")
PY
    fi
done
echo "Deployed RK 62 bundles to $MOD. Clear their cached icons if a part's look changed (see memory notes)."
