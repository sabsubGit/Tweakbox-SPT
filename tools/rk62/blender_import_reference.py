# Run inside Blender: exec(open('/mnt/storage/Code/Tweakbox/tools/rk62/blender_import_reference.py').read())
# (Re)builds the 'AK reference (game)' collection from akmn_reference.json. Never touches the RK collections.
import bpy, json
from mathutils import Matrix
SRC = '/home/teemu/Downloads/TarkovMods/RK62-reference/akmn_reference.json'
D = json.load(open(SRC))

def coll(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    p = parent or bpy.context.scene.collection
    if c.name not in [x.name for x in p.children]:
        p.children.link(c)
    return c

def wipe(c):
    for ch in list(c.children):
        wipe(ch); bpy.data.collections.remove(ch)
    for o in list(c.objects):
        me = o.data if o.type == 'MESH' else None
        bpy.data.objects.remove(o)
        if me and me.users == 0:
            bpy.data.meshes.remove(me)

ref = coll('AK reference (game)')
wipe(ref)
pts = coll('Attachment points', ref)
root = bpy.data.objects.new('AKMN_root', None)
root.empty_display_type = 'ARROWS'; root.empty_display_size = 0.05
ref.objects.link(root)

def mat(name, rgb, rough=0.5, metal=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    m.diffuse_color = (*rgb, 1)
    return m
M_steel = mat('AK steel', (0.18, 0.19, 0.20), 0.4, 0.8)
M_wood = mat('AK wood', (0.45, 0.22, 0.08), 0.6)
M_bake = mat('AK bakelite', (0.35, 0.10, 0.05), 0.4)
M_move = mat('AK vanilla moving part (keep)', (0.85, 0.45, 0.05), 0.5)
MOVING = ('trigger_LOD0', 'bolt_LOD0', 'release_LOD0', 'selector_LOD0', 'hammer_LOD0')

for o in D['objects']:
    part = o['part']
    c = coll('AK_moving_parts (stay vanilla)', ref) if (part == 'receiver' and o['name'] in MOVING) else coll('AK_' + part, ref)
    me = bpy.data.meshes.new(o['mesh'])
    me.from_pydata([tuple(v) for v in o['verts']], [], [tuple(f) for f in o['faces']])
    uv = me.uv_layers.new(name='UVMap')
    li = 0
    for f, fu in zip(o['faces'], o['face_uvs']):
        for k in fu:
            if k >= 0:
                uv.data[li].uv = o['uvs'][k]
            li += 1
    me.validate(); me.update()
    try:
        me.set_sharp_from_angle(angle=0.6)
    except Exception:
        pass
    ob = bpy.data.objects.new('AK_' + part + '__' + o['name'], me)
    c.objects.link(ob)
    ob.parent = root
    ob.matrix_basis = Matrix(o['matrix'])
    ob['ak_part'] = part; ob['ak_mesh'] = o['mesh']
    me.materials.append(M_move if o['name'] in MOVING else M_wood if part in ('handguard', 'stock')
                        else M_bake if part in ('pistol_grip', 'magazine') else M_steel)
    ob.hide_select = True          # reference only: can't be grabbed by accident

for p in D['points']:
    e = bpy.data.objects.new('pt_' + p['part'] + '__' + p['name'], None)
    e.empty_display_type = 'ARROWS' if p['name'] in ('aim_camera', 'fireport') else 'PLAIN_AXES'
    e.empty_display_size = 0.015
    pts.objects.link(e); e.parent = root; e.matrix_basis = Matrix(p['matrix'])
    e.hide_select = True
bpy.context.view_layer.update()
print('reference rebuilt:', len(D['objects']), 'meshes,', len(D['points']), 'points')
