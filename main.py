#!/usr/bin/env python3
"""THE WORLD IN ONE DAY - Friday 20 November 2026.

A dense one-page newspaper front page summing up the day's world news.
Pure Python 3 stdlib. Reads fonts.bin (DejaVu glyph atlas generated at
build time) from the same directory as this file. Writes one PNG to
$MAKEFUN_OUTPUT_DIR/entry.png (default /output/entry.png).

Deterministic: no randomness, no time, no network. Two runs write the
same bytes.
"""
import os
import struct
import sys
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 242, 231)
INK = (18, 18, 18)
INK_SOFT = (60, 58, 52)
GRAY = (110, 106, 96)
RULE = (40, 38, 34)
RED = (178, 34, 28)
RED_DARK = (140, 24, 20)
TINT = (236, 229, 212)
TINT2 = (228, 219, 196)
BLUE = (31, 74, 110)
BLUE_LT = (120, 165, 200)
GREEN = (46, 110, 70)
GOLD = (198, 158, 62)
ORANGE = (214, 110, 30)
SKY = (150, 190, 220)
SEA = (70, 120, 160)
NIGHT = (22, 34, 58)
NIGHT2 = (38, 56, 92)


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg=PAPER):
        self.w, self.h = w, h
        self.px = bytearray(bytes(bg) * (w * h))

    def _i(self, x, y):
        return (y * self.w + x) * 3

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._i(x, y)
            self.px[i:i + 3] = bytes(c)

    def blend(self, x, y, c, a):
        """Blend colour c over the pixel with alpha a (0..1)."""
        if 0 <= x < self.w and 0 <= y < self.h and a > 0:
            i = self._i(x, y)
            p = self.px
            p[i] = int(p[i] * (1 - a) + c[0] * a)
            p[i + 1] = int(p[i + 1] * (1 - a) + c[1] * a)
            p[i + 2] = int(p[i + 2] * (1 - a) + c[2] * a)

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = self._i(x0, yy)
            self.px[i:i + len(row)] = row

    def rect_outline(self, x, y, w, h, c, t=1):
        self.rect(x, y, w, t, c)
        self.rect(x, y + h - t, w, t, c)
        self.rect(x, y, t, h, c)
        self.rect(x + w - t, y, t, h, c)

    def disc(self, cx, cy, r, c, a=1.0):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    if a >= 1.0:
                        self.set(xx, yy, c)
                    else:
                        self.blend(xx, yy, c, a)

    def ring(self, cx, cy, r, c, t=1):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d2 = (xx - cx) ** 2 + (yy - cy) ** 2
                if (r - t) ** 2 <= d2 <= r * r:
                    self.set(xx, yy, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx, dy = x1 - x0, y1 - y0
        n = max(abs(dx), abs(dy), 1)
        for i in range(n + 1):
            x = x0 + dx * i / n
            y = y0 + dy * i / n
            for a in range(-(t // 2), t // 2 + 1):
                for b in range(-(t // 2), t // 2 + 1):
                    self.set(int(x) + a, int(y) + b, c)

    def polyline(self, pts, c, t=1):
        for i in range(len(pts) - 1):
            self.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], c, t)

    def polygon(self, pts, c):
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            for i in range(len(pts)):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % len(pts)]
                if y0 == y1:
                    continue
                if min(y0, y1) <= y < max(y0, y1):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                for x in range(max(0, int(xs[j])), min(self.w, int(xs[j + 1]) + 1)):
                    self.set(x, y, c)

    def vgrad(self, x, y, w, h, c0, c1):
        for yy in range(h):
            t = yy / max(1, h - 1)
            c = tuple(int(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))
            self.rect(x, y + yy, w, 1, c)

    def to_png(self):
        raw = bytearray()
        stride = self.w * 3
        for y in range(self.h):
            raw.append(0)
            raw += self.px[y * stride:(y + 1) * stride]
        comp = zlib.compress(bytes(raw), 6)

        def chunk(typ, data):
            c = struct.pack(">I", len(data)) + typ + data
            c += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
            return c

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# ---------------------------------------------------------------- fonts
MASTER = 80


def load_fonts(path):
    with open(path, "rb") as f:
        data = f.read()
    assert data[:4] == b"FNT1", "bad fonts.bin"
    off = 4
    n = struct.unpack_from("<H", data, off)[0]
    off += 2
    fonts = {}
    for _ in range(n):
        ln = data[off]
        off += 1
        name = data[off:off + ln].decode()
        off += ln
        nc = struct.unpack_from("<H", data, off)[0]
        off += 2
        glyphs = {}
        for _ in range(nc):
            cp, adv, w, h, ox, oy = struct.unpack_from("<IHHHhh", data, off)
            off += 14
            bmp = data[off:off + w * h]
            off += w * h
            glyphs[cp] = (adv, w, h, ox, oy, bmp)
        fonts[name] = glyphs
    return fonts


_GLYPH_CACHE = {}


def _scaled(fonts, name, size, ch):
    """(bitmap, w, h, advance, ox, oy) of ch at size px, area-averaged."""
    key = (name, size, ch)
    got = _GLYPH_CACHE.get(key)
    if got is not None:
        return got
    cp = ord(ch)
    g = fonts[name].get(cp)
    if g is None:
        g = fonts[name][ord("?")]
    adv, w, h, ox, oy = g[0], g[1], g[2], g[3], g[4]
    bmp = g[5]
    scale = size / MASTER
    sw = max(1, int(round(w * scale)))
    sh = max(1, int(round(h * scale)))
    out = bytearray(sw * sh)
    for yy in range(sh):
        sy0 = yy / scale
        sy1 = (yy + 1) / scale
        for xx in range(sw):
            sx0 = xx / scale
            sx1 = (xx + 1) / scale
            total = 0.0
            area = 0.0
            for sy in range(int(sy0), min(h, int(sy1) + 1)):
                wy = min(sy1, sy + 1) - max(sy0, sy)
                if wy <= 0:
                    continue
                for sx in range(int(sx0), min(w, int(sx1) + 1)):
                    wx = min(sx1, sx + 1) - max(sx0, sx)
                    if wx <= 0:
                        continue
                    total += bmp[sy * w + sx] * wx * wy
                    area += wx * wy
            out[yy * sw + xx] = int(total / area) if area > 0 else 0
    res = (bytes(out), sw, sh, adv * scale, ox * scale, oy * scale)
    _GLYPH_CACHE[key] = res
    return res


def text_width(fonts, name, size, text):
    tot = 0.0
    for ch in text:
        tot += _scaled(fonts, name, size, ch)[3]
    return tot


def draw_text(cv, fonts, name, size, x, y, text, col=INK):
    """Draw text with (x, y) = top-left of the ascender line."""
    cx = x
    for ch in text:
        bmp, w, h, adv, ox, oy = _scaled(fonts, name, size, ch)
        gx = int(round(cx + ox))
        gy = int(round(y + oy))
        for yy in range(h):
            py = gy + yy
            if py < 0 or py >= cv.h:
                continue
            for xx in range(w):
                v = bmp[yy * w + xx]
                if v:
                    cv.blend(gx + xx, py, col, v / 255.0)
        cx += adv
    return cx


def draw_centered(cv, fonts, name, size, cx, y, text, col=INK):
    w = text_width(fonts, name, size, text)
    return draw_text(cv, fonts, name, size, int(cx - w / 2), y, text, col)


def draw_tracked(cv, fonts, name, size, x, y, text, col=INK, track=1.0):
    cx = x
    for ch in text:
        cx = draw_text(cv, fonts, name, size, int(cx), y, ch, col)
        cx += track
    return cx


def wrap_text(fonts, name, size, text, max_w):
    """Greedy word wrap. Returns a list of lines."""
    lines = []
    for para in text.split("\n"):
        words = para.split()
        if not words:
            lines.append("")
            continue
        cur = words[0]
        for wd in words[1:]:
            trial = cur + " " + wd
            if text_width(fonts, name, size, trial) <= max_w:
                cur = trial
            else:
                lines.append(cur)
                cur = wd
        lines.append(cur)
    return lines


def draw_block(cv, fonts, name, size, x, y, text, max_w, leading, col=INK):
    """Draw a wrapped block; returns the y just below the last line."""
    lines = wrap_text(fonts, name, size, text, max_w)
    for i, ln in enumerate(lines):
        draw_text(cv, fonts, name, size, x, y + i * leading, ln, col)
    return y + len(lines) * leading


# ---------------------------------------------------------------- drawings
# Every scene is drawn from primitives. No external images.

def _stars(cv, x, y, w, h, n=24):
    pts = [(13, 9), (47, 22), (88, 6), (120, 18), (160, 8), (195, 20),
           (230, 7), (262, 24), (290, 10), (30, 40), (70, 48), (110, 38),
           (150, 46), (185, 36), (220, 48), (255, 40), (280, 52),
           (18, 62), (55, 70), (95, 60), (135, 68), (175, 60), (210, 70),
           (245, 62)]
    for i in range(min(n, len(pts))):
        sx, sy = pts[i]
        if sx < w and sy < h:
            cv.disc(x + sx, y + sy, 1, (235, 235, 225))


def draw_kyiv(cv, fonts, x, y, w, h):
    cv.vgrad(x, y, w, h, NIGHT, NIGHT2)
    _stars(cv, x, y, w, h)
    # city windows
    for bx, by in [(20, 80), (36, 84), (58, 78), (240, 82), (262, 78), (282, 84)]:
        cv.rect(x + bx, y + by, 4, 5, GOLD)
    # bridge deck and arches
    cv.rect(x, y + h - 26, w, 6, (12, 14, 22))
    for ax in (40, 130, 220):
        cv.line(x + ax, y + h - 26, x + ax + 45, y + h - 26, (12, 14, 22), 3)
    cv.line(x + 40, y + h - 26, x + 62, y + h - 58, (12, 14, 22), 3)
    cv.line(x + 85, y + h - 26, x + 62, y + h - 58, (12, 14, 22), 3)
    cv.line(x + 130, y + h - 26, x + 152, y + h - 62, (12, 14, 22), 3)
    cv.line(x + 175, y + h - 26, x + 152, y + h - 62, (12, 14, 22), 3)
    cv.line(x + 220, y + h - 26, x + 242, y + h - 56, (12, 14, 22), 3)
    cv.line(x + 265, y + h - 26, x + 242, y + h - 56, (12, 14, 22), 3)
    # explosion bursts
    for ex, ey, r in [(62, 52, 14), (152, 46, 17), (242, 54, 12)]:
        cv.disc(x + ex, y + ey, r + 6, ORANGE, 0.35)
        cv.disc(x + ex, y + ey, r, (240, 150, 40))
        cv.disc(x + ex, y + ey, r - 6, (250, 210, 90))
        for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1), (0, -1), (0, 1)]:
            cv.line(x + ex, y + ey, x + ex + dx * (r + 12), y + ey + dy * (r + 12),
                    (250, 200, 90), 1)
    # missile trails
    cv.line(x + 20, y + 10, x + 55, y + 44, (255, 255, 255), 1)
    cv.line(x + 300, y + 8, x + 258, y + 44, (255, 255, 255), 1)
    cv.disc(x + 20, y + 10, 2, (255, 255, 255))
    cv.disc(x + 300, y + 8, 2, (255, 255, 255))


