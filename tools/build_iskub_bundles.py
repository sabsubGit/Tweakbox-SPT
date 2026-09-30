"""Build the IDEA Iskub soda bundles by re-skinning copies of the game's own water-bottle bundles.

Why copies instead of a Unity build: the in-hand (container) bundle is full of EFT scripts (hand rig,
animator data, sound players). Rebuilding that in Unity needs stubbed EFT scripts and is fragile. Here
we take the four vanilla bundles, give them new bundle names / CAB ids so they load side by side with the
real water bottle, and swap only the meshes and textures. Everything else - hand rig, animations, sounds,
shader and cubemap references - stays exactly as BSG shipped it.

Inputs: the game's item_bottle bundles, the OBJs from Blender and the Substance Painter texture export.
Output: <out>/assets/content/weapons/usable_items/item_iskub/... plus a bundles.json manifest snippet.

Requires: pip install UnityPy Pillow numpy etcpak texture2ddecoder
Usage:    python build_iskub_bundles.py <game_dir> <obj_dir> <texture_dir> <out_dir>
"""
import hashlib
import json
import os
import struct
import sys

import numpy as np
import UnityPy
from PIL import Image

GAME, OBJ_DIR, TEX_DIR, OUT = sys.argv[1:5]
SA = os.path.join(GAME, "EscapeFromTarkov_Data/StreamingAssets/Windows")
VANILLA = "assets/content/weapons/usable_items/item_bottle/"
NEW = "assets/content/weapons/usable_items/item_iskub/"

# vanilla bundle key -> new bundle key
KEYS = {
    VANILLA + "textures/client_assets.bundle": NEW + "textures/client_assets.bundle",
    VANILLA + "client_assets.bundle": NEW + "client_assets.bundle",
    VANILLA + "item_water_bottle_loot.bundle": NEW + "item_iskub_loot.bundle",
    VANILLA + "item_water_bottle_container.bundle": NEW + "item_iskub_container.bundle",
}
# EasyBundle only picks up the asset whose name equals the bundle file name, so the prefab roots move too.
ROOT_RENAMES = {"item_water_bottle_loot": "item_iskub_loot",
                "item_water_bottle_container": "item_iskub_container"}


def new_cab(key):
    return "CAB-" + hashlib.md5(("tweakbox:" + key).encode()).hexdigest()


# ---------------------------------------------------------------- meshes -------------------------------
def load_obj(path):
    """OBJ (Blender, Z-up, X mirrored vs Unity) -> Unity-space vertex arrays + uint16 triangles."""
    V, VT, VN, faces = [], [], [], []
    for line in open(path):
        p = line.split()
        if not p:
            continue
        if p[0] == "v":
            V.append([float(x) for x in p[1:4]])
        elif p[0] == "vt":
            VT.append([float(x) for x in p[1:3]])
        elif p[0] == "vn":
            VN.append([float(x) for x in p[1:4]])
        elif p[0] == "f":
            corners = [tuple(int(i) - 1 for i in c.split("/")) for c in p[1:]]
            for k in range(1, len(corners) - 1):  # fan-triangulate (the exports are already triangles)
                faces.append((corners[0], corners[k], corners[k + 1]))
    V, VT, VN = np.array(V), np.array(VT), np.array(VN)
    remap, pos, nrm, uv, tris = {}, [], [], [], []
    for f in faces:
        idx = []
        for (vi, ti, ni) in f:
            key = (vi, ti, ni)
            if key not in remap:
                remap[key] = len(pos)
                pos.append(V[vi] * [-1, 1, 1])      # mirror X into Unity's left-handed space
                nrm.append(VN[ni] * [-1, 1, 1])
                uv.append(VT[ti])
            idx.append(remap[key])
        tris.append((idx[0], idx[2], idx[1]))        # mirroring flips handedness, so flip winding too
    pos, nrm, uv, tris = np.array(pos), np.array(nrm), np.array(uv), np.array(tris)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    return pos, nrm, uv, tris


