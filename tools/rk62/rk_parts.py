exec(open('/mnt/storage/Code/Tweakbox/tools/rk62/rk_lib.py').read())
# All numbers come from research/RK62_research.md (y = 0.893 + X/1000, z = Z/1000).
HW = 0.0172; SL = 0.0545; GZ = 0.025; S = 64
STEEL, PLASTIC = (0.22, 0.23, 0.24), (0.06, 0.06, 0.06)

# ================= gas tube =================
gt = lathe_y([(0.4880, 0.0090), (0.4950, 0.0090), (0.4960, 0.0080), (0.6970, 0.0080)], S, z=GZ)
for y in (0.6660, 0.6750, 0.6840, 0.6920):
    gt = diff(gt, cyl_x(0.00125, -0.02, 0.02, y=y, z=GZ + 0.0050, seg=14))
finish(gt, 'RK_gas_tube_model', 'RK_gas_tube', STEEL)

# ================= top cover =================
def shell(inset, y0, y1, dy):
    s = prism_y(ak_cover_profile(inset, 0.0080 if inset == 0 else -0.01), y0, y1)                 # AK cover section, see rk_lib
    return diff(s, prism_x([(0.20, 0.0170), (0.2430 + dy, 0.0170), (0.2679 + dy, COVER_TOP), (0.2679 + dy, 0.06), (0.20, 0.06)], -0.03, 0.03))   # chamfered rear end
cover = diff(shell(0.0, 0.2430, 0.4680, 0.0), shell(0.0013, 0.2443, 0.48, 0.0022))
# outline of the vanilla selector lever in its safe (up) position, read off the reference copy made by show_vanilla_selector.py
selcut = [(0.3060, 0.0), (0.3090, 0.0030), (0.3120, 0.0048), (0.3180, 0.0100), (0.3210, 0.0120), (0.3240, 0.0134), (0.3270, 0.0141), (0.3300, 0.0144), (0.3975, 0.0144), (0.3975, 0.0)]
_sel = bpy.data.objects.get('RK_selector_vanilla')
if _sel:
    top = {}
    for e in _sel.data.edges:
        a_, b_ = (_sel.data.vertices[k].co for k in e.vertices)
        if a_.x < 0.0165 or b_.x < 0.0165: continue
        for k in range(9):
            q = a_.lerp(b_, k / 8); kk = round(q.y / 0.0015); top[kk] = max(top.get(kk, -1), q.z)
    y_lo = min(v.co.y for v in _sel.data.vertices) + 0.0200                       # skip the hub: start where the arm begins to rise
    ks = sorted(k for k in top if k * 0.0015 >= y_lo)
    selcut = [(ks[0] * 0.0015, 0.0)] + [(k * 0.0015, max(top.get(j, -1) for j in (k - 1, k, k + 1)) + 0.0004) for k in ks]
    run_ = 0.0
    for k_ in range(1, len(selcut)): run_ = max(run_, selcut[k_][1]); selcut[k_] = (selcut[k_][0], run_)   # never dips again once it has risen: one clean straight edge along the bar
    zt = run_; selcut += [(0.3905, zt), (0.3905, 0.0)]  # run the cut on into the ejection port: no sliver of skirt left between them
cover = diff(cover,
             prism_x(selcut, 0.0050, 0.03),                                                                                    # selector-shaped cut-out in the right skirt: the lever drops into it on safe
             prism_x(rrect(0.3880, 0.4655, 0.0000, 0.0270, 0.0040, 8), 0.0040, 0.03))                                           # ejection port
cover = bevel(cover, 0.0009, 3, 20)                                               # soft pressed-steel creases between the facets
# rear slope details (photos/cover_rear_selector_sculpt_*.png): recoil spring guide button, a pressed triangular panel
# with two rivets under it, a tab with a rivet at each rear corner and the two flat plates along the rear edge
SA = Vector((0.0, 0.2430, 0.0170)); Sd = Vector((0.0, 0.8, 0.6)); Sn = Vector((0.0, -0.6, 0.8))                  # slope start, up-slope direction, outward normal
def onslope(u, v): q = SA + Sd * u + Sn * v; return (q.y, q.z)
button = bevel(prism_x([onslope(0.0090, -0.001), onslope(0.0175, -0.001), onslope(0.0175, 0.0018), onslope(0.0150, 0.0040), onslope(0.0090, 0.0040)], -0.0050, 0.0050), 0.0006, 2, 40)
Ms = Matrix((Vector((1, 0, 0)), Sn, Sd)).transposed().to_4x4(); Ms.translation = SA
# two pressed lines run from the button's lower corners out to the rear corners (the triangle in the sculpt), two rivets between them
ribs = [xform(bevel(prism_y([(sx * 0.0050, 0.0090), (sx * 0.0058, 0.0090), (sx * 0.0162, 0.0010), (sx * 0.0154, 0.0010)][::sx], -0.0004, 0.0004), 0.00015, 1, 60), Ms) for sx in (1, -1)]
cover = diff(cover, xform(box(-0.0056, 0.0056, -0.0060, 0.0060, 0.0084, 0.0181), Ms))       # hole for the spring guide's button (the button itself is on the receiver)
rear = [*ribs]
rear += [dome(0.0013, SA + Sd * 0.0045 + Vector((sx * 0.0042, 0, 0)), Sn, h=0.0007, seg=14) for sx in (1, -1)]
for sx in (1, -1):
    rear.append(bevel(box(*sorted((sx * (HW + 0.0003), sx * (HW + 0.0016))), 0.2436, 0.2530, 0.0086, 0.0140), 0.0004, 1, 60))      # corner tab
    rear.append(dome(0.0012, (sx * (HW + 0.0016), 0.2492, 0.0113), (sx, 0, 0), h=0.0006, seg=12))
    rear.append(bevel(box(*sorted((sx * 0.0058, sx * (HW + 0.0012))), 0.2380, 0.2445, 0.0111, 0.0137), 0.0007, 2, 60))            # raised plate along the rear edge, gap in the middle