def draw_cyclone(cv, fonts, x, y, w, h):
    cv.vgrad(x, y, w, h, (90, 140, 185), SEA)
    # coastline (sand) bottom right
    cv.polygon([(x + 170, y + h), (x + 200, y + 78), (x + 240, y + 92),
                (x + 280, y + 80), (x + w, y + 96), (x + w, y + h)],
               (214, 196, 150))
    cv.polygon([(x + 200, y + 78), (x + 240, y + 92), (x + 280, y + 80),
                (x + w, y + 96), (x + w, y + 88), (x + 280, y + 72),
                (x + 240, y + 84), (x + 200, y + 70)], (240, 225, 180))
    # spiral
    cx, cy = x + 120, y + 62
    for r in range(8, 58, 9):
        a0 = r * 0.35
        pts = []
        for k in range(0, 26):
            a = a0 + k * 0.22
            rr = r * (1 - k * 0.012)
            pts.append((int(cx + rr * 0.95 * _cos(a)), int(cy + rr * 0.8 * _sin(a))))
        cv.polyline(pts, (240, 244, 248), 2)
    cv.disc(cx, cy, 7, (240, 244, 248))
    # rain
    for rx, ry in [(30, 20), (60, 40), (90, 15), (250, 30), (280, 55), (210, 20),
                   (40, 90), (300, 90), (260, 110), (20, 110)]:
        cv.line(x + rx, y + ry, x + rx - 6, y + ry + 12, (200, 220, 235), 1)
    # land label area: small houses
    for hx in (215, 245, 272):
        cv.rect(x + hx, y + 108, 14, 10, (120, 70, 50))
        cv.polygon([(x + hx - 2, y + 108), (x + hx + 7, y + 100),
                    (x + hx + 16, y + 108)], (90, 50, 40))


