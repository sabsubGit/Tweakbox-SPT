# Modelling helpers for the RK 62 parts. Run inside Blender (exec). World axes of the reference scene:
# barrel = +Y (bore axis at x=0, z=0), top = +Z, right side = +X. Units: metres.
import bpy, bmesh, math
from mathutils import Vector

def _obj(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob

def box(x0, x1, y0, y1, z0, z1):
    v = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return _obj('box', v, f)

def prism_x(profile, x0, x1):
    """Polygon given as (y, z) points, extruded along X."""
    n = len(profile)
    v = [(x0, y, z) for y, z in profile] + [(x1, y, z) for y, z in profile]
    f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    f += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return _obj('prism', v, f)

def lathe_y(profile, seg=32, x=0.0, z=0.0, a0=0.0, a1=2 * math.pi):
    """Revolve (y, r) points around an axis parallel to Y. Closed ends where the profile is open."""
    full = abs(a1 - a0 - 2 * math.pi) < 1e-6
    steps = seg if full else seg + 1
    v, f = [], []
    for y, r in profile:
        for i in range(steps):
            a = a0 + (a1 - a0) * i / seg
            v.append((x + r * math.cos(a), y, z + r * math.sin(a)))
    for j in range(len(profile) - 1):
        for i in range(seg if full else seg):
            i2 = (i + 1) % steps
            if not full and i == seg: continue
            f.append((j * steps + i, j * steps + i2, (j + 1) * steps + i2, (j + 1) * steps + i))
    if full:
        f.append(tuple(range(steps)))
        f.append(tuple(range((len(profile) - 1) * steps, len(profile) * steps)))
    return _obj('lathe', v, f)

def cyl_y(r, y0, y1, x=0.0, z=0.0, seg=32):
    return lathe_y([(y0, r), (y1, r)], seg, x, z)

def _rot(ob, axis):
    # lathe is built around Y; remap vertices so the axis becomes X or Z
    for vert in ob.data.vertices:
        x, y, z = vert.co
        vert.co = (y, x, z) if axis == 'X' else (x, z, y)
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(ob.data); bm.free()
    return ob

def cyl_x(r, x0, x1, y=0.0, z=0.0, seg=24):
    return _rot(lathe_y([(x0, r), (x1, r)], seg, y, z), 'X')

def cyl_z(r, z0, z1, x=0.0, y=0.0, seg=24):
    return _rot(lathe_y([(z0, r), (z1, r)], seg, x, y), 'Z')

def strip_x(path, t, x0, x1):
    """A bent strip: (y, z) centre line, thickness t, extruded along X."""
    L, Rr = [], []
    for i, (y, z) in enumerate(path):
        a = Vector(path[max(i - 1, 0)]); b = Vector(path[min(i + 1, len(path) - 1)])
        d = (b - a).normalized(); nrm = Vector((-d.y, d.x)) * t / 2
        L.append((y + nrm.x, z + nrm.y)); Rr.append((y - nrm.x, z - nrm.y))
    return prism_x(L + Rr[::-1], x0, x1)

def _bool(a, b, op):
    m = a.modifiers.new('b', 'BOOLEAN'); m.operation = op; m.object = b; m.solver = 'EXACT'
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(a.evaluated_get(dg))
    old = a.data; a.modifiers.clear(); a.data = me
    bpy.data.meshes.remove(old)
    od = b.data; bpy.data.objects.remove(b); bpy.data.meshes.remove(od)
    return a

def union(a, *rest):
    for b in rest: a = _bool(a, b, 'UNION')
    return a

def diff(a, *rest):
    for b in rest: a = _bool(a, b, 'DIFFERENCE')
    return a

def mirror_x(make):
    """make(sign) -> object, for sign +1 and -1; returns both."""
    return [make(1), make(-1)]

def finish(ob, name, coll_name, mat_rgb=(0.5, 0.5, 0.52), sharp=35, dissolve=True, weighted=True):
    """Name it, move it into its RK collection (replacing an older version), shade it."""
    c = bpy.data.collections[coll_name]
    for o in list(c.objects):
        if o.name.split('.')[0] == name:
            d = o.data; bpy.data.objects.remove(o); bpy.data.meshes.remove(d)
    for cc in list(ob.users_collection): cc.objects.unlink(ob)
    c.objects.link(ob); ob.name = name; ob.data.name = name
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    if dissolve: bmesh.ops.dissolve_limit(bm, angle_limit=0.0005, verts=bm.verts, edges=bm.edges)   # off for turned parts: it would merge the rings densify() adds
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data); bm.free()
    for p in ob.data.polygons: p.use_smooth = True
    try: ob.data.set_sharp_from_angle(angle=math.radians(sharp))
    except Exception: pass
    # face-weighted normals: flat faces shade flat, only the bevels carry the rounding (kills ngon shading smears)
    try:
        if not weighted: raise RuntimeError('off for curved, lofted parts (it bands their facets)')
        wn = ob.modifiers.new('wn', 'WEIGHTED_NORMAL'); wn.keep_sharp = True; wn.weight = 100
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg)); old = ob.data
        ob.modifiers.clear(); ob.data = me; bpy.data.meshes.remove(old); ob.data.name = name
    except Exception as e:
        if weighted: print('weighted normals skipped:', e)
    m = bpy.data.materials.get('RK ' + name) or bpy.data.materials.new('RK ' + name)
    m.diffuse_color = (*mat_rgb, 1); ob.data.materials.clear(); ob.data.materials.append(m)
    print(name, len(ob.data.vertices), 'verts', len(ob.data.polygons), 'faces')
    return ob

