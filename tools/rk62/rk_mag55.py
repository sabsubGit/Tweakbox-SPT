# Run inside Blender: exec(open('/mnt/storage/Code/Tweakbox/tools/rk62/rk_mag55.py').read())
# RK 62 "waffle" magazine, rebuild 2026-11-27 on the vanilla "AK 7.62x39 30-round magazine (issued '55 or later)".
# User: "use this as a base and redo the magazine"; the old one was too bulky (body 26.4 mm wide vs 24.2, front strip
# 23.8 vs 18.2, floor plate 67 x 32 mm, pure R 0.215 arc while the AK curves forward more at the bottom).
# The steel magazine's own mesh IS the body here, so curve, depth (58.7 mm), the narrow front strip ("the lower area",
# 3 mm lower each side), the top with its lugs and the floor plate ("the bottom is the same as the AK one") are exact:
#   1. its pressed long ribs and the shallow groove are flattened into the side panel (|x| = SIDE),
#   2. the welded seam fin on the spine is squashed into the spine (a plastic magazine has none),
#   3. the waffle goes on top: two long ribs + a raised edge at the step = three columns of squares, and cross ribs
#      that are ONE piece each from the tip on one side's front strip, along the side, round the spine and back out
#      to the tip on the other side (they used to stop at the corner - "the waffle pattern when it wraps is not
#      connected"), running out to points on the front strip,
#   4. the sling loop on the front edge.
# Needs 'ref_mag_steel55' (blender_import_mag_refs.py). The previous magazine is kept, eye-hidden, as
# RK_waffle_mag_model_old in 'Old waffle mag (before AK 55 rebuild)' with its textured material.
exec(open('/mnt/storage/Code/Tweakbox/tools/rk62/rk_lib.py').read())
import bmesh, math
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

PLASTIC = (0.06, 0.06, 0.06)
R = 0.215; C = (0.411 + R, -0.006)      # reference arc of the AK magazine well: t = degrees down the arc, d = towards C (front)
SIDE = 0.01212                           # side panel half width after flattening (the '55 sheet level between its ribs)
RH = 0.0010                              # waffle rib height
RIB_W, RIB_TOP = 0.0008, 0.00035         # rib half width at the base / at the top
SINK = 0.0004                            # rib base sunk into the surface (closed overlapping shells, no boolean)
T0, T1, ROWS = 10.0, 47.6, 13            # first / last cross rib, rows of squares between them
TIP = 0.0025                             # cross rib points stop this far behind the front face

def pt(t, d, x=0.0):
    r = R - d; a = math.radians(t)
    return Vector((x, C[0] - r * math.cos(a), C[1] - r * math.sin(a)))
def td(p):
    dy, dz = p.y - C[0], p.z - C[1]
    return math.degrees(math.atan2(-dz, -dy)), R - math.hypot(dy, dz)
def inward(t):
    a = math.radians(t); return Vector((0.0, math.cos(a), math.sin(a)))
def ray_side(bvh, t, d, s):
    h = bvh.ray_cast(pt(t, d, s * 0.06), Vector((-s, 0, 0)), 0.1)
    return abs(h[0].x) if h[0] else None
def ray_back(bvh, t, x):
    h = bvh.ray_cast(pt(t, -0.08, x), inward(t), 0.2)
    return td(h[0])[1] if h[0] else None
def ray_front(bvh, t, x):
    h = bvh.ray_cast(pt(t, 0.08, x), -inward(t), 0.2)
    return td(h[0])[1] if h[0] else None
def table(f, t0=0.0, t1=56.0, step=0.25):
    ts = [t0 + k * step for k in range(int((t1 - t0) / step) + 1)]
    vals = [f(t) for t in ts]
    def get(t):
        k = min(max(int((t - t0) / step), 0), len(ts) - 2); u = (t - ts[k]) / step
        a, b = vals[k], vals[k + 1]
        if a is None or b is None: return a if b is None else b
        return a + (b - a) * u
    return get
def step_top_of(bvh, front):
    def f(t):
        fr = front(t)
        if fr is None: return None
        d = fr - 0.022
        while d < fr - 0.006:
            x = ray_side(bvh, t, d, 1)
            if x is not None and x < 0.0120: return d
            d += 0.0001
        return None
    return f

