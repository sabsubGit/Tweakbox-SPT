"""Slot-tree frames, the way the game assembles a weapon: a part's root sits on its slot turned +90 deg about X (RX90),
and its mesh / sub-slot nodes hang under that root. Everything is in AKMN 'weapon' space (Unity axes)."""
import numpy as np
from akref import Game, world, path_of

RX90 = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)
WEAPON_KEY = "assets/content/weapons/akm/weapon_izhmash_akmn_762x39_container.bundle"

class Weapon:
    def __init__(self, game, key=WEAPON_KEY):
        self.P = game.load(key)
        self.T = self.P.transforms()
        self.weapon_pid = next(p for p, t in self.T.items() if t[0] == "weapon" and "_simple" not in path_of(self.T, p))
        self.weapon_w = world(self.T, self.weapon_pid)
        base = path_of(self.T, self.weapon_pid) + "/"
        self.nodes = {t[0]: p for p, t in self.T.items() if path_of(self.T, p).startswith(base)}

    def frame(self, name):
        """Node frame in weapon space."""
        return np.linalg.inv(self.weapon_w) @ world(self.T, self.nodes[name])

class Part:
    def __init__(self, game, key):
        self.P = game.load(key)
        self.T = self.P.transforms()
        roots = [p for p, t in self.T.items() if t[1] == 0]
        self.root = roots[0]
        self.root_w = world(self.T, self.root)
        self.nodes = {t[0]: p for p, t in self.T.items()}

    def rel(self, name):
        """Node frame relative to the part's root."""
        return np.linalg.inv(self.root_w) @ world(self.T, self.nodes[name])

def to_local(frame, pos, nrm):
    inv = np.linalg.inv(frame)
    p = (inv[:3, :3] @ pos.T).T + inv[:3, 3]
    n = (frame[:3, :3].T @ nrm.T).T                       # rigid frames: inverse rotation = transpose
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    return p, n
