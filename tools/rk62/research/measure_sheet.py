"""Turn a side photo into a measurement sheet: rotate so the bore is level, scale to PX_MM px per mm, draw a 10 mm grid.
usage: measure_sheet.py in.jpg out.png x0 x1 (column range, in source px, where only the bare barrel is visible) length_mm [flip]"""
import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
src, out, x0, x1, length = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5])
flip = len(sys.argv) > 6
PX_MM = 4.0
im = Image.open(src).convert('RGB')
if flip: im = im.transpose(Image.FLIP_LEFT_RIGHT); x0, x1 = im.size[0] - x1, im.size[0] - x0
a = np.asarray(im).astype(int)
dark = (a.sum(2) < 600)                                   # not background
cols = np.arange(x0, x1, 4)
cy = np.array([np.nonzero(dark[:, c])[0].mean() for c in cols])
k, b = np.polyfit(cols, cy, 1)
ang = np.degrees(np.arctan(k))
rot = im.rotate(ang, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))
d = (np.asarray(rot).astype(int).sum(2) < 600)
xs = np.nonzero(d.any(0))[0]; ys = np.nonzero(d.any(1))[0]
Lpx = xs.max() - xs.min()
s = length * PX_MM / Lpx
rot = rot.crop((xs.min() - 20, ys.min() - 20, xs.max() + 20, ys.max() + 20))
rot = rot.resize((int(rot.size[0] * s), int(rot.size[1] * s)), Image.LANCZOS)
d = (np.asarray(rot).astype(int).sum(2) < 600)
xs = np.nonzero(d.any(0))[0]
muzzle = xs.max()
# bore row: centre of the barrel just behind the muzzle device (10% of length back from the tip)
c = int(muzzle - 0.10 * length * PX_MM)
rows = np.nonzero(d[:, c])[0]; bore = int(round(rows.mean()))
dr = ImageDraw.Draw(rot)
try: font = ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf', 13)
except Exception: font = ImageFont.load_default()
W, H = rot.size
for mm in range(-1000, 60, 10):
    x = muzzle + mm * PX_MM
    if 0 <= x < W:
        dr.line([(x, 0), (x, H)], fill=(255, 0, 0) if mm % 50 == 0 else (255, 170, 170), width=1)
        if mm % 50 == 0: dr.text((x + 2, 2), str(mm), fill=(200, 0, 0), font=font)
for mm in range(-300, 200, 10):
    y = bore - mm * PX_MM
    if 0 <= y < H:
        dr.line([(0, y), (W, y)], fill=(0, 0, 255) if mm % 50 == 0 else (170, 170, 255), width=1)
        if mm % 50 == 0: dr.text((2, y + 2), str(mm), fill=(0, 0, 200), font=font)
rot.save(out)
print(f"tilt {ang:.2f} deg, scale factor {s:.3f}, sheet {rot.size}, muzzle x={muzzle}, bore row={bore}")