# ---------- 0. keep the old magazine ----------
oldc = bpy.data.collections.get('Old waffle mag (before AK 55 rebuild)')
if oldc is None:
    oldc = bpy.data.collections.new('Old waffle mag (before AK 55 rebuild)'); bpy.context.scene.collection.children.link(oldc)
    old = bpy.data.objects.get('RK_waffle_mag_model')
    if old:
        for cc in list(old.users_collection): cc.objects.unlink(old)
        oldc.objects.link(old); old.name = 'RK_waffle_mag_model_old'; old.data.name = 'RK_waffle_mag_model_old'
        m_ = bpy.data.materials.get('RK RK_waffle_mag_model')
        if m_: m_.name = 'RK RK_waffle_mag_model (old textures)'
    lc = next((l for l in bpy.context.view_layer.layer_collection.children if l.collection == oldc), None)
    if lc: lc.hide_viewport = True

# ---------- 1. the '55 steel magazine in RK space ----------
root = bpy.data.objects['AKMN_root']
src = bpy.data.objects.get('ref_mag_steel55')
if src is None:
    exec(open('/mnt/storage/Code/Tweakbox/tools/rk62/blender_import_mag_refs.py').read()); src = bpy.data.objects['ref_mag_steel55']
Wm = root.matrix_basis @ src.matrix_parent_inverse @ src.matrix_basis
bm = bmesh.new(); bm.from_mesh(src.data); bm.transform(Wm)
if Wm.determinant() < 0: bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)          # weld the UV seams
bvh0 = BVHTree.FromBMesh(bm)
back5 = table(lambda t: ray_back(bvh0, t, 0.005))                    # spine beside the fin
front0 = table(lambda t: ray_front(bvh0, t, 0.0))
step0 = table(step_top_of(bvh0, front0), 7.0, 50.0)

# ---------- 2. squash the seam fin, flatten the pressed ribs ----------
fin = flat = 0
for v in bm.verts:
    t, d = td(v.co); ax = abs(v.co.x)
    if 9.05 < t < 49.3 and ax < 0.00085:
        b = ray_back(bvh0, t, 0.0025)
        if b is not None and d < b - 0.00015:
            v.co = pt(t, b, v.co.x); fin += 1; continue
    if 7.9 < t < 48.7 and ax > 0.01155:
        b, st = back5(t), step0(t)
        if b is not None and st is not None and b + 0.0016 < d < st - 0.0002:
            v.co.x = math.copysign(SIDE, v.co.x); flat += 1
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=2e-5)
bmesh.ops.dissolve_degenerate(bm, dist=2e-5, edges=bm.edges[:])
loose = [v for v in bm.verts if not v.link_faces]
bmesh.ops.delete(bm, geom=loose, context='VERTS')
open_before = sum(1 for e in bm.edges if len(e.link_faces) != 2)
# The fin's two ends could not be squashed: a blade from the rear lug down to the spine (t 8.8-10.3) and the part across
# the floor plate's stepped back (t > 48). Delete every face of the fin strip (x -0.55..0.77) that stands behind the
# surface beside it, then close the narrow footprint (n-gon, triangulated).
bvh_e = BVHTree.FromBMesh(bm)
fin_faces = []
for f in bm.faces:
    if not all(-0.00062 < v.co.x < 0.00084 for v in f.verts): continue
    t, d = td(f.calc_center_median())
    if not (t < 10.6 or t > 48.0): continue
    b = ray_back(bvh_e, t, 0.0025)
    if b is not None and d < b - 0.0002: fin_faces.append(f)
bmesh.ops.delete(bm, geom=fin_faces, context='FACES')
hole = [e for e in bm.edges if len(e.link_faces) == 1 and all(-0.00062 < v.co.x < 0.00084 for v in e.verts)
        and (lambda t: t < 10.8 or t > 47.8)(td(e.verts[0].co)[0])]
filled = bmesh.ops.holes_fill(bm, edges=hole, sides=0)['faces']
bmesh.ops.triangulate(bm, faces=filled, quad_method='BEAUTY', ngon_method='BEAUTY')
loose = [v for v in bm.verts if not v.link_faces]
bmesh.ops.delete(bm, geom=loose, context='VERTS')
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
print(f'fin verts squashed {fin}, fin end faces removed {len(fin_faces)}, holes filled {len(filled)}, rib verts flattened {flat}, '
      f'open edges {open_before} -> {sum(1 for e in bm.edges if len(e.link_faces) != 2)}')
