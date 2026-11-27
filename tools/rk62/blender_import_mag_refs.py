# Run inside Blender: exec(open('/mnt/storage/Code/Tweakbox/tools/rk62/blender_import_mag_refs.py').read())
# (Re)builds 'AK magazines (game reference)' from mag_reference.json (made by extract_mag_refs.py): vanilla AK 7.62x39
# magazines on the AKMN magazine slot, same frame as 'AK reference (game)'. Objects: ref_mag_<label>.
import bpy, json
from mathutils import Matrix
D = json.load(open('/home/teemu/Downloads/TarkovMods/RK62-reference/mag_reference.json'))

def coll(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    p = parent or bpy.context.scene.collection
    if c.name not in [x.name for x in p.children]:
        p.children.link(c)
    return c

c = coll('AK magazines (game reference)')
for o in list(c.objects):
    me = o.data; bpy.data.objects.remove(o)
    if me.users == 0: bpy.data.meshes.remove(me)
root = bpy.data.objects['AKMN_root']
m = bpy.data.materials.get('AK mag ref') or bpy.data.materials.new('AK mag ref')
m.diffuse_color = (0.25, 0.25, 0.27, 1)
for o in D['objects']:
    if o['name'].endswith('_glass'):
        continue
    me = bpy.data.meshes.new(o['mesh'])
    me.from_pydata([tuple(v) for v in o['verts']], [], [tuple(f) for f in o['faces']])
    uv = me.uv_layers.new(name='UVMap'); li = 0
    for f, fu in zip(o['faces'], o['face_uvs']):
        for k in fu:
            if k >= 0: uv.data[li].uv = o['uvs'][k]
            li += 1
    me.validate(); me.update()
    try: me.set_sharp_from_angle(angle=0.6)
    except Exception: pass
    me.materials.append(m)
    ob = bpy.data.objects.new('ref_mag_' + o['part'], me)
    c.objects.link(ob); ob.parent = root; ob.matrix_basis = Matrix(o['matrix'])
    ob.hide_select = True
bpy.context.view_layer.update()
print('magazine references:', [o.name for o in c.objects])