cover = join(cover, *rear)
# rear sight, after photos/rear_sight_closeup_render.png and photos/sight_picture.jpg. From the rear: two tall ears with the
# aperture leaf between them; the ears run on forward as low sloping side walls; a flat range leaf with a toothed left
# edge and a slider with a round knob each side; a rounded pivot yoke; a low split clamp block at the front.
base = bevel(prism_x([(0.2680, 0.0190), (0.3300, 0.0190), (0.3300, 0.0385), (0.2680, 0.0385)], -0.0135, 0.0135), 0.0008, 2, 35)
base = diff(base, cyl_y(0.0075, 0.26, 0.34, z=0.0253, seg=32))                   # hollow underneath: the recoil spring runs through here
def ear(s):                                                                      # ear + side wall in one piece
    x0, x1 = sorted((s * 0.0095, s * 0.0138))                                  # 0.3 mm proud of the sight base sides (no coplanar faces)
    return bevel(prism_x(round_poly([(0.2710, 0.0340), (0.2710, 0.0580), (0.2735, 0.0620), (0.2800, 0.0620), (0.2890, 0.0478), (0.2960, 0.0452), (0.3150, 0.0425), (0.3150, 0.0340)],
                                    [0, 0.002, 0.0035, 0.0035, 0.004, 0.003, 0, 0]), x0, x1), 0.0007, 2, 60)
def yoke(s):                                                                     # pivot yoke: a rounded lug each side, the leaf end between them
    x0, x1 = sorted((s * 0.00555, s * 0.01365))                                # 0.15 mm proud of the base, 0.2 mm in front of it
    return bevel(prism_x(round_poly([(0.3122, 0.0340), (0.3122, 0.0440), (0.3162, 0.0487), (0.3252, 0.0487), (0.3302, 0.0440), (0.3302, 0.0340)], [0, 0.003, 0.0035, 0.0035, 0.003, 0]), x0, x1), 0.0007, 2, 60)
ltop = lambda y: 0.0487 - (y - 0.2850) * 0.0900                                  # top of the range leaf, sloping down to the pivot
leaf_bar = bevel(prism_x([(0.2850, ltop(0.2850) - 0.0030), (0.3240, ltop(0.3240) - 0.0030), (0.3240, ltop(0.3240)), (0.2850, ltop(0.2850))], -0.0048, 0.0048), 0.0004, 1, 40)
# aperture leaf: a broad tombstone 14 mm wide with the peep, its top a little below the ears
aper = diff(prism_y([(0.0070, 0.0430), (0.0070, SL - 0.0017)] + [(0.0070 * math.cos(math.pi * i / 20), SL - 0.0017 + 0.0070 * math.sin(math.pi * i / 20)) for i in range(1, 20)]
                    + [(-0.0070, SL - 0.0017), (-0.0070, 0.0430)], 0.2835, 0.2860),
            cyl_y(0.0020, 0.28, 0.29, z=SL, seg=24), lathe_y([(0.2825, 0.0037), (0.2842, 0.0020)], 24, z=SL))               # 4 mm peep (real one is 1.6 mm; at the game's 12 cm eye relief this shows the whole front hood ring with some target around it) with a countersink
rack = [box(-0.0048, -0.0036, y, y + 0.0009, ltop(y) - 0.0004, ltop(y) + 0.0006) for y in [0.3010 + i * 0.0018 for i in range(11)]]   # teeth along the left edge of the leaf
slider = [bevel(box(-0.0056, 0.0056, 0.2945, 0.3005, 0.0436, 0.0492), 0.0005, 1, 35)]                                            # slider wrapped round the leaf ...
slider += [bevel(cyl_x(0.0034, *sorted((sx * 0.0050, sx * 0.0130)), y=0.2975, z=0.0468, seg=28), 0.0005, 2, 50) for sx in (1, -1)]   # ... with a round knob each side
pivot = [cyl_x(0.0013, -0.0137, 0.0137, y=0.3215, z=0.0450, seg=14), dome(0.0019, (0.0135, 0.3215, 0.0450), (1, 0, 0)), dome(0.0019, (-0.0135, 0.3215, 0.0450), (-1, 0, 0))]
clamp = diff(bevel(prism_x(round_poly([(0.3290, 0.0300), (0.3520, 0.0300), (0.3520, 0.0375), (0.3440, 0.0410), (0.3290, 0.0410)], [0, 0, 0.002, 0.003, 0]), -0.0100, 0.0100), 0.0008, 2, 35),
             box(-0.0005, 0.0005, 0.3310, 0.3600, 0.0345, 0.0500))                                                              # split clamp block
