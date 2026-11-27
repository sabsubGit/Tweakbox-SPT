"""Build the RK 62 part bundles by re-skinning copies of the game's own AK part bundles (same method as the Iskub soda:
no Unity build; hand rig / prefab / material settings stay exactly as BSG shipped them, only meshes and textures change).

Inputs:  game dir, unity_meshes/*.npz from rk_export_unity.py (already in the replaced node's local Unity space),
         Painter metal/rough exports (DirectX normals).
Output:  <out>/bundles/<new keys> + <out>/bundles.json
Usage:   python build_rk62_bundles.py <game_dir> <mesh_dir> <out_dir> [part ...]
"""
import hashlib, json, math, os, sys
import numpy as np
import UnityPy
from PIL import Image

GAME, MESH_DIR, OUT = sys.argv[1:4]
ONLY = set(sys.argv[4:])
SA = os.path.join(GAME, "EscapeFromTarkov_Data/StreamingAssets/Windows")
TEX_BLACK = os.path.expanduser("~/Downloads/TarkovMods/RK-62_Textures")
TEX_GREEN = os.path.expanduser("~/Downloads/TarkovMods/RK-62_Green_Textures")
TEX_MUZZLE = os.path.expanduser("~/Downloads/TarkovMods/Supressor and Flash")
NEWDIR = "assets/content/items/mods/tweakbox_rk62/"
MAX_TEX = 2048
MAX_TEX_BY_KIND = {"pistolgrip": 1024, "muzzle": 1024}                 # small parts don't need more

# name -> (vanilla bundle, mesh npz, texture files prefix)
PARTS = {
    "pistolgrip_rk62_black": ("assets/content/items/mods/pistol grips/pistolgrip_ak_izhmash_akm_bakelit.bundle",
                              "RK_pistol_grip", os.path.join(TEX_BLACK, "RK62_all_parts_RK RK_pistol_grip_model_")),
    "pistolgrip_rk62_green": ("assets/content/items/mods/pistol grips/pistolgrip_ak_izhmash_akm_bakelit.bundle",
                              "RK_pistol_grip", os.path.join(TEX_GREEN, "RK62_all_parts_RK RK_pistol_grip_model_")),
    "pistolgrip_rk62_bicycle": ("assets/content/items/mods/pistol grips/pistolgrip_ak_izhmash_akm_bakelit.bundle",
                                "RK_bicycle_grip", os.path.join(TEX_BLACK, "RK62_all_parts_RK RK_bicycle_grip_model_")),
}

def new_cab(key):
    return "CAB-" + hashlib.md5(("tweakbox:" + key).encode()).hexdigest()

# ---------------------------------------------------------------- meshes -------------------------------
def tangents(pos, nrm, uv, tris):
    tan, bit = np.zeros_like(pos, dtype=np.float64), np.zeros_like(pos, dtype=np.float64)
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    e1, e2 = pos[b] - pos[a], pos[c] - pos[a]
    d1, d2 = uv[b] - uv[a], uv[c] - uv[a]
    r = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    ok = np.abs(r) > 1e-12
    r = np.where(ok, 1.0 / np.where(ok, r, 1), 0)[:, None]
    t = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) * r
    s = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) * r
    for i in (a, b, c):
        np.add.at(tan, i, t); np.add.at(bit, i, s)
    t = tan - nrm * np.sum(nrm * tan, axis=1, keepdims=True)
    ln = np.linalg.norm(t, axis=1, keepdims=True)
    fb = np.cross(nrm, [0, 0, 1]); fb = np.where(np.linalg.norm(fb, axis=1, keepdims=True) < 1e-6, np.cross(nrm, [0, 1, 0]), fb)
    t = np.where(ln > 1e-9, t / np.maximum(ln, 1e-9), fb / np.linalg.norm(fb, axis=1, keepdims=True))
    w = np.where(np.sum(np.cross(nrm, t) * bit, axis=1) < 0, -1.0, 1.0)
    return np.hstack([t, w[:, None]])

