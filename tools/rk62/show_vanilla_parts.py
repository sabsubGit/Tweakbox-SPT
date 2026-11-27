# Run inside Blender: puts copies of the vanilla Tarkov AK moving parts (bolt carrier, trigger, hammer, magazine release,
# selector) where they sit in the weapon. Reference only: these stay the vanilla animated parts of the cloned weapon bundle.
import bpy
from mathutils import Matrix
root = bpy.data.objects['AKMN_root']
col = bpy.data.collections.get('RK62 vanilla parts (reference)') or bpy.data.collections.new('RK62 vanilla parts (reference)')
if col.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(col)
m = bpy.data.materials.get('RK vanilla part') or bpy.data.materials.new('RK vanilla part'); m.diffuse_color = (0.30, 0.26, 0.20, 1)
# bolt pulled 5 mm to the rear: at the AK rest position its charging handle ran into the front edge of the RK ejection port
OFFSET = {'bolt': (0.0, -0.0050, 0.0)}
for part in ('bolt', 'trigger', 'hammer', 'release'):
    src = bpy.data.objects['AK_receiver__%s_LOD0' % part]
    W = root.matrix_basis @ src.matrix_parent_inverse @ src.matrix_basis
    old = bpy.data.objects.get('RK_%s_vanilla' % part)
    if old: d = old.data; bpy.data.objects.remove(old); bpy.data.meshes.remove(d)
    me = src.data.copy(); me.transform(Matrix.Translation(OFFSET.get(part, (0, 0, 0))) @ W)
    if W.determinant() < 0: me.flip_normals()
    for p in me.polygons: p.use_smooth = True
    me.materials.clear(); me.materials.append(m)
    col.objects.link(bpy.data.objects.new('RK_%s_vanilla' % part, me))
    print('placed', part, len(me.vertices), 'verts')
exec(open('/mnt/storage/Code/Tweakbox/tools/rk62/show_vanilla_selector.py').read())