hw = [lathe_axis([(-0.0005, 0.0030), (0.0026, 0.0030), (0.0030, 0.0025)], (-0.0045, 0.3375, 0.0410), (0, 0, 1), 20),             # tall screw standing on the clamp
      diff(lathe_axis([(0.0, 0.0031), (0.0022, 0.0031), (0.0026, 0.0026)], (-0.0100, 0.3470, 0.0350), (-1, 0, 0), 20), box(-0.02, -0.0118, 0.3466, 0.3474, 0.03, 0.04)),   # cross bolt head on the left
      dome(0.0022, (0.0100, 0.3470, 0.0350), (1, 0, 0))]
cover = join(cover, base, ear(1), ear(-1), yoke(1), yoke(-1), leaf_bar, aper, clamp, *slider, *pivot, *hw, *rack)
finish(cover, 'RK_top_cover_model', 'RK_top_cover', STEEL)

# ================= plastic handguard (after the RK 62 M photo) =================
HGS = [(0.4880, 0.0035, 0.0228, 0.0350), (0.4895, 0.0035, 0.0246, 0.0368), (0.4960, 0.0035, 0.0246, 0.0368), (0.4975, 0.0035, 0.0236, 0.0358),   # steel ring at the receiver
       (0.5080, 0.0040, 0.0236, 0.0356), (0.5200, 0.0050, 0.0228, 0.0338), (0.5600, 0.0062, 0.0220, 0.0306), (0.6420, 0.0070, 0.0206, 0.0286),
       (0.6450, 0.0070, 0.0198, 0.0278), (0.6465, 0.0070, 0.0204, 0.0284), (0.6560, 0.0070, 0.0202, 0.0280), (0.6580, 0.0070, 0.0186, 0.0262),   # front cap ring
       (0.6585, 0.0070, 0.0150, 0.0230)]
hg = loft_y(HGS, S, 3.0)
for s_ in (1, -1):
    # recessed side panel (checkering goes here in the texture); the cutter follows the taper of the sides
    X0 = 0.0212
    cut = bevel(prism_x(rrect(0.5150, 0.6360, -0.0090, 0.0200, 0.0050, 8), X0, X0 + 0.02), 0.0006, 1, 60)
    cut = xform(cut, Matrix.Translation((0, 0.5755, 0)) @ Matrix.Rotation(math.radians(-0.95), 4, 'Z') @ Matrix.Translation((0, -0.5755, 0)))
    if s_ < 0: cut = xform(cut, Matrix.Scale(-1, 4, (1, 0, 0)))
    hg = diff(hg, cut)
    # three oval vents along the lower corner
    for y in (0.5270, 0.5650, 0.6030):
        slot = bevel(box(0.0100, 0.05, y, y + 0.0270, -0.0032, 0.0032), 0.0030, 4, 35)
        slot = xform(slot, Matrix.Translation((0, 0, 0.0030)) @ Matrix.Rotation(math.radians(s_ * 52 if s_ > 0 else 180 - 52), 4, 'Y'))
        hg = diff(hg, slot)
# shallow crease between the smooth top and the sides
for s_ in (1, -1):
    x0, x1 = sorted((s_ * 0.0185, s_ * 0.03))
    hg = diff(hg, box(x0, x1, 0.5050, 0.6420, 0.0262, 0.0270))
hg = diff(hg, lathe_y([(0.4800, 0.0130), (0.5128, 0.0130), (0.5136, 0.0091), (0.6700, 0.0091)], 32))            # barrel channel right through (the solid block used to plug the bore)
finish(hg, 'RK_handguard_plastic_model', 'RK_handguard_plastic', PLASTIC, sharp=40)

# ================= cheese grater handguard (measured on research/sheet_right_M62S.png) =================
Y0, Y1, GP = 0.4900, 0.6550, 2.25                                   # rounded arch (photos/cheese_grater_half_single.jpg)
def sec(y):                                                                      # tapering lower shell: top edge +14, bottom -39 -> -20
    t = (y - Y0) / (Y1 - Y0); bot = -0.0390 + 0.0190 * t
    return ((0.0200 + bot) / 2, 0.0195 - 0.0030 * t, (0.0200 - bot) / 2)
