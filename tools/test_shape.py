from build_thai_font import clusters, shape

assert clusters("กี่") == ["กี่"]
assert clusters("น้ำ") == ["น้ำ"]
assert clusters("เกม A") == ["เ", "ก", "ม", " ", "A"]
assert clusters("ปุ๋ย") == ["ปุ๋", "ย"]

t = {}
s = shape("กี่กี่ ก", t)
assert t == {"กี่": ""} and s == " ก"
shape("น้ำ", t)
assert t["น้ำ"] == ""
print("ok")

# sheet round trip: exported glyphs read back with the same ink
import os, tempfile
from build_thai_font import Renderer, export_sheet, load_sheet, ink, MARKS
ttf = os.environ.get("THAI_TTF", "C:/Windows/Fonts/tahoma.ttf")
r = Renderer(ttf, 10, 11, 9)
p = os.path.join(tempfile.mkdtemp(), "s.png")
export_sheet(r, p)
sheet = load_sheet(p, 11)
for ch in "กปฎญ":
    g, _, _ = r.glyph(ch)
    b = ink(g)
    assert g.crop((b[0], 0, b[2], 11)).tobytes() == sheet[ch].point(lambda v: 255 if v else 0).tobytes(), ch
for ch in "่ิุ":
    assert r.mark(ch).tobytes() == sheet[ch].tobytes(), ch
print("sheet ok")
