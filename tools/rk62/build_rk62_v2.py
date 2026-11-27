"""RK 62 part bundles, v2: parts are exported in AKMN weapon space and placed through the game's own slot tree.
A part = a 'clone set' (its prefab bundle + any texture bundle it depends on), copied under new keys/CAB ids, with:
  meshes   {mesh/node name: npz | None}   None = blanked (one degenerate triangle)
  textures {texture name suffix kind -> Painter prefix}  (LOD0 diff/gloss/nrm, LOD1 diff)
  moves    {node name: weapon-space point}  re-position slot / muzzle-flash nodes inside the part
  attach   [('weapon', slot), (parent part vanilla key, sub-slot), ...]
Usage: python build_rk62_v2.py <game_dir> <mesh_dir> <out_dir> [part ...]"""
import hashlib, json, math, os, sys
import numpy as np
import UnityPy
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from akref import Game
from rk_frames import Weapon, Part, RX90, to_local

GAME, MESH_DIR, OUT = sys.argv[1:4]
ONLY = set(sys.argv[4:])
g = Game(GAME)
SA = g.sa
NEWDIR = "assets/content/items/mods/tweakbox_rk62/"
TB = os.path.expanduser("~/Downloads/TarkovMods/RK-62_Textures/RK62_all_parts_RK ")
TG = os.path.expanduser("~/Downloads/TarkovMods/RK-62_Green_Textures/RK62_all_parts_RK ")
TM = os.path.expanduser("~/Downloads/TarkovMods/Supressor and Flash/RK62M_muzzle_parts_RK ")
GB = os.path.expanduser("~/Downloads/TarkovMods/Grips/Black/RK62_grips_RK ")        # remodelled grips (own Painter project, HDRP preset)
GG = os.path.expanduser("~/Downloads/TarkovMods/Grips/Green/RK62_grips_RK ")
TMAG = os.path.expanduser("~/Downloads/TarkovMods/Magazine/RK_waffle_mag_v2_RK ")  # waffle mag rebuilt on the AK '55 steel mag (rk_mag55.py), own Painter project, HDRP preset
MAX_TEX = {"pistolgrip": 2048, "muzzle": 1024}   # grips 2048: the ~2 mm checkering needs it

# RK weapon slot positions that differ from the AKMN (weapon space; weapon = Blender (x, -y, z))
# No slot moves any more: the game's AKM animation clips (shared, in other bundles) pin mod_muzzle, fireport and
# aim_camera to the AKM spots in every view. Instead the RK model fits them: barrel 33.6 mm longer so it ends at the
# AKM muzzle slot, both sights lowered onto the AKM eye height (z 0.0503). See memory eft-weapon-anim-clips-override-slots.
WEAPON_MOVES = {}

V = {  # vanilla bundles
    "grip": "assets/content/items/mods/pistol grips/pistolgrip_ak_izhmash_akm_bakelit.bundle",
    "stock": "assets/content/items/mods/stocks/stock_ak_izhmash_akm_std_wood.bundle",
    "mag": "assets/content/items/mods/magazines/mag_ak_izhmash_6l10_762x39_30.bundle",
    "gastube": "assets/content/items/mods/gasblock/gas_block_ak_izhmash_akm_std.bundle",
    "gastube_tex": "assets/content/items/mods/handguards/handguard_ak_izhmash_akm_std_wood_textures.bundle",
    "hg74": "assets/content/items/mods/handguards/handguard_ak_izhmash_ak74_std_wood.bundle",
    "b10": "assets/content/items/mods/handguards/handguard_ak_zenit_b10.bundle",
    "zhukov": "assets/content/items/mods/handguards/handguard_ak_magpul_zhukov_u_blk.bundle",          # layout: M-LOK mounts + left-hand pose
    "zhukov_mesh": "assets/content/items/mods/handguards/handguard_ak_magpul_zhukov_u_mesh",
    "zhukov_tex": "assets/content/items/mods/handguards/handguard_ak_magpul_zhukov_u_blk_textures",
    "zhukov_glnrm": "assets/content/items/mods/handguards/handguard_ak_magpul_zhukov_u_lod0_gloss_nrm",
    "cover": "assets/content/items/mods/recievers/reciever_ak_izhmash_akm_std.bundle",
    "b33": "assets/content/items/mods/recievers/reciever_ak_zenit_b33.bundle",
    "akml": "assets/content/items/mods/muzzle/muzzle_ak_izhmash_akml_762x39.bundle",
    "51t": "assets/content/items/mods/muzzle/muzzle_ar10_aac_blackout_51t_flash_hider_762x51.bundle",
    "51t_tex": "assets/content/items/mods/muzzle/muzzle_ar10_aac_blackout_51t_flash_hider_762x51_textures",
    "sl7i": "assets/content/items/mods/silencers/silencer_borelock_aseutra_sl7i_bl_86x70.bundle",
}
HG_CHAIN = [("weapon", "mod_gas_block"), (V["gastube"], "mod_handguard")]
MUZ = [("weapon", "mod_muzzle")]
FH_TIP, FHM_TIP, SUP_TIP = (0.0, -0.9266, 0.0), (0.0, -0.9231, 0.0), (0.0, -1.0201, 0.0)   # device tips on the lengthened barrel

def lods(stem, npz):
    return {stem + "_LOD0": npz, stem + "_LOD1": npz}