def pack(pos, nrm, tan, uv):
    n = len(pos)
    rec = np.zeros(n, dtype=[("p", "<f4", 3), ("n", "<f2", 4), ("t", "<f2", 4), ("u", "<f4", 2)])
    rec["p"] = pos; rec["n"][:, :3] = nrm; rec["t"] = tan; rec["u"] = uv
    assert rec.itemsize == 36
    return rec.tobytes()

def replace_mesh(obj, npz):
    d = np.load(npz)
    pos, nrm, uv, tris = d["pos"].astype(np.float64), d["nrm"].astype(np.float64), d["uv"].astype(np.float64), d["tris"].astype(np.int64)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    tan = tangents(pos, nrm, uv, tris)
    tt = obj.read_typetree()
    vd = tt["m_VertexData"]
    ch = [(c["stream"], c["offset"], c["format"], c["dimension"] & 0xF) for c in vd["m_Channels"][:5]]
    assert ch == [(0, 0, 0, 3), (0, 12, 1, 4), (0, 20, 1, 4), (0, 0, 0, 0), (0, 28, 0, 2)], ch
    for c in vd["m_Channels"][5:]:
        assert c["dimension"] & 0xF == 0, "extra vertex channel in use"
    vd["m_VertexCount"] = len(pos)
    vd["m_DataSize"] = pack(pos, nrm, tan, uv)
    tt["m_StreamData"] = {"offset": 0, "size": 0, "path": ""}
    big = len(pos) > 65535
    idx = tris.astype("<u4" if big else "<u2").tobytes()
    tt["m_IndexBuffer"] = idx if isinstance(tt["m_IndexBuffer"], (bytes, bytearray)) else list(idx)
    tt["m_IndexFormat"] = 1 if big else 0
    lo, hi = pos.min(0), pos.max(0)
    aabb = {"m_Center": dict(zip("xyz", map(float, (lo + hi) / 2))), "m_Extent": dict(zip("xyz", map(float, (hi - lo) / 2)))}
    sm = tt["m_SubMeshes"][0]
    sm.update({"firstByte": 0, "indexCount": len(tris) * 3, "topology": 0, "baseVertex": 0, "firstVertex": 0,
               "vertexCount": len(pos), "localAABB": aabb})
    tt["m_SubMeshes"] = [sm]
    tt["m_LocalAABB"] = aabb
    for k in ("m_Shapes", ):
        if k in tt and isinstance(tt[k], dict):
            for kk in ("vertices", "shapes", "channels", "fullWeights"):
                if kk in tt[k]: tt[k][kk] = []
    obj.save_typetree(tt)
    return lo, hi

# ---------------------------------------------------------------- textures -----------------------------
def textures(prefix, size):
    base = Image.open(prefix + "BaseColor.png").convert("RGB")
    rough = Image.open(prefix + "Roughness.png").convert("L")
    nrm = Image.open(prefix + "Normal.png").convert("RGB")
    s = min(size, base.size[0])
    if base.size[0] != s:
        base, rough, nrm = (im.resize((s, s), Image.LANCZOS) for im in (base, rough, nrm))
    gloss = 255 - np.asarray(rough).astype(np.int32)                      # EFT gloss = inverted roughness
    mask = np.clip(gloss * 0.35, 0, 255).astype(np.uint8)                 # diffuse alpha: reflection mask (vanilla ~37 mean)
    diff = Image.fromarray(np.dstack([np.asarray(base), mask]), "RGBA")
    n = np.asarray(nrm)
    x, y = n[..., 0], 255 - n[..., 1]                                     # Painter export is DirectX: flip green for Unity
    nm = Image.fromarray(np.dstack([np.full_like(x, 255), y, y, x]), "RGBA")   # Unity DXT5nm packing (1, y, y, x)
    gl = Image.fromarray(np.dstack([gloss.astype(np.uint8)] * 3), "RGB")
    return diff, gl, nm

def mips(img):
    return int(math.log2(max(img.size))) + 1

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