grow = lambda y, g: (y, sec(y)[0], sec(y)[1] + g, sec(y)[2] + g)
cg = loft_y([grow(Y0, 0.0014), grow(Y0 + 0.0070, 0.0014), grow(Y0 + 0.0078, 0.0), grow(Y1 - 0.0080, 0.0), grow(Y1 - 0.0050, -0.0006),
             grow(Y1, -0.0030), grow(Y1 + 0.0050, -0.0075)], S, GP)                                             # rear flange plate ... domed front end
cg = diff(cg, loft_y([grow(Y0 - 0.01, -0.0014), grow(Y1 - 0.0085, -0.0014), grow(Y1 - 0.0058, -0.0022)], 48, GP))   # stops before the dome thins out (it used to break through)
cg = diff(cg, cyl_y(0.0086, 0.6400, 0.6700, seg=40))                                               # barrel hole through the front dome (it used to plug the bore)
TOP = [(0.5160, 0.0060), (0.5370, 0.0060), (0.5590, 0.0060), (0.5810, 0.0060), (0.6060, 0.0060), (0.6350, 0.0060)]            # dia 10
BOT = [(0.5070, -0.0210), (0.5290, -0.0190), (0.5500, -0.0155), (0.5720, -0.0125), (0.5960, -0.0095), (0.6230, -0.0060)]      # dia 9
for hy, hz in TOP: cg = diff(cg, cyl_x(0.0050, -0.04, 0.04, y=hy, z=hz, seg=32))
for hy, hz in BOT: cg = diff(cg, cyl_x(0.0045, -0.04, 0.04, y=hy, z=hz, seg=32))
for hy in (0.5320, 0.5760, 0.6200):
    cg = diff(cg, bevel(box(-0.0030, 0.0030, hy, hy + 0.0220, -0.06, -0.010), 0.0025, 3, 35))
# pressed beads: each runs down one side, under the belly and up the other side, but stops short around a hole
beads = []
y = Y0 + 0.0115
while y < Y1 - 0.0100:
    cz, rx, rz = sec(y)
    th_top = se_theta(cz, rz, GP, 0.0130)                                        # beads start just under the top edge
    near_top = [hz for hy, hz in TOP if abs(hy - y) < 0.0064]
    near_bot = [hz for hy, hz in BOT if abs(hy - y) < 0.0060]
    hi = se_theta(cz, rz, GP, near_top[0] - 0.0068) if near_top else th_top
    if near_bot:
        lo_a = se_theta(cz, rz, GP, near_bot[0] + 0.0062); lo_b = se_theta(cz, rz, GP, near_bot[0] - 0.0062)
        if hi - lo_a > 0.12:
            beads += [bead(y, cz, rx, rz, GP, lo_a, hi), bead(y, cz, rx, rz, GP, math.pi - hi, math.pi - lo_a)]
        beads.append(bead(y, cz, rx, rz, GP, -math.pi - lo_b, lo_b))   # under the belly
    else:
        beads.append(bead(y, cz, rx, rz, GP, -math.pi - hi, hi))
    y += 0.0044
# pairs of small pressed dots beside every hole, on the side away from the other row
for row, sgn in ((TOP, 1), (BOT, -1)):
    for hy, hz in row:
        cz, rx, rz = sec(hy); zz = hz + sgn * 0.0068
        if abs(zz - cz) >= rz * 0.97: continue
        th = se_theta(cz, rz, GP, zz); px, pz = se_point(cz, rx, rz, GP, th)
        for s_ in (1, -1):
            n = Vector((s_ * px / (rx * rx), 0, (pz - cz) / (rz * rz))).normalized()
            if sgn == 1: ys = (hy - 0.0030, hy + 0.0030)
            else:                                                                # lower row: in the gaps BETWEEN the ribs, never on top of one
                k = round((hy - (Y0 + 0.0115 + 0.0022)) / 0.0044); m = Y0 + 0.0115 + 0.0022 + k * 0.0044
                ys = (m, m + (0.0044 if hy > m else -0.0044))
            for yy in ys:
                beads.append(dome(0.0009, (s_ * px, yy, pz), n, h=0.0006, seg=10))
seam = bevel(prism_x([(Y0 + 0.006, sec(Y0)[0] - sec(Y0)[2] - 0.0045), (Y1 - 0.008, sec(Y1)[0] - sec(Y1)[2] - 0.0045),
                      (Y1 - 0.008, sec(Y1)[0] - sec(Y1)[2] + 0.0020), (Y0 + 0.006, sec(Y0)[0] - sec(Y0)[2] + 0.0020)], -0.0016, 0.0016), 0.0004, 1, 40)   # bottom seam flange
beads.append(seam)
strip = bevel(box(-0.0118, 0.0118, Y0 + 0.004, Y1 - 0.003, 0.0190, 0.0245), 0.0010, 2, 35)                      # top strip under the exposed gas tube
strip = diff(strip, cyl_y(0.0084, 0.48, 0.67, z=GZ, seg=40))
ferr = diff(lathe_y([(Y1 + 0.0040, 0.0118), (Y1 + 0.0050, 0.0128), (Y1 + 0.0085, 0.0128), (Y1 + 0.0095, 0.0112)], 48), cyl_y(0.0086, 0.65, 0.67, seg=32))
finish(join(union(cg, strip, ferr), *beads), 'RK_handguard_cheesegrater_model', 'RK_handguard_cheesegrater', STEEL)