PARTS = {
    "pistolgrip_rk62_black":   dict(set=[V["grip"]], attach=[("weapon", "mod_pistol_grip")], meshes=lods("pistolgrip_ak_izhmash_akm_bakelit", "RK_pistol_grip"), tex=GB + "RK_pistol_grip_model_"),
    "pistolgrip_rk62_green":   dict(set=[V["grip"]], attach=[("weapon", "mod_pistol_grip")], meshes=lods("pistolgrip_ak_izhmash_akm_bakelit", "RK_pistol_grip"), tex=GG + "RK_pistol_grip_model_"),
    "pistolgrip_rk62_bicycle": dict(set=[V["grip"]], attach=[("weapon", "mod_pistol_grip")], meshes=lods("pistolgrip_ak_izhmash_akm_bakelit", "RK_bicycle_grip"), tex=GB + "RK_bicycle_grip_model_"),
    "stock_rk62":              dict(set=[V["stock"]], attach=[("weapon", "mod_stock")], meshes=lods("stock_ak_izhmash_akm_std_wood", "RK_stock"), tex=TB + "RK_stock_model_"),
    "mag_rk62_waffle":         dict(set=[V["mag"]], attach=[("weapon", "mod_magazine")], meshes=lods("mag_ak_izhmash_6L10_762x39_30", "RK_waffle_mag"), tex=TMAG + "RK_waffle_mag_model_"),
    "gastube_rk62":            dict(set=[V["gastube"], V["gastube_tex"]], attach=[("weapon", "mod_gas_block")], meshes=lods("gas_block_ak_izhmash_akm_std", "RK_gas_tube"), tex=TB + "RK_gas_tube_model_"),
    "handguard_rk62_plastic":  dict(set=[V["hg74"]], attach=HG_CHAIN, meshes=lods("handguard_ak_izhmash_ak74_std_wood", "RK_handguard_plastic"), tex=TB + "RK_handguard_plastic_model_"),
    "handguard_rk62_grater":   dict(set=[V["hg74"]], attach=HG_CHAIN, meshes=lods("handguard_ak_izhmash_ak74_std_wood", "RK_handguard_cheesegrater"), tex=TB + "RK_handguard_cheesegrater_model_"),
    # RK 62 M handguard on the Magpul Zhukov-U (M-LOK): side mounts take M-LOK rail sections (then lights/lasers),
    # the bottom mount M-LOK foregrips or the 4.1" rail. Mounts sit on our surfaces: side walls x +-15.5 mm at the front
    # side slot (Blender y 0.696, z 3.5 mm), bottom z -17.4 mm under the middle bottom slot (y 0.610). Weapon y = -Blender y.
    "handguard_rk62m":         dict(set=[V["zhukov"], V["zhukov_mesh"], V["zhukov_tex"], V["zhukov_glnrm"]], attach=HG_CHAIN,
                                    meshes=lods("handguard_ak_magpul_zhukov_u", "RK62M_handguard"),
                                    tex=TG + "RK62M_handguard_model_",
                                    moves={"mod_foregrip": (0.0, -0.6100, -0.0174), "mod_mount_000": (-0.0155, -0.6959, 0.0035),
                                           "mod_mount_001": (0.0155, -0.6959, 0.0035)}),
    "cover_rk62":              dict(set=[V["cover"]], attach=[("weapon", "mod_reciever")], meshes=lods("reciever_ak_izhmash_akm_std", "RK_top_cover"), tex=TB + "RK_top_cover_model_"),
    "cover_rk62m":             dict(set=[V["b33"]], attach=[("weapon", "mod_reciever")], meshes=lods("reciever_ak_zenit_b33", "RK62M_top_cover"), tex=TG + "RK62M_top_cover_model_",
                                    moves={"mod_scope": "RAIL"}),
    "muzzle_rk62_flashhider":  dict(set=[V["akml"]], attach=MUZ, meshes=lods("muzzle_ak_izhmash_akml_762x39", "RK_flash_hider"), tex=TB + "RK_flash_hider_model_",
                                    moves={"muzzleflash_000": FH_TIP}),
    "muzzle_rk62m_flashhider": dict(set=[V["51t"], V["51t_tex"]], attach=MUZ, meshes=lods("muzzle_ar10_aac_blackout_51t_flash_hider_762x51", "RK62M_flash_hider"),
                                    tex=TM + "RK62M_flash_hider_model_",
                                    moves={"mod_muzzle": (0.0, -0.8566, 0.0), "muzzleflash_000": FHM_TIP, "muzzleflash_001": FHM_TIP, "muzzleflash_002": FHM_TIP, "muzzleflash_003": FHM_TIP}),
    "silencer_rk62m":          dict(set=[V["sl7i"]], attach=MUZ + [(V["51t"], "mod_muzzle")], meshes=lods("silencer_borelock_aseutra_sl7i_bl_86x70", "RK62M_suppressor"),
                                    tex=TM + "RK62M_suppressor_model_", moves={"muzzleflash_000": SUP_TIP}),
}

def new_cab(key):
    return "CAB-" + hashlib.md5(("tweakbox:" + key).encode()).hexdigest()

# ------------------------------------------------------------------ frames ---------------------------------------
W = Weapon(g)
_parts = {}
def part(key):
    if key not in _parts:
        _parts[key] = Part(g, key)
    return _parts[key]

def weapon_frame(slot):
    F = W.frame(slot).copy()
    if slot in WEAPON_MOVES:
        F[:3, 3] = WEAPON_MOVES[slot]
    return F

def root_frame(attach, moves_of=None):
    """attach chain -> weapon-space frame of the part root. moves_of(key) gives a parent's node moves."""
    kind, slot = attach[0]
    F = weapon_frame(slot) @ RX90
    for key, sub in attach[1:]:
        S = F @ part(key).rel(sub)
        mv = (moves_of(key) or {}).get(sub) if moves_of else None
        if mv is not None and not isinstance(mv, str):
            S[:3, 3] = mv
        F = S @ RX90
    return F

def moves_for_vanilla(key):
    for spec in PARTS.values():
        if spec["set"][0] == key and spec.get("moves"):
            return spec["moves"]
    return None

# ------------------------------------------------------------------ meshes ---------------------------------------
def tangents(pos, nrm, uv, tris):
    tan, bit = np.zeros_like(pos), np.zeros_like(pos)
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
    t = np.where(ln > 1e-9, t / np.maximum(ln, 1e-9), fb / np.maximum(np.linalg.norm(fb, axis=1, keepdims=True), 1e-9))
    w = np.where(np.sum(np.cross(nrm, t) * bit, axis=1) < 0, -1.0, 1.0)
    return np.hstack([t, w[:, None]])

def pack(pos, nrm, tan, uv):
    rec = np.zeros(len(pos), dtype=[("p", "<f4", 3), ("n", "<f2", 4), ("t", "<f2", 4), ("u", "<f4", 2)])
    rec["p"] = pos; rec["n"][:, :3] = nrm; rec["t"] = tan; rec["u"] = uv
    return rec.tobytes()

def write_mesh(obj, pos, nrm, uv, tris):
    tan = tangents(pos, nrm, uv, tris)
    tt = obj.read_typetree()
    vd = tt["m_VertexData"]
    want = [(0, 0, 0, 3), (0, 12, 1, 4), (0, 20, 1, 4), (0, 0, 0, 0), (0, 28, 0, 2)]
    ch = [(c["stream"], c["offset"], c["format"], c["dimension"] & 0xF) for c in vd["m_Channels"]]
    if ch[:5] != want or any(c[3] for c in ch[5:]):
        # another layout (extra colour / uv channels): rewrite the channel table to ours (pos f32x3, nrm f16x4, tan f16x4, uv f32x2)
        for i, c in enumerate(vd["m_Channels"]):
            st, off, fmt, dim = want[i] if i < 5 else (0, 0, 0, 0)
            c["stream"], c["offset"], c["format"] = st, off, fmt
            c["dimension"] = (c["dimension"] & ~0xF) | dim if (c["dimension"] & 0xF) == dim else dim
        print(f"    (vertex layout of {tt['m_Name']} rewritten from {ch[:6]})")
    vd["m_VertexCount"] = len(pos)
    vd["m_DataSize"] = pack(pos, nrm, tan, uv)
    tt["m_StreamData"] = {"offset": 0, "size": 0, "path": ""}
    big = len(pos) > 65535
    idx = tris.astype("<u4" if big else "<u2").tobytes()
    tt["m_IndexBuffer"] = idx if isinstance(tt["m_IndexBuffer"], (bytes, bytearray)) else list(idx)
    tt["m_IndexFormat"] = 1 if big else 0
    lo, hi = pos.min(0), pos.max(0)
    aabb = {"m_Center": dict(zip("xyz", map(float, (lo + hi) / 2))), "m_Extent": dict(zip("xyz", map(float, np.maximum((hi - lo) / 2, 1e-4))))}
    sm = tt["m_SubMeshes"][0]
    sm.update({"firstByte": 0, "indexCount": len(tris) * 3, "topology": 0, "baseVertex": 0, "firstVertex": 0, "vertexCount": len(pos), "localAABB": aabb})
    tt["m_SubMeshes"] = [sm]; tt["m_LocalAABB"] = aabb
    obj.save_typetree(tt)