def tangents(pos, nrm, uv, tris):
    tan, bit = np.zeros_like(pos), np.zeros_like(pos)
    for a, b, c in tris:
        e1, e2 = pos[b] - pos[a], pos[c] - pos[a]
        d1, d2 = uv[b] - uv[a], uv[c] - uv[a]
        r = d1[0] * d2[1] - d2[0] * d1[1]
        if abs(r) < 1e-12:
            continue
        r = 1.0 / r
        t = (e1 * d2[1] - e2 * d1[1]) * r
        s = (e2 * d1[0] - e1 * d2[0]) * r
        for i in (a, b, c):
            tan[i] += t
            bit[i] += s
    t = tan - nrm * np.sum(nrm * tan, axis=1, keepdims=True)   # Gram-Schmidt against the normal
    ln = np.linalg.norm(t, axis=1, keepdims=True)
    fallback = np.cross(nrm, [0, 0, 1])
    t = np.where(ln > 1e-9, t / np.maximum(ln, 1e-9), fallback)
    w = np.where(np.sum(np.cross(nrm, t) * bit, axis=1) < 0, -1.0, 1.0)
    return np.hstack([t, w[:, None]])


def pack_vertices(pos, nrm, tan, uv):
    """Match the vanilla layout: pos f32x3 @0, normal f16x4 @12, tangent f16x4 @20, uv0 f32x2 @28 (stride 36)."""
    n = len(pos)
    buf = bytearray(n * 36)
    nrm4 = np.hstack([nrm, np.zeros((n, 1))]).astype(np.float16)
    tan4 = tan.astype(np.float16)
    for i in range(n):
        o = i * 36
        struct.pack_into("<3f", buf, o, *pos[i])
        buf[o + 12:o + 20] = nrm4[i].tobytes()
        buf[o + 20:o + 28] = tan4[i].tobytes()
        struct.pack_into("<2f", buf, o + 28, *uv[i])
    return bytes(buf)


def replace_mesh(obj, objpath):
    pos, nrm, uv, tris = load_obj(objpath)
    if len(pos) >= 65535:
        raise SystemExit(f"{objpath}: too many vertices for a 16-bit index buffer")
    tan = tangents(pos, nrm, uv, tris)
    tt = obj.read_typetree()
    vd = tt["m_VertexData"]
    ch = [(c["stream"], c["offset"], c["format"], c["dimension"] & 0xF) for c in vd["m_Channels"][:5]]
    assert ch == [(0, 0, 0, 3), (0, 12, 1, 4), (0, 20, 1, 4), (0, 0, 0, 0), (0, 28, 0, 2)], ch
    data = pack_vertices(pos, nrm, tan, uv)
    vd["m_VertexCount"] = len(pos)
    vd["m_DataSize"] = data
    tt["m_StreamData"] = {"offset": 0, "size": 0, "path": ""}   # vertex data now inline, not in the .resS
    idx = tris.astype("<u2").tobytes()
    tt["m_IndexBuffer"] = idx if isinstance(tt["m_IndexBuffer"], (bytes, bytearray)) else list(idx)
    tt["m_IndexFormat"] = 0
    lo, hi = pos.min(0), pos.max(0)
    aabb = {"m_Center": dict(zip("xyz", map(float, (lo + hi) / 2))),
            "m_Extent": dict(zip("xyz", map(float, (hi - lo) / 2)))}
    sm = tt["m_SubMeshes"][0]
    sm.update({"firstByte": 0, "indexCount": len(tris) * 3, "topology": 0, "baseVertex": 0,
               "firstVertex": 0, "vertexCount": len(pos), "localAABB": aabb})
    tt["m_SubMeshes"] = [sm]
    tt["m_LocalAABB"] = aabb
    obj.save_typetree(tt)
    print(f"    mesh {tt['m_Name']}: {len(pos)} verts, {len(tris)} tris <- {os.path.basename(objpath)}")


