# Run inside Blender. Uses the outliner EYE (hide), never "disable in viewports", so everything can be toggled by hand.
import bpy
def _layer(lc, name):
    if lc.collection.name == name: return lc
    for c in lc.children:
        f = _layer(c, name)
        if f: return f
def rk_show(shown=('RK_receiver', 'RK_gas_tube', 'RK_top_cover', 'RK_handguard_cheesegrater', 'RK_pistol_grip', 'RK_stock', 'RK_waffle_mag', 'RK_flash_hider'),
            hidden_objects=('AK_cover_ref',), hidden_collections=('AK reference (game)',)):
    for c in bpy.data.collections: c.hide_viewport = False                      # nothing stays disabled
    for o in bpy.data.objects: o.hide_viewport = False
    top = bpy.data.collections['RK62 parts (your models)']
    for c in top.children:
        lc = _layer(bpy.context.view_layer.layer_collection, c.name)
        if lc: lc.hide_viewport = c.name not in shown
    for n in hidden_collections:
        lc = _layer(bpy.context.view_layer.layer_collection, n)
        if lc: lc.hide_viewport = True
    for o in bpy.data.objects:
        if o.name in bpy.context.view_layer.objects: o.hide_set(o.name in hidden_objects)
def rk_unhide():                                                                 # everything visible (needed before rk_uv.py: hidden objects cannot be unwrapped)
    for c in bpy.data.collections: c.hide_viewport = False
    for o in bpy.data.objects: o.hide_viewport = False
    def walk(lc):
        lc.hide_viewport = False
        for c in lc.children: walk(c)
    walk(bpy.context.view_layer.layer_collection)
    for o in bpy.context.view_layer.objects: o.hide_set(False)
RK62 = ('RK_receiver', 'RK_gas_tube', 'RK_top_cover', 'RK_handguard_cheesegrater', 'RK_pistol_grip', 'RK_stock', 'RK_waffle_mag', 'RK_flash_hider')
RK62M = ('RK_receiver', 'RK_gas_tube', 'RK62M_top_cover', 'RK62M_handguard', 'RK62M_side_rail', 'RK_pistol_grip', 'RK_stock', 'RK_waffle_mag', 'RK62M_flash_hider')
def rk_show_m(suppressor=False):                                                  # the RK 62 M as issued (one muzzle device at a time)
    rk_show(RK62M + (('RK62M_suppressor',) if suppressor else ()))
if __name__ == '__main__': rk_show()
