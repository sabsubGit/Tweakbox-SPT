"""Extract vanilla AK magazines (LOD0 meshes) placed on the AKMN mod_magazine slot, in the same Blender frame as
akmn_reference.json ('AK reference (game)'). Usage: python extract_mag_refs.py <game_dir> <out.json>"""
import json, re, sys
import numpy as np
sys.path.insert(0, "/mnt/storage/Code/Tweakbox/tools/rk62")
from akref import Game, world, path_of

GAME, OUT = sys.argv[1:3]
P = np.array([[-1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)
to_blender = lambda M: P @ M @ np.linalg.inv(P)
RX90 = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)
WEAPON = "assets/content/weapons/akm/weapon_izhmash_akmn_762x39_container.bundle"
D = "assets/content/items/mods/magazines/"
MAGS = {
    "steel55": D + "mag_ak_izhmash_ak_std_55_762x39_30.bundle",
    "6l10": D + "mag_ak_izhmash_6l10_762x39_30.bundle",
    "ak103": D + "mag_ak_izhmash_ak103_std_762x39_30.bundle",
    "pmag": D + "mag_ak_magpul_pmag_30_ak_akm_gen_m3_762x39_30.bundle",
    "uspalm": D + "mag_ak_us_palm_ak30_762x39_blk.bundle",
    "ultimag": D + "mag_ak_fab_defense_ultimag_ak_30r_762x39_30.bundle",
    "alu30": D + "mag_ak_izhmash_akms_aluminium_762x39_30.bundle",
}
SKIP = re.compile(r"LOD[1-9]|collider|patron|_simple", re.I)

def parse_obj(text):
    V, VT, F = [], [], []
    for line in text.splitlines():
        p = line.split()
        if not p:
            continue
        if p[0] == "v":
            x, y, z = map(float, p[1:4]); V.append((x, -z, y))
        elif p[0] == "vt":
            VT.append(tuple(map(float, p[1:3])))
        elif p[0] == "f":
            F.append([tuple(int(i) - 1 if i else -1 for i in (c.split("/") + ["", ""])[:2]) for c in p[1:]])
    return V, VT, F

g = Game(GAME)
W = g.load(WEAPON)
T = W.transforms()
weapon_pid = next(p for p, t in T.items() if t[0] == "weapon" and "_simple" not in path_of(T, p))
weapon_w = world(T, weapon_pid)
slot = next(np.linalg.inv(weapon_w) @ world(T, p) for p, t in T.items()
            if t[0] == "mod_magazine" and path_of(T, p).startswith(path_of(T, weapon_pid) + "/"))
frame = slot @ RX90
out = {"objects": []}
for label, key in MAGS.items():
    Pp = g.load(key)
    sf = Pp.main
    Tp = Pp.transforms()
    root = next(p for p, t in Tp.items() if t[1] == 0)
    root_w = world(Tp, root)
    seen = set()
    for pid, (name, par, M, go_pid) in Tp.items():
        full = path_of(Tp, pid)
        if SKIP.search(full):
            continue
        go = Pp.typetree(sf, go_pid)
        mesh = None
        for c in go["m_Component"]:
            csf, cpid = Pp.deref(sf, c["component"])
            if csf is not None and csf.objects[cpid].type.name == "MeshFilter":
                msf, mpid = Pp.deref(csf, Pp.typetree(csf, cpid)["m_Mesh"])
                if msf is not None:
                    mesh = msf.objects[mpid]
        if mesh is None or mesh.path_id in seen:
            continue
        seen.add(mesh.path_id)
        m = mesh.read()
        V, VT, F = parse_obj(m.export())
        local = np.linalg.inv(root_w) @ world(Tp, pid)
        out["objects"].append({"part": label, "name": name, "mesh": m.m_Name, "matrix": to_blender(frame @ local).tolist(),
                               "verts": [[round(c, 6) for c in v] for v in V], "uvs": [[round(c, 6) for c in t] for t in VT],
                               "faces": [[c[0] for c in f] for f in F], "face_uvs": [[c[1] for c in f] for f in F]})
        print(f"  {label:8} {full:70} {len(V):6} verts")
json.dump(out, open(OUT, "w"))
print(len(out["objects"]), "meshes ->", OUT)