# ================= pistol grip =================
gp_ = [(0.2610, -0.0370), (0.3030, -0.0370), (0.3030, -0.0450), (0.2975, -0.0700), (0.2900, -0.1050), (0.2862, -0.1215), (0.2890, -0.1290), (0.2860, -0.1335),
       (0.2780, -0.1340), (0.2400, -0.1262), (0.2378, -0.1218), (0.2422, -0.1160), (0.2490, -0.0850), (0.2575, -0.0500)]
grip = prism_x(round_poly(gp_, [0.001, 0.001, 0.004, 0.012, 0.012, 0.006, 0.004, 0.004, 0.006, 0.004, 0.004, 0.006, 0.012, 0.010]), -0.0136, 0.0136)   # every corner of the outline rounded
grip = bevel(grip, 0.0092, 9, 60)                                                # well rounded front and back straps, oval in section
for s_ in (1, -1):                                                               # recessed checkered panel, slanted like the grip
    x0, x1 = sorted((s_ * 0.0129, s_ * 0.03))
    grip = diff(grip, bevel(prism_x(round_poly([(0.2690, -0.0540), (0.2920, -0.0540), (0.2790, -0.1150), (0.2560, -0.1150)], 0.0050), x0, x1), 0.0012, 3, 60))
    grip = union(grip, dome(0.0026, (s_ * 0.0134, 0.2880, -0.0455), (s_, 0, 0)))  # cross pin at the top
grip = union(grip, lathe_axis([(0.0, 0.0050), (0.0012, 0.0050), (0.0018, 0.0042)], (0.0, 0.2640, -0.1300), (0.0, -0.20, -1.0), 20))   # screw plug underneath
finish(grip, 'RK_pistol_grip_model', 'RK_pistol_grip', PLASTIC, sharp=40)

# ================= bicycle grip =================
prof = [(0.0, 0.0125), (0.004, 0.0135)]
d = 0.006
while d < 0.088:
    prof += [(d, 0.0122), (d + 0.0008, 0.0138), (d + 0.0022, 0.0138), (d + 0.0030, 0.0122)]; d += 0.0036
prof += [(0.090, 0.0138), (0.095, 0.0138), (0.097, 0.0120)]
bg = lathe_axis(prof, (0.0, 0.2830, -0.0375), (0.0, -0.30, -1.0), 40)
finish(union(bg, bevel(box(-0.0120, 0.0120, 0.2610, 0.3030, -0.0430, -0.0370), 0.001, 2, 35)), 'RK_bicycle_grip_model', 'RK_bicycle_grip', PLASTIC, sharp=40)

# ================= tube stock (droops 6 degrees) with the bent-strap triangle butt (research/img/ria_4091_3744.jpg) =================
A0, A1 = Vector((0.0, 0.2350, -0.0165)), Vector((0.0, 0.0630, -0.0345))
axis = (A1 - A0).normalized(); L = (A1 - A0).length
upn = Vector((0.0, axis.z, -axis.y))                                                                                                 # square to the tube, pointing up
tube = lathe_axis([(-0.004, 0.0128), (0.0, 0.0130), (0.0030, 0.0148), (0.0080, 0.0157), (0.0150, 0.0155), (L - 0.0050, 0.0155),      # rubber sleeve with its shoulder
                   (L - 0.0040, 0.0162), (L - 0.0020, 0.0168), (L + 0.0050, 0.0168), (L + 0.0070, 0.0162), (L + 0.0080, 0.0132),      # collar ring
                   (L + 0.0480, 0.0132), (L + 0.0560, 0.0108), (L + 0.0700, 0.0104), (L + 0.0735, 0.0088), (L + 0.0748, 0.0050)], A0, axis, S)             # bare steel end, rounded off
# the strap arms are formed around the tube at the collar and welded there; from there one strap runs up to the
# rounded top corner, down the upright, round the bottom corner and back up to the underside of the collar.
# The strap is a channel: its side flanges are shallow on the arms and deep on the upright (photo: about 20 mm).
ST, SW, RC = 0.0030, 0.0130, 0.0166
def land(sgn, corner):
    P = A0 + axis * (L + 0.0075) + upn * (sgn * (RC + ST / 2)); c = Vector((0.0, corner[0], corner[1]))
    return P, P + (c - P).normalized() * 0.0260
