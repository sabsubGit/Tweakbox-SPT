"""Merge one feature's bundles.json entries into the mod's bundles.json, replacing only entries under its own prefix.
Usage: merge_manifest.py <target bundles.json> <new entries json> <key prefix>"""
import json, os, sys
target, new, prefix = sys.argv[1:4]
old = json.load(open(target))["manifest"] if os.path.exists(target) else []
keep = [e for e in old if not e["key"].startswith(prefix)]
add = json.load(open(new))["manifest"]
json.dump({"manifest": keep + add}, open(target, "w"), indent=2)
print(f"{target}: kept {len(keep)} entries, wrote {len(add)} under {prefix}")