# ---------------------------------------------------------------- textures -----------------------------
def load_textures():
    # The label is now painted directly in the right position (front centred in the UV strip, back
    # at the seam, matching the vanilla convention) - re-exported from Painter, no roll needed.
    P = os.path.join(TEX_DIR, "IskubWithCap_DefaultMaterial_")
    base_arr = np.asarray(Image.open(P + "BaseColor.png").convert("RGB")).copy()
    # BaseColor only: an unpainted margin at the UV border baked in as a near-black band (confirmed
    # by column brightness scan; Normal/Roughness don't have it), widest in the label band (cols
    # 985-1021) and narrower elsewhere. A roll alone would just relocate this band instead of removing
    # it, so pad it first - per row, from that row's own last non-dark pixel, since a single shared
    # source column smears whatever is at that column's edge (e.g. the label box) across every row.
    # Checked directly (row 840 for example: columns 0-20 are the same white as columns 960-980):
    # painted content actually WRAPS across this gap, e.g. the label box's design continues from
    # one side straight through to the other. So each row is cross-faded between its last good
    # pixel before the gap and its first good pixel after wrapping past column 0, rather than
    # filled from a single source, which would only ever be right for a flat, one-colour area.
    W = base_arr.shape[1]
    dark = base_arr.mean(-1) < 25
    margin = 6  # clears the anti-aliased blend pixels around the gap, not just the pure-black ones
    lo, hi = 983, 1023
    for row in range(base_arr.shape[0]):
        left = lo
        while left > 0 and dark[row, left - 1]:
            left -= 1
        left = max(left - margin, 0)
        right = hi % W
        steps = 0
        while dark[row, right] and steps < W:  # wrap past column 0 if the gap runs to the edge
            right = (right + 1) % W
            steps += 1
        right = (right + margin) % W
        c_left, c_right = base_arr[row, left].astype(float), base_arr[row, right].astype(float)
        t = np.linspace(0, 1, hi - lo)[:, None]
        base_arr[row, lo:hi] = np.round(c_left * (1 - t) + c_right * t)
    base = Image.fromarray(base_arr)
    rough = np.asarray(Image.open(P + "Roughness.png").convert("L"))
    nrm = np.asarray(Image.open(P + "Normal.png").convert("RGB"))
    gloss = 255 - rough                                            # EFT gloss = inverted roughness
    diff = np.dstack([np.asarray(base), gloss])                    # diffuse alpha: reflection mask ~ gloss
    x, y = nrm[..., 0], nrm[..., 1]                                # Painter exports OpenGL (Y+), as Unity
    nm = np.dstack([np.full_like(x, 255), y, y, x])                # Unity DXT5nm packing: (1, y, y, x)
    return {"item_water_bottle_LOD0_diff": (Image.fromarray(diff, "RGBA"), 12),
            "item_water_bottle_LOD0_nrm": (Image.fromarray(nm, "RGBA"), 12),
            "item_water_bottle_LOD0_gloss": (Image.fromarray(np.dstack([gloss] * 3), "RGB"), 10)}


# ---------------------------------------------------------------- bundle surgery -----------------------
def swap_strings(node, table):
    if isinstance(node, dict):
        return {k: swap_strings(v, table) for k, v in node.items()}
    if isinstance(node, list):
        return [swap_strings(v, table) for v in node]
    if isinstance(node, str):
        for old, new in table.items():
            node = node.replace(old, new)
        return node
    return node