TC, BC = (-0.0185, 0.0080), (-0.0090, -0.1078)                                                                                        # where the straight runs would meet
Pu, Bu = land(1, TC); Pl, Bl = land(-1, BC)
du = (Pu - Bu).normalized() * 0.0025; dl = (Pl - Bl).normalized() * 0.0025
ctrl = [((Bu.y + du.y, Bu.z + du.z), 0), ((Bu.y, Bu.z), 0), (TC, 0.0130), ((-0.0182, -0.0450), 0.0200), (BC, 0.0120), ((Bl.y, Bl.z), 0), ((Bl.y + dl.y, Bl.z + dl.z), 0)]
def fillet(ctrl, n=10):                                                                                                               # true rounded corners (quadratic blend of radius r)
    out = []
    for i, (p, r) in enumerate(ctrl):
        p = Vector(p)
        if not r: out.append(p); continue
        a = Vector(ctrl[i - 1][0]); b = Vector(ctrl[i + 1][0])
        q0 = p + (a - p).normalized() * r; q1 = p + (b - p).normalized() * r
        out += [(1 - t) ** 2 * q0 + 2 * t * (1 - t) * p + t * t * q1 for t in [k / n for k in range(n + 1)]]
    return out
def resample(p, step=0.002):
    out = [Vector(p[0])]
    for a, b in zip(p, p[1:]):
        a, b = Vector(a), Vector(b); n = max(1, int((b - a).length / step))
        out += [a.lerp(b, k / n) for k in range(1, n + 1)]
    return out
sp = resample(fillet(ctrl))
strap = bevel(strip_x([tuple(p) for p in sp], ST, -SW, SW), 0.0006, 2, 60)
# Kept simple, as on the service rifle (photos/rk62_right_military_sling.png): just the bent flat strap, formed
# around the tube at the collar, and the tube end pinned to the upright. No side plates, buttons or latch.
sad = [bevel(saddle(A0, axis, upn * sgn, L - 0.0030, L + 0.0075, P, B + (B - P).normalized() * 0.003, RC, ST, SW, 1.25), 0.0005, 2, 50)
       for sgn, P, B in ((1, Pu, Bu), (-1, Pl, Bl))]
Pp = A0 + axis * (L + 0.0640)                                                                                                         # cross pin through the tube end
ears = [bevel(prism_x(rrect(-0.0175, Pp.y + 0.0075, Pp.z - 0.0075, Pp.z + 0.0075, 0.0060, 8), *sorted((s_ * 0.0106, s_ * 0.0128))), 0.0005, 2, 60) for s_ in (1, -1)]   # two small lugs on the upright holding the pin
riv = [dome(0.0034, (s_ * 0.0128, Pp.y, Pp.z), (s_, 0, 0), h=0.0014) for s_ in (1, -1)]
finish(join(tube, strap, *sad, *ears, *riv), 'RK_stock_model', 'RK_stock', STEEL)

# ================= waffle magazine (after photos/waffle_mag_loose.jpg) =================
# Rear two thirds of each side: full thickness with RAISED thin ribs (3 columns of squares). Front third: sunken smooth area;
# the cross ribs run out onto it as points. The cross ribs also wrap around the rear spine.
R = 0.215; C = (0.411 + R, -0.006); MX = 0.0132; RH = 0.0010; STEP = 0.0013; DS = 0.0090; T0, T1, PITCH = 10.3, 50.5, (50.5 - 10.3) / 13                                 # waffle starts below the AK top part (cut at 9.7 degrees)
mag = bevel(arc_loft(C, R, -1.5, 52, -0.0305, 0.0305, MX, steps=44), 0.0026, 4, 60)
for s_ in (1, -1):
    x0, x1 = sorted((s_ * (MX - STEP), s_ * 0.03))
    mag = diff(mag, arc_bar(C, R, T0 - 2.0, 53.0, DS, 0.04, x0, x1, steps=40))                      # sunken front area
parts = [bevel(arc_loft(C, R, T0, T1, dd - 0.0007, dd + 0.0007, MX + RH + 0.00009, steps=40), 0.0004, 1, 40) for dd in (-0.0175, -0.0045)]   # two long ribs
parts.append(arc_loft(C, R, T0 - 2.0, 52.0, DS - 0.0014, DS, MX + RH * 0.6, steps=40))             # raised edge along the step
t = T0
while t <= T1 + 0.1:
    for s_ in (1, -1):
        parts.append(arc_rib(C, R, t, [(-0.0300, 0.0008, RH * 0.7), (-0.0270, 0.0008, RH), (DS, 0.0008, RH), (DS + 0.0006, 0.0011, RH * 0.8, -STEP),
                                       (DS + 0.0045, 0.0012, -STEP * 0.35, -STEP), (DS + 0.0105, 0.0002, -STEP + 0.0001, -STEP)], MX, s_))
    parts.append(arc_loft(C, R, t - 0.22, t + 0.22, -0.0316, -0.0290, MX - 0.0030, steps=1))        # the rib wraps round the spine
    t += PITCH
# smooth cap part inside the magazine well with its edge, floor plate with lip, lugs
parts += [arc_loft(C, R, T0 - 2.4, T0 - 2.0, -0.0300, 0.0300, MX + 0.0004, steps=1)]
parts += [bevel(arc_loft(C, R, 51.6, 54.6, -0.0335, 0.0335, 0.0160, steps=2), 0.0010, 2, 50),
          bevel(arc_loft(C, R, 54.6, 55.3, -0.0300, 0.0340, 0.0150, steps=1), 0.0005, 1, 50)]