def prism_y(profile, y0, y1):
    """Polygon given as (x, z) points, extruded along Y."""
    n = len(profile)
    v = [(x, y0, z) for x, z in profile] + [(x, y1, z) for x, z in profile]
    f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    f += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return _obj('prism', v, f)

def arch(hw, z0, zs, zt, n=10, inset=0.0):
    """Cover cross-section: straight sides from z0 to zs, elliptical top up to zt."""
    hw -= inset; zt -= inset
    pts = [(hw, z0)]
    for i in range(n + 1):
        a = math.pi * i / n
        pts.append((hw * math.cos(a), zs + (zt - zs) * math.sin(a)))
    pts.append((-hw, z0))
    return pts

def loft_y(sections, seg=28, power=2.6):
    """Rings along Y. sections: (y, centre z, half width, half height). Superellipse cross-section."""
    v, f = [], []
    for y, cz, rx, rz in sections:
        for i in range(seg):
            a = 2 * math.pi * i / seg
            c, s = math.cos(a), math.sin(a)
            v.append((rx * math.copysign(abs(c) ** (2 / power), c), y, cz + rz * math.copysign(abs(s) ** (2 / power), s)))
    for j in range(len(sections) - 1):
        for i in range(seg):
            f.append((j * seg + i, j * seg + (i + 1) % seg, (j + 1) * seg + (i + 1) % seg, (j + 1) * seg + i))
    f.append(tuple(range(seg))); f.append(tuple(range((len(sections) - 1) * seg, len(sections) * seg)))
    return _obj('loft', v, f)

def arc_loft(C, R, t0, t1, d0, d1, hx, steps=None):
    """Curved bar in the YZ plane (magazine). Centre C=(y,z), radius R, angles in degrees measured down from
    horizontal; d = offset towards the centre (front of the magazine), hx = half width."""
    steps = steps or max(1, int(abs(t1 - t0) / 2.5))
    v, f = [], []
    for k in range(steps + 1):
        t = math.radians(t0 + (t1 - t0) * k / steps)
        for d, x in ((d0, -hx), (d1, -hx), (d1, hx), (d0, hx)):
            r = R - d
            v.append((x, C[0] - r * math.cos(t), C[1] - r * math.sin(t)))
    for k in range(steps):
        for i in range(4):
            f.append((k * 4 + i, k * 4 + (i + 1) % 4, (k + 1) * 4 + (i + 1) % 4, (k + 1) * 4 + i))
    f.append((0, 1, 2, 3)); f.append(tuple(steps * 4 + i for i in (3, 2, 1, 0)))
    return _obj('arc', v, f)

