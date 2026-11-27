# Run inside Blender: puts a copy of the vanilla Tarkov AK selector lever where it sits on the weapon, so the RK can be
# judged with it. Reference only - the lever stays the vanilla moving part in the cloned weapon bundle (do not export it).
import bpy
from mathutils import Matrix
src = bpy.data.objects['AK_receiver__selector_LOD0']; root = bpy.data.objects['AKMN_root']
W = root.matrix_basis @ src.matrix_parent_inverse @ src.matrix_basis
old = bpy.data.objects.get('RK_selector_vanilla')
if old: d = old.data; bpy.data.objects.remove(old); bpy.data.meshes.remove(d)
SEL_BACK = 0.0100                                                                 # lever moved 10 mm to the rear so its tip stops short of the ejection port (starts y 0.388)
me = src.data.copy(); me.transform(Matrix.Translation((-0.0010, -SEL_BACK, 0)) @ W)   # and 1 mm inwards: the RK receiver is that much narrower than the AKM's
# Shown in the SAFE (up) position like the reference pictures: swing it about its axis until the bar's top edge is at z 14.3 mm (just under the cover's shoulder).
# (In game the lever is animated; the bundle rest pose is lower.)
import math
PV = Matrix.Translation((0, 0.2945 - SEL_BACK, -0.0084))
best = None
for k in range(0, 400):
    a = math.radians(k * 0.1); R = PV @ Matrix.Rotation(a, 4, 'X') @ PV.inverted()
    top = max((R @ v.co).z for v in me.vertices)
    if best is None or abs(top - 0.0143) < best[0]: best = (abs(top - 0.0143), a)
    if top > 0.0143: break
me.transform(PV @ Matrix.Rotation(best[1], 4, 'X') @ PV.inverted()); print('selector swung up by', round(math.degrees(best[1]), 1), 'deg')
if W.determinant() < 0: me.flip_normals()
ob = bpy.data.objects.new('RK_selector_vanilla', me)
col = bpy.data.collections.get('RK62 vanilla parts (reference)') or bpy.data.collections.new('RK62 vanilla parts (reference)')
if col.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(col)
col.objects.link(ob)
for p in me.polygons: p.use_smooth = True
m = bpy.data.materials.get('RK vanilla selector') or bpy.data.materials.new('RK vanilla selector'); m.diffuse_color = (0.22, 0.23, 0.24, 1)
me.materials.clear(); me.materials.append(m)
print('vanilla selector placed', len(me.vertices), 'verts')