def main():
    envs, cab_map = {}, {}
    for old_key in KEYS:
        env = UnityPy.load(os.path.join(SA, old_key))
        envs[old_key] = env
        cab = next(n for n in env.file.files if n.startswith("CAB-") and "." not in n)
        cab_map[cab] = new_cab(KEYS[old_key])
    lower = {k.lower(): v.lower() for k, v in cab_map.items()}
    texs = load_textures()

    for old_key, env in envs.items():
        new_key = KEYS[old_key]
        print(f"{old_key}\n  -> {new_key}")
        # 1. content swaps. UnityPy's read_typetree() re-reads the ORIGINAL data even after
        # save_typetree(), so anything changed here is remembered and skipped in step 2.
        changed = set()
        for obj in env.objects:
            t = obj.type.name
            if t == "Texture2D" and old_key.endswith("textures/client_assets.bundle"):
                tex = obj.read()
                img, fmt = texs[tex.m_Name]
                tex.set_image(img, target_format=fmt, mipmap_count=11)
                tex.save()
                changed.add(obj.path_id)
                print(f"    texture {tex.m_Name}: {img.size} fmt {fmt}")
            elif t == "Mesh" and old_key.endswith("item_bottle/client_assets.bundle"):
                m = obj.read()
                count = m.m_VertexData.m_VertexCount
                if m.m_Name == "item_water_bottle_LOD0" and count == 2544:
                    replace_mesh(obj, os.path.join(OBJ_DIR, "IskubNoCap.obj"))       # in-hand body
                    changed.add(obj.path_id)
                elif m.m_Name in ("item_water_bottle_LOD0", "item_water_bottle_LOD1") and count == 2952:
                    replace_mesh(obj, os.path.join(OBJ_DIR, "IskubWithCap.obj"))     # loot LOD0/LOD1
                    changed.add(obj.path_id)
            elif t == "GameObject" and not old_key.endswith("client_assets.bundle"):
                tt = obj.read_typetree()
                if tt["m_Name"] in ROOT_RENAMES:
                    print(f"    root {tt['m_Name']} -> {ROOT_RENAMES[tt['m_Name']]}")
                    tt["m_Name"] = ROOT_RENAMES[tt["m_Name"]]
                    obj.save_typetree(tt)
                    changed.add(obj.path_id)
        # 2. identity: CAB names, stream paths, bundle names, dependencies, container keys
        for obj in env.objects:
            t = obj.type.name
            if t in ("Mesh", "Texture2D", "AudioClip") and obj.path_id not in changed:
                tt = obj.read_typetree()
                nt = swap_strings(tt, cab_map)
                if nt != tt:
                    obj.save_typetree(nt)
            elif t == "AssetBundle":
                tt = obj.read_typetree()
                tt["m_Name"] = new_key
                tt["m_AssetBundleName"] = new_key
                tt["m_Dependencies"] = [lower.get(d, d) for d in tt["m_Dependencies"]]
                tt["m_Container"] = [[k.replace("item_bottle/item_water_bottle", "item_iskub/item_iskub")
                                       .replace("item_bottle/", "item_iskub/"), v] for k, v in tt["m_Container"]]
                obj.save_typetree(tt)
        for name, f in list(env.file.files.items()):
            if hasattr(f, "externals"):
                for ext in f.externals:
                    for old, new in cab_map.items():
                        ext.path = ext.path.replace(old, new)
        renamed = {}
        for name, f in env.file.files.items():
            nn = name
            for old, new in cab_map.items():
                nn = nn.replace(old, new)
            if hasattr(f, "name"):
                f.name = nn
            renamed[nn] = f
        env.file.files.clear()
        env.file.files.update(renamed)
        env.file.mark_changed() if hasattr(env.file, "mark_changed") else None

        out = os.path.join(OUT, "bundles", new_key)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as fh:
            fh.write(env.file.save(packer="lz4"))
        print(f"    wrote {out} ({os.path.getsize(out)} bytes)")

    # bundles.json entries: vanilla dependencies with our copies substituted
    manifest = json.load(open(os.path.join(SA, "Windows.json")))
    entries = []
    for old_key, new_key in KEYS.items():
        deps = [KEYS.get(d, d) for d in manifest[old_key]["Dependencies"]]
        entries.append({"key": new_key, "dependencyKeys": deps})
    with open(os.path.join(OUT, "bundles.json"), "w") as fh:
        json.dump({"manifest": entries}, fh, indent=2)
    print("wrote bundles.json with", len(entries), "entries")


if __name__ == "__main__":
    main()
