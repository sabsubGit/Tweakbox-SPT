"""Rebuild the AKMN exactly as the game assembles it (factory parts on their slot transforms) and write it as a
Blender-ready JSON: every LOD0 mesh in its own part frame + the frame's matrix, plus the attachment points.
Axes: Blender = (-x, -z, y) of Unity; matrices conjugated the same way (same convention as the Iskub round trip)."""
import json, re, sys
import numpy as np
sys.path.insert(0, "/mnt/storage/Code/Tweakbox/tools/rk62")
from akref import Game, world, path_of

GAME, OUT = sys.argv[1:3]
P = np.array([[-1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)
to_blender = lambda M: P @ M @ np.linalg.inv(P)

WEAPON = "assets/content/weapons/akm/weapon_izhmash_akmn_762x39_container.bundle"
# part label, bundle, parent part label, slot transform name on the parent
PARTS = [
    ("gas_tube", "assets/content/items/mods/gasblock/gas_block_ak_izhmash_akm_std.bundle", "receiver", "mod_gas_block"),
    ("handguard", "assets/content/items/mods/handguards/handguard_ak_izhmash_akm_std_wood.bundle", "gas_tube", "mod_handguard"),
    ("muzzle", "assets/content/items/mods/muzzle/muzzle_ak_izhmash_akm_std_762x39.bundle", "receiver", "mod_muzzle"),
    ("pistol_grip", "assets/content/items/mods/pistol grips/pistolgrip_ak_izhmash_akm_bakelit.bundle", "receiver", "mod_pistol_grip"),
    ("dust_cover", "assets/content/items/mods/recievers/reciever_ak_izhmash_akm_std.bundle", "receiver", "mod_reciever"),
    ("rear_sight", "assets/content/items/mods/sights rear/sight_rear_ak_izhmash_akm_std.bundle", "receiver", "mod_sight_rear"),
    ("stock", "assets/content/items/mods/stocks/stock_ak_izhmash_akm_std_wood.bundle", "receiver", "mod_stock"),
    ("magazine", "assets/content/items/mods/magazines/mag_ak_izhmash_6l10_762x39_30.bundle", "receiver", "mod_magazine"),
]
SKIP = re.compile(r"LOD[1-9]|collider|MuzzleJet|_simple", re.I)

g = Game(GAME)
out = {"objects": [], "points": [], "frames": {}}

def parse_obj(text):
    V, VT, F = [], [], []
    for line in text.splitlines():
        p = line.split()
        if not p:
            continue
        if p[0] == "v":
            x, y, z = map(float, p[1:4]); V.append((x, -z, y))          # OBJ (Y-up) -> Blender (Z-up)
        elif p[0] == "vt":
            VT.append(tuple(map(float, p[1:3])))
        elif p[0] == "f":
            F.append([tuple(int(i) - 1 if i else -1 for i in (c.split("/") + ["", ""])[:2]) for c in p[1:]])
    return V, VT, F

def add_prefab(label, P_, frame_M, root_filter=None):
    """Export every LOD0 renderer of a prefab. frame_M = Unity matrix of the prefab root in weapon space."""
    sf = P_.main
    T = P_.transforms()
    roots = [pid for pid, t in T.items() if t[1] == 0]
    root = roots[0] if root_filter is None else next(p for p in roots if root_filter(T[p][0]))
    # the part's own frame (prefab root) in weapon space, already in Blender axes
    out["frames"][label] = to_blender(frame_M).tolist()
    seen = set()
    for pid, (name, par, M, go_pid) in T.items():
        full = path_of(T, pid)
        if not full.startswith(T[root][0]) or SKIP.search(full):
            continue
        rel = world(T, pid, stop=0) if root_filter is None else None
        # matrix of this node relative to the prefab root
        chain = world(T, pid)
        root_w = world(T, root)
        local = np.linalg.inv(root_w) @ chain
        if name.startswith("mod_") or name in ("aim_camera", "fireport", "shellport", "mod_align_front"):
            out["points"].append({"part": label, "name": name, "matrix": to_blender(frame_M @ local).tolist()})
        go = P_.typetree(sf, go_pid)
        mesh = None
        for c in go["m_Component"]:
            csf, cpid = P_.deref(sf, c["component"])
            if csf is not None and csf.objects[cpid].type.name == "MeshFilter":
                msf, mpid = P_.deref(csf, P_.typetree(csf, cpid)["m_Mesh"])
                if msf is not None:
                    mesh = msf.objects[mpid]
        if mesh is None or (mesh.path_id, name) in seen:
            continue
        seen.add((mesh.path_id, name))
        m = mesh.read()
        V, VT, F = parse_obj(m.export())
        out["objects"].append({"part": label, "name": name, "mesh": m.m_Name,
                               "matrix": to_blender(frame_M @ local).tolist(),
                               "verts": [[round(c, 6) for c in v] for v in V],
                               "uvs": [[round(c, 6) for c in t] for t in VT],
                               "faces": [[c[0] for c in f] for f in F],
                               "face_uvs": [[c[1] for c in f] for f in F]})
        print(f"  {label:12} {name:44} {len(V):6} verts")

# receiver: frame = the 'weapon' node of the full (non-simple) model
W = g.load(WEAPON)
T = W.transforms()
weapon_pid = next(p for p, t in T.items() if t[0] == "weapon" and "_simple" not in path_of(T, p))
weapon_w = world(T, weapon_pid)
slots = {"receiver": {}}
for pid, t in T.items():
    if t[0].startswith("mod_") and path_of(T, pid).startswith(path_of(T, weapon_pid) + "/"):
        slots["receiver"][t[0]] = np.linalg.inv(weapon_w) @ world(T, pid)
# add_prefab places nodes relative to the prefab root; weapon_w already includes the root's own transform
full_root = next(p for p, t in T.items() if t[1] == 0 and "_simple" not in t[0])
add_prefab("receiver", W, np.linalg.inv(weapon_w) @ world(T, full_root), root_filter=lambda n: "_simple" not in n)
out["frames"]["receiver"] = np.eye(4).tolist()

# Part meshes sit under a LOD node turned -90 deg about X (and so do the slot points inside parts); the game attaches a
# part turned +90 deg about X relative to its slot, which makes every mesh line up with the receiver.
RX90 = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)
for label, key, parent, slot in PARTS:
    Pp = g.load(key)
    frame = slots[parent][slot] @ RX90
    Tp = Pp.transforms()
    root = next(p for p, t in Tp.items() if t[1] == 0)
    slots[label] = {t[0]: frame @ np.linalg.inv(world(Tp, root)) @ world(Tp, p) for p, t in Tp.items() if t[0].startswith("mod_")}
    add_prefab(label, Pp, frame)

json.dump(out, open(OUT, "w"))
print(f"{len(out['objects'])} meshes, {len(out['points'])} attachment/aim points -> {OUT}")
