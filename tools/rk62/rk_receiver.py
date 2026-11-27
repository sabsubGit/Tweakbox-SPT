exec(open('/mnt/storage/Code/Tweakbox/tools/rk62/rk_lib.py').read())
# All numbers come from research/RK62_research.md (y = 0.893 + X/1000, z = Z/1000).
HW = 0.0172; SL = 0.0545; GZ = 0.025; S = 64
# ------------------------------------------------ milled receiver body ------------------------------------------------
body = prism_x([(0.2350, -0.0270), (0.2420, -0.0320), (0.3330, -0.0305), (0.3810, -0.0300), (0.4430, -0.0290), (0.4470, -0.0250),
                (0.4880, -0.0180), (0.4880, 0.0050), (0.3880, 0.0050), (0.3840, 0.0080), (0.2350, 0.0080)], -HW, HW)
body = union(body,
             box(-HW, -0.0150, 0.3800, 0.4680, 0.0050, 0.0080),                                   # left wall stays at +8 to the front
             box(-HW, HW, 0.2350, 0.2430, 0.0080, 0.0110),                                        # rear wall
             box(-HW, HW, 0.4680, 0.4880, 0.0050, 0.0210), cyl_y(0.0098, 0.4680, 0.4880, z=GZ, seg=S),   # gas tube block
             prism_y(ak_cover_profile(0.0, 0.0050), 0.4680, 0.4745),            # full-profile shoulder the cover butts against (closes the cover's open front)
             box(-0.0125, 0.0125, 0.2610, 0.3030, -0.0370, -0.0300))                              # pistol grip seat
body = bevel(body, 0.0020, 5, 35)                                                                 # soft machined edges
body = diff(body,
            box(-0.0150, 0.0150, 0.2430, 0.4680, -0.0120, 0.03),                                  # action cavity
            box(-0.0135, 0.0135, 0.3790, 0.4440, -0.06, -0.004),                                  # magazine well
            box(-0.0045, 0.0045, 0.2960, 0.3400, -0.05, -0.010),                                  # trigger slot
            box(-0.0072, 0.0072, 0.3570, 0.3795, -0.06, -0.0180),                                 # magazine catch slot, tall enough for the AK magazine's rear latch lug
            cyl_y(0.0086, 0.46, 0.50, z=GZ, seg=40))                                              # gas piston passage
for s in (1, -1):                                                                                 # pill-shaped lightening cuts
    x0, x1 = sorted((s * 0.0156, s * 0.03))
    body = diff(body, prism_x(rrect(0.4050, 0.4820, -0.0170, -0.0080, 0.0045, 8), x0, x1))
body = union(body, bevel(box(0.0150, HW, 0.4640, 0.4680, 0.0040, 0.0082), 0.0004, 1, 40))         # wall rises to meet the cover lip at the front of the port (was a 3 mm gap)
body = diff(body, box(HW - 0.0007, 0.03, 0.2300, 0.3120, 0.0040, 0.0095))                             # right side: the top 4 mm of the wall is milled back a little under the cover (ledge line in the photo)
# inner guide rails for the bolt carrier (visible through the port)
body = union(body, box(0.0128, 0.0152, 0.2600, 0.4680, 0.0015, 0.0040), box(-0.0152, -0.0128, 0.2600, 0.4680, 0.0015, 0.0040))
# selector: axis boss, the two stop notches and the arc scratch plate edge
body = union(body, bevel(cyl_x(0.0075, HW - 0.001, HW + 0.0012, y=0.2845, z=-0.0084, seg=40), 0.0004, 2, 50),
             bevel(cyl_x(0.0045, -HW - 0.0012, -HW + 0.001, y=0.2845, z=-0.0084, seg=32), 0.0004, 2, 50))
for (ny, nz) in ((0.3930, -0.0120), (0.3900, -0.0230)):
    body = diff(body, prism_x(rrect(ny - 0.0030, ny + 0.0030, nz - 0.0013, nz + 0.0013, 0.0012, 5), HW - 0.0008, 0.03))