def build_part(name, vanilla_key, mesh, tex_prefix, manifest):
    new_key = NEWDIR + name + ".bundle"
    old_stem = os.path.splitext(os.path.basename(vanilla_key))[0]
    env = UnityPy.load(os.path.join(SA, vanilla_key))
    cab = next(n for n in env.file.files if n.startswith("CAB-") and "." not in n)
    cab_map = {cab: new_cab(new_key)}
    npz = os.path.join(MESH_DIR, mesh + ".npz")
    diff, gloss, nrm = textures(tex_prefix, MAX_TEX_BY_KIND.get(name.split("_")[0], MAX_TEX))
    small = diff.resize((64, 64), Image.LANCZOS)
    changed, lo, hi = set(), None, None
    print(f"{name}\n  {vanilla_key}\n  -> {new_key}")
    for obj in env.objects:
        t = obj.type.name
        if t == "Mesh":
            m = obj.read()
            lo, hi = replace_mesh(obj, npz)
            changed.add(obj.path_id); print(f"    mesh {m.m_Name} <- {mesh} ({len(np.load(npz)['pos'])} verts)")
        elif t == "Texture2D":
            tx = obj.read(); nm_ = tx.m_Name
            img, fmt = ((small, 12) if "LOD1" in nm_ else (diff, 12)) if nm_.endswith("_diff") else \
                       (gloss, 10) if nm_.endswith("_gloss") else (nrm, 12) if nm_.endswith("_nrm") else (None, None)
            if img is None:
                print("    !! texture left as is:", nm_); continue
            tx.set_image(img, target_format=fmt, mipmap_count=mips(img)); tx.save()
            changed.add(obj.path_id); print(f"    texture {nm_}: {img.size}")
        elif t == "GameObject":
            tt = obj.read_typetree()
            if tt["m_Name"].startswith(old_stem):
                tt["m_Name"] = name + tt["m_Name"][len(old_stem):]
                obj.save_typetree(tt); changed.add(obj.path_id)
    # drop collider: fit the new mesh (mesh nodes sit under the root turned -90 deg about X: (x, y, z) -> (x, z, -y))
    for obj in env.objects:
        if obj.type.name == "BoxCollider":
            tt = obj.read_typetree()
            rlo = np.array([lo[0], lo[2], -hi[1]]); rhi = np.array([hi[0], hi[2], -lo[1]])
            tt["m_Center"] = dict(zip("xyz", map(float, (rlo + rhi) / 2))); tt["m_Size"] = dict(zip("xyz", map(float, rhi - rlo)))
            obj.save_typetree(tt); changed.add(obj.path_id)
            print("    collider", [round(v, 4) for v in tt["m_Size"].values()])
    for obj in env.objects:
        t = obj.type.name
        if t in ("Mesh", "Texture2D") and obj.path_id not in changed:
            tt = obj.read_typetree(); nt = swap_strings(tt, cab_map)
            if nt != tt: obj.save_typetree(nt)
        elif t == "AssetBundle":
            tt = obj.read_typetree()
            tt["m_Name"] = new_key; tt["m_AssetBundleName"] = new_key
            base = (os.path.dirname(vanilla_key) + "/" + old_stem).lower()           # container keys keep the editor's capitals
            tt["m_Container"] = [[(NEWDIR + name + k[len(base):]) if k.lower().startswith(base) else k, v] for k, v in tt["m_Container"]]
            obj.save_typetree(tt)
            print("    container", [k for k, v in tt["m_Container"]][:3])
    renamed = {}
    for fname, f in env.file.files.items():
        nn = fname
        for old, new in cab_map.items():
            nn = nn.replace(old, new)
        if hasattr(f, "name"): f.name = nn
        renamed[nn] = f
    env.file.files.clear(); env.file.files.update(renamed)
    out = os.path.join(OUT, "bundles", new_key)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "wb") as fh:
        fh.write(env.file.save(packer="lz4"))
    print(f"    wrote {out} ({os.path.getsize(out) // 1024} KB)")
    return {"key": new_key, "dependencyKeys": manifest[vanilla_key]["Dependencies"]}

def main():
    manifest = json.load(open(os.path.join(SA, "Windows.json")))
    entries = [build_part(n, *PARTS[n], manifest) for n in PARTS if not ONLY or n in ONLY]
    path = os.path.join(OUT, "bundles_rk62.json")
    json.dump({"manifest": entries}, open(path, "w"), indent=2)
    print("wrote", path, len(entries), "entries")

if __name__ == "__main__":
    main()