def blank():
    return np.zeros((3, 3)), np.tile([0.0, 0.0, 1.0], (3, 1)), np.zeros((3, 2)), np.array([[0, 1, 2]])

# ------------------------------------------------------------------ textures -------------------------------------
def tex_path(prefix, channel):
    """Painter names exports <project>_<texture set>_<channel>.png. Any project counts (e.g. a separate grips project
    exported into the same folder): the newest file for this texture set wins."""
    import glob
    folder, stem = os.path.split(prefix)
    tset = stem.split("_RK ", 1)[1] if "_RK " in stem else stem                  # e.g. "RK_pistol_grip_model_"
    found = glob.glob(os.path.join(glob.escape(folder), "*_RK " + glob.escape(tset) + channel + ".png"))
    return max(found, key=os.path.getmtime) if found else prefix + channel + ".png"

# EFT's weapon shader (p0/Reflective/Bumped Specular SMap) is spec/gloss, not Painter's metal/rough:
#   _MainTex RGB = diffuse, A = reflection (cubemap) mask; _SpecMap = gloss; _BumpMap = DXT5nm-style (x in A, y in G).
# Metal has no diffuse colour in PBR - its look comes from reflections - so metal areas get a darker diffuse here,
# calibrated so the RK receiver lands where the vanilla AK receiver/dust cover sit (diffuse x tint ~0.08-0.12).
METAL_DARKEN = 0.70        # diffuse = base * (1 - 0.70 * metallic)
AO_STRENGTH = 0.55         # the game shader has no AO slot: Painter's AO is baked into diffuse (Painter only shades ambient light with it, so not at full strength)
REFL_BASE, REFL_METAL = 0.30, 0.15     # (old curve, kept for reference)
# Painter smoothness is remapped into the ranges the game's own parts use (gloss map 0.45-0.64, reflection mask 0.10-0.29
# even on matte plastic): matte parts mapped near 0 looked blotchy in game (M handguard, suppressor)
GLOSS_LO, GLOSS_HI = 0.38, 0.80            # gloss map = 0.38 + 0.42 * smoothness
REFL_LO, REFL_HI, REFL_M = 0.10, 0.32, 0.05   # reflection mask = (0.10 + 0.22 * smoothness + 0.05 * metallic) * AO
FMT = {"diff": 25, "gloss": 25, "nrm": 25, "lod1": 12}   # BC7 (the game uses it too, e.g. SR-3M): much cleaner than DXT1/5 at the same size
# Olive grade for the green parts (green folder, green grip, RK 62 M muzzle parts): the real RK 62 M is a grey-olive
# drab (about Cerakote O.D. Green), the Painter green came out a bluer, darker green in game. Applied to base colour only.
OLIVE = dict(hue_deg=-26, sat=0.82, val=1.18)
def olive_grade(img):
    hsv = np.asarray(img.convert("HSV")).astype(np.float32)
    hsv[..., 0] = (hsv[..., 0] + OLIVE["hue_deg"] / 360 * 255) % 255
    hsv[..., 1] = np.clip(hsv[..., 1] * OLIVE["sat"], 0, 255); hsv[..., 2] = np.clip(hsv[..., 2] * OLIVE["val"], 0, 255)
    return Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB")
def is_green_set(prefix):
    return any(prefix.startswith(g) for g in (TG, GG, TM))
AO_NAMES = ("AmbientOcclusion", "Mixed_AO", "AO", "Ambient_occlusion", "ambient_occlusion")
MAT_STD = {"_Color": 1.0, "_SpecColor": 1.0, "_ReflectColor": 0.55}             # same neutral settings on every RK part
MAT_STD_F = {"_Glossness": 1.4, "_Specularness": 1.0}                          # (vanilla parts range 0.9-2.1 / 0.8-1.2)

def standardize_material(tt):
    """Neutral, identical material settings for all RK parts (the cloned vanilla materials carry per-part tints
    0.56-1.0 and gloss multipliers 0.9-2.1, which made one Painter finish look different on every part)."""
    sp = tt["m_SavedProperties"]; keys = {k for k, _ in sp["m_Colors"]} | {k for k, _ in sp["m_Floats"]}
    if "_ReflectColor" not in keys:
        return False
    for k, v in sp["m_Colors"]:
        if k in MAT_STD:
            v["r"] = v["g"] = v["b"] = float(MAT_STD[k])
    sp["m_Floats"] = [[k, float(MAT_STD_F[k]) if k in MAT_STD_F else v] for k, v in sp["m_Floats"]]
    return True

def find_maps(prefix):
    """The newest Painter export for this texture set, whatever the preset or project name. Works with the PBR
    metal/rough preset (BaseColor, Roughness, Metallic, Normal [DirectX], optional AO) and with the Unity HDRP preset
    (BaseMap, MaskMap = R metallic / G AO / A smoothness, Normal [OpenGL]). Files of one export are grouped by time."""
    import re
    folder, stem = os.path.split(prefix)
    tset = ("RK " + stem.split("_RK ", 1)[1] if "_RK " in stem else stem).rstrip("_").lower()
    files = [f for f in os.listdir(folder) if f.lower().endswith((".png", ".tga", ".tif", ".tiff")) and tset in f.lower()]
    def pick(*keys, near=None):
        hits = [f for f in files if any(re.search(r"[_\-. ]" + k + r"(?![a-z])", f[f.lower().index(tset) + len(tset):], re.I) for k in keys)]
        hits = [os.path.join(folder, f) for f in hits]
        if near is not None:
            hits = [h for h in hits if abs(os.path.getmtime(h) - near) < 1800] or []
        return max(hits, key=os.path.getmtime) if hits else None
    nrm = pick("Normal", "Normal_DirectX", "Normal_OpenGL", "NormalGL", "NormalDX")
    assert nrm, f"no normal map for {tset} in {folder}"
    t = os.path.getmtime(nrm)
    maps = {"normal": nrm, "base": pick("BaseColor", "Base_Color", "BaseMap", "Albedo", near=t), "mask": pick("MaskMap", "Mask_Map", "Mask", near=t),
            "rough": pick("Roughness", near=t), "smooth": pick("Smoothness", "Glossiness", near=t), "metal": pick("Metallic", "Metalness", near=t),
            "ao": pick(*AO_NAMES, near=t)}
    n = os.path.basename(nrm).lower()
    maps["gl_normal"] = ("opengl" in n or "normalgl" in n) or (maps["mask"] is not None and "directx" not in n)   # HDRP preset = OpenGL normals
    assert maps["base"] and (maps["rough"] or maps["smooth"] or maps["mask"]), f"incomplete export for {tset}: {maps}"
    return maps

