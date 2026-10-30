"""Draw sample lines with a built font the way Noita does (pen += width), scaled x4.

python -I tools/preview.py mods/thai preview/out.png "key1" "key2" ...
Lines are taken from the shaped translation.csv by key.
"""
import csv
import os
import re
import sys

from PIL import Image

mod, out, keys = sys.argv[1], sys.argv[2], sys.argv[3:]
rows = {r[0]: r[1] for r in csv.reader(open(os.path.join(mod, "translation.csv"), encoding="utf-8")) if len(r) > 1}
lines = [rows[k].split("\\n")[0][:60] for k in keys]

shots = []
for name in ["font_pixel", "font_pixel_huge"]:
    xml = open(os.path.join(mod, "fonts", name + ".xml"), encoding="utf-8").read()
    atlas = Image.open(os.path.join(mod, "fonts", name + ".png"))
    q = {}
    for tag in re.findall(r"<QuadChar[^>]*>", xml):
        a = {k: int(v) for k, v in re.findall(r'(\w+)="(-?\d+)"', tag)}
        q[a["id"]] = a
    h = max(a["rect_h"] for a in q.values())
    img = Image.new("RGBA", (420, (h + 2) * len(lines)), (60, 40, 50, 255))
    for i, line in enumerate(lines):
        x = 2
        for ch in line:
            a = q.get(ord(ch)) or q[ord("?")]
            g = atlas.crop((a["rect_x"], a["rect_y"], a["rect_x"] + a["rect_w"], a["rect_y"] + a["rect_h"]))
            img.alpha_composite(g, (x + a["offset_x"], i * (h + 2) + a["offset_y"]))
            x += a["width"]
    shots.append(img.resize((img.width * 4, img.height * 4), Image.NEAREST))

sheet = Image.new("RGBA", (shots[0].width, sum(s.height for s in shots) + 8), (0, 0, 0, 255))
y = 0
for s in shots:
    sheet.paste(s, (0, y))
    y += s.height + 8
sheet.save(out)
