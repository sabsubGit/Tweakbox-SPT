# Smart-UV every RK part (one 0-1 layout per part) so they are paintable. Re-run after any model change.
import bpy, math
top = bpy.data.collections['RK62 parts (your models)']
bpy.ops.object.select_all(action='DESELECT')
for c in top.children:
    for ob in c.objects:
        if ob.type != 'MESH': continue
        hidden = ob.hide_get(); 
        bpy.context.view_layer.objects.active = ob; ob.select_set(True)
        try:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004, area_weight=0.0, scale_to_bounds=False)
            bpy.ops.object.mode_set(mode='OBJECT')
            print('uv', ob.name, len(ob.data.uv_layers))
        except Exception as e:
            print('uv FAILED', ob.name, e)
            try: bpy.ops.object.mode_set(mode='OBJECT')
            except Exception: pass
        ob.select_set(False)