def normal_is_opengl(n, fallback):
    """A normal map baked from height is curl-free, which fixes the sign of green: d(R)/dy correlates negatively with
    d(G)/dx for OpenGL (green up) and positively for DirectX. Painter's HDRP preset gave OpenGL for the grips but the
    all-parts / muzzle projects came out DirectX, so measure per map; nearly flat maps keep the fallback."""
    R = n[..., 0].astype(np.float32) / 255 - 0.5; G = n[..., 1].astype(np.float32) / 255 - 0.5
    sel = np.hypot(R, G) > 0.003                                   # even nearly flat maps (green parts: ~1,500 px over 0.01) carry enough
    if sel.sum() < 500: return fallback
    c = np.corrcoef(np.gradient(R, axis=0)[sel], np.gradient(G, axis=1)[sel])[0, 1]
    return fallback if abs(c) < 0.05 else c < 0

def textures(prefix, size):
    M = find_maps(prefix)
    base = Image.open(M["base"]).convert("RGB")
    if is_green_set(prefix):
        base = olive_grade(base)
    nrm = Image.open(M["normal"]).convert("RGB")
    mask = Image.open(M["mask"]).convert("RGBA") if M["mask"] else None
    if M["rough"]: rough = Image.open(M["rough"]).convert("L")
    elif M["smooth"]: rough = Image.eval(Image.open(M["smooth"]).convert("L"), lambda v: 255 - v)
    else: rough = Image.eval(mask.getchannel("A"), lambda v: 255 - v)
    metal = Image.open(M["metal"]).convert("L") if M["metal"] else mask.getchannel("R") if mask else Image.new("L", base.size, 0)
    ao = Image.open(M["ao"]).convert("L") if M["ao"] else mask.getchannel("G") if mask else Image.new("L", base.size, 255)
    from PIL import ImageFilter
    a0 = np.asarray(ao)
    if (a0 == 0).mean() > 0.01:            # Painter leaves AO black outside the UV islands: pad the islands out so smaller mips don't pull black into the seams
        for _ in range(4):
            a0 = np.where(a0 == 0, np.asarray(Image.fromarray(a0).filter(ImageFilter.MaxFilter(5))), a0)
        ao = Image.fromarray(a0)
    ao = ao.filter(ImageFilter.GaussianBlur(1.5 * ao.size[0] / 2048))   # low-poly AO has no fine detail: smooth away bake grain (seen at 8-10 levels)
    s = min(size, base.size[0])
    base, rough, nrm, metal, ao = (im.resize((s, s), Image.LANCZOS) if im.size[0] != s else im for im in (base, rough, nrm, metal, ao))
    b = np.asarray(base).astype(np.float32) / 255; g = 1 - np.asarray(rough).astype(np.float32) / 255
    m = np.asarray(metal).astype(np.float32) / 255; a = 1 - AO_STRENGTH * (1 - np.asarray(ao).astype(np.float32) / 255)
    dif = b * (1 - METAL_DARKEN * m)[..., None] * a[..., None]
    refl = (REFL_LO + (REFL_HI - REFL_LO) * g + REFL_M * m) * a
    gl8 = np.clip((GLOSS_LO + (GLOSS_HI - GLOSS_LO) * g) * (0.6 + 0.4 * a) * 255 + 0.5, 0, 255).astype(np.uint8)
    diff = Image.fromarray(np.dstack([np.clip(dif * 255 + 0.5, 0, 255).astype(np.uint8), np.clip(refl * 255 + 0.5, 0, 255).astype(np.uint8)]), "RGBA")
    n = np.asarray(nrm)
    gl_n = normal_is_opengl(n, M["gl_normal"])
    x, y = n[..., 0], (n[..., 1] if gl_n else 255 - n[..., 1])   # Unity wants OpenGL (green up); Painter's DirectX export is flipped
    nm = Image.fromarray(np.dstack([np.full_like(x, 255), y, y, x]), "RGBA")
    gl = Image.fromarray(np.dstack([gl8] * 3), "RGB")
    src = "HDRP mask map" if mask is not None and not (M["metal"] and M["ao"]) else "separate maps"
    print(f"    maps {os.path.basename(M['base'])}: {src}, normals {'OpenGL' if gl_n else 'DirectX'}; diffuse {dif.mean():.3f} "
          f"(base {b.mean():.3f}, metallic {m.mean():.2f}), reflection {refl.mean():.3f}, gloss {g.mean():.2f}, "
          f"AO {'from ' + ('mask map' if not M['ao'] else os.path.basename(M['ao'])) if (M['ao'] or mask is not None) else 'none'}")
    return {"diff": diff, "gloss": gl, "nrm": nm, "lod1": diff.resize((128, 128), Image.LANCZOS)}

def mips(img):
    return int(math.log2(max(img.size))) + 1

def tex_kind(name):
    n = name.lower()
    if "lod1" in n: return "lod1"
    for k in ("diff", "gloss", "nrm"):
        if n.endswith("_" + k) or ("_" + k + "_") in n: return k          # also e.g. ..._LOD0_diff_blk (Zhukov-U)
    return None

# ------------------------------------------------------------------ bundle surgery -------------------------------
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

