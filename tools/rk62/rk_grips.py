# Run inside Blender: exec(open('/mnt/storage/Code/Tweakbox/tools/rk62/rk_grips.py').read())
# RK 62 pistol grip + "bicycle" grip, rebuilt from measurements (2026-11-26, round 2 after the user's in-game look).
#  - pistol grip side outline traced row by row from research/sheet_crop_grip.png (M62/S, 6.4 px/mm; X = mm behind the
#    muzzle, Z = mm above the bore; world y = 0.893 + X/1000, z = Z/1000)
#  - bicycle grip from photos/bicycle_grip_trigger_guard.png, scaled on the 31 mm stock sleeve and the 42 mm grip block
#    (both gave 9.4 px/mm): 32.5 mm over the ribs, 80 mm long, rib pitch 2.4 mm, raked 16.7 deg, flared to the rear on top
#  - both get a real socket on top like the game's grips: a rim that wraps the receiver's grip block
#    (x +-12.5, y .261-.303, z -.037..-.031) with a pocket, the grip-bolt stud and a washer inside
exec(open('/mnt/storage/Code/Tweakbox/tools/rk62/rk_lib.py').read())
import math
from mathutils import Vector

PLASTIC = (0.06, 0.06, 0.06)
Yw = lambda X: 0.893 + X / 1000.0
RIM_TOP = -0.0316                      # 0.6 mm under the receiver bottom (-0.031): no coplanar faces
POCKET = dict(x=0.0128, y0=0.2603, y1=0.3037, r=0.0040, floor=-0.0373)   # block + 0.3 mm (corners rounder: the block's corners just sit in the grip), floor 0.3 mm under the block (-0.037)

