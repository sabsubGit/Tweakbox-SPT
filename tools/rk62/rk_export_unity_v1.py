# Run inside Blender. Writes each RK part as Unity mesh data in the LOCAL space of the vanilla node it replaces, so the
# bundle builder can drop it straight into a copied game bundle.
#   Unity = (-x, z, -y) of Blender mesh data relative to the reference node (verified against the game's raw AKM receiver
#   vertex data, incl. its left/right asymmetry); the mirror flips handedness, so triangle winding is flipped too.
# Output: <OUT>/<part>.npz with pos (n,3) f32, nrm (n,3) f32, uv (n,2) f32, tris (m,3) u32, plus bounds.
import bpy, os
import numpy as np

OUT = os.path.expanduser('~/Downloads/TarkovMods/RK62-reference/unity_meshes')
REF = {   # RK part -> vanilla AKMN node (LOD0) whose local space the part is written in
    'RK_pistol_grip_model': 'AK_pistol_grip__pistolgrip_ak_izhmash_akm_bakelit_LOD0',
    'RK_bicycle_grip_model': 'AK_pistol_grip__pistolgrip_ak_izhmash_akm_bakelit_LOD0',
}

def ref_world(name):
    root = bpy.data.objects['AKMN_root']; o = bpy.data.objects[name]
    return root.matrix_basis @ o.matrix_parent_inverse @ o.matrix_basis

def export(part, ref, out=OUT):
    os.makedirs(out, exist_ok=True)
    ob = bpy.data.objects[part]
    M = ref_world(ref).inverted() @ ob.matrix_world
    R = M.to_3x3().inverted().transposed()
    me = ob.data
    me.calc_loop_triangles()
    uvl = me.uv_layers.active.data
    key_index, pos, nrm, uv, tris = {}, [], [], [], []
    for t in me.loop_triangles:
        idx = []
        for li in t.loops:
            l = me.loops[li]
            p = M @ me.vertices[l.vertex_index].co
            n = (R @ l.normal).normalized()
            u = uvl[li].uv
            k = (l.vertex_index, round(n.x, 4), round(n.y, 4), round(n.z, 4), round(u.x, 6), round(u.y, 6))
            if k not in key_index:
                key_index[k] = len(pos)
                pos.append((-p.x, p.z, -p.y)); nrm.append((-n.x, n.z, -n.y)); uv.append((u.x, u.y))
            idx.append(key_index[k])
        tris.append((idx[0], idx[2], idx[1]))           # mirrored -> flip winding
    pos, nrm, uv = (np.array(a, dtype=np.float32) for a in (pos, nrm, uv)); tris = np.array(tris, dtype=np.uint32)
    np.savez(os.path.join(out, part.replace('_model', '') + '.npz'), pos=pos, nrm=nrm, uv=uv, tris=tris, ref=ref)
    print('%-32s -> %-60s %6d verts %6d tris  min %s max %s' % (part, ref, len(pos), len(tris), pos.min(0).round(4), pos.max(0).round(4)))

if __name__ == '__main__':
    for part, ref in REF.items():
        export(part, ref)