def build(name, spec, manifest):
    keys = spec["set"]
    main = keys[0]
    old_stem = os.path.splitext(os.path.basename(main))[0]
    newkey = {k: NEWDIR + name + ("" if k == main else "_" + os.path.splitext(os.path.basename(k))[0].split("_")[-1]) + ".bundle" for k in keys}
    envs = {k: UnityPy.load(os.path.join(SA, k)) for k in keys}
    cab_map = {}
    for k, env in envs.items():
        cab = next(n for n in env.file.files if n.startswith("CAB-") and "." not in n)
        cab_map[cab] = new_cab(newkey[k])
    lower = {a.lower(): b.lower() for a, b in cab_map.items()}
    print(f"{name}\n  " + "\n  ".join(f"{k} -> {newkey[k]}" for k in keys))
    P = part(main)
    Froot = root_frame(spec["attach"], moves_for_vanilla)
    kind_size = next((v for k, v in MAX_TEX.items() if name.startswith(k)), 2048)
    tx = textures(spec["tex"], kind_size)
    changed = {k: set() for k in keys}
    bounds = []
    # moves: node local position so that its weapon-space position is the target
    moves = dict(spec.get("moves", {}))
    if moves.get("mod_scope") == "RAIL":
        moves["mod_scope"] = rail_point(P, Froot)
    for k, env in envs.items():
        for obj in env.objects:
            t = obj.type.name
            if t == "Mesh":
                m = obj.read(); mn = m.m_Name
                if mn not in spec["meshes"]:
                    print("    !! mesh left as is:", mn); continue
                src = spec["meshes"][mn]
                if src is None:
                    pos, nrm, uv, tris = blank()
                else:
                    d = np.load(os.path.join(MESH_DIR, src + ".npz"))
                    frame = Froot @ P.rel(mn)
                    pos, nrm = to_local(frame, d["pos"].astype(float), d["nrm"].astype(float))
                    uv, tris = d["uv"].astype(float), d["tris"].astype(np.int64)
                    if mn.endswith("_LOD0"): bounds.append((frame, pos))
                write_mesh(obj, pos, nrm, uv, tris); changed[k].add(obj.path_id)
                print(f"    mesh {mn} <- {src or 'blank'} ({len(pos)} verts)")
            elif t == "Texture2D":
                tt_ = obj.read(); kind = tex_kind(tt_.m_Name)
                if kind is None:
                    print("    !! texture left as is:", tt_.m_Name); continue
                img = tx[kind]
                tt_.set_image(img, target_format=FMT[kind], mipmap_count=mips(img)); tt_.save()
                changed[k].add(obj.path_id); print(f"    texture {tt_.m_Name}: {img.size}")
            elif t == "Material":
                tt = obj.read_typetree()
                if standardize_material(tt):
                    obj.save_typetree(tt); changed[k].add(obj.path_id)
            elif t == "GameObject" and k == main:
                tt = obj.read_typetree()
                if tt["m_Name"].startswith(old_stem):
                    tt["m_Name"] = name + tt["m_Name"][len(old_stem):]
                    obj.save_typetree(tt); changed[k].add(obj.path_id)
            elif t == "Transform" and k == main:
                go = obj.read().m_GameObject.read().m_Name
                if go in moves:
                    parent = obj.read_typetree()["m_Father"]["m_PathID"]
                    pname = next(o.read().m_GameObject.read().m_Name for o in env.objects if o.type.name == "Transform" and o.path_id == parent)
                    Fp = Froot @ P.rel(pname)
                    q = np.linalg.inv(Fp) @ np.array([*moves[go], 1.0])
                    tt = obj.read_typetree(); tt["m_LocalPosition"] = dict(zip("xyz", map(float, q[:3])))
                    obj.save_typetree(tt); changed[k].add(obj.path_id)
                    print(f"    moved {go} -> weapon {np.round(moves[go], 4).tolist()}")
    # drop collider around LOD0 (root space)
    if bounds:
        inv = np.linalg.inv(Froot)
        allp = np.vstack([((inv @ f)[:3, :3] @ p.T).T + (inv @ f)[:3, 3] for f, p in bounds])   # LOD0 vertices in root space
        lo, hi = allp.min(0), allp.max(0)
        for obj in envs[main].objects:
            if obj.type.name == "BoxCollider":
                tt = obj.read_typetree()
                tt["m_Center"] = dict(zip("xyz", map(float, (lo + hi) / 2))); tt["m_Size"] = dict(zip("xyz", map(float, np.maximum(hi - lo, 0.005))))
                obj.save_typetree(tt); changed[main].add(obj.path_id)
                print("    collider", np.round(hi - lo, 4).tolist())
    entries = []
    for k, env in envs.items():
        for obj in env.objects:
            t = obj.type.name
            if t in ("Mesh", "Texture2D", "AudioClip") and obj.path_id not in changed[k]:
                tt = obj.read_typetree(); nt = swap_strings(tt, cab_map)
                if nt != tt: obj.save_typetree(nt)
            elif t == "AssetBundle":
                tt = obj.read_typetree()
                tt["m_Name"] = newkey[k]; tt["m_AssetBundleName"] = newkey[k]
                tt["m_Dependencies"] = [newkey.get(d, lower.get(d.lower(), d)) for d in tt["m_Dependencies"]]
                base = (os.path.dirname(main) + "/" + old_stem).lower()
                tt["m_Container"] = [[(NEWDIR + name + c[len(base):]) if c.lower().startswith(base) else c, v] for c, v in tt["m_Container"]]
                obj.save_typetree(tt)
        for fname, f in env.file.files.items():
            if hasattr(f, "externals"):
                for ext in f.externals:
                    for old, new in cab_map.items():
                        ext.path = ext.path.replace(old, new)
        # the .resS stream file still holds the vanilla mesh/texture data we replaced (ours is stored inline):
        # drop it unless an untouched object (e.g. a cubemap) still streams from it
        still = False
        for obj in env.objects:
            if obj.type.name in ("Mesh", "Texture2D", "Cubemap", "AudioClip", "Texture2DArray") and obj.path_id not in changed[k]:
                tt = obj.read_typetree()
                sd = tt.get("m_StreamData") or tt.get("m_Resource") or {}
                if isinstance(sd, dict) and sd.get("path"):
                    still = True
        if not still:
            for fname in [n for n in env.file.files if n.endswith(".resS")]:
                env.file.files.pop(fname)
        renamed = {}
        for fname, f in env.file.files.items():
            nn = fname
            for old, new in cab_map.items():
                nn = nn.replace(old, new)
            if hasattr(f, "name"): f.name = nn
            renamed[nn] = f
        env.file.files.clear(); env.file.files.update(renamed)
        out = os.path.join(OUT, "bundles", newkey[k])
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as fh:
            fh.write(env.file.save(packer="lz4"))
        print(f"    wrote {newkey[k]} ({os.path.getsize(out) // 1024} KB)")
        entries.append({"key": newkey[k], "dependencyKeys": [newkey.get(d, d) for d in manifest[k]["Dependencies"]]})
    return entries

def rail_point(P, Froot):
    """mod_scope on the RK 62 M rail: same height above the rail top as the vanilla B-33 slot above its own rail."""
    van = P.rel("mod_scope")
    # rail top of our M cover: highest point of the exported mesh, middle of the rail length
    d = np.load(os.path.join(MESH_DIR, "RK62M_top_cover.npz"))["pos"]
    d = d[(d[:, 1] < -0.3560) & (d[:, 1] > -0.4660) & (np.abs(d[:, 0]) < 0.011)]   # the rail only (the rear sight ears are taller)
    top = d[:, 2].max()
    y_mid = -0.4110
    # vanilla: slot height vs B-33 mesh top, both in weapon space
    vp = vanilla_points(P, Froot)
    return (0.0, float(y_mid), float(top + vp))

