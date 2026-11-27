# Seam-based UVs for every RK part (replaces the smart-project layout of rk_uv.py for texturing).
#  1. seams only on real creases (dihedral > SEAM_DEG)
#  2. tube-like islands (two or more big boundary loops) get ONE cut along their hidden side, so they unroll into straight strips
#  3. angle-based unwrap; small holes are virtually filled
#  4. islands that still stretch badly, or are closed (no boundary), fall back to a planar projection of just those faces
#  5. straighten, equal texel density, tight packing
# Run in Blender after the models are final:  exec(open('.../rk_uv2.py').read());  rk_uv2(names or None)
import bpy, bmesh, math, heapq
from mathutils import Vector
from collections import defaultdict

SEAM_DEG = 40
HIDDEN = {'RK_handguard_cheesegrater_model': (0, 0, 1)}          # side to hide the tube seam on (default underneath)

def _islands(bm):
    parent = list(range(len(bm.faces)))
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for e in bm.edges:
        if e.seam or len(e.link_faces) != 2: continue
        a, b = find(e.link_faces[0].index), find(e.link_faces[1].index)
        if a != b: parent[a] = b
    groups = defaultdict(list)
    for f in bm.faces: groups[find(f.index)].append(f)
    return list(groups.values())

def _loops(faces):
    fs = set(faces); bedges = []
    for f in faces:
        for e in f.edges:
            inside = sum(1 for g in e.link_faces if g in fs)
            if inside == 1 or e.seam: bedges.append(e)
    bedges = list(set(bedges))
    adj = defaultdict(list)
    for e in bedges:
        for v in e.verts: adj[v].append(e)
    seen, loops = set(), []
    for e in bedges:
        if e in seen: continue
        st, comp = [e], []; seen.add(e)
        while st:
            x = st.pop(); comp.append(x)
            for v in x.verts:
                for y in adj[v]:
                    if y not in seen: seen.add(y); st.append(y)
        loops.append(comp)
    return loops

def _cut_tubes(bm, faces, hide):
    hide = Vector(hide)
    for _ in range(8):
        loops = _loops(faces)
        if len(loops) < 2: return
        lens = [sum(e.calc_length() for e in l) for l in loops]
        big = [l for l, L in sorted(zip(loops, lens), key=lambda t: -t[1]) if L > 0.3 * max(lens)]
        if len(big) < 2:
            _cut_cup(faces, big[0], max(lens), hide); return
        if len(big) > 2 and _ == 0: return 'frame'                                   # a frame of bevel strips round a box: no good unwrap, project it flat
        fs = set(faces)
        verts = {v for f in faces for v in f.verts}
        hs = [v.co.dot(hide) for v in verts]; lo, hi = min(hs), max(hs); span = max(hi - lo, 1e-6)
        src = {v for e in big[0] for v in e.verts}; dst = {v for e in big[1] for v in e.verts}
        dist = {v: 0.0 for v in src}; prev = {}; pq = [(0.0, id(v), v) for v in src]; heapq.heapify(pq); end = None
        while pq:
            d, _, v = heapq.heappop(pq)
            if d > dist.get(v, 1e9): continue
            if v in dst: end = v; break
            for e in v.link_edges:
                if not any(g in fs for g in e.link_faces): continue
                w = e.other_vert(v)
                cost = e.calc_length() * (1 + 6 * (hi - w.co.dot(hide)) / span)   # strongly prefer the hidden side
                nd = d + cost
                if nd < dist.get(w, 1e9): dist[w] = nd; prev[w] = (v, e); heapq.heappush(pq, (nd, id(w), w))
        if end is None: return
        v = end
        while v in prev: u, e = prev[v]; e.seam = True; v = u

def _dijkstra(fs, src, cost):
    dist = {v: 0.0 for v in src}; prev = {}; pq = [(0.0, id(v), v) for v in src]; heapq.heapify(pq)
    while pq:
        d, _, v = heapq.heappop(pq)
        if d > dist.get(v, 1e9): continue
        for e in v.link_edges:
            if not any(g in fs for g in e.link_faces): continue
            w = e.other_vert(v); nd = d + cost(e, w)
            if nd < dist.get(w, 1e9): dist[w] = nd; prev[w] = (v, e); heapq.heappush(pq, (nd, id(w), w))
    return dist, prev