parts += [bevel(box(-0.0045, 0.0045, 0.3735, 0.3830, -0.0190, -0.0050), 0.0006, 1, 40), bevel(box(-0.0050, 0.0050, 0.4400, 0.4455, -0.0150, -0.0080), 0.0006, 1, 40)]
# sling loop on the front edge above the floor plate
ta = math.radians(45.0); rr = R - 0.0318
P0 = Vector((0.0, C[0] - rr * math.cos(ta), C[1] - rr * math.sin(ta)))
e_in = Vector((0.0, math.cos(ta), math.sin(ta))); e_t = Vector((0.0, math.sin(ta), -math.cos(ta)))
outer = [(-0.0125, -0.0020), (0.0125, -0.0020), (0.0105, 0.0070), (0.0085, 0.0095), (-0.0085, 0.0095), (-0.0105, 0.0070)]
loop = diff(bevel(prism_x(outer, -0.0030, 0.0030), 0.0012, 3, 30), bevel(prism_x(rrect(-0.0078, 0.0078, 0.0012, 0.0062, 0.0020, 6), -0.01, 0.01), 0.0001, 1, 80))
M = Matrix((Vector((1, 0, 0)), e_t, e_in)).transposed().to_4x4(); M.translation = P0
parts.append(xform(loop, M))
# The part that goes into the rifle is the Tarkov AK magazine's own: feed lips, front lug and the rear latch lug are copied from
# the vanilla 6L10 magazine (same arc, same well) and everything of ours above 9.7 degrees on the arc is cut away.
wmag = join(mag, *parts)
TCUT = math.radians(9.7); cut_co = Vector((0.0, C[0], C[1])); cut_no = Vector((0.0, math.sin(TCUT), -math.cos(TCUT)))   # normal points down the magazine
_vm = bpy.data.objects.get('AK_magazine__mag_ak_izhmash_6L10_762x39_30_LOD0'); _root = bpy.data.objects.get('AKMN_root')
if _vm and _root:
    Wm = _root.matrix_basis @ _vm.matrix_parent_inverse @ _vm.matrix_basis
    me_ = _vm.data.copy(); me_.transform(Wm)
    if Wm.determinant() < 0: me_.flip_normals()
    top_ = bpy.data.objects.new('ak_mag_top', me_); bpy.context.scene.collection.objects.link(top_)
    wmag = join(bisect_keep(wmag, cut_co, cut_no, True), bisect_keep(top_, cut_co, cut_no, False))
else:
    print('vanilla magazine reference not found - RK magazine keeps its own top')
finish(wmag, 'RK_waffle_mag_model', 'RK_waffle_mag', PLASTIC)

# ================= flash hider, 70 mm, with the long bayonet bar =================
fh = diff(lathe_y([(0.8230, 0.0086), (0.8235, 0.0095), (0.8285, 0.0095), (0.8295, 0.0090), (0.8880, 0.0092), (0.8930, 0.0078)], S),
          lathe_y([(0.81, 0.0056), (0.8860, 0.0056), (0.90, 0.0085)], 40))
for a in (60, 180, 300):
    fh = diff(fh, rot_y(bevel(box(-0.0026, 0.0026, 0.8600, 0.92, 0.0, 0.02), 0.0020, 3, 35), a))
bar = bevel(prism_x([(0.8360, -0.0090), (0.8800, -0.0090), (0.8800, -0.0170), (0.8360, -0.0170)], -0.0032, 0.0032), 0.0006, 2, 40)
bar = union(bar, box(-0.0050, 0.0050, 0.8400, 0.8760, -0.0182, -0.0165), dome(0.0014, (0.0032, 0.8450, -0.0130), (1, 0, 0), seg=10), dome(0.0014, (0.0032, 0.8700, -0.0130), (1, 0, 0), seg=10))
finish(union(fh, bar), 'RK_flash_hider_model', 'RK_flash_hider', STEEL)

# ================= RK 62 M flash hider: Ase Utra BoreLock HiPer, measured on Saniainen's model (web/saniainen_muzzle/.../Flashhider.stl) =================
# 66.5 mm long: knurled lock ring (27.6 mm, 6 mm long), a thin gap, the fine suppressor thread (25.9 mm, 8 grooves),
# a short cone down to the 22 mm body, three 4.2 mm slots from just in front of the cone to the tip, a shallow groove near
# the tip for the protector cap, and a bore that opens up towards the front.
Y0 = 0.8230; YE = Y0 + 0.0665
n_k = 72
knurl = [((0.0138 if k % 2 == 0 else 0.0132) * math.cos(math.pi * k / n_k), (0.0138 if k % 2 == 0 else 0.0132) * math.sin(math.pi * k / n_k)) for k in range(2 * n_k)]
ring = bevel(prism_y(knurl, Y0, Y0 + 0.0060), 0.0004, 1, 20)
body = lathe_y(densify([(Y0 + 0.0058, 0.0118), (Y0 + 0.0068, 0.0118), (Y0 + 0.0070, 0.0129)] +
               sum([[(Y0 + 0.0078 + 0.0014 * i, 0.0129), (Y0 + 0.0083 + 0.0014 * i, 0.0124), (Y0 + 0.0088 + 0.0014 * i, 0.0129)] for i in range(8)], []) +   # suppressor thread
               [(Y0 + 0.0188, 0.0129), (Y0 + 0.0192, 0.0127), (Y0 + 0.0228, 0.0110),                                                                   # alignment cone
                (Y0 + 0.0565, 0.0110), (Y0 + 0.0568, 0.0105), (Y0 + 0.0588, 0.0105), (Y0 + 0.0591, 0.0110),                                            # protector groove
                (YE - 0.0012, 0.0110), (YE, 0.0099)]), S)                                                          # rings every 4 mm                                                                                                # tip chamfer