body_me = bpy.data.meshes.new('mag55_body'); bm.to_mesh(body_me)
bvh = BVHTree.FromBMesh(bm); bm.free()
body = bpy.data.objects.new('mag55_body', body_me); bpy.context.scene.collection.objects.link(body)
back = table(lambda t: ray_back(bvh, t, 0.0), 7.0, 50.0)
front = table(lambda t: ray_front(bvh, t, 0.0), 7.0, 50.0)
step = table(step_top_of(bvh, front), 7.0, 50.0)
print('t=10/30/47.6  back', [round(back(t) * 1000, 2) for t in (10, 30, 47.6)], 'front', [round(front(t) * 1000, 2) for t in (10, 30, 47.6)],
      'step', [round(step(t) * 1000, 2) for t in (10, 30, 47.6)])

# ---------- 3. waffle ----------
def rib_mesh(name, rings):
    """rings: list of 4-vertex sections (base, top, top, base); quads between them, caps at both ends.
    Also writes 'rib_strip' UVs (metres): u = length along the rib, v = across its profile, so every rib unrolls into ONE
    straight strip. Automatic unwrapping makes the side walls into hollow U shapes (they lie flat in the cross-section)
    that waste most of the texture. The hidden underside gets no width. Faces are tagged rk_rib = 1."""
    v, f = [], []
    for r_ in rings: v += [tuple(p) for p in r_]
    n = len(rings)
    for k in range(n - 1):
        for i in range(4):
            f.append((k * 4 + i, k * 4 + (i + 1) % 4, (k + 1) * 4 + (i + 1) % 4, (k + 1) * 4 + i))
    f.append((0, 1, 2, 3)); f.append(tuple((n - 1) * 4 + i for i in (3, 2, 1, 0)))
    ob = _obj(name, v, f)
    S = [0.0]; V = []
    for k, r_ in enumerate(rings):
        if k: S.append(S[-1] + ((r_[1] + r_[2]) / 2 - (rings[k - 1][1] + rings[k - 1][2]) / 2).length)
        a = (r_[1] - r_[0]).length; b = (r_[2] - r_[1]).length; c = (r_[3] - r_[2]).length
        mid = a + b / 2; V.append([-mid, a - mid, a + b - mid, a + b + c - mid, a + b + c - mid + 0.00001])
    me = ob.data
    uv = me.uv_layers.new(name='rib_strip'); tag = me.attributes.new('rk_rib', 'INT', 'FACE')
    for p in me.polygons:
        tag.data[p.index].value = 1
        ks = {vi // 4 for vi in p.vertices}; idx = {vi % 4 for vi in p.vertices}
        if len(ks) == 1:                                                 # end cap: flat, in its own plane
            k = ks.pop(); o_ = Vector(v[k * 4]); ax = (Vector(v[k * 4 + 3]) - o_).normalized(); ay = p.normal.cross(ax)
            for li in p.loop_indices:
                q = Vector(v[me.loops[li].vertex_index]) - o_; uv.data[li].uv = (ax.dot(q) - 0.01, ay.dot(q))
            continue
        bottom = idx == {0, 3}
        for li in p.loop_indices:
            vi = me.loops[li].vertex_index; k, i = vi // 4, vi % 4
            uv.data[li].uv = (S[k], V[k][4] if (bottom and i == 0) else V[k][i])
    return ob

def simplify(path, tol, keep=()):
    """Douglas-Peucker on (x, d) points; indices in keep always stay."""
    def rec(i, j, out):
        a, b = path[i], path[j]; L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1e-12
        best, bi = -1.0, None
        for k in range(i + 1, j):
            p = path[k]
            dist = abs((b[0] - a[0]) * (a[1] - p[1]) - (a[0] - p[0]) * (b[1] - a[1])) / L
            if k in keep: dist = 1.0
            if dist > best: best, bi = dist, k
        if bi is not None and best > tol:
            rec(i, bi, out); out.append(bi); rec(bi, j, out)
    out = [0]; rec(0, len(path) - 1, out); out.append(len(path) - 1)
    return [path[i] for i in sorted(set(out))]

def cross_rib(t):
    """One rib right round the magazine at angle t: right strip tip -> right side -> spine -> left side -> left tip."""
    b, fr = back(t), front(t)
    ds = []; d = fr - TIP
    while d > b + 0.0065:
        ds.append(d); d -= 0.0003 if d > step(t) - 0.002 else 0.0010   # fine over the step and the strip
    right = [(ray_side(bvh, t, d, 1), d) for d in ds]
    Q = (0.0, b + 0.006); arc = []
    for k in range(4, 69):                                               # polar rays round the spine
        ph = math.radians(k * 2.5); dx, dd = math.cos(ph), -math.sin(ph)
        h = bvh.ray_cast(pt(t, Q[1] + dd * 0.05, Q[0] + dx * 0.05), Vector((-dx, 0, 0)) - dd * inward(t), 0.1)
        if h[0]: arc.append((h[0].x, td(h[0])[1]))
    left = [(-ray_side(bvh, t, d, -1), d) for d in reversed(ds)]
    path = []
    for p in right + arc + left:
        if p[0] is None: continue
        if not path or math.hypot(p[0] - path[-1][0], p[1] - path[-1][1]) > 0.00015: path.append(p)
    st = step(t)
    sb = st + 0.0035                                                     # bottom of the step slope: the front strip starts here
    keep = {0, len(path) - 1}
    for side_ in (1, -1):                                                # the taper starts at sb: keep a point there
        cand = [i for i, p in enumerate(path) if p[0] * side_ > 0.004]
        if cand: keep.add(min(cand, key=lambda i: abs(path[i][1] - sb)))
    path = simplify(path, 0.00002, keep)
    n = len(path); rings = []
    for i, (x, d) in enumerate(path):
        a_, c_ = path[max(i - 1, 0)], path[min(i + 1, n - 1)]
        tx, tdd = c_[0] - a_[0], c_[1] - a_[1]; L = math.hypot(tx, tdd) or 1.0
        nx, nd = -tdd / L, tx / L                                        # outward normal in the section plane
        if d > sb:                                                       # on the front strip: run out to a point
            u = min((d - sb) / max(fr - TIP - sb, 1e-6), 1.0)
            h = RH * (1.0 - 0.7 * u); wb = RIB_W * (1.0 - 0.55 * u); wt = max(RIB_TOP * (1.0 - 0.9 * u), 0.00004)
        else:
            h, wb, wt = RH, RIB_W, RIB_TOP
        bx, bd = x - nx * SINK, d - nd * SINK; ux, ud = x + nx * h, d + nd * h
        ab, at = math.degrees(wb / (R - bd)), math.degrees(wt / (R - ud))
        rings.append([pt(t - ab, bd, bx), pt(t - at, ud, ux), pt(t + at, ud, ux), pt(t + ab, bd, bx)])
    return rib_mesh('waffle_cross', rings)

def long_rib(dfun, h, wb, wt, ta, tb):
    rings = []
    for s_ in (1, -1):
        rr = []
        k = 0; n = max(2, int((tb - ta) / 1.0))
        for k in range(n + 1):
            t = ta + (tb - ta) * k / n; d = dfun(t)
            q = [((SIDE - SINK), d - wb), ((SIDE + h), d - wt), ((SIDE + h), d + wt), ((SIDE - SINK), d + wb)]
            if s_ < 0: q = q[::-1]
            rr.append([pt(t, dd, s_ * xx) for xx, dd in q])
        rings.append(rib_mesh('waffle_long', rr))
    return join(*rings)

parts = []
pitch = (T1 - T0) / ROWS
for k in range(ROWS + 1):
    parts.append(cross_rib(T0 + k * pitch))
col = lambda t: ((step(t) - 0.0007) - (back(t) + 0.0012)) / 3.0
for k in (1, 2):
    parts.append(long_rib(lambda t, k=k: back(t) + 0.0012 + col(t) * k, RH, RIB_W, RIB_TOP, T0, T1))
parts.append(long_rib(lambda t: step(t) - 0.0007, RH * 0.6, 0.0007, 0.0003, T0 - 1.5, T1 + 1.0))   # raised edge along the step

# ---------- 4. sling loop on the front edge, above the floor plate ----------
ta = 45.0; e_in = inward(ta); e_t = Vector((0.0, math.sin(math.radians(ta)), -math.cos(math.radians(ta))))
P0 = pt(ta, front(ta) + 0.0013)
outer = [(-0.0125, -0.0020), (0.0125, -0.0020), (0.0105, 0.0070), (0.0085, 0.0095), (-0.0085, 0.0095), (-0.0105, 0.0070)]
loop = diff(bevel(prism_x(outer, -0.0030, 0.0030), 0.0012, 3, 30), bevel(prism_x(rrect(-0.0078, 0.0078, 0.0012, 0.0062, 0.0020, 6), -0.01, 0.01), 0.0001, 1, 80))
M = Matrix((Vector((1, 0, 0)), e_t, e_in)).transposed().to_4x4(); M.translation = P0
parts.append(xform(loop, M))

mag = join(body, *parts)
finish(mag, 'RK_waffle_mag_model', 'RK_waffle_mag', PLASTIC, dissolve=False)

# ---------- 5. UVs: rk_uv2 for the body, the straight 'rib_strip' layout for the ribs, then one pack ----------
exec(open('/mnt/storage/Code/Tweakbox/tools/rk62/rk_show.py').read())
exec(open('/mnt/storage/Code/Tweakbox/tools/rk62/rk_uv2.py').read())
_lc = {}
def _walk(lc):
    _lc[lc.name] = lc.hide_viewport
    for c_ in lc.children: _walk(c_)
_walk(bpy.context.view_layer.layer_collection)
_ob_h = {o.name: o.hide_get() for o in bpy.context.view_layer.objects}
_c_vp = {c_.name: c_.hide_viewport for c_ in bpy.data.collections}
_o_vp = {o.name: o.hide_viewport for o in bpy.data.objects}
try:
    rk_unhide()
    rk_uv2(['RK_waffle_mag_model'], verbose=False)
finally:                                                                  # put the user's visibility back as it was
    for c_ in bpy.data.collections: c_.hide_viewport = _c_vp.get(c_.name, False)
    for o in bpy.data.objects: o.hide_viewport = _o_vp.get(o.name, False)
    def _rest(lc):
        if lc.name in _lc: lc.hide_viewport = _lc[lc.name]
        for c_ in lc.children: _rest(c_)
    _rest(bpy.context.view_layer.layer_collection)
    for o in bpy.context.view_layer.objects:
        if o.name in _ob_h: o.hide_set(_ob_h[o.name])
ob = bpy.data.objects['RK_waffle_mag_model']; me = ob.data
uvA = me.uv_layers[0]; strip = me.uv_layers['rib_strip']; tag = me.attributes['rk_rib']
def _uv_area(p, lay):
    u = [lay.data[li].uv for li in p.loop_indices]
    return abs(sum(u[i].x * u[(i + 1) % len(u)].y - u[(i + 1) % len(u)].x * u[i].y for i in range(len(u)))) / 2
ratios = sorted(math.sqrt(_uv_area(p, uvA) / p.area) for p in me.polygons if not tag.data[p.index].value and p.area > 1e-8)
k_uv = ratios[int(len(ratios) * 0.9)]                                     # visible body density (hidden islands are shrunk)
for p in me.polygons:
    if tag.data[p.index].value:
        for li in p.loop_indices: uvA.data[li].uv = strip.data[li].uv * k_uv
me.uv_layers.remove(me.uv_layers['rib_strip']); me.attributes.remove(me.attributes['rk_rib'])
me.uv_layers.active_index = 0; me.uv_layers[0].active_render = True
_act = bpy.context.view_layer.objects.active; _sel = list(bpy.context.selected_objects); _hid = ob.hide_get()
for o in _sel: o.select_set(False)
ob.hide_set(False); bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.select_all(action='SELECT')
bpy.ops.uv.pack_islands(rotate=True, rotate_method='AXIS_ALIGNED', margin_method='FRACTION', margin=0.003, shape_method='CONCAVE')
bpy.ops.object.mode_set(mode='OBJECT')
ob.select_set(False); ob.hide_set(_hid)
for o in _sel: o.select_set(True)
bpy.context.view_layer.objects.active = _act
me = ob.data; uvA = me.uv_layers[0]                                      # re-fetch: edit mode reallocated the layer
a_uv = sum(_uv_area(p, uvA) for p in me.polygons); a_3d = sum(p.area for p in me.polygons)
print(f'UV coverage {a_uv:.0%}, average {math.sqrt(a_uv / a_3d) * 2048 / 1000:.2f} px/mm at 2048')
