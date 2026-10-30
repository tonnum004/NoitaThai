"""Build Thai pixel fonts + shaped translation.csv for a Noita translation mod.

Noita draws text one codepoint at a time with no shaping, so Thai vowel/tone marks
cannot stack on their own. This script pre-renders every "cluster" (consonant +
marks) found in the translation as a single glyph in the Private Use Area and
rewrites the CSV to use those codepoints. Latin glyphs are copied from the game's
own pixel fonts so English text, numbers and symbols look unchanged.

Usage:
  python -I tools/build_thai_font.py --game "C:/Program Files (x86)/Steam/steamapps/common/Noita" --mod path/to/mods/thai

Edit translation_src.csv (created from translation.csv on the first run), then re-run.

Hand-drawn glyphs: add --export-sheets once to get <mod>/fonts_src/thai_11px.png and
thai_15px.png (white = ink, the lighter band = consonant body rows; cell order in the
matching .txt). Edit them in any pixel editor and build again: drawn cells replace the
TTF, empty cells fall back to it. Delete a sheet to go back to the TTF for that size.
"""
import argparse
import csv
import io
import os
import re
import shutil

from PIL import Image, ImageDraw, ImageFont

UPPER = set("\u0e31\u0e34\u0e35\u0e36\u0e37\u0e47\u0e4d")  # ั ิ ี ึ ื ็ ํ
TONE = set("\u0e48\u0e49\u0e4a\u0e4b\u0e4c\u0e4e")  # ่ ้ ๊ ๋ ์ ๎
LOWER = set("\u0e38\u0e39\u0e3a")  # ุ ู ฺ
MARKS = UPPER | TONE | LOWER
SARA_AM = "\u0e33"  # ำ = nikhahit over the base + า
BASES = {chr(c) for c in range(0x0E01, 0x0E2F)} | {"\u0e24", "\u0e26"}
TALL = set("ปฝฟฬชซศส")  # right-side ascender (tall or short): marks move left
PUA_START = 0xE000
THAI_SPACING = [chr(c) for c in range(0x0E01, 0x0E5C) if chr(c) not in MARKS and not 0x0E3B <= c <= 0x0E3E]
ATLAS_W = 2048

# (game font name, Thai body height in px (height of ก), cell height, baseline row, add 1px-down shadow)
FONTS = [
    ("font_pixel", 5, 11, 9, True),
    ("font_pixel_big", 5, 11, 9, False),
    ("font_pixel_huge", 7, 15, 12, False),
]


def size_for(ttf, body):
    """Largest TTF size whose ก is at most `body` px tall, so any Thai font fits the game's cells."""
    h = lambda s: (lambda b: b[3] - b[1])(ImageFont.truetype(ttf, s).getbbox("ก"))
    return max(s for s in range(4, 64) if h(s) <= body)


def clusters(text):
    """Split text into tokens; a cluster is base + marks (+ ำ). Other chars are single tokens."""
    out, i = [], 0
    while i < len(text):
        c = text[i]
        j = i + 1
        if c in BASES:
            while j < len(text) and text[j] in MARKS:
                j += 1
            if j < len(text) and text[j] == SARA_AM:
                j += 1
        out.append(text[i:j])
        i = j
    return out


def shape(text, table):
    """Replace multi-char clusters with PUA codepoints, adding new ones to table."""
    res = []
    for tok in clusters(text):
        if len(tok) > 1:
            if tok not in table:
                table[tok] = chr(PUA_START + len(table))
            tok = table[tok]
        res.append(tok)
    return "".join(res)


def ink(img):
    """Return (x0, y0, x1, y1) of white pixels or None."""
    return img.point(lambda p: 255 if p > 127 else 0).getbbox()


