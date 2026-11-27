exec(open('/mnt/storage/Code/Tweakbox/tools/rk62/rk_lib.py').read())
HW = 0.0172; SL = 0.0545; GZ = 0.025
STEEL, ALU = (0.22, 0.23, 0.24), (0.25, 0.29, 0.22)
DOVE_IN = 0.0010

# ---------------- picatinny rail helper ----------------
def pic_rail(y0, y1, z0):
    p = [(-0.0080, 0), (0.0080, 0), (0.0080, 0.0035), (0.0106, 0.0061), (0.0106, 0.0068), (0.0078, 0.0096),
         (-0.0078, 0.0096), (-0.0106, 0.0068), (-0.0106, 0.0061), (-0.0080, 0.0035)]
    r = prism_y([(x, z0 + z) for x, z in p], y0, y1)
    y = y0 + 0.0040
    while y + 0.0052 < y1 - 0.002:
        r = diff(r, box(-0.02, 0.02, y, y + 0.0052, z0 + 0.0066, z0 + 0.02)); y += 0.0100
    return r

# ---------------- RK 62 M top cover: same cover and rear sight, plus a top rail ----------------
src = bpy.data.objects['RK_top_cover_model']
m = src.copy(); m.data = src.data.copy(); bpy.context.scene.collection.objects.link(m)
m = join(m, pic_rail(0.3560, 0.4660, COVER_TOP), box(-0.0060, 0.0060, 0.3563, 0.4657, COVER_TOP - 0.0011, COVER_TOP + 0.0002))   # ends 0.3 mm short of the rail's ends (no coplanar faces)   # joined: the cover is made of overlapping shells now
finish(m, 'RK62M_top_cover_model', 'RK62M_top_cover', STEEL)

# ---------------- RK 62 M handguard (photos/rk62m_both_sides.png, 1.27 px/mm) ----------------
# Long aluminium shell from the receiver to just past the gas block, covering the gas tube. Flat top level with the cover,
# tall plain upper sides, a row of five M-LOK slots on each side, a second row on the lower chamfers and one underneath.
# The original front sight tower stands up through a notch in the top at the front.
MY0, MY1 = 0.4885, 0.7460; MW = HW + 0.0008                                    # same width as the top cover / receiver block
def m_prof(i=0.0):
    half = [(0.0150 - 0.5 * i, -0.0177 + i), (MW - i, -0.0020 + 0.4 * i), (MW - i, 0.0310 - 0.4 * i), (0.0115 - 0.5 * i, COVER_TOP - i)]
    return half + [(-x, z) for x, z in half[::-1]]
MSW, MBZ, MSB = 0.0155, -0.0174, 0.0075                                          # side half width, bottom, half width of the flat underneath
MYR = 0.4747                                                                     # the top of the shell runs back over the gas tube block to butt against the cover
def rear_prof(i=0.0):                                                             # the receiver's own outline, kept along the WHOLE handguard: receiver sides and bottom line, the cover's rounded top
    cov = [p for p in ak_cover_profile(i, 0.0085) if p[0] > 0]
    # below the cover line the shell is slimmer than the receiver (closer to the barrel) with two big 45 degree corners underneath
    half = [(MSB - 0.41 * i, MBZ + i), (MSW - i, MBZ + (MSW - MSB) + 0.41 * i), (MSW - i, 0.0080)] + cov + [(0.0, COVER_TOP - i)]
    return half + [(-x, z) for x, z in half[-2::-1]]
hg = bevel(prism_y(rear_prof(), MYR, MY1), 0.0008, 2, 50)
hg = diff(hg, prism_y(rear_prof(0.0018), MYR - 0.01, MY1 + 0.01),
          box(-0.05, 0.05, 0.46, MY0, -0.05, 0.0214),                             # behind the receiver's front face only the top tongue remains
          cyl_y(0.0101, 0.46, 0.5000, z=GZ, seg=40))                              # room for the block's round top
cuts = [box(-0.0150, 0.0150, 0.7090, 0.76, 0.0140, 0.05), box(-0.0115, 0.0115, 0.6920, 0.76, 0.0200, 0.05),   # open top at the front: gas block and front sight stand in a trough
        box(HW - 0.0004, 0.03, MY0 + 0.004, MY1 - 0.004, 0.0088, 0.0095), box(-0.03, -HW + 0.0004, MY0 + 0.004, MY1 - 0.004, 0.0088, 0.0095)]   # fine line along the side
for k in range(5):
    y = 0.5080 + 0.0430 * k
    cuts.append(prism_x(rrect(y, y + 0.0320, 0.0000, 0.0070, 0.0030, 6), -0.03, 0.03))                       # side row
    cuts.append(prism_x(rrect(y, y + 0.0320, -0.0150, -0.0105, 0.0021, 6), -0.03, 0.03))                     # row on the 45 degree corners
    cuts.append(rot_y(prism_x(rrect(y, y + 0.0320, -0.0035, 0.0035, 0.0030, 6), 0.0100, 0.0300), 90))        # underneath
for y in (0.6760, 0.6860, 0.6960):
    cuts.append(cyl_x(0.0015, -0.03, 0.03, y=y, z=0.0128, seg=14))                                           # three small holes high up near the front
cuts.append(box(-0.03, -0.0070, 0.7095, 0.7205, -0.03, -0.0010))                                             # window on the left for the sling loop on the gas block
hg = diff(hg, *cuts)
finish(hg, 'RK62M_handguard_model', 'RK62M_handguard', ALU)

# ---------------- RK 62 M side rail for AK-style sight mounts: the Tarkov AKMN dovetail itself ----------------
_dv = bpy.data.objects.get('AK_receiver__mount_akm_izhmash_akmn_dovetail_LOD0'); _root = bpy.data.objects.get('AKMN_root')
if _dv and _root:
    Wd = _root.matrix_basis @ _dv.matrix_parent_inverse @ _dv.matrix_basis
    me_ = _dv.data.copy(); me_.transform(Matrix.Translation((DOVE_IN, 0, 0)) @ Wd)                           # moved in: the RK receiver is narrower than the AKM's
    if Wd.determinant() < 0: me_.flip_normals()
    dv = bpy.data.objects.new('dove', me_); bpy.context.scene.collection.objects.link(dv)
    if 'RK62M_side_rail' not in bpy.data.collections:
        bpy.data.collections['RK62 parts (your models)'].children.link(bpy.data.collections.new('RK62M_side_rail'))
    finish(dv, 'RK62M_side_rail_model', 'RK62M_side_rail', STEEL)