def _cut_cup(faces, loop, perimeter, hide):
    """A deep pocket closed at one end (one boundary loop) would unwrap as a star: slit it from the opening to the far end."""
    fs = set(faces); src = {v for e in loop for v in e.verts}
    dist, _ = _dijkstra(fs, src, lambda e, w: e.calc_length())
    far = max(dist, key=dist.get)
    if dist[far] < 0.5 * perimeter: return                                         # shallow (a cap, a flat face): fine as it is
    verts = {v for f in faces for v in f.verts}
    hs = [v.co.dot(hide) for v in verts]; hi = max(hs); span = max(hi - min(hs), 1e-6)
    _, prev = _dijkstra(fs, src, lambda e, w: e.calc_length() * (1 + 6 * (hi - w.co.dot(hide)) / span))
    v = far
    while v in prev: u, e = prev[v]; e.seam = True; v = u

def _stretch(bm, faces, uvl):
    def uva(f):
        us = [l[uvl].uv for l in f.loops]
        return sum(us[i].x * us[(i + 1) % len(us)].y - us[(i + 1) % len(us)].x * us[i].y for i in range(len(us))) / 2
    a3 = sum(f.calc_area() for f in faces) or 1e-12
    a2 = sum(abs(uva(f)) for f in faces) or 1e-12
    m = a2 / a3; bad = 0.0; flipped = 0
    sign = 1 if sum(uva(f) for f in faces) >= 0 else -1
    for f in faces:
        A = f.calc_area()
        if A < 1e-12: continue
        r = abs(uva(f)) / A / m
        if r < 0.55 or r > 1.8: bad += A
        if uva(f) * sign < 0: flipped += 1
    return bad / a3, flipped

AXIAL = {'RK62M_suppressor_model', 'RK62M_flash_hider_model', 'RK62M_handguard_model', 'RK_handguard_plastic_model', 'RK_handguard_cheesegrater_model', 'RK_gas_tube_model', 'RK_flash_hider_model',
         'RK62M_side_rail_model', 'RK_receiver_model', 'RK_top_cover_model', 'RK62M_top_cover_model'}      # long along Y: end faces get their own islands
STD = ['RK_receiver_model', 'RK_gas_tube_model', 'RK_top_cover_model', 'RK_handguard_cheesegrater_model', 'RK_pistol_grip_model', 'RK_stock_model',
       'RK_waffle_mag_model', 'RK_flash_hider_model', 'RK_bolt_vanilla', 'RK_trigger_vanilla', 'RK_hammer_vanilla', 'RK_release_vanilla', 'RK_selector_vanilla']
def _config(name):                                                                # which parts sit around this one on the finished rifle
    c = list(STD)
    if name == 'RK_handguard_plastic_model': c[c.index('RK_handguard_cheesegrater_model')] = name
    if name == 'RK_bicycle_grip_model': c[c.index('RK_pistol_grip_model')] = name
    if name == 'RK62M_suppressor_model': c.append('RK62M_flash_hider_model')
    if name == 'RK62M_flash_hider_model': c[c.index('RK_flash_hider_model')] = name
    if name.startswith('RK62M'):
        c[c.index('RK_top_cover_model')] = 'RK62M_top_cover_model'; c[c.index('RK_handguard_cheesegrater_model')] = 'RK62M_handguard_model'
        c.append('RK62M_side_rail_model')
    if name not in c: c.append(name)
    return c

_bvh = {}
def _scene_tree(names):
    from mathutils.bvhtree import BVHTree
    key = tuple(sorted(names))
    if key not in _bvh:
        bm = bmesh.new()
        for n in key:
            o = bpy.data.objects.get(n)
            if not o: continue
            me = o.data.copy(); me.transform(o.matrix_world); bm.from_mesh(me); bpy.data.meshes.remove(me)
        _bvh[key] = BVHTree.FromBMesh(bm); bm.free()
    return _bvh[key]

def _dirs(n):
    t = n.orthogonal().normalized(); b = n.cross(t)
    out = [n]
    for el, k in ((math.radians(55), 6), (math.radians(25), 6)):
        for j in range(k):
            a = 2 * math.pi * (j + 0.5 * (el < 0.5)) / k
            out.append((n * math.sin(el) + (t * math.cos(a) + b * math.sin(a)) * math.cos(el)).normalized())
    return out

