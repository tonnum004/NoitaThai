"""Render the same Thai lines with several TTFs at the game's pixel sizes, scaled x3.

python -I tools/compare_fonts.py out.png font1.ttf font2.ttf ...
"""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_thai_font import FONTS, Renderer, clusters, size_for

LINES = ["แผ่นจารึกมรกต - เล่มที่", "ความเร็วชาร์จมานา", "ห้องใต้ดินสัญลักษณ์", "ปุ๋ย ต่ำ เปิด ไทย ฎีกา"]

out, ttfs = sys.argv[1], sys.argv[2:]
shots = []
for ttf in ttfs:
    for name, body, h, base, _ in (FONTS[0], FONTS[2]):
        r = Renderer(ttf, size_for(ttf, body), h, base)
        img = Image.new("L", (260, h * len(LINES)), 0)
        for i, line in enumerate(LINES):
            x = 2
            for tok in clusters(line):
                if tok == " ":
                    x += 4
                    continue
                g, ox, adv = r.cluster(tok) if len(tok) > 1 else r.glyph(tok)
                img.paste(255, (x + ox, i * h), g.point(lambda p: 255 if p > 127 else 0))
                x += adv
        print(os.path.basename(ttf), name, "size", r.font.size)
        shots.append(img.resize((img.width * 3, img.height * 3), Image.NEAREST))

sheet = Image.new("L", (shots[0].width, sum(s.height + 10 for s in shots)), 60)
y = 0
for s in shots:
    sheet.paste(s, (0, y))
    y += s.height + 10
sheet.save(out)