fh2 = union(body, ring)
fh2 = diff(fh2, lathe_y(densify([(0.81, 0.0068), (Y0 + 0.0200, 0.0068), (Y0 + 0.0205, 0.0044), (Y0 + 0.0300, 0.0044), (Y0 + 0.0310, 0.0050), (YE + 0.01, 0.0066)]), 40))   # barrel thread, bore, widening prong section
for a in (90, 210, 330):                                                         # three slots, open at the front, round at the back
    slot = union(box(-0.0021, 0.0021, Y0 + 0.0255, 0.92, 0.0, 0.02), cyl_z(0.0021, 0.0, 0.02, x=0.0, y=Y0 + 0.0255, seg=18))
    fh2 = diff(fh2, rot_y(slot, a))
finish(fh2, 'RK62M_flash_hider_model', 'RK62M_flash_hider', STEEL, dissolve=False)

# ================= RK 62 M suppressor: Ase Utra S-series SL5i-BL look (catalogue: 43-44.5 mm, adds 92 mm), proportions from Saniainen's Base/Can/baffle =================
# Slides over the HiPer flash hider and locks on its knurled ring. Base with a catch tab and a screw, smooth 44.5 mm body,
# front cap tapering to a crown of six fingers. Hollow at the back (the flash hider sits inside), 9 mm bore out the front.
Y0 = 0.8230; YF = Y0 + 0.1593
sup = lathe_y(densify([(Y0 - 0.0017, 0.0188), (Y0 - 0.0010, 0.0196), (Y0 + 0.0058, 0.0196), (Y0 + 0.0062, 0.0190), (Y0 + 0.0072, 0.0190), (Y0 + 0.0076, 0.0201),
               (Y0 + 0.0262, 0.0201), (Y0 + 0.0266, 0.0196), (Y0 + 0.0280, 0.0196), (Y0 + 0.0285, 0.0218), (Y0 + 0.0293, 0.02225),                 # base, lock ring, step to the body
               (Y0 + 0.1255, 0.02225), (Y0 + 0.1262, 0.0217), (Y0 + 0.1270, 0.0217), (Y0 + 0.1278, 0.02175),                                        # body, joint to the front cap
               (Y0 + 0.1330, 0.02175), (Y0 + 0.1560, 0.0180), (YF - 0.0003, 0.0172), (YF, 0.0160), (YF, 0.0090), (YF - 0.0012, 0.0062)], 0.008), S)   # rings every 8 mm        # front cap cone and face
sup = diff(sup, lathe_y(densify([(Y0 - 0.004, 0.0142), (Y0 + 0.0680, 0.0142), (Y0 + 0.0695, 0.0045), (YF + 0.01, 0.0045)], 0.008), 48))                         # pocket for the flash hider, bore
cuts = []
for a in range(0, 360, 60):
    cuts.append(rot_y(bevel(box(-0.0018, 0.0018, YF - 0.0125, YF + 0.01, 0.0098, 0.03), 0.0006, 1, 50), a + 30))                               # crown fingers
    cuts.append(rot_y(box(-0.0020, 0.0020, Y0 - 0.004, Y0 + 0.0035, 0.0172, 0.03), a))                                                         # notches in the rear lip
sup = diff(sup, *cuts)
nose = diff(lathe_y([(YF - 0.0060, 0.0092), (YF + 0.0030, 0.0092), (YF + 0.0042, 0.0080), (YF + 0.0042, 0.0062)], 48), cyl_y(0.0050, YF - 0.01, YF + 0.01, seg=32))   # muzzle nose standing out of the crown
sup = join(sup, nose)
tab = bevel(union(box(0.0196, 0.0226, Y0 + 0.0105, Y0 + 0.0215, -0.0042, 0.0042), box(0.0215, 0.0236, Y0 + 0.0060, Y0 + 0.0120, -0.0042, 0.0042)), 0.0005, 2, 40)   # catch tab
screw = screw_head(0.0028, (-0.0201, Y0 + 0.0165, 0.0), (-1, 0, 0), h=0.0012)
finish(join(sup, tab, screw), 'RK62M_suppressor_model', 'RK62M_suppressor', STEEL, dissolve=False)
