# Run inside Blender. Writes RK parts as Unity mesh data in AKMN WEAPON space (the prefab's 'weapon' node), so the bundle
# builder can work out every part's local frame from the game's own slot tree (weapon slot -> part root -> sub-slot ...).
#   Blender world = AKMN_root @ P @ u_weapon, P = [[-1,0,0],[0,0,-1],[0,1,0]] (Unity -> Blender axes, verified exactly
#   against the raw AKM receiver data), so u_weapon = P^-1 @ AKMN_root^-1 @ b. P mirrors, so triangle winding flips.
# Output: <OUT>/<part>.npz  pos (n,3) f32, nrm (n,3) f32, uv (n,2) f32, tris (m,3) u32  (weapon space)
#         <OUT>/points.json  named target points in weapon space (slot moves etc.)
import bpy, os, json
import numpy as np
from mathutils import Matrix, Vector

OUT = os.path.expanduser('~/Downloads/TarkovMods/RK62-reference/unity_meshes')
P = Matrix(((-1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
PARTS = ['RK_receiver_model', 'RK_gas_tube_model', 'RK_top_cover_model', 'RK_handguard_plastic_model', 'RK_handguard_cheesegrater_model',
         'RK_pistol_grip_model', 'RK_bicycle_grip_model', 'RK_stock_model', 'RK_waffle_mag_model', 'RK_flash_hider_model',
         'RK62M_top_cover_model', 'RK62M_handguard_model', 'RK62M_side_rail_model', 'RK62M_flash_hider_model', 'RK62M_suppressor_model']

def world_of(ob):
    if ob.parent is None:
        return ob.matrix_world.copy()
    return world_of(ob.parent) @ ob.matrix_parent_inverse @ ob.matrix_basis      # reference objects sit in an excluded collection

def to_weapon():
    return P.inverted() @ bpy.data.objects['AKMN_root'].matrix_basis.inverted()

def export(name, out_name=None, out=OUT):
    os.makedirs(out, exist_ok=True)
    ob = bpy.data.objects[name]
    M = to_weapon() @ world_of(ob)
    R = M.to_3x3().inverted().transposed()
    me = ob.data
    me.calc_loop_triangles()
    uvl = me.uv_layers.active.data if me.uv_layers.active else None
    key_index, pos, nrm, uv, tris = {}, [], [], [], []
    for t in me.loop_triangles:
        idx = []
        for li in t.loops:
            l = me.loops[li]
            p = M @ me.vertices[l.vertex_index].co
            n = (R @ l.normal).normalized()
            u = uvl[li].uv if uvl else Vector((0, 0))
            k = (l.vertex_index, round(n.x, 4), round(n.y, 4), round(n.z, 4), round(u.x, 6), round(u.y, 6))
            if k not in key_index:
                key_index[k] = len(pos)
                pos.append(p[:]); nrm.append(n[:]); uv.append((u.x, u.y))
            idx.append(key_index[k])
        tris.append((idx[0], idx[2], idx[1]))                # P mirrors: flip winding
    pos, nrm, uv = (np.array(a, dtype=np.float32) for a in (pos, nrm, uv)); tris = np.array(tris, dtype=np.uint32)
    fn = os.path.join(out, (out_name or name.replace('_model', '')) + '.npz')
    np.savez(fn, pos=pos, nrm=nrm, uv=uv, tris=tris)
    print('%-34s %6d verts %6d tris  weapon-space min %s max %s' % (name, len(pos), len(tris), pos.min(0).round(4), pos.max(0).round(4)))

def point(b):
    """Blender world point -> weapon space."""
    return list(to_weapon() @ Vector(b))

if __name__ == '__main__':
    for n in PARTS:
        if n in bpy.data.objects:
            export(n)