# left side: long milled step with its notch, as on the M62 close-up
body = diff(body, box(-0.03, -HW + 0.0007, 0.2700, 0.4000, 0.0020, 0.0095), box(-0.03, -HW + 0.0007, 0.3999, 0.4679, 0.0045, 0.0095))   # cut past the wall top (a flush cut left open edges)
# takedown lug at the rear top, with its two holes
lug = bevel(box(-0.0052, 0.0052, 0.2350, 0.2428, 0.0100, 0.0118), 0.0006, 2, 35)             # low plain step in the gap between the cover's two rear plates (sculpt picture: no tall block, no holes)
# magazine catch ears + pivot pin; axis pins with domed heads on both sides
cheek = [(0.3570, -0.0300), (0.3790, -0.0300), (0.3790, -0.0500), (0.3585, -0.0780), (0.3500, -0.0780)]   # leans back towards the grip: straight slanted rear edge, front edge cut away diagonally (RIA side photo)
ears = union(bevel(prism_x(cheek, 0.0060, 0.0080), 0.0005, 2, 35), bevel(prism_x(cheek, -0.0080, -0.0060), 0.0005, 2, 35),
             cyl_x(0.0017, -0.0084, 0.0084, y=0.3700, z=-0.0500, seg=20))
ears = union(ears, dome(0.0022, (0.0084, 0.3700, -0.0500), (1, 0, 0)), dome(0.0022, (-0.0084, 0.3700, -0.0500), (-1, 0, 0)))
body = union(body, lug, ears)
for (py, pz, pr) in ((0.3200, -0.0270, 0.0024), (0.3580, -0.0200, 0.0024), (0.4780, -0.0060, 0.0030)):
    body = union(body, dome(pr, (HW, py, pz), (1, 0, 0)), dome(pr, (-HW, py, pz), (-1, 0, 0)))
for y in (0.3890, 0.3920, 0.3950):                                                                # three small rivets (right)
    body = union(body, dome(0.0009, (HW, y, -0.0235), (1, 0, 0), h=0.0005, seg=10))
# (no sling loop on the left rear: the RK's left side is flat there - maker's mark and serial number, texture only; photos/rk62_left_rear_sako1966.png)
# ------------------------------------------------ barrel ------------------------------------------------
barrel = lathe_y([(0.4840, 0.0125), (0.5120, 0.0125), (0.5135, 0.0088), (0.6960, 0.0085), (0.7430, 0.0085), (0.7445, 0.00775),
                  (0.8130, 0.00775), (0.8140, 0.0084), (0.8190, 0.0084), (0.8200, 0.00775), (0.8230, 0.00775), (0.8230, 0.0068), (0.8380, 0.0068)], S)
# ------------------------------------------------ gas block + front sight ------------------------------------------------
# After research/img/ria_4091_3744.jpg (right side, 15.5 px/mm zoom) and photos/front_sight_left_render.png:
# a thin sleeve round the barrel, a waisted neck, the gas block lug with a big slotted screw on each side,
# a sight tower and a small hood ring on top.
sleeve = lathe_y([(0.7063, 0.0093), (0.7076, 0.0102), (0.7440, 0.0102), (0.7453, 0.0093)], S)
neck = prism_x(round_poly([(0.7082, 0.0), (0.7082, 0.0105), (0.7114, 0.0130), (0.7114, 0.0250), (0.7262, 0.0250), (0.7264, 0.0185), (0.7300, 0.0135),
                           (0.7370, 0.0108), (0.7440, 0.0096), (0.7440, 0.0)], [0, 0.001, 0.002, 0, 0, 0.004, 0.004, 0.003, 0.001, 0]), -0.0060, 0.0060)