def vanilla_points(P, Froot):
    """height of the vanilla B-33 mod_scope above that cover's own top surface."""
    import UnityPy as U
    from UnityPy.helpers.MeshHelper import MeshHandler
    env = U.load(os.path.join(SA, V["b33"]))
    m = next(o.read() for o in env.objects if o.type.name == "Mesh" and o.read().m_Name == "reciever_ak_zenit_b33_LOD0")
    h = MeshHandler(m); h.process(); pv = np.array(h.m_Vertices).reshape(-1, 3)
    vanF = W.frame("mod_reciever") @ RX90                          # where a B-33 sits on the AKMN
    f = vanF @ P.rel("reciever_ak_zenit_b33_LOD0"); w = (f[:3, :3] @ pv.T).T + f[:3, 3]
    s = (vanF @ P.rel("mod_scope"))[:3, 3]
    return float(s[2] - w[:, 2].max())

# ------------------------------------------------------------------ the rifle --------------------------------------
WEAPON_SET = ["assets/content/weapons/akm/weapon_izhmash_akmn_762x39_container.bundle",
              "assets/content/weapons/akm/client_assets.bundle",
              "assets/content/weapons/akm/textures/client_assets.bundle"]
WEAPONS = {
    # name: (receiver textures, side rail textures or None)
    "weapon_valmet_rk62_762x39": (TB + "RK_receiver_model_", "BLACK_RAIL"),     # side rail in black once it exists (see black_rail())
    "weapon_valmet_rk62m_762x39": (TG + "RK_receiver_model_", TG + "RK62M_side_rail_model_"),
}
AIM_Z = 0.0545                                    # RK sight line above the bore (the AKMN's aim_camera is at 0.0503)
AIM_Y = -(0.2842 - 0.120)                         # eye 12 cm behind the rear peep (weapon y = -Blender y), like the game's MP5 drum sight; the AKMN eye is 17 cm back
SELECTOR_SHIFT = (-0.0010, 0.0100, 0.0)          # weapon space: 1 mm in towards the receiver, 10 mm back
BOLT_SHIFT = (0.0, 0.0050, 0.0)                  # 5 mm back (its charging handle cleared the RK port's front lip)
# The AKM animations throw the carrier back up to 139.8 mm (firing 133.7); the RK receiver ends at Blender y 0.235,
# 37 mm short of the AKM's, so the carrier's tail poked out of the back. Its rear part is squashed so the rear end
# rests at y 0.3768 and stops at 0.2370 at full travel (inside the receiver).
BOLT_TAIL_START, BOLT_REAR_LIMIT = -0.4200, -0.3873   # (round 2: 2 mm clearance still let a sliver through - now 12.5 mm inside the receiver)

def read_mesh(obj):
    from UnityPy.helpers.MeshHelper import MeshHandler
    m = obj.read(); h = MeshHandler(m); h.process()
    nv = m.m_VertexData.m_VertexCount
    pos = np.array(h.m_Vertices, float).reshape(nv, -1)[:, :3]
    nrm = np.array(h.m_Normals, float).reshape(nv, -1)[:, :3]
    uv = np.array(h.m_UV0, float).reshape(nv, -1)[:, :2]
    tris = np.array([t for sub in h.get_triangles() for t in sub], dtype=np.int64).reshape(-1, 3)
    return pos, nrm, uv, tris

def shift_clip_curves(env, deltas, prefix="Weapon_root/Weapon_root_anim/weapon/"):
    """Add a constant offset to the localPosition curves of the named weapon nodes in every AnimationClip
    (constant, dense and streamed curves, plus the per-curve start/stop values). Returns the changed path ids."""
    import zlib, struct
    f2u = lambda f: struct.unpack("<I", struct.pack("<f", f))[0]
    u2f = lambda u: struct.unpack("<f", struct.pack("<I", u))[0]
    target = {zlib.crc32((prefix + n).encode()): d for n, d in deltas.items()}
    size = {1: 3, 2: 4, 3: 3, 4: 3}
    out, stats = set(), {}
    for obj in env.objects:
        if obj.type.name != "AnimationClip":
            continue
        tt = obj.read_typetree(); mc = tt["m_MuscleClip"]; d = mc["m_Clip"]["data"]
        sc, dc = d["m_StreamedClip"]["curveCount"], d["m_DenseClip"]["m_CurveCount"]
        add, idx = {}, 0                                   # curve index -> offset
        for b in tt["m_ClipBindingConstant"]["genericBindings"]:
            n = size.get(b["attribute"], 1) if b["typeID"] == 4 else 1
            if b["typeID"] == 4 and b["attribute"] == 1 and b["path"] in target:
                for k in range(3):
                    add[idx + k] = target[b["path"]][k]
            idx += n
        assert idx == sc + dc + len(d["m_ConstantClip"]["data"]), tt["m_Name"]
        if not add:
            continue
        for ci, v in add.items():
            if ci >= sc + dc:
                d["m_ConstantClip"]["data"][ci - sc - dc] += v; stats["const"] = stats.get("const", 0) + 1
            elif ci >= sc:
                dense = d["m_DenseClip"]
                for f in range(dense["m_FrameCount"]):
                    dense["m_SampleArray"][f * dc + ci - sc] += v
                stats["dense"] = stats.get("dense", 0) + 1
            va = mc["m_ValueArrayDelta"][ci]; va["m_Start"] += v; va["m_Stop"] += v
        data, i = d["m_StreamedClip"]["data"], 0
        while i < len(data):                               # frames: time, key count, keys (curve index, 4 cubic coefficients)
            nk = data[i + 1]; i += 2
            for _ in range(nk):
                ci = data[i]
                if ci in add:
                    data[i + 4] = f2u(u2f(data[i + 4]) + add[ci]); stats["streamed keys"] = stats.get("streamed keys", 0) + 1
                i += 5
        obj.save_typetree(tt); out.add(obj.path_id)
    print(f"    animation clips: {len(out)} shifted ({stats}) by " + ", ".join(f"{n} {[round(v, 4) for v in dv]}" for n, dv in deltas.items()))
    return out

def black_rail():
    """The plain RK 62 gets the side rail only when a black version exists: the black folder's newest side-rail export
    must differ from the green one (until then both folders hold the same olive rail)."""
    import hashlib
    try:
        b, g = find_maps(TB + "RK62M_side_rail_model_")["base"], find_maps(TG + "RK62M_side_rail_model_")["base"]
    except AssertionError:
        return None
    same = hashlib.md5(open(b, "rb").read()).digest() == hashlib.md5(open(g, "rb").read()).digest()
    print("    side rail for the RK 62:", "none yet (no black version exported - the black folder holds the green rail)" if same else "black " + os.path.basename(b))
    return None if same else TB + "RK62M_side_rail_model_"