def _cos(a):
    import math
    return math.cos(a)


def _sin(a):
    import math
    return math.sin(a)


def draw_selloff(cv, fonts, x, y, w, h):
    cv.rect(x, y, w, h, (250, 246, 238))
    # grid
    for gy in range(4):
        yy = y + 18 + gy * 26
        cv.line(x + 8, yy, x + w - 8, yy, (220, 214, 200), 1)
    # descending bars
    vals = [86, 74, 78, 60, 52, 40, 30]
    bw = (w - 24) // len(vals)
    for i, v in enumerate(vals):
        bx = x + 12 + i * bw
        bh = int(v * (h - 40) / 100)
        cv.rect(bx, y + h - 14 - bh, bw - 6, bh, (190, 60, 45) if i >= 4 else (210, 120, 90))
    # falling line
    pts = [(x + 16, y + 16), (x + 60, y + 30), (x + 105, y + 26),
           (x + 150, y + 48), (x + 195, y + 62), (x + 240, y + 74),
           (x + 285, y + 96), (x + w - 12, y + h - 22)]
    cv.polyline(pts, RED_DARK, 3)
    for px, py in pts:
        cv.disc(px, py, 3, RED_DARK)
    # down arrow
    ax, ay = x + w - 34, y + 8
    cv.line(ax + 8, ay, ax + 8, ay + 14, RED, 3)
    cv.polygon([(ax - 2, ay + 12), (ax + 18, ay + 12), (ax + 8, ay + 26)],
               RED)