def rot_y(ob, deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    for vert in ob.data.vertices:
        x, y, z = vert.co
        vert.co = (c * x + s * z, y, -s * x + c * z)
    return ob

def bevel(ob, width, seg=2, angle=30):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(angle)]
    bmesh.ops.bevel(bm, geom=edges, offset=width, segments=seg, profile=0.5, affect='EDGES', clamp_overlap=True)
    bm.to_mesh(ob.data); bm.free()
    return ob

from mathutils import Matrix
def xform(ob, M):
    ob.data.transform(M)
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(ob.data); bm.free()
    return ob

def cyl_between(p0, p1, r, seg=20):
    """Round rod between two world points."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    ob = cyl_y(r, 0.0, d.length, seg=seg)
    return xform(ob, Matrix.Translation(p0) @ Vector((0, 1, 0)).rotation_difference(d.normalized()).to_matrix().to_4x4())

def lathe_axis(profile, origin, direction, seg=32):
    """Lathe whose axis starts at origin and points along direction; profile = (distance along axis, radius)."""
    ob = lathe_y(profile, seg)
    return xform(ob, Matrix.Translation(Vector(origin)) @ Vector((0, 1, 0)).rotation_difference(Vector(direction).normalized()).to_matrix().to_4x4())

def round_top(y0, y1, z0, z1, n=8):
    """(y, z) outline of a plate with a semicircular top, for prism_x."""
    r = (y1 - y0) / 2; cy = (y0 + y1) / 2
    pts = [(y1, z0)]
    for i in range(n + 1):
        a = math.pi * i / n
        pts.append((cy + r * math.cos(a), z1 - r + r * math.sin(a)))
    pts.append((y0, z0))
    return pts[::-1]

def rrect(y0, y1, z0, z1, r, n=6):
    """(y, z) outline of a rounded rectangle, for prism_x / cutters."""
    r = min(r, (y1 - y0) / 2, (z1 - z0) / 2)
    pts = []
    for cy, cz, a0 in ((y1 - r, z0 + r, -90), (y1 - r, z1 - r, 0), (y0 + r, z1 - r, 90), (y0 + r, z0 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cy + r * math.cos(a), cz + r * math.sin(a)))
    return pts

def dome(r, origin, direction, h=0.0011, seg=20):
    """Low domed pin / rivet head sitting on a surface at origin, bulging along direction."""
    prof = [(-0.0006, r), (h * 0.25, r), (h * 0.55, r * 0.86), (h * 0.85, r * 0.55), (h, r * 0.15)]
    return lathe_axis(prof, origin, direction, seg)

def screw_head(r, origin, direction, h=0.0016, seg=24):
    """Slotted screw head."""
    d = Vector(direction).normalized()
    head = lathe_axis([(-0.0006, r), (h * 0.7, r), (h, r * 0.82)], origin, direction, seg)
    o = Vector(origin) + d * h
    side = d.cross(Vector((0, 0, 1)))
    if side.length < 1e-6: side = Vector((0, 1, 0))
    side.normalize(); up = d.cross(side)
    slot = box(-r * 1.2, r * 1.2, -r * 0.14, r * 0.14, -h * 0.45, 0.001)
    M = Matrix((side, up, d)).transposed().to_4x4(); M.translation = o
    return diff(head, xform(slot, M))

def arc_bar(C, R, t0, t1, d0, d1, x0, x1, steps=None):
    """Like arc_loft but between two X planes (for one-sided steps and cuts on the magazine)."""
    steps = steps or max(1, int(abs(t1 - t0) / 2.0))
    v, f = [], []
    for k in range(steps + 1):
        t = math.radians(t0 + (t1 - t0) * k / steps)
        for d, x in ((d0, x0), (d1, x0), (d1, x1), (d0, x1)):
            r = R - d
            v.append((x, C[0] - r * math.cos(t), C[1] - r * math.sin(t)))
    for k in range(steps):
        for i in range(4):
            f.append((k * 4 + i, k * 4 + (i + 1) % 4, (k + 1) * 4 + (i + 1) % 4, (k + 1) * 4 + i))
    f.append((0, 1, 2, 3)); f.append(tuple(steps * 4 + i for i in (3, 2, 1, 0)))
    return _obj('arcbar', v, f)

def arc_rib(C, R, t_deg, stations, x_base, side):
    """Raised rib running across the magazine side (along d) at angle t. stations: (d, half width in m, height).
    Trapezoid section; height 0 at a station = the rib fades into the surface there."""
    v, f = [], []
    t = math.radians(t_deg)
    for d, w, h in stations:
        r = R - d; a = w / r
        for da, hh in ((-a, -0.0004), (-a * 0.45, h), (a * 0.45, h), (a, -0.0004)):
            x = side * (x_base + hh)
            v.append((x, C[0] - r * math.cos(t + da), C[1] - r * math.sin(t + da)))
    n = len(stations)
    for k in range(n - 1):
        for i in range(4):
            f.append((k * 4 + i, k * 4 + (i + 1) % 4, (k + 1) * 4 + (i + 1) % 4, (k + 1) * 4 + i))
    f.append((0, 1, 2, 3)); f.append(tuple((n - 1) * 4 + i for i in (3, 2, 1, 0)))
    return _obj('rib', v, f)

def arc_rib(C, R, t_deg, stations, x_base, side):
    """Rib across the magazine side at angle t. stations: (d, half width in m, height above x_base). Steep flanks (0.5 mm)."""
    v, f = [], []
    t = math.radians(t_deg)
    for d, w, h in stations:
        r = R - d; a = w / r; ai = max(w - 0.0005, w * 0.3) / r
        for da, hh in ((-a, -0.0004), (-ai, h), (ai, h), (a, -0.0004)):
            v.append((side * (x_base + hh), C[0] - r * math.cos(t + da), C[1] - r * math.sin(t + da)))
    n = len(stations)
    for k in range(n - 1):
        for i in range(4):
            f.append((k * 4 + i, k * 4 + (i + 1) % 4, (k + 1) * 4 + (i + 1) % 4, (k + 1) * 4 + i))
    f.append((0, 1, 2, 3)); f.append(tuple((n - 1) * 4 + i for i in (3, 2, 1, 0)))
    return _obj('rib', v, f)

def se_point(cz, rx, rz, power, th):
    """Point on a superellipse section (x, z) at parameter angle th (radians)."""
    c, s = math.cos(th), math.sin(th)
    return (rx * math.copysign(abs(c) ** (2 / power), c), cz + rz * math.copysign(abs(s) ** (2 / power), s))

def se_theta(cz, rz, power, z):
    """Parameter angle (first quadrant side, radians, -90..90 deg) where the section reaches height z."""
    u = max(-1.0, min(1.0, (z - cz) / rz))
    return math.copysign(math.asin(abs(u) ** (power / 2)), u)

def bead(y, cz, rx, rz, power, th0, th1, half_w=0.0011, h=0.0010, steps=28, fade=0.12):
    """Pressed bead running around a superellipse section from th0 to th1 (radians), rounded ends that fade out."""
    v, f = [], []
    for k in range(steps + 1):
        u = k / steps; th = th0 + (th1 - th0) * u
        e = min(1.0, u / fade, (1 - u) / fade); e = math.sin(e * math.pi / 2)          # rounded run-out
        x, z = se_point(cz, rx, rz, power, th)
        n = Vector((x / (rx * rx), 0, (z - cz) / (rz * rz))); n.normalize()
        w = half_w * (0.35 + 0.65 * e)
        for dy, hh in ((-w, -0.0004), (-w * 0.45, h * e), (w * 0.45, h * e), (w, -0.0004)):
            v.append((x + n.x * hh, y + dy, z + n.z * hh))
    for k in range(steps):
        for i in range(4):
            f.append((k * 4 + i, k * 4 + (i + 1) % 4, (k + 1) * 4 + (i + 1) % 4, (k + 1) * 4 + i))
    f.append((0, 1, 2, 3)); f.append(tuple(steps * 4 + i for i in (3, 2, 1, 0)))
    return _obj('bead', v, f)

def arc_rib(C, R, t_deg, stations, x_base, side):
    """Rib across the magazine side at angle t. stations: (d, half width m, top height above x_base[, base offset]).
    The optional base offset lets a rib run on over a lower (sunken) surface."""
    v, f = [], []
    t = math.radians(t_deg)
    for st in stations:
        d, w, h = st[:3]; base = st[3] if len(st) > 3 else 0.0
        r = R - d; a = w / r; ai = max(w - 0.0005, w * 0.3) / r
        for da, hh in ((-a, base - 0.0004), (-ai, h), (ai, h), (a, base - 0.0004)):
            v.append((side * (x_base + hh), C[0] - r * math.cos(t + da), C[1] - r * math.sin(t + da)))
    n = len(stations)
    for k in range(n - 1):
        for i in range(4):
            f.append((k * 4 + i, k * 4 + (i + 1) % 4, (k + 1) * 4 + (i + 1) % 4, (k + 1) * 4 + i))
    f.append((0, 1, 2, 3)); f.append(tuple((n - 1) * 4 + i for i in (3, 2, 1, 0)))
    return _obj('rib', v, f)

def bead(y, cz, rx, rz, power, th0, th1, half_w=0.0011, h=0.0010, steps=None, fade=0.0028, spacing=0.0011):
    """Pressed bead around a superellipse section from th0 to th1. Sampled evenly by LENGTH (the parameter bunches up on
    flat sides), with rounded ends that run out over `fade` metres."""
    N = 1500
    pts = [Vector(se_point(cz, rx, rz, power, th0 + (th1 - th0) * i / N)) for i in range(N + 1)]
    cum = [0.0]
    for i in range(N): cum.append(cum[-1] + (pts[i + 1] - pts[i]).length)
    L = cum[-1]; n = max(4, int(L / spacing)); v, f = [], []; j = 0
    for k in range(n + 1):
        s = L * k / n
        while j < N - 1 and cum[j + 1] < s: j += 1
        u = (s - cum[j]) / max(cum[j + 1] - cum[j], 1e-12)
        p = pts[j].lerp(pts[j + 1], u)
        tan = (pts[min(j + 1, N)] - pts[j]).normalized()
        nrm = Vector((tan.y, -tan.x))
        if nrm.dot(Vector((p.x, p.y - cz))) < 0: nrm = -nrm
        e = min(1.0, s / fade, (L - s) / fade); e = math.sin(max(e, 0.0) * math.pi / 2)
        w = half_w * (0.45 + 0.55 * e)
        for dy, hh in ((-w, -0.0004), (-w * 0.45, h * e), (w * 0.45, h * e), (w, -0.0004)):
            v.append((p.x + nrm.x * hh, y + dy, p.y + nrm.y * hh))
    for k in range(n):
        for i in range(4):
            f.append((k * 4 + i, k * 4 + (i + 1) % 4, (k + 1) * 4 + (i + 1) % 4, (k + 1) * 4 + i))
    f.append((0, 1, 2, 3)); f.append(tuple(n * 4 + i for i in (3, 2, 1, 0)))
    return _obj('bead', v, f)


def saddle(origin, axis, up, s_hug0, s_hug1, P, B, Rc, t, w, th_max, M=14, K=10, t_end=None):
    """A strap end formed around a tube: hugs the tube (radius Rc) between s_hug0 and s_hug1 along the axis, then
    opens out into a flat strap (half width w, thickness t) whose centre runs from P to B (world points)."""
    X = Vector((1, 0, 0))
    def loc(p): d = p - origin; return d.dot(axis), d.dot(up)
    sP, hP = loc(P); sB, hB = loc(B)
    st = [(s_hug0, Rc + t / 2, 0.0), (s_hug1, Rc + t / 2, 0.0)]
    for k in range(1, K + 1):
        u = k / K; f = u * u * (3 - 2 * u)
        st.append((sP + (sB - sP) * u, hP + (hB - hP) * u, f))
    v, f_ = [], []
    n = 2 * (M + 1)
    for s, hc, f in st:
        ring = []
        for side in (1, -1):
            js = range(M + 1) if side == 1 else range(M, -1, -1)
            for j in js:
                q = -1 + 2 * j / M
                r = Rc + t / 2 + side * t / 2; th = q * th_max
                ax_, ah = r * math.sin(th), r * math.cos(th) + (hc - (Rc + t / 2))
                fx, fh = q * w, hc + side * (t_end or t) / 2
                x = ax_ + (fx - ax_) * f; h = ah + (fh - ah) * f
                ring.append(origin + axis * s + up * h + X * x)
        v += [tuple(p) for p in ring]
    for k in range(len(st) - 1):
        for i in range(n):
            f_.append((k * n + i, k * n + (i + 1) % n, (k + 1) * n + (i + 1) % n, (k + 1) * n + i))
    f_.append(tuple(range(n))); f_.append(tuple(range((len(st) - 1) * n, len(st) * n)))
    return _obj('saddle', v, f_)


def strip_var(path, ts, x0, x1):
    """Like strip_x, with a thickness per path point."""
    L, Rr = [], []
    for i, (y, z) in enumerate(path):
        a = Vector(path[max(i - 1, 0)]); b = Vector(path[min(i + 1, len(path) - 1)])
        d = (b - a).normalized(); nrm = Vector((-d.y, d.x)) * ts[i] / 2
        L.append((y + nrm.x, z + nrm.y)); Rr.append((y - nrm.x, z - nrm.y))
    return prism_x(L + Rr[::-1], x0, x1)


def join(a, *rest):
    """Put closed shells into one mesh WITHOUT a boolean (they simply overlap). Never leaves holes; use it for
    many small raised details where the exact boolean gets flaky."""
    bm = bmesh.new(); bm.from_mesh(a.data)
    for b in rest:
        bm.from_mesh(b.data); d = b.data; bpy.data.objects.remove(b); bpy.data.meshes.remove(d)
    bm.to_mesh(a.data); bm.free()
    return a


def wire(pts, r, seg=14, rounds=3):
    """Round rod along a (y, z) path in the x = 0 plane; corners are rounded off (Chaikin)."""
    p = [Vector(q) for q in pts]
    for _ in range(rounds):
        q = [p[0]]
        for a, b in zip(p, p[1:]): q += [a.lerp(b, 0.25), a.lerp(b, 0.75)]
        q.append(p[-1]); p = q
    v, f = [], []
    for i, c in enumerate(p):
        d = (p[min(i + 1, len(p) - 1)] - p[max(i - 1, 0)]).normalized(); n = Vector((-d.y, d.x))
        for k in range(seg):
            a = 2 * math.pi * k / seg
            v.append((r * math.cos(a), c.x + n.x * r * math.sin(a), c.y + n.y * r * math.sin(a)))
    for i in range(len(p) - 1):
        for k in range(seg):
            f.append((i * seg + k, i * seg + (k + 1) % seg, (i + 1) * seg + (k + 1) % seg, (i + 1) * seg + k))
    f.append(tuple(range(seg))); f.append(tuple(range((len(p) - 1) * seg, len(p) * seg)))
    return _obj('wire', v, f)


def round_poly(pts, r, n=6):
    """Closed (y, z) polygon with every corner rounded off (r = one radius, or one per corner)."""
    out = []; m = len(pts)
    for i, p in enumerate(pts):
        p = Vector(p); a = Vector(pts[i - 1]); b = Vector(pts[(i + 1) % m])
        rr = r[i] if isinstance(r, (list, tuple)) else r
        rr = min(rr, (a - p).length * 0.45, (b - p).length * 0.45)
        q0 = p + (a - p).normalized() * rr; q1 = p + (b - p).normalized() * rr
        out += [tuple((1 - t) ** 2 * q0 + 2 * t * (1 - t) * p + t * t * q1) for t in [k / n for k in range(n + 1)]]
    return out


# Cross-section of the Tarkov AKM dust cover (sliced from the game mesh), narrowed 3 % and lowered 1.65 mm: upright body,
# rounded shoulder, narrower neck, domed top at COVER_TOP. The vanilla AK bolt carrier (top z 33.3) clears the inside.
COVER_TOP = 0.0357
_AKP = [(0.0180, 0.01665), (0.0173, 0.01845), (0.0163, 0.01995), (0.0152, 0.0210), (0.0127, 0.0227), (0.01215, 0.02305), (0.0110, 0.02475), (0.01065, 0.02635),
        (0.0103, 0.02815), (0.0097, 0.02955), (0.0087, 0.03095), (0.0077, 0.0321), (0.0066, 0.0331), (0.0053, 0.0339), (0.0040, 0.0345), (0.0021, 0.03505)]
def ak_cover_profile(inset=0.0, z0=0.0080):
    """Closed (x, z) outline of the cover cross-section; inset > 0 gives the inner surface."""
    i = inset
    half = [(0.0180 - i, z0)] + [(max(x - i, x * 0.5), z - i * (z - 0.0080) / 0.0277) for x, z in _AKP]
    return half + [(0.0, COVER_TOP - i)] + [(-x, z) for x, z in half[::-1]]


def bisect_keep(ob, co, no, keep_normal_side=True):
    """Cut a mesh with a plane and keep one side (the side the normal points to, or the other); the cut is capped."""
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)                      # game meshes are split along UV seams: weld first so the cut makes closed loops
    r = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6, plane_co=co, plane_no=no,
                               clear_inner=keep_normal_side, clear_outer=not keep_normal_side)
    edges = [e for e in r['geom_cut'] if isinstance(e, bmesh.types.BMEdge) and e.is_valid and len(e.link_faces) == 1]
    if edges:
        try: bmesh.ops.triangle_fill(bm, edges=edges, use_beauty=True)
        except Exception as ex: print('cap skipped:', ex)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data); bm.free()
    return ob


def ak_islands(name, keep):
    """Loose pieces of a vanilla reference mesh, in weapon space. keep(xmin, xmax, ymin, ymax, zmin, zmax, nverts) -> bool picks them."""
    src = bpy.data.objects.get(name); root = bpy.data.objects.get('AKMN_root')
    if not src or not root: print('reference', name, 'not found'); return None
    W = root.matrix_basis @ src.matrix_parent_inverse @ src.matrix_basis
    bm = bmesh.new(); bm.from_mesh(src.data); bm.transform(W)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    seen, drop = set(), []
    for v in bm.verts:
        if v.index in seen: continue
        st, comp = [v], []; seen.add(v.index)
        while st:
            a = st.pop(); comp.append(a)
            for e in a.link_edges:
                b = e.other_vert(a)
                if b.index not in seen: seen.add(b.index); st.append(b)
        xs = [q.co.x for q in comp]; ys = [q.co.y for q in comp]; zs = [q.co.z for q in comp]
        if not keep(min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), len(comp)): drop += comp
    bmesh.ops.delete(bm, geom=drop, context='VERTS')
    if W.determinant() < 0: bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new('ak_piece'); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('ak_piece', me); bpy.context.scene.collection.objects.link(ob)
    return ob


def densify(profile, step=0.004):
    """Lathe profile with extra points on long segments, so a turned part gets rings every `step` metres
    (long thin triangles bake with streaks in Painter)."""
    out = [profile[0]]
    for (y0, r0), (y1, r1) in zip(profile, profile[1:]):
        n = max(1, int(round(math.hypot(y1 - y0, r1 - r0) / step)))
        out += [(y0 + (y1 - y0) * k / n, r0 + (r1 - r0) * k / n) for k in range(1, n + 1)]
    return out