lug = prism_x(round_poly([(0.7150, 0.0146), (0.7250, 0.0146), (0.7290, 0.0200), (0.7373, 0.0200), (0.7373, 0.0372), (0.7150, 0.0372)], [0.004, 0.003, 0.003, 0.0045, 0.0015, 0.001]), -0.0102, 0.0102)      # gas block lug: wide and deep enough to swallow the gas tube end on a flat face
head = lathe_y([(0.6960, 0.0092), (0.6975, 0.0098), (0.7170, 0.0098)], S, z=GZ)                                                                     # gas tube end, runs straight into the lug's rear face
tower = prism_x(round_poly([(0.7147, 0.0360), (0.7331, 0.0360), (0.7331, 0.0492), (0.7185, 0.0492), (0.7160, 0.0440)], [0, 0, 0.001, 0.001, 0.003]), -0.0056, 0.0056)   # target-side face is straight up, flush with the ring front
gb = join(diff(bevel(union(sleeve, neck, lug, tower), 0.0009, 3, 35), cyl_y(0.0039, 0.7000, 0.7500, seg=24)), head)   # bore continues through the sleeve                                 # tube end kept as its own shell: a clean crease, no smeared shading
hood = diff(cyl_y(0.0068, 0.7185, 0.7331, z=0.0545, seg=S), cyl_y(0.0054, 0.71, 0.74, z=0.0545, seg=48),
            prism_x([(0.7000, 0.0400), (0.7183, 0.0400), (0.7185, 0.0477), (0.7223, 0.0613), (0.7240, 0.0700), (0.7000, 0.0700)], -0.02, 0.02))   # shooter's side face is slanted: the top is cut back about 15 degrees
hood = bevel(hood, 0.0005, 2, 50)
post = union(cyl_z(0.0009, 0.0480, SL, x=0.0, y=0.7260, seg=16), cyl_z(0.0024, 0.0480, 0.0497, x=0.0, y=0.7260, seg=20))
# flip-up night sight, folded down: the blade hangs from a pin between two ears on the back of the tower
night = join(bevel(prism_x(round_poly([(0.7097, 0.0395), (0.7113, 0.0395), (0.7118, 0.0486), (0.7092, 0.0486)], [0.0004, 0.0004, 0.0012, 0.0012]), -0.0015, 0.0015), 0.0003, 1, 60),   # short blade, folded DOWN (tritium dot = texture)
             *[bevel(prism_x(round_poly([(0.7088, 0.0448), (0.7175, 0.0448), (0.7175, 0.0492), (0.7088, 0.0492)], [0.0016, 0, 0, 0.0016]), *sorted((sx * 0.0019, sx * 0.0048))), 0.0003, 1, 60) for sx in (1, -1)],   # hinge ears
             bevel(box(-0.0048, 0.0048, 0.7128, 0.7175, 0.0448, 0.0492), 0.0003, 1, 60),                                                            # bridge joining the ears to the tower
             cyl_x(0.0009, -0.0052, 0.0052, y=0.7105, z=0.0470, seg=12),
             *[dome(0.0012, (sx * 0.0048, 0.7105, 0.0470), (sx, 0, 0), h=0.0005, seg=12) for sx in (1, -1)])