def _openness(ob, bm):
    tree = _scene_tree(_config(ob.name))
    M = ob.matrix_world; R = M.to_3x3().inverted().transposed()
    op = {}
    for f in bm.faces:
        n = (R @ f.normal).normalized(); c = M @ f.calc_center_median() + n * 0.0002; free = 0; ds = _dirs(n)
        for d in ds:
            if tree.ray_cast(c, d, 0.4)[0] is None: free += 1
        op[f.index] = free / len(ds)
    return op

def _uv_groups(bm, uvl):
    parent = {f.index: f.index for f in bm.faces}
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for e in bm.edges:
        if len(e.link_faces) != 2: continue
        f0, f1 = e.link_faces
        a = {l.vert: l[uvl].uv for l in f0.loops if l.vert in e.verts}; b = {l.vert: l[uvl].uv for l in f1.loops if l.vert in e.verts}
        if all((a[k] - b[k]).length < 1e-5 for k in a): parent[find(f0.index)] = find(f1.index)
    g = defaultdict(list)
    for f in bm.faces: g[find(f.index)].append(f)
    return list(g.values())

def _uva(f, uvl):
    us = [l[uvl].uv for l in f.loops]
    return abs(sum(us[i].x * us[(i + 1) % len(us)].y - us[(i + 1) % len(us)].x * us[i].y for i in range(len(us)))) / 2

