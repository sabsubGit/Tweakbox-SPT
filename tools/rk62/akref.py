"""Shared helpers: load an EFT bundle with its dependencies (via Windows.json) and walk prefab hierarchies."""
import json, os
import numpy as np
import UnityPy

class Game:
    def __init__(self, game_root):
        self.sa = os.path.join(game_root, "EscapeFromTarkov_Data/StreamingAssets/Windows")
        self.index = json.load(open(os.path.join(self.sa, "Windows.json")))

    def load(self, key):
        """Environment with the bundle and its (non-shader, non-texture) dependencies."""
        order, seen = [], set()
        def walk(k):
            if k in seen:
                return
            seen.add(k)
            if k in ("shaders", "cubemaps") or "/textures/" in k or k not in self.index:
                return
            for d in self.index[k]["Dependencies"]:
                walk(d)
            order.append(k)
        walk(key)
        env = UnityPy.load(*[os.path.join(self.sa, k) for k in order])
        return Prefabs(env, os.path.join(self.sa, key))

class Prefabs:
    def __init__(self, env, main_path):
        self.env = env
        self.cabs = {}
        self.main = None
        for path, bf in env.files.items():
            for name, f in getattr(bf, "files", {}).items():
                if hasattr(f, "objects"):
                    self.cabs[name.lower()] = f
                    if os.path.abspath(path) == os.path.abspath(main_path) and self.main is None:
                        self.main = f
        self.tt = {}

    def typetree(self, sf, pid):
        k = (id(sf), pid)
        if k not in self.tt:
            self.tt[k] = sf.objects[pid].read_typetree()
        return self.tt[k]

    def deref(self, sf, pptr):
        fid, pid = pptr["m_FileID"], pptr["m_PathID"]
        if pid == 0:
            return None, None
        if fid == 0:
            return sf, pid
        ext = sf.externals[fid - 1].path
        cab = os.path.basename(ext).lower()
        tgt = self.cabs.get(cab)
        return (tgt, pid) if tgt is not None and pid in tgt.objects else (None, None)

    def transforms(self, sf=None):
        """{transform path_id: (name, parent_pid, local 4x4, gameobject pid)} for one serialized file."""
        sf = sf or self.main
        out = {}
        for pid, o in sf.objects.items():
            if o.type.name != "Transform":
                continue
            t = self.typetree(sf, pid)
            go = self.typetree(sf, t["m_GameObject"]["m_PathID"])
            out[pid] = (go["m_Name"], t["m_Father"]["m_PathID"], trs(t), t["m_GameObject"]["m_PathID"])
        return out

def trs(t):
    p, q, s = t["m_LocalPosition"], t["m_LocalRotation"], t["m_LocalScale"]
    x, y, z, w = q["x"], q["y"], q["z"], q["w"]
    R = np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                  [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                  [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
    M = np.eye(4)
    M[:3, :3] = R @ np.diag([s["x"], s["y"], s["z"]])
    M[:3, 3] = [p["x"], p["y"], p["z"]]
    return M

def world(trs_map, pid, stop=0):
    M = np.eye(4)
    while pid and pid != stop and pid in trs_map:
        M = trs_map[pid][2] @ M
        pid = trs_map[pid][1]
    return M

def path_of(trs_map, pid):
    names = []
    while pid and pid in trs_map:
        names.append(trs_map[pid][0])
        pid = trs_map[pid][1]
    return "/".join(reversed(names))