def build_weapon(name, rec_tex, rail_tex, manifest):
    if rail_tex == "BLACK_RAIL":
        rail_tex = black_rail()
    newkey = {WEAPON_SET[0]: NEWDIR + name + "_container.bundle",
              WEAPON_SET[1]: NEWDIR + name + "_meshes.bundle",
              WEAPON_SET[2]: NEWDIR + name + "_textures.bundle"}
    envs = {k: UnityPy.load(os.path.join(SA, k)) for k in WEAPON_SET}
    cab_map, cab_of = {}, {}
    for k, env in envs.items():
        cab = next(n for n in env.file.files if n.startswith("CAB-") and "." not in n)
        cab_map[cab] = new_cab(newkey[k]); cab_of[k] = cab
    lower = {a.lower(): b.lower() for a, b in cab_map.items()}
    cont, mesh_env, tex_env = (envs[k] for k in WEAPON_SET)
    print(f"{name}")
    changed = {k: set() for k in WEAPON_SET}
    cf = next(f for n, f in cont.file.files.items() if hasattr(f, "externals"))
    ext_index = {i + 1: e.path.split("/")[-1].lower() for i, e in enumerate(cf.externals)}
    mesh_cab = cab_of[WEAPON_SET[1]].lower()
    # 1. container: which meshes the rifle's nodes use, receiver renderers -> spare material, slot moves
    go_name = {}
    for obj in cont.objects:
        if obj.type.name == "GameObject":
            go_name[obj.path_id] = obj.read_typetree()["m_Name"]
    mesh_of_node, spare_mat = {}, None
    mats = {}
    for obj in mesh_env.objects:
        if obj.type.name == "Material":
            mats[obj.read_typetree()["m_Name"]] = obj.path_id
    spare_mat = mats["mount_akms_izhmash_akmsn_dovetail_LOD0"]
    for obj in cont.objects:
        t = obj.type.name
        if t == "MeshFilter":
            tt = obj.read_typetree(); gname = go_name.get(tt["m_GameObject"]["m_PathID"])
            if ext_index.get(tt["m_Mesh"]["m_FileID"]) == mesh_cab:
                mesh_of_node.setdefault(gname, tt["m_Mesh"]["m_PathID"])
        elif t == "MeshRenderer":
            tt = obj.read_typetree(); gname = go_name.get(tt["m_GameObject"]["m_PathID"])
            if gname in ("weapon_izhmash_akm_762x39_LOD0", "weapon_izhmash_akm_762x39_LOD1"):
                fid = tt["m_Materials"][0]["m_FileID"]
                assert ext_index[fid] == mesh_cab
                tt["m_Materials"] = [{"m_FileID": fid, "m_PathID": spare_mat}]
                obj.save_typetree(tt); changed[WEAPON_SET[0]].add(obj.path_id)
                print(f"    renderer {gname} -> spare material (RK receiver textures)")
        elif t == "GameObject":
            tt = obj.read_typetree()
            if tt["m_Name"].startswith("weapon_izhmash_akmn_762x39"):
                tt["m_Name"] = name + tt["m_Name"][len("weapon_izhmash_akmn_762x39"):]
                obj.save_typetree(tt); changed[WEAPON_SET[0]].add(obj.path_id)
    moves = dict(WEAPON_MOVES)
    old_pos, new_pos = {}, {}
    for obj in cont.objects:
        if obj.type.name == "Transform":
            tt = obj.read_typetree(); gname = go_name.get(tt["m_GameObject"]["m_PathID"])
            par = tt["m_Father"]["m_PathID"]
            pname = next((go_name.get(o.read_typetree()["m_GameObject"]["m_PathID"]) for o in cont.objects if o.path_id == par), None)
            if pname != "weapon":
                continue
            if gname in moves:
                old_pos.setdefault(gname, tuple(tt["m_LocalPosition"][k] for k in "xyz"))
                tt["m_LocalPosition"] = dict(zip("xyz", map(float, moves[gname])))
            else:
                continue
            obj.save_typetree(tt); changed[WEAPON_SET[0]].add(obj.path_id)
            new_pos[gname] = tuple(tt["m_LocalPosition"][k] for k in "xyz")
            print(f"    moved {gname} -> {[round(v, 4) for v in tt['m_LocalPosition'].values()]}")
    # the AKM animation clips key these nodes' positions in every clip, which would snap them back to the AKM spots
    # (muzzle device floating ahead of the RK barrel, sight camera at the AKM height) - shift those curves the same way
    deltas = {n: tuple(b - a for a, b in zip(old_pos[n], new_pos[n])) for n in new_pos}
    if deltas:
        changed[WEAPON_SET[1]] |= shift_clip_curves(mesh_env, deltas)
    # 2. meshes
    rec = np.load(os.path.join(MESH_DIR, "RK_receiver.npz"))
    plan = {"weapon_izhmash_akm_762x39_LOD0": ("RK_receiver", "weapon_izhmash_akm_762x39_LOD0"),
            "weapon_izhmash_akm_762x39_LOD1": ("RK_receiver", "weapon_izhmash_akm_762x39_LOD1"),
            "weapon_izhmash_akm_762x39_kolodka_LOD0": (None, None), "weapon_izhmash_akm_762x39_kolodka_LOD1": (None, None),
            "mount_akm_izhmash_akmn_dovetail_LOD0": (("RK62M_side_rail", "mount_akm_izhmash_akmn_dovetail_LOD0") if rail_tex else (None, None)),
            "selector_LOD0": ("SHIFT", SELECTOR_SHIFT), "bolt_LOD0": ("BOLT", BOLT_SHIFT), "bolt_LOD1": ("BOLT", BOLT_SHIFT)}
    by_pid = {pid: node for node, pid in mesh_of_node.items()}
    for obj in mesh_env.objects:
        if obj.type.name != "Mesh" or obj.path_id not in by_pid:
            continue
        node = by_pid[obj.path_id]
        if node not in plan:
            continue
        src, arg = plan[node]
        if src is None:
            pos, nrm, uv, tris = blank()
        elif src in ("SHIFT", "BOLT"):
            pos, nrm, uv, tris = read_mesh(obj)
            F = W.frame(node)
            pos = pos + F[:3, :3].T @ np.array(arg)                        # weapon-space shift seen from the node
            if src == "BOLT":                                              # squash the carrier's tail (weapon +y = rearwards)
                wp = (F[:3, :3] @ pos.T).T + F[:3, 3]
                rear, keep = wp[:, 1].max(), BOLT_TAIL_START
                if rear > BOLT_REAR_LIMIT:
                    k = (BOLT_REAR_LIMIT - keep) / (rear - keep); m = wp[:, 1] > keep
                    wp[m, 1] = keep + (wp[m, 1] - keep) * k
                    pos = (F[:3, :3].T @ (wp - F[:3, 3]).T).T
                    print(f"    bolt tail squashed: rear {-rear:.4f} -> {-BOLT_REAR_LIMIT:.4f} (Blender y)")
        else:
            d = np.load(os.path.join(MESH_DIR, src + ".npz"))
            pos, nrm = to_local(W.frame(arg), d["pos"].astype(float), d["nrm"].astype(float))
            uv, tris = d["uv"].astype(float), d["tris"].astype(np.int64)
        write_mesh(obj, pos, nrm, uv, tris); changed[WEAPON_SET[1]].add(obj.path_id)
        print(f"    mesh {node} <- {src if src else 'blank'} ({len(pos)} verts)")
    # the spare material gets the receiver material's shader settings
    rec_mat = next(o for o in mesh_env.objects if o.type.name == "Material" and o.path_id == mats["weapon_izhmash_akm_762x39_LOD0"]).read_typetree()
    for obj in mesh_env.objects:
        if obj.type.name == "Material" and obj.path_id == spare_mat:
            tt = obj.read_typetree()
            tt["m_SavedProperties"]["m_Floats"] = rec_mat["m_SavedProperties"]["m_Floats"]
            tt["m_SavedProperties"]["m_Colors"] = rec_mat["m_SavedProperties"]["m_Colors"]
            tt["m_ShaderKeywords"] = rec_mat.get("m_ShaderKeywords", tt.get("m_ShaderKeywords"))
            standardize_material(tt)
            obj.save_typetree(tt); changed[WEAPON_SET[1]].add(obj.path_id)
        elif rail_tex and obj.type.name == "Material" and obj.path_id == mats.get("mount_akm_izhmash_akmn_dovetail_LOD0"):
            tt = obj.read_typetree()
            if standardize_material(tt):
                obj.save_typetree(tt); changed[WEAPON_SET[1]].add(obj.path_id)
    # 3. textures: spare (AKMS dovetail) set <- receiver, AKMN dovetail set <- side rail
    rtx = textures(rec_tex, 2048)
    stx = textures(rail_tex, 1024) if rail_tex else None
    for obj in tex_env.objects:
        if obj.type.name != "Texture2D":
            continue
        t = obj.read(); n = t.m_Name; kind = tex_kind(n)
        src = rtx if n.startswith("mount_akms_izhmash_akmsn_dovetail_LOD0") else stx if (stx and n.startswith("mount_akm_izhmash_akmn_dovetail_LOD0")) else None
        if src is None or kind not in ("diff", "gloss", "nrm"):
            continue
        img = src[kind]
        t.set_image(img, target_format=FMT[kind], mipmap_count=mips(img)); t.save()
        changed[WEAPON_SET[2]].add(obj.path_id); print(f"    texture {n} <- {img.size}")
    # 3b. slim the texture bundle: keep only textures the rifle's renderers use (stored inline), the rest become 4x4
    used_mats = set()
    for obj in cont.objects:
        if obj.type.name == "MeshRenderer":
            for m in obj.read_typetree()["m_Materials"]:
                if ext_index.get(m["m_FileID"]) == mesh_cab:
                    used_mats.add(m["m_PathID"])
    mf = next(f for n, f in mesh_env.file.files.items() if hasattr(f, "externals"))
    mext = {i + 1: e.path.split("/")[-1].lower() for i, e in enumerate(mf.externals)}
    tex_cab = cab_of[WEAPON_SET[2]].lower()
    keep = set()
    for obj in mesh_env.objects:
        if obj.type.name == "Material" and obj.path_id in used_mats:
            for k_, v in obj.read_typetree()["m_SavedProperties"]["m_TexEnvs"]:
                if mext.get(v["m_Texture"]["m_FileID"]) == tex_cab:
                    keep.add(v["m_Texture"]["m_PathID"])
    tiny = Image.new("RGBA", (4, 4), (128, 128, 128, 255))
    for obj in tex_env.objects:
        if obj.type.name != "Texture2D" or obj.path_id in changed[WEAPON_SET[2]]:
            continue
        if obj.path_id in keep:
            t = obj.read()
            from UnityPy.helpers.ResourceReader import get_resource_data
            sd = t.m_StreamData
            data = bytes(get_resource_data(sd.path, t.object_reader.assets_file, sd.offset, sd.size)) if sd and sd.size else bytes(t.image_data)
            assert len(data) == t.m_CompleteImageSize or len(data) > 0, t.m_Name
            tt = obj.read_typetree(); tt["image data"] = data; tt["m_StreamData"] = {"offset": 0, "size": 0, "path": ""}
            obj.save_typetree(tt)
        else:
            t = obj.read(); t.set_image(tiny, target_format=12, mipmap_count=1); t.save()
        changed[WEAPON_SET[2]].add(obj.path_id)
    print(f"    textures kept {len(keep)} (inline), the rest made tiny")
    if not any(o.type.name in ("Texture2D", "Cubemap") and o.path_id not in changed[WEAPON_SET[2]] for o in tex_env.objects):
        for fname in [n for n in tex_env.file.files if n.endswith(".resS")]:
            tex_env.file.files.pop(fname)
    # 4. identity + write
    entries = []
    for k, env in envs.items():
        for obj in env.objects:
            t = obj.type.name
            if t in ("Mesh", "Texture2D", "AudioClip") and obj.path_id not in changed[k]:
                tt = obj.read_typetree(); nt = swap_strings(tt, cab_map)
                if nt != tt: obj.save_typetree(nt)
            elif t == "AssetBundle":
                tt = obj.read_typetree()
                tt["m_Name"] = newkey[k]; tt["m_AssetBundleName"] = newkey[k]
                tt["m_Dependencies"] = [newkey.get(d, lower.get(d.lower(), d)) for d in tt["m_Dependencies"]]
                if k == WEAPON_SET[0]:
                    base = "assets/content/weapons/akm/weapon_izhmash_akmn_762x39"
                    tt["m_Container"] = [[(NEWDIR + name + c[len(base):]) if c.lower().startswith(base) else c, v] for c, v in tt["m_Container"]]
                obj.save_typetree(tt)
        for fname, f in env.file.files.items():
            if hasattr(f, "externals"):
                for ext in f.externals:
                    for old, new in cab_map.items():
                        ext.path = ext.path.replace(old, new)
        renamed = {}
        for fname, f in env.file.files.items():
            nn = fname
            for old, new in cab_map.items():
                nn = nn.replace(old, new)
            if hasattr(f, "name"): f.name = nn
            renamed[nn] = f
        env.file.files.clear(); env.file.files.update(renamed)
        out = os.path.join(OUT, "bundles", newkey[k])
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as fh:
            fh.write(env.file.save(packer="lz4"))
        print(f"    wrote {newkey[k]} ({os.path.getsize(out) // 1024} KB)")
        entries.append({"key": newkey[k], "dependencyKeys": [newkey.get(d, d) for d in manifest[k]["Dependencies"]]})
    return entries

def main():
    manifest = json.load(open(os.path.join(SA, "Windows.json")))
    entries = []
    for n, spec in PARTS.items():
        if ONLY and n not in ONLY:
            continue
        entries += build(n, spec, manifest)
    for n, (rt, st) in WEAPONS.items():
        if ONLY and n not in ONLY:
            continue
        entries += build_weapon(n, rt, st, manifest)
    json.dump({"manifest": entries}, open(os.path.join(OUT, "bundles_rk62.json"), "w"), indent=2)
    print("wrote bundles_rk62.json:", len(entries), "bundles")

if __name__ == "__main__":
    main()