def rk_uv2(names=None, verbose=True, hidden_scale=0.3):
    _bvh.clear()
    top = bpy.data.collections['RK62 parts (your models)']
    objs = [o for c in top.children for o in c.objects if o.type == 'MESH' and (names is None or o.name in names)]
    if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    report = []
    for ob in objs:
        for o in bpy.context.view_layer.objects: o.select_set(False)
        bpy.context.view_layer.objects.active = ob; ob.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(ob.data); bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()
        axial = ob.name in AXIAL
        for e in bm.edges:
            if len(e.link_faces) != 2: e.seam = False; continue
            f0, f1 = e.link_faces
            e.seam = e.calc_face_angle(0) > math.radians(SEAM_DEG) or (axial and (abs(f0.normal.y) > 0.8) != (abs(f1.normal.y) > 0.8))
        hide = HIDDEN.get(ob.name, (0, 0, -1))
        closed = []
        for faces in _islands(bm):
            if not _loops(faces): closed.append(faces); continue
            if _cut_tubes(bm, faces, hide) == 'frame': closed.append(faces)
        bmesh.update_edit_mesh(ob.data)
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.unwrap(method='ANGLE_BASED', fill_holes=True, correct_aspect=True, margin=0.001)
        # planar projection where the unwrap failed: closed islands, stretched or flipped ones, and collapsed ones (density far off the rest)
        bm = bmesh.from_edit_mesh(ob.data); bm.faces.ensure_lookup_table(); uvl = bm.loops.layers.uv.active
        fallback = set(f.index for faces in closed for f in faces)
        isl = _islands(bm); dens = []
        for faces in isl:
            a3 = sum(f.calc_area() for f in faces); a2 = sum(_uva(f, uvl) for f in faces)
            dens.append((a2 / a3 if a3 > 1e-12 else 1.0, a3))
        tot = sum(a for _, a in dens); acc = 0; med = 1.0
        for d, a in sorted(dens):
            acc += a
            if acc >= tot / 2: med = d; break
        for faces, (d, a) in zip(isl, dens):
            s, fl = _stretch(bm, faces, uvl)
            if s > 0.08 or fl > 0 or d < 0.3 * med or d > 3.0 * med: fallback |= {f.index for f in faces}
        if fallback:
            for f in bm.faces: f.select = f.index in fallback
            bmesh.update_edit_mesh(ob.data)
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.002, area_weight=0.0, scale_to_bounds=False)
        # zero-area sliver faces (left by boolean cuts) would be blown up to the whole sheet by the density step: fold them onto a neighbour
        bm = bmesh.from_edit_mesh(ob.data); bm.faces.ensure_lookup_table(); uvl = bm.loops.layers.uv.active
        degen = {f for f in bm.faces if f.calc_area() < 1e-10}
        for f in degen:                                                           # take ALL its uvs from ONE real neighbour, so it can't tie two islands together
            nb = next((g for e in f.edges for g in e.link_faces if g not in degen), None) or \
                 next((g for v in f.verts for g in v.link_faces if g not in degen), None)
            if nb is None:
                for l in f.loops: l[uvl].uv = f.loops[0][uvl].uv.copy()
                continue
            ref = {l.vert: l[uvl].uv for l in nb.loops}
            for l in f.loops:
                src = ref.get(l.vert) or min(nb.loops, key=lambda k: (k.vert.co - l.vert.co).length)[uvl].uv
                l[uvl].uv = src.copy()
        bmesh.update_edit_mesh(ob.data)
        bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.select_all(action='SELECT')
        try: bpy.ops.uv.align_rotation(method='AUTO')
        except Exception as ex: print('align skipped', ex)
        bpy.ops.uv.average_islands_scale()
        # hidden surfaces (inside the receiver, bore, spring, inner walls, bases of rivets) get less texture
        bm = bmesh.from_edit_mesh(ob.data); bm.faces.ensure_lookup_table(); uvl = bm.loops.layers.uv.active
        op = _openness(ob, bm)
        for faces in _uv_groups(bm, uvl):
            A = sum(f.calc_area() for f in faces) or 1e-12
            o = sum(op[f.index] * f.calc_area() for f in faces) / A
            k = hidden_scale + (1 - hidden_scale) * min(1.0, o / 0.35)
            if k > 0.999: continue
            us = [l[uvl] for f in faces for l in f.loops]
            cx = sum(u.uv.x for u in us) / len(us); cy = sum(u.uv.y for u in us) / len(us)
            for u in us: u.uv.x = cx + (u.uv.x - cx) * k; u.uv.y = cy + (u.uv.y - cy) * k
        bmesh.update_edit_mesh(ob.data)
        try: bpy.ops.uv.pack_islands(rotate=True, rotate_method='AXIS_ALIGNED', margin_method='FRACTION', margin=0.004, shape_method='CONCAVE')   # straight, pixel-aligned islands
        except TypeError: bpy.ops.uv.pack_islands(rotate=True, margin=0.004)
        bpy.ops.object.mode_set(mode='OBJECT')
        bm = bmesh.new(); bm.from_mesh(ob.data); bm.faces.ensure_lookup_table(); uvl = bm.loops.layers.uv.active
        n_isl = len(_uv_groups(bm, uvl)); cov = sum(_uva(f, uvl) for f in bm.faces); area = sum(f.calc_area() for f in bm.faces)
        vis = sum(_uva(f, uvl) for f in bm.faces if op.get(f.index, 1) > 0.35)
        st = 0.0
        for faces in _uv_groups(bm, uvl): st += _stretch(bm, faces, uvl)[0] * sum(f.calc_area() for f in faces)
        st /= max(area, 1e-12)
        report.append((ob.name, n_isl, cov, area, len(fallback) / max(len(bm.faces), 1), vis, st, 2048 * math.sqrt(vis / max(sum(f.calc_area() for f in bm.faces if op.get(f.index, 1) > 0.35) * 1e6, 1e-12))))
        bm.free(); ob.select_set(False)
    if verbose:
        for r in report: print('%-34s islands %5d  coverage %3.0f%% (visible %3.0f%%)  stretched %4.1f%%  visible px/mm at 2048: %4.1f' % (r[0], r[1], r[2] * 100, r[5] * 100, r[6] * 100, r[7]))
    return report

def _uv_islands(bm, uvl):
    parent = {f.index: f.index for f in bm.faces}
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for e in bm.edges:
        if len(e.link_faces) != 2: continue
        f0, f1 = e.link_faces
        a = {l.vert: l[uvl].uv for l in f0.loops if l.vert in e.verts}; b = {l.vert: l[uvl].uv for l in f1.loops if l.vert in e.verts}
        if all((a[k] - b[k]).length < 1e-5 for k in a): parent[find(f0.index)] = find(f1.index)
    return {find(i) for i in parent}

def _uv_cover(bm, uvl):
    t = 0.0
    for f in bm.faces:
        us = [l[uvl].uv for l in f.loops]
        t += abs(sum(us[i].x * us[(i + 1) % len(us)].y - us[(i + 1) % len(us)].x * us[i].y for i in range(len(us)))) / 2
    return t
