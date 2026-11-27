"""crop_sheet.py sheet.png muzzle_x bore_row out.png mm_x0 mm_x1 mm_z0 mm_z1 [zoom]  - crop a region given in sheet mm, label every 10 mm."""
import sys
from PIL import Image, ImageDraw, ImageFont
sheet, mx, br, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
x0, x1, z0, z1 = map(float, sys.argv[5:9]); zoom = float(sys.argv[9]) if len(sys.argv) > 9 else 1.0
P = 4.0
im = Image.open(sheet)
box = (int(mx + x0 * P), int(br - z1 * P), int(mx + x1 * P), int(br - z0 * P))
c = im.crop(box); c = c.resize((int(c.size[0] * zoom), int(c.size[1] * zoom)), Image.LANCZOS)
d = ImageDraw.Draw(c); f = ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf', 12)
mm = int(x0 // 10 * 10)
while mm <= x1:
    px = (mm - x0) * P * zoom
    if 0 <= px < c.size[0]: d.text((px + 2, 1), str(mm), fill=(220, 0, 0), font=f); d.text((px + 2, c.size[1] - 14), str(mm), fill=(220, 0, 0), font=f)
    mm += 10
mm = int(z0 // 10 * 10)
while mm <= z1:
    py = (z1 - mm) * P * zoom
    if 0 <= py < c.size[1]: d.text((1, py + 1), str(mm), fill=(0, 0, 220), font=f); d.text((c.size[0] - 26, py + 1), str(mm), fill=(0, 0, 220), font=f)
    mm += 10
c.save(out)