class Renderer:
    def __init__(self, ttf, size, cell_h, baseline, sheet=None):
        self.font = ImageFont.truetype(ttf, size)
        self.h, self.base = cell_h, baseline
        self.pad = 16
        self.sheet = sheet or {}  # hand-drawn glyphs override the TTF
        body = self.render("ก")[0]
        b = ink(body)
        self.body_top = b[1]  # first row of a normal consonant

    def render(self, ch):
        """Draw ch with its baseline at self.base; return (L image, x origin, advance)."""
        im = Image.new("L", (self.pad * 3, self.h), 0)
        if ch in self.sheet and ch not in MARKS:
            g = self.sheet[ch]
            im.paste(g, (self.pad, 0))
            return im, self.pad, g.width + 1  # 1px letter gap, like the game's pixel fonts
        d = ImageDraw.Draw(im)
        d.fontmode = "1"
        d.text((self.pad, self.base), ch, font=self.font, fill=255, anchor="ls")
        return im, self.pad, round(self.font.getlength(ch))

    def mark(self, ch):
        if ch in self.sheet:
            return self.sheet[ch]
        # tall canvas: some fonts (e.g. Sarabun) draw marks far above the cell
        im = Image.new("L", (self.pad * 3, self.h * 4), 0)
        d = ImageDraw.Draw(im)
        d.fontmode = "1"
        d.text((self.pad, self.h * 3), ch, font=self.font, fill=255, anchor="ls")
        b = ink(im)
        assert b, f"mark U+{ord(ch):04X} renders empty at size {self.font.size}; use a bigger size"
        return im.crop((b[0], b[1], b[2], b[3]))

    def glyph(self, ch):
        """Plain glyph: (image cropped to ink columns, offset_x, advance)."""
        im, ox, adv = self.render(ch)
        b = ink(im)
        if not b:
            return Image.new("L", (1, self.h), 0), 0, adv
        x0, x1 = min(b[0], ox), max(b[2], ox + adv)
        return im.crop((x0, 0, x1, self.h)), x0 - ox, adv

    def cluster(self, tok):
        """Compose base + stacked marks into one glyph image of width = advance."""
        base, marks = tok[0], tok[1:]
        am = marks.endswith(SARA_AM)
        if am:
            marks = marks[:-1] + "\u0e4d"  # nikhahit sits with the upper vowels
        im, ox, adv = self.render(base)
        b = ink(im) or (ox, 0, ox + adv, self.h)
        right = b[2] - (2 if base in TALL else 0)
        imgs = {m: self.mark(m) for m in marks}
        above = sum(g.height for m, g in imgs.items() if m not in LOWER)
        # a 1-row gap keeps a mark from merging into the consonant's stem, if there is room
        top = self.body_top - (1 if above < self.body_top else 0)
        # upper vowels first so a tone mark lands above them
        for m in sorted(marks, key=lambda m: m in TONE):
            g = imgs[m]
            if m in LOWER:
                # shortcut: ฎ ฏ ญ ฐ keep their descender under a lower vowel; real Thai fonts adjust it.
                y = self.base
            else:
                y = top - g.height
                top = y
            # 11px cells are tight: clamp inside the cell instead of clipping
            y = max(0, min(y, self.h - g.height))
            # tones sit 1px left so they don't continue a vowel's tail or the stem
            im.paste(255, (right - g.width - (1 if m in TONE else 0), y), g)
        if am:
            aa, _, aa_adv = self.render("\u0e32")
            a = ink(aa)
            im.paste(aa.crop((a[0], 0, a[2], self.h)), (ox + adv, 0), aa.crop((a[0], 0, a[2], self.h)))
            adv += aa_adv
        b = ink(im)
        x0, x1 = min(b[0], ox), max(b[2], ox + adv)
        return im.crop((x0, 0, x1, self.h)), x0 - ox, adv


# ๛ (U+0E5B) is too wide for a cell and almost never used: it always comes from the TTF
SHEET_CHARS = [c for c in THAI_SPACING if c != "๛"] + sorted(MARKS)
SHEET_COLS, SHEET_CW = 16, 14