def draw_ukeu(cv, fonts, x, y, w, h):
    cv.rect(x, y, w, h, TINT)
    # Union Jack (simplified)
    fx, fy, fw, fh = x + 12, y + 14, 74, 44
    cv.rect(fx, fy, fw, fh, (30, 60, 130))
    cv.line(fx, fy, fx + fw, fy + fh, (255, 255, 255), 6)
    cv.line(fx + fw, fy, fx, fy + fh, (255, 255, 255), 6)
    cv.rect(fx + fw // 2 - 4, fy, 8, fh, (200, 40, 40))
    cv.rect(fx, fy + fh // 2 - 4, fw, 8, (200, 40, 40))
    # EU flag
    ex, ey, ew, eh = x + w - 86, y + 14, 74, 44
    cv.rect(ex, ey, ew, eh, (20, 50, 130))
    for k in range(12):
        a = k * 3.14159 / 6
        sx = int(ex + ew / 2 + 13 * _cos(a))
        sy = int(ey + eh / 2 + 13 * _sin(a))
        cv.disc(sx, sy, 2, GOLD)
    # gold link arc
    cv.line(x + 92, y + 36, x + w - 92, y + 36, GOLD, 3)
    cv.disc(x + w // 2, y + 36, 5, GOLD)
    draw_centered(cv, fonts, "sans_bold", 10, x + w // 2, y + h - 16,
                  "DEAL IN BRUSSELS", INK)


def draw_cop(cv, fonts, x, y, w, h):
    cv.rect(x, y, w, h, TINT)
    # globe
    cx, cy, r = x + 52, y + 36, 26
    cv.disc(cx, cy, r, (90, 150, 200))
    cv.polygon([(cx - 18, cy - 8), (cx - 4, cy - 16), (cx + 8, cy - 6),
                (cx - 2, cy + 4), (cx - 14, cy + 2)], GREEN)
    cv.polygon([(cx + 4, cy + 8), (cx + 18, cy + 2), (cx + 16, cy + 16),
                (cx + 2, cy + 20), (cx - 4, cy + 12)], GREEN)
    cv.ring(cx, cy, r, BLUE, 2)
    # thermometer
    tx, ty = x + 108, y + 12
    cv.rect(tx, ty, 10, 40, (255, 255, 255))
    cv.rect_outline(tx, ty, 10, 40, INK, 1)
    cv.rect(tx + 2, ty + 22, 6, 16, RED)
    cv.disc(tx + 5, ty + 44, 8, RED)
    cv.disc(tx + 5, ty + 44, 5, (255, 120, 100))
    # empty document
    dx, dy = x + 138, y + 14
    cv.rect(dx, dy, 42, 44, (255, 255, 255))
    cv.rect_outline(dx, dy, 42, 44, INK, 1)
    for i in range(3):
        cv.line(dx + 6, dy + 10 + i * 8, dx + 36, dy + 10 + i * 8, (200, 196, 186), 2)
    cv.line(dx + 6, dy + 8, dx + 36, dy + 50, RED, 2)
    cv.line(dx + 36, dy + 8, dx + 6, dy + 50, RED, 2)
    draw_centered(cv, fonts, "sans_bold", 10, x + w // 2, y + h - 16,
                  "NO DEAL ON THE LAST DAY", INK)


def draw_japan(cv, fonts, x, y, w, h):
    cv.rect(x, y, w, h, TINT)
    vals = [30, 38, 34, 46, 54, 62]
    bw = (w - 24) // len(vals)
    for i, v in enumerate(vals):
        bx = x + 12 + i * bw
        bh = int(v * (h - 34) / 100)
        cv.rect(bx, y + h - 18 - bh, bw - 5, bh, GREEN if i < 5 else RED)
    # yen sign
    draw_centered(cv, fonts, "sans_bold", 22, x + w - 34, y + 6, "\u00a5", INK)
    draw_centered(cv, fonts, "sans_bold", 10, x + w // 2, y + h - 16,
                  "PRICES UP 2.3%", INK)


def draw_cricket(cv, fonts, x, y, w, h):
    cv.rect(x, y, w, h, (120, 170, 100))
    # pitch
    cv.rect(x + 30, y + 8, w - 60, h - 20, (205, 180, 130))
    # stumps
    for sx in (x + 44, x + 50, x + 56):
        cv.line(sx, y + 16, sx, y + 34, (230, 200, 90), 2)
    cv.line(x + 44, y + 15, x + 56, y + 15, (230, 200, 90), 2)
    # bat (angled)
    cv.polygon([(x + 120, y + 18), (x + 132, y + 14), (x + 150, y + 40),
                (x + 140, y + 46)], (150, 105, 60))
    cv.line(x + 126, y + 16, x + 116, y + 6, (120, 85, 50), 3)
    # ball
    cv.disc(x + 162, y + 52, 6, (180, 40, 30))
    cv.disc(x + 160, y + 50, 2, (240, 120, 100))
    draw_centered(cv, fonts, "sans_bold", 10, x + w // 2, y + h - 16,
                  "A CENTURY IN 3 FORMATS", INK)


def draw_oil(cv, fonts, x, y, w, h):
    cv.vgrad(x, y, w, h, (240, 200, 130), (225, 170, 95))
    cv.disc(x + w - 34, y + 22, 14, (250, 220, 120))
    # derrick
    bx, by = x + 70, y + h - 16
    cv.polygon([(bx, by - 52), (bx + 44, by - 52), (bx + 30, by),
                (bx + 14, by)], (40, 36, 32))
    cv.line(bx + 6, by - 12, bx + 38, by - 40, (90, 80, 70), 2)
    cv.line(bx + 38, by - 12, bx + 6, by - 40, (90, 80, 70), 2)
    cv.line(bx + 22, by - 52, bx + 22, by - 62, (40, 36, 32), 3)
    # ground
    cv.rect(x, y + h - 16, w, 8, (180, 130, 70))
    draw_centered(cv, fonts, "sans_bold", 10, x + w // 2, y + h - 16,
                  "FIRST CRUDE DUE 1 DEC", INK)


def draw_ballot(cv, fonts, x, y, w, h):
    cv.rect(x, y, w, h, TINT)
    # ballot box
    bx, by, bw, bh = x + 62, y + 16, 68, 40
    cv.rect(bx, by, bw, bh, BLUE)
    cv.rect(bx, by, bw, 8, (24, 58, 92))
    cv.rect(bx + 20, by + 2, 28, 4, (12, 12, 12))
    # paper going in
    cv.polygon([(bx + 26, by - 8), (bx + 48, by - 8), (bx + 48, by + 4),
                (bx + 26, by + 4)], (255, 255, 255))
    cv.line(bx + 30, by - 4, bx + 44, by - 4, GRAY, 1)
    # check mark
    cv.line(bx + 78, by + 18, bx + 86, by + 28, GREEN, 3)
    cv.line(bx + 86, by + 28, bx + 102, by + 8, GREEN, 3)
    draw_centered(cv, fonts, "sans_bold", 10, x + w // 2, y + h - 16,
                  "VOTE 28 FEB 2027", INK)


def draw_strike(cv, fonts, x, y, w, h):
    cv.rect(x, y, w, h, TINT)
    # marchers
    cols = [(178, 34, 28), (31, 74, 110), (46, 110, 70), (120, 70, 50),
            (90, 90, 110)]
    for i, c in enumerate(cols):
        px = x + 22 + i * 34
        cv.disc(px + 8, y + 20, 7, (210, 180, 150))
        cv.rect(px, y + 28, 16, 22, c)
        cv.line(px + 2, y + 50, px + 2, y + 60, INK, 2)
        cv.line(px + 14, y + 50, px + 14, y + 60, INK, 2)
    # placards
    cv.rect(x + 30, y + 8, 34, 12, (255, 255, 255))
    cv.rect_outline(x + 30, y + 8, 34, 12, INK, 1)
    cv.rect(x + 120, y + 6, 34, 12, (255, 255, 255))
    cv.rect_outline(x + 120, y + 6, 34, 12, INK, 1)
    cv.line(x + 46, y + 20, x + 46, y + 26, INK, 2)
    cv.line(x + 136, y + 18, x + 136, y + 26, INK, 2)
    draw_centered(cv, fonts, "sans_bold", 10, x + w // 2, y + h - 16,
                  "1M IN 100+ SQUARES", INK)


def draw_nvidia(cv, fonts, x, y, w, h):
    cv.rect(x, y, w, h, TINT)
    # chip
    cx, cy, s = x + 62, y + 10, 44
    for k in range(5):
        cv.line(cx - 8, cy + 5 + k * 8, cx - 2, cy + 5 + k * 8, INK, 2)
        cv.line(cx + s + 2, cy + 5 + k * 8, cx + s + 8, cy + 5 + k * 8, INK, 2)
    cv.rect(cx, cy, s, s, (20, 60, 40))
    cv.rect_outline(cx, cy, s, s, INK, 2)
    cv.rect(cx + 12, cy + 12, s - 24, s - 24, (60, 140, 90))
    draw_centered(cv, fonts, "sans_bold", 12, cx + s // 2, cy + s // 2 - 6,
                  "AI", (255, 255, 255))
    # red down arrow
    ax, ay = x + w - 52, y + 10
    cv.polygon([(ax, ay + 26), (ax + 10, ay + 26), (ax + 10, ay + 44),
                (ax + 20, ay + 44), (ax + 20, ay + 26), (ax + 30, ay + 26),
                (ax + 15, ay + 52), (ax, ay + 26)], RED)
    draw_centered(cv, fonts, "sans_bold", 10, x + w // 2, y + h - 16,
                  "$491BN WIPED OUT", INK)


def draw_china(cv, fonts, x, y, w, h):
    cv.rect(x, y, w, h, TINT)
    # bank building
    bx, by, bw, bh = x + 52, y + 12, 88, 42
    cv.polygon([(bx - 6, by), (bx + bw // 2, by - 10), (bx + bw + 6, by)],
               (150, 40, 40))
    cv.rect(bx, by, bw, bh, (235, 225, 205))
    cv.rect_outline(bx, by, bw, bh, INK, 1)
    for i in range(4):
        cx = bx + 10 + i * 22
        cv.rect(cx, by + 6, 8, bh - 12, INK)
    cv.rect(bx - 4, by + bh, bw + 8, 4, INK)
    draw_centered(cv, fonts, "sans_bold", 10, x + w // 2, y + h - 16,
                  "3.0% AND 3.5% HELD", INK)


def draw_tanker(cv, fonts, x, y, w, h):
    cv.vgrad(x, y, w, h, (140, 180, 210), SEA)
    # waves
    for wx in range(x + 6, x + w - 6, 22):
        cv.line(wx, y + h - 2, wx + 12, y + h - 2, (220, 235, 245), 2)
    # tanker hull
    cv.polygon([(x + 30, y + 42), (x + 160, y + 42), (x + 150, y + 60),
                (x + 40, y + 60)], (30, 30, 36))
    cv.rect(x + 40, y + 24, 110, 18, (50, 50, 58))
    cv.rect(x + 130, y + 12, 16, 12, (50, 50, 58))
    cv.line(x + 138, y + 12, x + 138, y + 2, (50, 50, 58), 3)
    # fire plume
    for fx, fy, r, c in [(70, 24, 10, ORANGE), (78, 18, 8, (240, 150, 40)),
                         (72, 12, 5, (250, 210, 90))]:
        cv.disc(x + fx, y + fy, r, c, 0.9)
    cv.disc(x + 80, y + 8, 10, (90, 90, 95), 0.5)
    draw_centered(cv, fonts, "sans_bold", 10, x + w // 2, y + h - 16,
                  "8 MILES OFF KHASAB", INK)


# ---------------------------------------------------------------- world map
CONTINENTS = [
    # North America
    [(-168, 66), (-140, 70), (-125, 71), (-110, 68), (-95, 69), (-85, 66),
     (-80, 73), (-65, 60), (-55, 52), (-60, 46), (-70, 42), (-75, 35),
     (-80, 32), (-85, 29), (-90, 21), (-95, 19), (-100, 16), (-105, 20),
     (-110, 24), (-115, 30), (-125, 40), (-125, 48), (-135, 58),
     (-155, 58), (-165, 60)],
    # Greenland
    [(-58, 64), (-45, 60), (-30, 68), (-25, 70), (-40, 76), (-58, 76)],
    # South America
    [(-80, 10), (-75, 11), (-70, 12), (-62, 10), (-55, 6), (-50, 0),
     (-44, -3), (-35, -8), (-38, -15), (-40, -22), (-48, -28), (-55, -35),
     (-62, -41), (-68, -50), (-70, -54), (-73, -50), (-73, -40),
     (-72, -30), (-70, -18), (-77, -12), (-80, -5), (-81, 0), (-80, 8)],
    # Europe
    [(-10, 36), (-9, 43), (-2, 48), (-4, 50), (0, 51), (3, 53), (8, 57),
     (10, 59), (18, 56), (21, 55), (24, 59), (28, 60), (30, 62), (25, 65),
     (20, 70), (15, 68), (12, 62), (5, 60), (-5, 58), (-10, 54),
     (-10, 48), (-9, 43), (-2, 37), (-6, 36)],
    # Africa
    [(-17, 15), (-15, 27), (-10, 31), (-5, 35), (10, 37), (20, 32),
     (30, 31), (32, 28), (35, 28), (37, 22), (40, 15), (43, 11), (48, 11),
     (51, 10), (46, 5), (40, -2), (38, -10), (35, -18), (32, -26),
     (28, -33), (20, -35), (16, -28), (12, -18), (12, -8), (9, 4),
     (4, 6), (-8, 4), (-13, 8), (-17, 12)],
    # Asia
    [(30, 62), (40, 68), (60, 69), (80, 72), (100, 77), (110, 74),
     (130, 72), (150, 70), (170, 66), (178, 65), (170, 60), (162, 56),
     (158, 52), (150, 59), (142, 55), (140, 50), (135, 44), (130, 42),
     (127, 40), (122, 38), (120, 32), (122, 28), (118, 25), (110, 20),
     (108, 12), (105, 8), (100, 7), (98, 10), (95, 15), (92, 21),
     (90, 22), (88, 22), (85, 19), (80, 15), (76, 10), (75, 8), (72, 20),
     (68, 22), (62, 25), (58, 26), (56, 27), (52, 28), (50, 29),
     (48, 30), (44, 29), (40, 25), (38, 22), (35, 28), (34, 27),
     (32, 28), (30, 36), (27, 37), (26, 38), (23, 36), (22, 37),
     (26, 40), (28, 42), (30, 46), (30, 52), (28, 58)],
    # Australia
    [(113, -22), (114, -30), (115, -34), (120, -34), (124, -33),
     (129, -32), (132, -32), (135, -35), (138, -35), (140, -38),
     (145, -38), (150, -37), (153, -32), (153, -27), (150, -23),
     (146, -19), (142, -15), (142, -11), (136, -12), (132, -11),
     (130, -13), (126, -14), (122, -17), (118, -20), (113, -22)],
    # United Kingdom
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53), (-1, 51)],
    # Japan
    [(130, 31), (132, 33), (135, 34), (137, 35), (139, 36), (140, 38),
     (141, 40), (142, 42), (144, 44), (141, 45), (140, 43), (139, 41),
     (137, 38), (135, 36), (133, 34), (130, 33)],
    # New Zealand
    [(167, -45), (170, -43), (173, -41), (175, -38), (177, -38),
     (178, -37), (175, -40), (172, -42), (168, -46)],
]


def draw_map(cv, fonts, x, y, w, h, pins):
    cv.rect(x, y, w, h, (214, 228, 235))
    cv.rect_outline(x, y, w, h, RULE, 1)
    for poly in CONTINENTS:
        pts = []
        for lon, lat in poly:
            px = x + int((lon + 180) / 360 * w)
            py = y + int((75 - lat) / 130 * h)
            pts.append((px, py))
        cv.polygon(pts, (196, 188, 160))
    # graticule
    for lon in (-120, -60, 0, 60, 120):
        gx = x + int((lon + 180) / 360 * w)
        cv.line(gx, y, gx, y + h, (190, 205, 218), 1)
    for lat in (60, 30, 0, -30):
        gy = y + int((75 - lat) / 130 * h)
        cv.line(x, gy, x + w, gy, (190, 205, 218), 1)
    # pins
    for num, lon, lat in pins:
        px = x + int((lon + 180) / 360 * w)
        py = y + int((75 - lat) / 130 * h)
        cv.disc(px, py, 6, RED)
        cv.ring(px, py, 6, (255, 255, 255), 1)
        tw = text_width(fonts, "sans_bold", 7, str(num))
        draw_text(cv, fonts, "sans_bold", 7, int(px - tw / 2), py - 4,
                  str(num), (255, 255, 255))


# ---------------------------------------------------------------- stories
# Every fact below was verified against a live source on 20-21 Nov 2026.
# Decks are trimmed so they wrap to at most 3 lines in their column.

HEROES = [
    dict(tag="UKRAINE \u00b7 WAR", draw=draw_kyiv,
         headline="Missiles hit three Kyiv bridges",
         deck="Russia's biggest barrage of November: 111 missiles and 404 "
              "drones overnight. Nine killed, power and water cut; a Kh-101 "
              "falls in Poland.",
         source="Kyiv Independent \u00b7 BBC \u00b7 Reuters"),
    dict(tag="INDIA \u00b7 WEATHER", draw=draw_cyclone,
         headline="Cyclone Akvan strikes Odisha",
         deck="Landfall near Gopalpur at 02:00 UTC with 80 km/h winds. Over "
              "300,000 people moved to 9,341 shelters; 209 mm of rain at "
              "Patrapur.",
         source="IMD \u00b7 Deccan Herald"),
    dict(tag="MARKETS \u00b7 TECH", draw=draw_selloff,
         headline="The AI trade unwinds in Asia",
         deck="Taiwan's Taiex falls 6.2% to 36,033 in its worst week since "
              "1991. Seoul -5.2%, Tokyo -5.1%, Hong Kong -1.9% as chipmakers "
              "lead the slide.",
         source="Al Jazeera \u00b7 Anadolu \u00b7 Reuters"),
]

FEATURES = [
    dict(tag="BRUSSELS", draw=draw_ukeu,
         headline="UK and EU seal the reset deal",
         deck="Burnham in Brussels: food deal, youth mobility for 100,000 "
              "under-32s, emissions link. Worth ~\u00a317bn.",
         source="Reuters \u00b7 CNN"),
    dict(tag="ANTALYA", draw=draw_cop,
         headline="COP31 ends its last day with no deal",
         deck="The revised draft drops all fossil-fuel references and the "
              "$120bn figure. Talks run past Friday.",
         source="UN News \u00b7 AP"),
    dict(tag="TOKYO", draw=draw_japan,
         headline="Japan inflation at 2.3%",
         deck="October CPI rises from 2.1%; core 2.2%. A December rise is in "
              "view; the Bank of Japan rate is 1.25%.",
         source="Statistics Bureau \u00b7 Reuters"),
    dict(tag="WELLINGTON", draw=draw_cricket,
         headline="Phillips makes 118 in Wellington",
         deck="Tons in all three formats v India in a year: ODI 106, T20I "
              "107, Test 118. A first for New Zealand.",
         source="ICC \u00b7 AP"),
    dict(tag="TURKANA", draw=draw_oil,
         headline="Kenya switches on its first oil",
         deck="Rigs start in Turkana; first crude due 1 December at 20,000 "
              "barrels a day. Ruto flags off the cargo.",
         source="People Daily \u00b7 Pulse"),
    dict(tag="SAN SALVADOR", draw=draw_ballot,
         headline="Bukele files for a third term",
         deck="The president registers his candidacy with VP Felix Ulloa "
              "beside him. The vote is on 28 February 2027.",
         source="Reuters \u00b7 AP"),
    dict(tag="ROME", draw=draw_strike,
         headline="Italy stops for a general strike",
         deck="CGIL's 24-hour strike over the 2027 budget draws more than a "
              "million people to 100-plus squares.",
         source="Reuters \u00b7 CGIL"),
    dict(tag="NEW YORK", draw=draw_nvidia,
         headline="Nvidia falls 14% in a day",
         deck="Shares drop to $125.53 after Reuters reports the SEC is "
              "examining its accounting. $491bn wiped out.",
         source="Reuters \u00b7 Motley Fool"),
    dict(tag="BEIJING", draw=draw_china,
         headline="China holds its lending rates",
         deck="LPR held at 3.0% and 3.5%, unchanged for an 18th straight "
              "month. The repo is the anchor.",
         source="Xinhua \u00b7 Reuters"),
    dict(tag="KHASAB", draw=draw_tanker,
         headline="Tanker ablaze off Oman",
         deck="A tanker is struck by an unknown projectile 8 nautical miles "
              "north of Khasab. Fire on board; no casualties.",
         source="UKMTO \u00b7 Reuters"),
]

STATS = [
    ("111", "MISSILES AT UKRAINE"),
    ("300,000+", "MOVED TO SHELTERS"),
    ("-6.2%", "TAIWAN INDEX, ONE DAY"),
    ("-14%", "NVIDIA IN A DAY"),
    ("1,070", "ARGENTINA RISK (BP)"),
    ("118", "PHILLIPS, WELLINGTON"),
]

ALSO = [
    ("Lviv", "station strike kills two, ten in hospital", "Mayor Sadovyi"),
    ("Poland", "Kh-101 missile crashes in Nowy Lipowiec", "Reuters"),
    ("Ganjam", "209 mm rain falls at Patrapur", "IMD"),
    ("Seoul", "KOSPI falls 5.2% as chipmakers slide", "Anadolu"),
    ("Tokyo", "SoftBank down 14.5%, worst since 2024", "CNBC"),
    ("Hong Kong", "Hang Seng off 1.9%", "Anadolu"),
    ("New York", "Nasdaq -5.3%, S&P 500 in correction", "Investopedia"),
    ("UK-EU", "tuition fees parked in the reset deal", "Reuters"),
    ("COP31", "draft cut from 144 to 80 paragraphs", "AP"),
    ("Japan", "BoJ rate 1.25%; December rise in view", "Reuters"),
    ("Kenya", "Ruto names crude's trading name 1 Dec", "People Daily"),
    ("Bukele", "four rivals line up for 28 Feb vote", "Reuters"),
    ("Italy", "rail freight halts 23 hours from 21:00", "ANSA"),
    ("Nvidia", "seventh straight weekly fall", "Dealroom"),
    ("China", "overnight repo is the policy anchor", "Reuters"),
    ("Hormuz", "shipping traffic down 15%", "ShipUniverse"),
    ("Pakistan", "India holds its Indus treaty stand", "Asia Daily"),
    ("Seoul", "impeachment motion due at court by 7 Dec", "JoongAng"),
    ("Argentina", "risk up 139 points in a day", "J.P. Morgan"),
    ("Barcelona", "8.2% saw tumours vanish", "ecancer"),
    ("Las Vegas", "Russell fastest in practice, 1:34.041", "Formula 1"),
    ("Anthropic", "shares slide on day two after IPO", "Investopedia"),
]

# (number, lon, lat) - story order 1-13; Wellington pin nudged west so
# its disc stays inside the map frame.
PINS = [
    (1, 30.5, 50.5), (2, 85.0, 19.5), (3, 121.5, 25.0),
    (4, 4.4, 50.8), (5, 30.7, 36.9), (6, 139.7, 35.7),
    (7, 168.0, -41.3), (8, 36.0, 3.0), (9, -89.2, 13.7),
    (10, 12.5, 41.9), (11, -74.0, 40.7), (12, 116.4, 39.9),
    (13, 56.2, 26.2),
]

DATE_CHECK = [
    "DATE CHECK \u2014 Left out: Uganda's Ebola measures, announced Thursday "
    "19 November; BepiColombo's Mercury capture, due Saturday 21 November, "
    "had not happened yet.",
    "Everything on this page happened, or was first reported, on Friday "
    "20 November 2026.",
]


# ---------------------------------------------------------------- layout
X0, X1 = 22, 1002
CW = X1 - X0
DEBUG = os.environ.get("DEBUG")


def _note(msg):
    if DEBUG:
        print(msg, file=sys.stderr)


def _tag_band(cv, fonts, x, y, w, text):
    cv.rect(x, y, w, 20, RED)
    draw_centered(cv, fonts, "sans_bold", 11, x + w // 2, y + 5, text,
                  (255, 255, 255))


def _mini_tag(cv, fonts, x, y, text):
    tw = text_width(fonts, "sans_bold", 8, text)
    cv.rect(x, y, int(tw) + 10, 14, RED)
    draw_text(cv, fonts, "sans_bold", 8, x + 5, y + 3, text,
              (255, 255, 255))


def build(fonts):
    cv = Canvas(W, H, PAPER)
    cv.rect_outline(10, 10, 1004, 1004, RULE, 2)

    # top line
    draw_tracked(cv, fonts, "sans_bold", 11, X0, 22, "THE WORLD IN ONE DAY",
                 INK, 1.5)
    right = "35 STORIES \u00b7 7 REGIONS"
    rw = text_width(fonts, "sans_bold", 11, right) + 1.5 * (len(right) - 1)
    draw_tracked(cv, fonts, "sans_bold", 11, int(X1 - rw), 22, right, INK, 1.5)
    cv.rect(X0, 36, CW, 1, RULE)

    # masthead + kicker
    draw_centered(cv, fonts, "serif_bold", 54, 512, 42,
                  "Friday 20 November 2026", INK)
    draw_centered(cv, fonts, "serif", 15, 512, 100,
                  "Missiles over Kyiv, a cyclone ashore in Odisha, and the "
                  "AI trade unwinds from Taipei to New York", INK_SOFT)
    cv.rect(X0, 122, CW, 3, RULE)
    cv.rect(X0, 127, CW, 1, RULE)

    # stat strip
    for i, (num, label) in enumerate(STATS):
        bx = X0 + i * 164
        cv.rect(bx, 133, 160, 48, TINT)
        cv.rect_outline(bx, 133, 160, 48, RULE, 1)
        draw_centered(cv, fonts, "serif_bold", 26, bx + 80, 138, num, INK)
        draw_centered(cv, fonts, "sans_bold", 8, bx + 80, 168, label,
                      INK_SOFT)

    # heroes
    for i, st in enumerate(HEROES):
        hx = X0 + i * 330
        _tag_band(cv, fonts, hx, 189, 320, st["tag"])
        st["draw"](cv, fonts, hx, 209, 320, 118)
        hl = wrap_text(fonts, "serif_bold", 20, st["headline"], 320)
        _note("hero %d headline lines: %d" % (i + 1, len(hl)))
        draw_block(cv, fonts, "serif_bold", 20, hx, 331, st["headline"],
                   320, 24, INK)
        dk = wrap_text(fonts, "sans", 11.5, st["deck"], 320)
        _note("hero %d deck lines: %d" % (i + 1, len(dk)))
        draw_block(cv, fonts, "sans", 11.5, hx, 383, st["deck"], 320, 15,
                   INK_SOFT)
        draw_text(cv, fonts, "sans", 9, hx, 431, st["source"], GRAY)

    # features: two rows of five
    for row in range(2):
        for col in range(5):
            st = FEATURES[row * 5 + col]
            fx = X0 + col * 197
            fy = 452 + row * 180
            st["draw"](cv, fonts, fx, fy, 192, 80)
            _mini_tag(cv, fonts, fx, fy, st["tag"])
            hl = wrap_text(fonts, "serif_bold", 13, st["headline"], 192)
            _note("feature %d headline lines: %d" % (row * 5 + col + 1,
                                                      len(hl)))
            draw_block(cv, fonts, "serif_bold", 13, fx, fy + 84,
                       st["headline"], 192, 16, INK)
            dk = wrap_text(fonts, "sans", 10, st["deck"], 192)
            _note("feature %d deck lines: %d" % (row * 5 + col + 1, len(dk)))
            draw_block(cv, fonts, "sans", 10, fx, fy + 119, st["deck"],
                       192, 13, INK_SOFT)
            draw_text(cv, fonts, "sans", 8.5, fx, fy + 161, st["source"],
                      GRAY)

    # bottom: map + also list
    draw_tracked(cv, fonts, "sans_bold", 11, X0, 814,
                 "WHERE IT HAPPENED \u00b7 PINS 1\u201313", INK, 1.0)
    draw_tracked(cv, fonts, "sans_bold", 11, 292, 814,
                 "ALSO ON FRIDAY 20 NOVEMBER", INK, 1.0)
    draw_map(cv, fonts, X0, 829, 260, 127, PINS)
    for i, (place, text, src) in enumerate(ALSO):
        col = 0 if i < 11 else 1
        r = i % 11
        ax = 292 + col * 360
        ay = 829 + r * 11
        line = "%d. %s: %s (%s)" % (i + 1, place, text, src)
        wdt = text_width(fonts, "sans", 9.5, line)
        _note("also %d width %.0f" % (i + 1, wdt))
        draw_text(cv, fonts, "sans", 9.5, ax, ay, line, INK)

    # date check + footer
    cv.rect(X0, 962, CW, 32, TINT2)
    cv.rect_outline(X0, 962, CW, 32, RULE, 1)
    draw_text(cv, fonts, "sans", 10, X0 + 8, 967, DATE_CHECK[0], INK)
    draw_text(cv, fonts, "sans", 10, X0 + 8, 980, DATE_CHECK[1], INK)
    draw_centered(cv, fonts, "sans", 9, 512, 1000,
                  "Original drawings \u00b7 Sources named beside each story "
                  "\u00b7 The World in One Day", GRAY)
    return cv


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    fonts = load_fonts(os.path.join(base, "fonts.bin"))
    cv = build(fonts)
    data = cv.to_png()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print("wrote %s %d bytes %dx%d" % (path, len(data), W, H))


if __name__ == "__main__":
    main()