def pchip(xs, ys):
    """Monotone cubic through (xs ascending, ys) - smooth outlines without overshoot."""
    n = len(xs); h = [xs[i + 1] - xs[i] for i in range(n - 1)]; dl = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [dl[0]] + [0.0 if dl[i - 1] * dl[i] <= 0 else 3 * (h[i - 1] + h[i]) / ((2 * h[i] + h[i - 1]) / dl[i - 1] + (h[i] + 2 * h[i - 1]) / dl[i]) for i in range(1, n - 1)] + [dl[-1]]
    def f(x):
        if x <= xs[0]: return ys[0] + m[0] * (x - xs[0])
        if x >= xs[-1]: return ys[-1] + m[-1] * (x - xs[-1])
        i = max(k for k in range(n - 1) if xs[k] <= x); t = (x - xs[i]) / h[i]
        return ((2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h[i] * m[i]
                + (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h[i] * m[i + 1])
    return f

def curve(pts):                         # pts (Z mm, value) in any order -> f(Z mm)
    pts = sorted(pts); return pchip([p[0] for p in pts], [p[1] for p in pts])

def se_ring(c, e1, e2, a_rear, a_front, b, p, N, b_front=None):
    """Superellipse ring: half width a along e1 (narrowing from a_rear to a_front towards +e2), half depth b along e2."""
    bf = b if b_front is None else b_front
    out = []
    for k in range(N):
        t = 2 * math.pi * k / N; u, v = math.cos(t), math.sin(t)
        a = a_rear + (a_front - a_rear) * (v + 1) / 2
        x = a * math.copysign(abs(u) ** (2 / p), u)
        y = (bf if v > 0 else b) * math.copysign(abs(v) ** (2 / p), v)
        out.append(c + e1 * x + e2 * y)
    return out

def se_ring_polar(c, e1, e2, a_rear, a_front, b, p, N, b_front=None):
    """Same superellipse as se_ring, but vertex k sits on the fixed ray at angle 2*pi*k/N from the centre. Rings of
    different shape then line up vertex for vertex (no sliding round the outline -> no twisted, folded quads)."""
    bf = b if b_front is None else b_front
    out = []
    for k in range(N):
        t = 2 * math.pi * k / N; u, v = math.cos(t), math.sin(t)
        a = a_rear + (a_front - a_rear) * (v + 1) / 2; bb = bf if v > 0 else b
        r = ((abs(u) / a) ** p + (abs(v) / bb) ** p) ** (-1 / p)
        out.append(c + e1 * (r * u) + e2 * (r * v))
    return out

def loft(rings, name='loft'):
    N = len(rings[0]); verts = [tuple(p) for r in rings for p in r]
    faces = [(i * N + k, i * N + (k + 1) % N, (i + 1) * N + (k + 1) % N, (i + 1) * N + k) for i in range(len(rings) - 1) for k in range(N)]
    faces += [tuple(range(N))[::-1], tuple((len(rings) - 1) * N + k for k in range(N))]
    return _obj(name, verts, faces)

def loft_uv(rings, seam_k, tube, name='loft'):
    """strip() plus a cylindrical UV on the outer tube (rings tube[0]..tube[1]): u = length round the ring from seam_k,
    v = length down the rings (groove walls included, so the ribs don't stretch). One island, seam at seam_k. All other
    faces keep zero UVs and are unwrapped separately (unwrap_rest)."""
    ob = strip(rings, name); me = ob.data; N = len(rings[0]); R = len(rings)
    v = [0.0]
    for i in range(1, R): v.append(v[-1] + sum((rings[i][k] - rings[i - 1][k]).length for k in range(N)) / N)
    U = []
    for i in range(R):
        u = [0.0]
        for j in range(N): u.append(u[-1] + (rings[i][(seam_k + j + 1) % N] - rings[i][(seam_k + j) % N]).length)
        U.append(u)
    uvl = me.uv_layers.new(name='UVMap').data
    nv = N * R
    for poly in me.polygons:
        vids = [me.loops[li].vertex_index for li in poly.loop_indices]
        if any(vi >= nv for vi in vids) or not all(tube[0] <= vi // N <= tube[1] for vi in vids):
            for li in poly.loop_indices: uvl[li].uv = (0.0, 0.0)
            continue
        js = [((vi % N) - seam_k) % N for vi in vids]
        wrap = max(js) == N - 1 and min(js) == 0
        for li, vi, j in zip(poly.loop_indices, vids, js):
            if wrap and j == 0: j = N
            uvl[li].uv = (U[vi // N][j], -v[vi // N])
    return ob

def unwrap_rest(ob, hidden=lambda c: False, hidden_scale=0.35):
    """Smart-project the faces that still have no UVs (boolean cutters), shrink islands that are hidden when the grip is
    mounted, equalise texel density and pack."""
    import bmesh as _bm
    for o in bpy.context.view_layer.objects: o.select_set(False)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bm = _bm.from_edit_mesh(ob.data); uvl = bm.loops.layers.uv.active
    for f in bm.faces: f.select = all(l[uvl].uv.length < 1e-9 for l in f.loops)
    _bm.update_edit_mesh(ob.data)
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.002, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    bm = _bm.from_edit_mesh(ob.data); uvl = bm.loops.layers.uv.active
    # shrink whole islands of hidden faces: group faces by UV connectivity
    parent = {f.index: f.index for f in bm.faces}
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for e in bm.edges:
        if len(e.link_faces) != 2: continue
        f0, f1 = e.link_faces
        a_ = {l.vert: l[uvl].uv.copy() for l in f0.loops if l.vert in e.verts}; b_ = {l.vert: l[uvl].uv.copy() for l in f1.loops if l.vert in e.verts}
        if all((a_[k] - b_[k]).length < 1e-6 for k in a_): parent[find(f0.index)] = find(f1.index)
    isl = {}
    for f in bm.faces: isl.setdefault(find(f.index), []).append(f)
    shrunk = 0
    for faces in isl.values():
        if all(hidden(ob.matrix_world @ f.calc_center_median()) for f in faces):
            ls = [l for f in faces for l in f.loops]; c = sum((l[uvl].uv for l in ls), Vector((0, 0))) / len(ls)
            for l in ls: l[uvl].uv = c + (l[uvl].uv - c) * hidden_scale
            shrunk += 1
    _bm.update_edit_mesh(ob.data)
    try: bpy.ops.uv.pack_islands(rotate=True, rotate_method='AXIS_ALIGNED', margin_method='FRACTION', margin=0.004, shape_method='CONCAVE')
    except TypeError: bpy.ops.uv.pack_islands(rotate=True, margin=0.004)
    bpy.ops.object.mode_set(mode='OBJECT'); ob.select_set(False)
    print('%s: %d UV islands, %d hidden ones shrunk' % (ob.name, len(isl), shrunk))

def prism_z(poly_xy, z0, z1):
    n = len(poly_xy)
    v = [(x, y, z0) for x, y in poly_xy] + [(x, y, z1) for x, y in poly_xy]
    f = [tuple(range(n))[::-1], tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return _obj('prism_z', v, f)

def rrect_xy(hx, y0, y1, r, n=6):
    pts = []
    for cx, cy, a0 in ((hx - r, y0 + r, -90), (hx - r, y1 - r, 0), (-hx + r, y1 - r, 90), (-hx + r, y0 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def strip(rings, name='strip'):
    """One closed surface from a sequence of rings (same vertex count): quads between neighbours, a fan to the centre of
    the first and of the last ring. No booleans, so no n-gons or slivers to spoil the shading."""
    N = len(rings[0]); verts = [tuple(p) for r in rings for p in r]
    c0 = sum(rings[0], Vector()) / N; c1 = sum(rings[-1], Vector()) / N
    verts += [tuple(c0), tuple(c1)]; i0, i1 = len(verts) - 2, len(verts) - 1
    faces = [(i * N + k, i * N + (k + 1) % N, (i + 1) * N + (k + 1) % N, (i + 1) * N + k) for i in range(len(rings) - 1) for k in range(N)]
    faces += [(i0, (k + 1) % N, k) for k in range(N)]
    last = (len(rings) - 1) * N
    faces += [(i1, last + k, last + (k + 1) % N) for k in range(N)]
    return _obj(name, verts, faces)

def sdf_rrect(x, y, hx, y0, y1, r):
    cy, hy = (y0 + y1) / 2, (y1 - y0) / 2
    qx, qy = abs(x) - (hx - r), abs(y - cy) - (hy - r)
    return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - r

def pocket_rings(rim_ring):
    """Pocket outline under each rim vertex (same ray from the pocket centre), at rim height and at the floor."""
    P = POCKET; c = Vector((0, (P['y0'] + P['y1']) / 2, 0))
    top, floor = [], []
    for v in rim_ring:
        d = Vector((v.x - c.x, v.y - c.y, 0)).normalized(); lo, hi = 0.0, 0.05
        for _ in range(50):
            m = (lo + hi) / 2; q = c + d * m
            if sdf_rrect(q.x, q.y, P['x'], P['y0'], P['y1'], P['r']) < 0: lo = m
            else: hi = m
        q = c + d * lo
        top.append(Vector((q.x, q.y, v.z))); floor.append(Vector((q.x, q.y, P['floor'])))
    return floor, top

def end_rings(last, centre, normal_in, r_bore=0.0046, depth=0.0035, mid=0.55):
    """Close a flat end inwards: a ring part way in, the counterbore edge, the counterbore wall (ends in the last ring)."""
    m = [centre + (v - centre) * mid for v in last]
    bore = [centre + (v - centre).normalized() * r_bore for v in last]
    deep = [b + normal_in * depth for b in bore]
    return [m, bore, deep]

def socket_extras(ob):
    """The grip bolt's end and its washer, standing in the pocket (separate shells, joined - no boolean)."""
    P = POCKET; yc = (P['y0'] + P['y1']) / 2
    def cyl(r, z0, z1, seg):
        ring = lambda z: [Vector((r * math.cos(2 * math.pi * k / seg), yc + r * math.sin(2 * math.pi * k / seg), z)) for k in range(seg)]
        return strip([ring(z0), ring(z1)], 'cyl')
    return join(ob, cyl(0.0043, P['floor'] - 0.0006, P['floor'] + 0.0008, 32),                       # washer
                cyl(0.0026, P['floor'] - 0.0006, -0.0342, 20))                                       # bolt end (runs on up inside the block)

def ring_sharp(ob, N, n_rings, hard, strip_angle=None, angle=40):
    """Hard edges by design, not by a threshold: whole rings in `hard` are sharp, the rest of the strip is smooth
    (or angle-based if strip_angle is given, e.g. for crisp ribs); the joined extras (screw, stud) stay angle-based.
    A threshold right at a crease's angle made it sharp at some vertices and not others -> wedge-shaped shading."""
    me = ob.data; first_extra = n_rings * N + 2
    for e in me.edges:
        a_, b_ = sorted(e.vertices); n0, n1 = me.vertices[a_].normal, me.vertices[b_].normal
        if b_ >= first_extra or a_ >= n_rings * N:
            fs = [p for p in edge_faces.get(e.index, [])]
            e.use_edge_sharp = len(fs) == 2 and me.polygons[fs[0]].normal.angle(me.polygons[fs[1]].normal) > math.radians(angle)
            continue
        ra, rb = a_ // N, b_ // N
        if ra == rb: e.use_edge_sharp = ra in hard
        elif strip_angle is not None:
            fs = edge_faces.get(e.index, [])
            e.use_edge_sharp = len(fs) == 2 and me.polygons[fs[0]].normal.angle(me.polygons[fs[1]].normal) > math.radians(strip_angle)
        else: e.use_edge_sharp = False
    if strip_angle is not None:                                   # rings in the strip: also angle-based (ribs), plus the hard ones
        for e in me.edges:
            a_, b_ = sorted(e.vertices)
            if b_ < n_rings * N and a_ // N == b_ // N and a_ // N not in hard:
                fs = edge_faces.get(e.index, [])
                e.use_edge_sharp = len(fs) == 2 and me.polygons[fs[0]].normal.angle(me.polygons[fs[1]].normal) > math.radians(strip_angle)
    me.update()

def edge_face_map(me):
    m = {}
    for p in me.polygons:
        for ek in p.edge_keys:
            m.setdefault(ek, []).append(p.index)
    return {e.index: m.get(tuple(sorted(e.vertices)), []) for e in me.edges}

def wall_check(outer_rings, min_wall=0.0006, label=''):
    """Real check, not just the rim: from points all over the pocket wall (every depth), shoot rays straight outwards at
    the grip's OUTER surface. Each must hit it from the inside, at least min_wall away. Returns the thinnest wall."""
    from mathutils.bvhtree import BVHTree
    tmp = strip(outer_rings, 'wallcheck'); tree = BVHTree.FromObject(tmp, bpy.context.evaluated_depsgraph_get())
    d_ = tmp.data; bpy.data.objects.remove(tmp); bpy.data.meshes.remove(d_)
    P = POCKET; c = Vector((0, (P['y0'] + P['y1']) / 2, 0)); thinnest, where = 1.0, None
    for x, y in rrect_xy(P['x'], P['y0'], P['y1'], P['r'], n=10):
        d = Vector((x - c.x, y - c.y, 0)).normalized()
        for i in range(8):
            z = RIM_TOP - 0.0002 + (P['floor'] - (RIM_TOP - 0.0002)) * i / 7
            hit, nrm, _, dist = tree.ray_cast(Vector((x, y, z)), d)
            w = dist if (hit is not None and nrm.dot(d) > 0) else -1.0
            if w < thinnest: thinnest, where = w, (round(x * 1000, 1), round(y * 1000, 1), round(z * 1000, 1))
    print('%s pocket wall: thinnest %.2f mm at %s' % (label, thinnest * 1000, where))
    assert thinnest >= min_wall, label + ': the pocket breaks through (or nearly) the outer wall'
    return thinnest

def pocket_fits(a, b, yc, p, margin=0.0009):
    """Every pocket outline point lies inside the rim superellipse with some wall left."""
    for x, y in rrect_xy(POCKET['x'], POCKET['y0'], POCKET['y1'], POCKET['r']):
        if (abs(x) / (a - margin)) ** p + (abs(y - yc) / (b - margin)) ** p > 1: return False
    return True

def retire_old(name, coll):
    """Keep the previous version for comparison: renamed *_old in an eye-hidden collection, with its textured material."""
    ob = bpy.data.objects.get(name)
    if not ob: return
    old = bpy.data.collections.get('Old grips (before remodel)') or bpy.data.collections.new('Old grips (before remodel)')
    if old.name not in [c.name for c in bpy.context.scene.collection.children]: bpy.context.scene.collection.children.link(old)
    if bpy.data.objects.get(name.replace('_model', '_old')): return                # the original is already kept; finish() replaces this one
    for c in list(ob.users_collection): c.objects.unlink(ob)
    old.objects.link(ob); ob.name = name.replace('_model', '_old'); ob.data.name = ob.name
    m = bpy.data.materials.get('RK ' + name)
    if m: m.name = 'RK ' + name + ' (old textures)'
    def lc_of(lc):
        if lc.collection == old: return lc
        for c in lc.children:
            f = lc_of(c)
            if f: return f
    lc = lc_of(bpy.context.view_layer.layer_collection)
    if lc: lc.hide_viewport = True                                                  # the eye, not "disable in viewports"

# ============================================================ pistol grip ============================================================
# Outline of the ISSUED grip, traced from photos/side_view_clean.jpg (0.99 px/mm on the 914 mm rifle) and checked on
# photos/rk62_right_military_sling.png: front and rear raked 22 deg, the rear straight down for its first ~16 mm, the
# front strap straight with only a small chin at the top where the trigger guard hooks in. (The gridded RIA photo is a
# civilian M62/S grip: tall vertical front strap and 19 deg rake - not this one.)
FRONT = curve([(-37, -588.1), (-40, -588.0), (-44, -586.7), (-48, -585.7), (-52, -585.7), (-56, -586.5), (-61.2, -588.6), (-73.3, -593.6), (-85.4, -598.6),
               (-97.5, -603.6), (-109.6, -608.6), (-121.8, -613.6), (-131, -617.4), (-140, -621.1)])
REAR = curve([(-36, -632.0), (-45, -632.0), (-52, -632.2), (-57, -632.8), (-62, -634.3), (-69.3, -637.0), (-81.4, -641.9), (-93.5, -646.8),
              (-105.6, -651.7), (-117.7, -656.6), (-123, -658.8), (-131, -662.0), (-140, -665.7)])
HALF_W = curve([(-36, 13.0), (-45, 13.0), (-60, 13.2), (-75, 13.7), (-90, 14.0), (-140, 14.0)])          # mm, half width at the back strap
FRONT_NARROW = 0.86                      # the front strap is a little narrower than the back
P_BODY, P_RIM = 2.7, 8.0
RIM = dict(rear=-634.5, front=-587.6, a=14.4)
Z_LEDGE, Z_FLARE, Z_ROUND = -36.6, -45.0, -52.0   # under the rim: a 0.5 mm ledge, a concave flare into the neck, corners rounding off down to -52
N = 64

def grip_section(Zmm, grow_a=0.0, grow_rear=0.0, grow_front=0.0, shrink_a=0.0):
    """(centre y, half depths, half widths, exponent) of the horizontal section at Z mm."""
    if Zmm >= -32.0:                                                               # rim (with a 0.4 mm chamfer on its top edge)
        k = 0.4 * (Zmm + 32.0) / 0.4 if Zmm > -32.0 else 0.0
        yr, yf, a, p, fn = RIM['rear'] + k, RIM['front'] - k, RIM['a'] - k, P_RIM, 1.0
    elif Zmm >= Z_LEDGE + 0.4:
        yr, yf, a, p, fn = RIM['rear'], RIM['front'], RIM['a'], P_RIM, 1.0
    else:
        yr, yf, a, p, fn = REAR(Zmm), FRONT(Zmm), HALF_W(Zmm), P_BODY, FRONT_NARROW
        if Zmm > Z_FLARE:                                                          # flare: rim ledge (rim minus 0.5 mm) easing into the neck
            t = (Z_LEDGE - Zmm) / (Z_LEDGE - Z_FLARE); e = (1 - t) ** 2
            yr += (RIM['rear'] + 0.5 - REAR(Z_LEDGE)) * e
            yf += (RIM['front'] - 0.5 - FRONT(Z_LEDGE)) * e
            a += (RIM['a'] - 0.5 - HALF_W(Z_LEDGE)) * e
        if Zmm > Z_ROUND:                                                          # corners round off gradually (over 15 mm): no twisted quads
            t = (Z_LEDGE - Zmm) / (Z_LEDGE - Z_ROUND); k_ = 1 - t * t * (3 - 2 * t)
            p = P_BODY + (P_RIM - P_BODY) * k_; fn = FRONT_NARROW + (1 - FRONT_NARROW) * k_
    yr, yf = Yw(yr) - grow_rear / 1000, Yw(yf) + grow_front / 1000
    a = (a + grow_a - shrink_a) / 1000
    return Vector((0, (yr + yf) / 2, Zmm / 1000)), (yf - yr) / 2, a, a * fn, p

def grip_loft(zs, **kw):
    rings = []
    for Z in zs:
        c, b, a_r, a_f, p = grip_section(Z, **kw)
        rings.append(se_ring(c, Vector((1, 0, 0)), Vector((0, 1, 0)), a_r, a_f, b, p, N))
    return loft(rings)

# bottom: slants down to the front, rear lip at (-658.5, -123.5), front corner at about (-617, -130.5)
B0 = Vector((0, Yw(-658.5), -0.1235)); B1 = Vector((0, Yw(-614.0), -0.1310))
t_ = (B1 - B0).normalized(); N_UP = Vector((0, -t_.z, t_.y))                      # points up into the grip
if N_UP.z < 0: N_UP = -N_UP
UP = Vector((0, 0, 1)); EX = Vector((1, 0, 0))

def centre_line(Zmm):
    return Vector((0, (Yw(FRONT(Zmm)) + Yw(REAR(Zmm))) / 2, Zmm / 1000))
def height_above_bottom(Zmm):
    return (centre_line(Zmm) - B0).dot(N_UP)
def z_at_height(d):
    lo, hi = -150.0, -90.0
    for _ in range(60):
        m = (lo + hi) / 2
        if height_above_bottom(m) > d: hi = m
        else: lo = m
    return (lo + hi) / 2

def tilted_section(C, n, grow_a=0.0, grow_rear=0.0, grow_front=0.0, shrink=0.0):
    """Section of the grip in the plane through C with normal n: walk along the plane's forward direction to the front
    and rear outline curves."""
    e2 = (Vector((0, 1, 0)) - n * n.y).normalized()
    def edge(curve_, sign):
        lo, hi = 0.0, 0.06
        for _ in range(60):
            m = (lo + hi) / 2; q = C + e2 * (sign * m)
            inside = (q.y - Yw(curve_(q.z * 1000))) * sign < 0
            if inside: lo = m
            else: hi = m
        return lo
    sf = edge(FRONT, 1) + (grow_front - shrink) / 1000; sr = edge(REAR, -1) + (grow_rear - shrink) / 1000
    c = C + e2 * ((sf - sr) / 2); b = (sf + sr) / 2
    a = (HALF_W(C.z * 1000) + grow_a - shrink) / 1000
    return se_ring_polar(c, EX, e2, a, a * FRONT_NARROW, b, P_BODY, N)

c0, b0, a0, _, _ = grip_section(-33.0)
assert pocket_fits(a0, b0, c0.y, P_RIM), 'pocket breaks through the pistol grip rim'

# 1. horizontal sections: rim, ledge, flare, body down to Z -95
zs = [RIM_TOP * 1000, -32.0, -36.2, Z_LEDGE] + [Z_LEDGE - 0.6 - 0.9 * i for i in range(10)] + [-46.0 - 1.25 * i for i in range(40)]
zs = sorted(set(round(z, 3) for z in zs if z >= -95.0), reverse=True)
outer = []
for Z in zs:
    c, b, a_r, a_f, p = grip_section(Z)
    outer.append(se_ring_polar(c, EX, Vector((0, 1, 0)), a_r, a_f, b, p, N))
# 2. sections tilting from level to the slant of the bottom
Z_T = z_at_height(0.009); n_bl = max(4, int((-95.0 - Z_T) / 1.25))
for i in range(1, n_bl + 1):
    t = i / n_bl; w = t * t * (3 - 2 * t); Zc = -95.0 + (Z_T - -95.0) * t
    outer.append(tilted_section(centre_line(Zc), (UP * (1 - w) + N_UP * w).normalized()))
# 3. sections parallel to the bottom: base band (0.7 mm proud, rear lip 1.6, front lip 1.0) and the rounded bottom edge
BAND = dict(grow_a=0.7, grow_rear=1.6, grow_front=1.0)
for d, kw in ((0.0075, {}), (0.0060, {}), (0.0049, {}), (0.00465, dict(grow_a=0.35, grow_rear=0.8, grow_front=0.5)), (0.0044, BAND),
              (0.0030, BAND), (0.0016, BAND), (0.0008, dict(BAND, shrink=0.3)), (0.0003, dict(BAND, shrink=0.8)), (0.0, dict(BAND, shrink=1.6))):
    C = centre_line(z_at_height(d)); C = C - N_UP * ((C - B0).dot(N_UP) - d)            # exactly d above the bottom plane
    outer.append(tilted_section(C, N_UP, **kw))
# consecutive rings must not cross
def plane_normal(r):                                       # Newell normal of a (planar) ring, pointing up
    n = Vector()
    for a_, b_ in zip(r, r[1:] + r[:1]): n += Vector(((a_.y - b_.y) * (a_.z + b_.z), (a_.z - b_.z) * (a_.x + b_.x), (a_.x - b_.x) * (a_.y + b_.y)))
    n.normalize(); return n if n.z > 0 else -n
def crossing(rings, report=False):
    """Smallest distance by which a ring lies below the previous ring's plane (must be > 0 everywhere)."""
    worst, at = 1.0, None
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        c0_ = sum(r0, Vector()) / len(r0); n0 = plane_normal(r0)
        m = min((c0_ - q).dot(n0) for q in r1)
        if m < worst: worst, at = m, i
    if report: print('   tightest ring pair', at, at + 1, '%.3f mm' % (worst * 1000))
    return worst
crossing(outer, report=True)
print('pistol grip: %d rings, smallest ring step %.3f mm' % (len(outer), crossing(outer) * 1000))
assert crossing(outer) > 0, 'grip rings cross'

# the bottom: flat, with the counterbored grip-bolt screw in the middle
wall_check(outer, label='pistol grip')
S_b = centre_line(z_at_height(0.0)); S_b = S_b - N_UP * (S_b - B0).dot(N_UP)
floor_r, top_r = pocket_rings(outer[0])
grip = strip([floor_r, top_r] + outer + end_rings(outer[-1], S_b, N_UP), 'pistol')
grip = join(grip, screw_head(0.0039, S_b + N_UP * 0.0035, -N_UP, h=0.0014, seg=24))
grip = socket_extras(grip)
retire_old('RK_pistol_grip_model', 'RK_pistol_grip')
finish(grip, 'RK_pistol_grip_model', 'RK_pistol_grip', PLASTIC, sharp=40, weighted=False, dissolve=False)
_g = bpy.data.objects['RK_pistol_grip_model']; edge_faces = edge_face_map(_g.data)
o_ = 2; L_ = len(outer); g3 = o_ + L_ - 10
ring_sharp(_g, N, 2 + L_ + 3, hard={0, 1, o_, o_ + 1, o_ + 2, o_ + 3, g3 + 2, g3 + 4, o_ + L_ - 1, o_ + L_ + 1, o_ + L_ + 2})
# (the checkered panel is texture only: a 0.8 mm boolean recess on this curved surface left slivers that shaded like holes)

# ============================================================ bicycle grip ============================================================
TH = math.radians(16.7)                                    # rake, measured on the photo against the (6 deg drooping) stock tube
D = Vector((0, -math.sin(TH), -math.cos(TH)))              # down the grip axis
E2_AX = Vector((0, math.cos(TH), -math.sin(TH)))           # forward, square to the axis
A0 = Vector((0, 0.2885, RIM_TOP))                          # axis at rim height: its front then meets the trigger guard 11 mm down, as in the photo
L = 0.0794                                                 # 80 mm from the receiver bottom
R_OUT, DEPTH, PITCH = 0.01625, 0.0009, 0.0024
TOP = dict(c=Vector((0, 0.2822, RIM_TOP)), a=0.0166, b=0.0240, p=4.5)            # rim footprint, wraps the grip block
S_F = 0.016                                                                       # flare length (along the axis)
assert pocket_fits(TOP['a'], TOP['b'], TOP['c'].y, TOP['p']), 'pocket breaks through the bicycle grip rim'
NB = 48

RIB = [(0.00, -0.55), (0.17, -0.05), (0.45, -0.05), (0.62, -0.55), (0.81, -1.0)]   # (phase, offset in groove depths)
# straight collar at the full rim size from the rim down to 1.2 mm under the pocket floor (the pocket must not break
# through), then the flare into the round ribbed body
Z_COL = POCKET['floor'] - 0.0012
S_C = (RIM_TOP - Z_COL) / math.cos(TH)                                              # axis distance to the collar's bottom
S_RIB0, S_RIB1 = S_C + 0.0015, 0.0752                                               # ribs between the collar and the end flange
ss = [S_C, S_C + 0.0008]
n_r = int((S_RIB1 - S_RIB0) / PITCH)
for i in range(n_r):
    ss += [S_RIB0 + (i + ph) * PITCH for ph, _ in RIB]
ss += [S_RIB0 + n_r * PITCH, 0.0765, 0.0779, 0.0788, 0.0792, L]
ss = sorted(set(round(s, 6) for s in ss))
def rib_off(s):
    if s < S_RIB0 or s > S_RIB0 + n_r * PITCH: return 0.0
    ph = ((s - S_RIB0) / PITCH) % 1.0
    best = min(RIB, key=lambda q: min(abs(q[0] - ph), 1 - abs(q[0] - ph)))
    return best[1] * DEPTH
def end_off(s):                                            # end flange 0.4 mm proud, rounded into a flat end
    table = [(0.0765, 0.0), (0.0779, 0.0004), (0.0788, 0.0004), (0.0792, -0.0003), (L, -0.0015)]
    if s < table[0][0]: return None
    for (s0, v0), (s1, v1) in zip(table, table[1:]):
        if s <= s1: return v0 + (v1 - v0) * (s - s0) / (s1 - s0)
    return table[-1][1]

EX_, EY_ = Vector((1, 0, 0)), Vector((0, 1, 0))
def collar(z, inset=0.0):
    c = Vector((0, TOP['c'].y, z))
    return se_ring_polar(c, EX_, EY_, TOP['a'] - inset, TOP['a'] - inset, TOP['b'] - inset, TOP['p'], NB)
rings = [collar(RIM_TOP, 0.0004), collar(RIM_TOP - 0.0004), collar(Z_COL + 0.0004)]   # chamfered top edge, straight collar
for s in ss:
    w_t = max(0.0, 1 - (s - S_C) / S_F); w = w_t ** 2                       # tilt eases linearly, size and offset quadratically
    n = (D * (1 - w_t) + Vector((0, 0, -1)) * w_t).normalized()
    e1 = Vector((1, 0, 0)); e2 = (Vector((0, 1, 0)) - n * n.y).normalized()
    base = A0 + D * s
    c = base + e2 * ((TOP['c'].y - base.y) * w)                               # slid back over the block's footprint at the collar
    eo = end_off(s)
    r = R_OUT + (eo if eo is not None else rib_off(s))
    a = r + (TOP['a'] - R_OUT) * w
    b = r + (TOP['b'] - R_OUT) * w
    p = 2.0 + (TOP['p'] - 2.0) * w
    rings.append(se_ring_polar(c, e1, e2, a, a, b, p, NB))
# consecutive rings must not cross (the tilting flare): each step has to move down the axis everywhere
worst = crossing(rings, report=True)
print('bicycle grip: %d rings, smallest ring step %.3f mm' % (len(rings), worst * 1000))
assert worst > 0, 'flare rings cross'
wall_check(rings, label='bicycle grip')
end_c = A0 + D * L
floor_r, top_r = pocket_rings(rings[0])
seq = [floor_r, top_r] + rings + end_rings(rings[-1], end_c, -D, r_bore=0.0050, depth=0.0030, mid=0.6)
bg = loft_uv(seq, seam_k=3 * NB // 4, tube=(2, 2 + len(rings) - 1), name='bicycle')   # UV seam straight down the back (into the palm)
bg = join(bg, screw_head(0.0042, end_c - D * 0.0030, D, h=0.0014, seg=24))
bg = socket_extras(bg)
retire_old('RK_bicycle_grip_model', 'RK_bicycle_grip')
finish(bg, 'RK_bicycle_grip_model', 'RK_bicycle_grip', PLASTIC, sharp=40, weighted=False, dissolve=False)
_b = bpy.data.objects['RK_bicycle_grip_model']; edge_faces = edge_face_map(_b.data)
Lb = len(rings)
ring_sharp(_b, NB, 2 + Lb + 3, hard={0, 1, 2, 3, 4, 5, 2 + Lb - 1, 2 + Lb + 1, 2 + Lb + 2}, strip_angle=40)

# ---------------------------------------------------------------- UVs ----------------------------------------------------------------
def in_pocket(p):                                          # hidden once the grip sits on the receiver block
    return p.z > POCKET['floor'] - 0.0008 and abs(p.x) < POCKET['x'] + 0.0002 and POCKET['y0'] - 0.0002 < p.y < POCKET['y1'] + 0.0002
for cname in ('RK_pistol_grip', 'RK_bicycle_grip'):        # unwrapping needs them visible (eye only)
    def _lc(lc):
        if lc.collection.name == cname: return lc
        for c in lc.children:
            f = _lc(c)
            if f: return f
    l_ = _lc(bpy.context.view_layer.layer_collection)
    if l_: l_.hide_viewport = False
for n in ('RK_pistol_grip_model', 'RK_bicycle_grip_model'): bpy.data.objects[n].hide_set(False)
unwrap_rest(bpy.data.objects['RK_bicycle_grip_model'], hidden=in_pocket)
exec(open('/mnt/storage/Code/Tweakbox/tools/rk62/rk_uv2.py').read().split("\nif __name__")[0])
rk_uv2(['RK_pistol_grip_model', 'RK_bicycle_grip_model'][:1])

# trigger guard check: the guard band (receiver) should just meet the grip fronts, as on the real rifle
rec = bpy.data.objects.get('RK_receiver_model')
if rec:
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    for gname in ('RK_pistol_grip_model', 'RK_bicycle_grip_model'):
        g = bpy.data.objects[gname]; bvh = BVHTree.FromObject(g, dg)
        for z in (-0.040, -0.042, -0.045):
            hit = bvh.ray_cast(Vector((0, 0.34, z)), Vector((0, -1, 0)))
            print('  %s front at z %.0f mm: y %.4f' % (gname, z * 1000, hit[0].y if hit[0] else float('nan')))