def sheet_cell(i, h):
    return (i % SHEET_COLS) * SHEET_CW, (i // SHEET_COLS) * h


def squash(big, ch):
    """Render ch one body-row taller, then drop the body row most like the one above it.
    Tiny 1-bit renders fill Thai loops in; this keeps them open (a starting point for hand edits)."""
    g, _, _ = big.glyph(ch)
    w = g.width
    rows = [g.crop((0, y, w, y + 1)) for y in range(big.h)]
    body = range(big.body_top + 1, big.base)
    diff = lambda y: sum(a != b for a, b in zip(rows[y].tobytes(), rows[y - 1].tobytes()))
    mid = (big.body_top + big.base) / 2
    drop = min(body, key=lambda y: (diff(y), abs(y - mid)))
    out = Image.new("L", (w, big.h), 0)
    for i, y in enumerate([y for y in range(big.h) if y != drop]):
        out.paste(rows[y], (0, i + 1))
    return out


def export_sheet(r, path, big=None):
    """Write an editable grid: white = ink; the lighter band marks the consonant body rows.
    big: a Renderer one body-row taller; spacing glyphs are squashed from it."""
    if big:
        assert big.body_top == r.body_top - 1 and big.base == r.base
    rows = -(-len(SHEET_CHARS) // SHEET_COLS)
    im = Image.new("RGB", (SHEET_COLS * SHEET_CW, rows * r.h))
    for i, ch in enumerate(SHEET_CHARS):
        cx, cy = sheet_cell(i, r.h)
        bg = (40, 40, 70) if (i % SHEET_COLS + i // SHEET_COLS) % 2 else (70, 40, 40)
        for y in range(r.h):
            band = tuple(c + 25 for c in bg) if r.body_top <= y < r.base else bg
            im.paste(band, (cx, cy + y, cx + SHEET_CW, cy + y + 1))
        if ch in MARKS:
            g = r.mark(ch)
            y = r.base if ch in LOWER else max(0, r.body_top - 1 - g.height)
            im.paste((255, 255, 255), (cx + 1, cy + y), g)
        else:
            g = squash(big, ch) if big else r.glyph(ch)[0]
            b = ink(g)
            if b:
                assert b[2] - b[0] < SHEET_CW, f"{ch} is wider than a sheet cell"
                im.paste((255, 255, 255), (cx + 1, cy), g.crop((b[0], 0, b[2], r.h)))
    im.save(path)
    with open(os.path.splitext(path)[0] + ".txt", "w", encoding="utf-8") as f:
        f.write("cell order (row by row, 16 per row):\n")
        for i in range(0, len(SHEET_CHARS), SHEET_COLS):
            f.write(" ".join(("◌" + c) if c in MARKS else c for c in SHEET_CHARS[i:i + SHEET_COLS]) + "\n")


def load_sheet(path, h):
    """Read hand-edited glyphs. Bright pixels are ink; empty cells fall back to the TTF."""
    im = Image.open(path).convert("L")
    out = {}
    for i, ch in enumerate(SHEET_CHARS):
        cx, cy = sheet_cell(i, h)
        cell = im.crop((cx, cy, cx + SHEET_CW, cy + h)).point(lambda p: 255 if p > 127 else 0)
        b = cell.getbbox()
        if b:
            # marks: shape only (placement is computed); others: keep rows, trim columns
            out[ch] = cell.crop(b) if ch in MARKS else cell.crop((b[0], 0, b[2], h))
    return out


def load_game_font(game, name):
    xml = open(os.path.join(game, "data", "fonts", name + ".xml"), encoding="utf-8").read()
    png = Image.open(os.path.join(game, "data", "fonts", name + ".png")).convert("RGBA")
    head = xml[: xml.index("<QuadChar")]
    glyphs = {}
    for tag in re.findall(r"<QuadChar[^>]*>", xml):
        a = {k: int(v) for k, v in re.findall(r'(\w+)="(-?\d+)"', tag)}
        crop = png.crop((a["rect_x"], a["rect_y"], a["rect_x"] + a["rect_w"], a["rect_y"] + a["rect_h"]))
        glyphs[a["id"]] = (crop, a["offset_x"], a["offset_y"], a["width"])
    return head, glyphs


def to_rgba(l_img, shadow):
    """White glyph; optional black shadow 1px below, like the game's font_pixel."""
    w, h = l_img.size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px, src = out.load(), l_img.load()
    for y in range(h):
        for x in range(w):
            if src[x, y] > 127:
                px[x, y] = (255, 255, 255, 255)
            elif shadow and y > 0 and src[x, y - 1] > 127:
                px[x, y] = (0, 0, 0, 255)
    return out


def sheet_path(sheets_dir, cell_h):
    return os.path.join(sheets_dir, f"thai_{cell_h}px.png")


def build_font(game, mod_dir, rel_dir, spec, ttf, table, sheets_dir):
    name, body, cell_h, baseline, shadow = spec
    head, glyphs = load_game_font(game, name)
    sp = sheet_path(sheets_dir, cell_h)
    sheet = load_sheet(sp, cell_h) if os.path.exists(sp) else None
    r = Renderer(ttf, size_for(ttf, body), cell_h, baseline, sheet)
    for ch in THAI_SPACING + sorted(MARKS):
        im, ox, adv = r.glyph(ch)  # marks get advance 0 and negative offset: best-effort fallback
        glyphs[ord(ch)] = (to_rgba(im, shadow), ox, 0, adv)
    for tok, pua in table.items():
        im, ox, adv = r.cluster(tok)
        glyphs[ord(pua)] = (to_rgba(im, shadow), ox, 0, adv)

    # shelf-pack into rows of ATLAS_W
    row_h = max(g[0].height for g in glyphs.values())
    x = y = 0
    placed = []
    for cid in sorted(glyphs):
        img = glyphs[cid][0]
        if x + img.width > ATLAS_W:
            x, y = 0, y + row_h + 1
        placed.append((cid, x, y))
        x += img.width + 1
    atlas = Image.new("RGBA", (ATLAS_W, y + row_h), (0, 0, 0, 0))
    lines = [head.replace(f"data/fonts/{name}.png", f"{rel_dir}/{name}.png")]
    for cid, gx, gy in placed:
        img, ox, oy, adv = glyphs[cid]
        atlas.paste(img, (gx, gy))
        lines.append(
            f'  <QuadChar id="{cid}" offset_x="{ox}" offset_y="{oy}" rect_h="{img.height}" '
            f'rect_w="{img.width}" rect_x="{gx}" rect_y="{gy}" width="{adv}" >\n  </QuadChar>\n'
        )
    lines.append("</FontData>\n")
    out = os.path.join(mod_dir, "fonts")
    os.makedirs(out, exist_ok=True)
    atlas.save(os.path.join(out, name + ".png"))
    open(os.path.join(out, name + ".xml"), "w", encoding="utf-8", newline="\n").write("".join(lines))
    return atlas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True, help="Noita install folder")
    ap.add_argument("--mod", required=True, help="mod folder, e.g. <game>/mods/thai")
    ap.add_argument("--ttf", help="Thai TTF (default: the .ttf in the sheets folder, else Tahoma; "
                                  "Tahoma is Microsoft's: fine for testing, NOT for publishing)")
    ap.add_argument("--sheets", help="folder of hand-edited glyph sheets (default <mod>/fonts_src)")
    ap.add_argument("--export-sheets", action="store_true",
                    help="write editable sheets from --ttf (never overwrites) and stop")
    args = ap.parse_args()
    sheets_dir = args.sheets or os.path.join(args.mod, "fonts_src")
    if not args.ttf:
        bundled = sorted(f for f in os.listdir(sheets_dir) if f.endswith(".ttf")) if os.path.isdir(sheets_dir) else []
        args.ttf = os.path.join(sheets_dir, bundled[0]) if bundled else "C:/Windows/Fonts/tahoma.ttf"
    print("TTF:", args.ttf)

    if args.export_sheets:
        os.makedirs(sheets_dir, exist_ok=True)
        for name, body, cell_h, baseline, _ in FONTS:
            sp = sheet_path(sheets_dir, cell_h)
            if os.path.exists(sp):
                print("kept", sp)
                continue
            r = Renderer(args.ttf, size_for(args.ttf, body), cell_h, baseline)
            big = Renderer(args.ttf, size_for(args.ttf, body + 1), cell_h, baseline)
            export_sheet(r, sp, big if big.body_top == r.body_top - 1 else None)
            print("wrote", sp)
        return

    mod_id = os.path.basename(os.path.abspath(args.mod))
    src = os.path.join(args.mod, "translation_src.csv")
    dst = os.path.join(args.mod, "translation.csv")
    if not os.path.exists(src):
        shutil.copyfile(dst, src)  # first run: keep the editable original
        print("created", src, "(edit this file from now on)")

    rows = list(csv.reader(open(src, encoding="utf-8-sig", newline="")))
    table = {}
    for row in rows[1:]:
        for i in range(1, len(row)):
            # the game expects a literal \n, not a real line break inside a field
            row[i] = shape(row[i].replace("\r\n", "\\n").replace("\n", "\\n"), table)
    assert PUA_START + len(table) <= 0xF8FF, "too many clusters for the Private Use Area"
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    open(dst, "w", encoding="utf-8", newline="").write(buf.getvalue())

    rel = f"mods/{mod_id}/fonts"
    for spec in FONTS:
        build_font(args.game, args.mod, rel, spec, args.ttf, table, sheets_dir)

    xml_path = os.path.join(args.mod, "translation.xml")
    xml = open(xml_path, encoding="utf-8").read()
    for attr, name in [("font_default", "font_pixel"), ("font_inventory_title", "font_pixel_big"),
                       ("font_important_message_title", "font_pixel_huge"),
                       ("font_world_space_message", "font_pixel")]:
        xml = re.sub(rf'{attr}="[^"]*"', f'{attr}="{rel}/{name}.xml"', xml)
    if "fonts_pixel_font" not in xml:
        xml = xml.replace('fonts_utf8="1"', 'fonts_utf8="1"\n\tfonts_pixel_font="1"')
    open(xml_path, "w", encoding="utf-8", newline="\n").write(xml)
    print(f"{len(rows) - 1} rows, {len(table)} Thai clusters -> {dst}, fonts in {rel}")


if __name__ == "__main__":
    main()