A_ = math.radians(-44)
screws = [screw_head(0.0050, (sx * 0.0102, 0.7315, 0.0301), (sx, 0, 0), h=0.0018) for sx in (1, -1)]                    # big slotted clamp screw, a head on each side
screws += [dome(0.0015, (sx * 0.0102, 0.7234, 0.0305), (sx, 0, 0), seg=12) for sx in (1, -1)]                           # small pin beside it
screws += [dome(0.0021, (sx * 0.0101 * math.cos(A_), yy, 0.0101 * math.sin(A_)), (sx * math.cos(A_), 0, math.sin(A_))) for sx in (1, -1) for yy in (0.7147, 0.7379)]   # sleeve cross pins
swlug = bevel(prism_x(round_poly([(0.7105, -0.0080), (0.7195, -0.0080), (0.7185, -0.0150), (0.7115, -0.0150)], 0.0030), -0.0028, 0.0028), 0.0005, 1, 60)   # small lug under the sleeve
ring = xform(wire([(0.7150, -0.0128), (0.7184, -0.0128), (0.7184, 0.0150), (0.7116, 0.0150), (0.7116, -0.0128), (0.7150, -0.0128)], 0.0010, 12, 3), Matrix.Translation((-0.0122, 0, 0)))   # sling loop, swung up along the left side
ring = join(ring, cyl_x(0.0010, -0.0122, 0.0, y=0.7150, z=-0.0128, seg=12))
# The safety selector lever is NOT modelled here: the vanilla Tarkov AK selector (a separate moving part in the weapon
# bundle, vanilla pivot y 0.2945 z -0.0084) is kept, moved 10 mm to the rear (pivot y 0.2845) to keep the port clear. tools/rk62/show_vanilla_selector.py puts a copy in the scene.
rec = join(diff(union(body, barrel), cyl_y(0.0039, 0.4675, 0.8500, seg=24)), gb, hood, post, night, swlug, ring, *screws)   # barrel bored through (7.62 mm), open into the action      # front sight group joined as closed shells (the union left open edges)
# ------------------------------------------------ wire trigger guard ------------------------------------------------
# trigger guard: a flat steel band (1.4 mm thick, 9 mm wide), out of the receiver in front of the grip, bending
# down and forward, then running flat into the catch housing
gp = [Vector(q) for q in [(0.3000, -0.0360), (0.3030, -0.0440), (0.3110, -0.0590), (0.3180, -0.0640), (0.3400, -0.0640), (0.3620, -0.0640)]]
for _ in range(3):
    q = [gp[0]]
    for a_, b_ in zip(gp, gp[1:]): q += [a_.lerp(b_, 0.25), a_.lerp(b_, 0.75)]
    gp = q + [gp[-1]]
rec = join(rec, bevel(strip_x([tuple(p) for p in gp], 0.0014, -0.0045, 0.0045), 0.0004, 1, 60))                                                                                   # no front web on the catch housing: the magazine's rear latch lug comes in there            # front web of the catch housing channel; the catch lever itself is the vanilla AK 'release' part
# recoil spring with its guide rod and rear block: the Tarkov AK's own (a static part of the vanilla receiver mesh, so it has to be in ours)
spring = ak_islands('AK_receiver__weapon_izhmash_akm_762x39_LOD0',
                    lambda x0, x1, y0, y1, z0, z1, n: abs(x0) < 0.0075 and abs(x1) < 0.0075 and z0 > 0.0015 and z1 < 0.0325 and 0.2600 < y0 < 0.2700 and y1 < 0.4830)   # spring and rod only: the AK's rear guide block poked out through our cover's rear slope
if spring: rec = join(rec, spring)
# Rear trunnion and the recoil spring guide block, both fixed to the receiver so the spring stays put with the cover off
# (the cover is removable in game). As on the real RK, the guide's button rises through a hole in the cover's sloped rear.
SA_ = Vector((0.0, 0.2430, 0.0170)); Sd_ = Vector((0.0, 0.8, 0.6)); Sn_ = Vector((0.0, -0.6, 0.8))      # the cover's rear slope (start, up-slope, outward)
def onsl(u, v): q = SA_ + Sd_ * u + Sn_ * v; return (q.y, q.z)
zin = lambda y: 0.0170 + 0.75 * (y - 0.2430) - 0.0024                                                    # 0.6 mm under the cover's inner slope
trun = bevel(box(-0.0150, 0.0150, 0.2425, 0.2560, -0.0120, 0.0082), 0.0006, 1, 60)                       # solid rear of the action
gblk = bevel(prism_x([(0.2448, 0.0080), (0.2448, zin(0.2448)), (0.2668, zin(0.2668)), (0.2668, 0.0190), (0.2560, 0.0110), (0.2560, 0.0080)],
                     -0.0065, 0.0065), 0.0006, 2, 40)                                                    # guide block: the spring and rod seat in its front face
gbtn = bevel(prism_x([onsl(0.0090, -0.0040), onsl(0.0175, -0.0040), onsl(0.0175, 0.0018), onsl(0.0150, 0.0040), onsl(0.0090, 0.0040)],
                     -0.0050, 0.0050), 0.0006, 2, 40)                                                    # wedge button, stands 4 mm proud of the cover
rec = join(rec, trun, gblk, gbtn)
finish(rec, 'RK_receiver_model', 'RK_receiver', (0.22, 0.23, 0.24))
