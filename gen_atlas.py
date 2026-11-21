#!/usr/bin/env python3
"""Generate fonts.bin for the news-image-20261120 entry.

Renders DejaVu glyphs at a large master size with PIL (build-time only;
the graded program reads fonts.bin and uses the stdlib only).

Format (FNT1, little-endian):
  magic b'FNT1', u16 n_fonts, then per font: u8 name_len, name,
  u16 n_chars, then per char: u32 codepoint, u16 advance, u16 w, u16 h,
  i16 ox, i16 oy, then w*h bytes of coverage 0..255.
"""
import struct
import sys
from PIL import Image, ImageDraw, ImageFont

MASTER = 80
FONTS = [
    ("serif_bold", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"),
    ("serif", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
    ("sans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ("sans_bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]

CHARS = list(range(32, 127)) + [
    0x2022,  # bullet
    0x2013,  # en dash
    0x2014,  # em dash
    0x2018, 0x2019,  # curly single quotes
    0x201C, 0x201D,  # curly double quotes
    0x00B7,  # middle dot
    0x00A3,  # pound
    0x20AC,  # euro
    0x00D7,  # multiply
    0x00B0,  # degree
    0x00B1,  # plus-minus
    0x00A5,  # yen
    0x2192,  # right arrow
    0x2713,  # check mark
]


def render_font(path):
    font = ImageFont.truetype(path, MASTER)
    glyphs = {}
    for cp in CHARS:
        ch = chr(cp)
        img = Image.new("L", (MASTER * 2, MASTER * 2), 0)
        d = ImageDraw.Draw(img)
        # Anchor at (10, 10); measure ink bbox and offsets.
        d.text((10, 10), ch, font=font, fill=255, anchor="la")
        bbox = img.getbbox()
        if bbox is None:
            glyphs[cp] = (font.getlength(ch), 0, 0, 0, 0, b"")
            continue
        x0, y0, x1, y1 = bbox
        w, h = x1 - x0, y1 - y0
        bmp = img.crop(bbox).tobytes()
        # Offset of the ink box relative to the draw origin (10, 10).
        ox, oy = x0 - 10, y0 - 10
        adv = font.getlength(ch)
        glyphs[cp] = (adv, w, h, ox, oy, bmp)
    return glyphs


def main(out_path):
    data = bytearray()
    data += b"FNT1"
    data += struct.pack("<H", len(FONTS))
    for name, path in FONTS:
        glyphs = render_font(path)
        nb = name.encode()
        data += struct.pack("<B", len(nb)) + nb
        data += struct.pack("<H", len(glyphs))
        for cp in sorted(glyphs):
            adv, w, h, ox, oy, bmp = glyphs[cp]
            data += struct.pack("<IHHHhh", cp, round(adv), w, h, ox, oy)
            data += bmp
    with open(out_path, "wb") as f:
        f.write(data)
    print("wrote", out_path, len(data), "bytes")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "fonts.bin")
