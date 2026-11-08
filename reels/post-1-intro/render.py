"""Render Post 1 (Intro Reel) as a 1080x1920 animated MP4.

Faceless host in a red hoodie, face hidden by the lime pixel mask.
Shots follow the brief: masked desk shot -> hands open a laptop ->
blank chat screen with a blinking cursor -> back to the masked shot.

Usage:  python3 render.py [--out out.mp4] [--voice line01.wav line02.wav ...]
Needs:  Pillow, numpy, ffmpeg on PATH, Inter + Noto Color Emoji fonts.
"""

import math
import random
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
DURATION = 28.0
HERE = Path(__file__).resolve().parent
OUT = HERE / "post-1-intro.mp4"
# shot cuts and beats; retime() moves them to fit a recorded voiceover
T_HANDS, T_SCREEN, T_TIMER, T_STUCK, T_BACK, T_END = 3.0, 8.6, 10.6, 12.4, 15.7, 24.6
VOICE = None

LIME = (209, 254, 23)
LIME_D = (150, 196, 0)
RED = (206, 32, 41)
RED_D = (140, 16, 24)
RED_L = (235, 64, 64)
SKIN = (214, 160, 122)
SKIN_D = (182, 126, 92)
INK = (14, 14, 16)
WHITE = (255, 255, 255)

FONT_DIR = "/usr/share/fonts/opentype/inter/"
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"


def font(weight, size):
    return ImageFont.truetype(f"{FONT_DIR}Inter-{weight}.otf", size)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


# ---------------------------------------------------------------- emoji

_emoji_cache = {}


def emoji(ch, size):
    key = (ch, size)
    if key not in _emoji_cache:
        f = ImageFont.truetype(EMOJI_FONT, 109)
        im = Image.new("RGBA", (136, 128), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((0, 0), ch, font=f, embedded_color=True)
        im = im.crop(im.getbbox())
        r = size / im.height
        _emoji_cache[key] = im.resize((int(im.width * r), size), Image.LANCZOS)
    return _emoji_cache[key]


# ---------------------------------------------------------------- scene: room + masked host

def vertical_gradient(w, h, top, bottom):
    t = np.linspace(0, 1, h)[:, None, None]
    arr = np.array(top)[None, None, :] * (1 - t) + np.array(bottom)[None, None, :] * t
    return Image.fromarray(np.repeat(arr, w, axis=1).astype(np.uint8), "RGB")


def radial_glow(w, h, cx, cy, radius, color, strength):
    y, x = np.ogrid[:h, :w]
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / radius
    a = np.clip(1 - d, 0, 1) ** 2 * strength
    layer = np.zeros((h, w, 4), np.uint8)
    layer[..., :3] = color
    layer[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(layer, "RGBA")


def build_room():
    """Static background for the masked shot (oversized for push-ins)."""
    bw, bh = int(W * 1.15), int(H * 1.15)
    img = vertical_gradient(bw, bh, (38, 34, 44), (22, 20, 26)).convert("RGBA")
    d = ImageDraw.Draw(img)
    ox, oy = (bw - W) // 2, (bh - H) // 2

    # window with night-blue light, left
    wx, wy = ox + 70, oy + 260
    d.rounded_rectangle((wx, wy, wx + 300, wy + 520), 14, fill=(30, 44, 70))
    d.rectangle((wx + 146, wy, wx + 154, wy + 520), fill=(20, 22, 30))
    d.rectangle((wx, wy + 256, wx + 300, wy + 264), fill=(20, 22, 30))
    d.rounded_rectangle((wx - 10, wy - 10, wx + 310, wy + 530), 18, outline=(18, 18, 24), width=12)

    # shelf + plant + books, right
    sx, sy = ox + 690, oy + 470
    d.rectangle((sx, sy, sx + 330, sy + 16), fill=(70, 52, 40))
    for i, (bwid, bh2, col) in enumerate([(34, 120, (80, 92, 140)), (28, 100, (160, 90, 60)),
                                           (40, 130, (60, 60, 70)), (26, 90, LIME_D)]):
        x0 = sx + 20 + sum(v[0] + 6 for v in [(34,), (28,), (40,), (26,)][:i])
        d.rectangle((x0, sy - bh2, x0 + bwid, sy), fill=col)
    px = sx + 250
    d.polygon([(px - 34, sy), (px + 34, sy), (px + 26, sy - 64), (px - 26, sy - 64)], fill=(150, 80, 56))
    for ang in range(-70, 80, 22):
        a = math.radians(ang - 90)
        ex, ey = px + math.cos(a) * 90, sy - 64 + math.sin(a) * 110
        d.line((px, sy - 64, ex, ey), fill=(60, 120, 70), width=14)
        d.ellipse((ex - 16, ey - 16, ex + 16, ey + 16), fill=(70, 140, 80))

    # framed pixel poster
    fx, fy = ox + 735, oy + 130
    d.rectangle((fx, fy, fx + 220, fy + 260), fill=(16, 16, 20))
    rnd = random.Random(7)
    for gy in range(6):
        for gx in range(5):
            c = rnd.choice([LIME, LIME_D, (40, 40, 48), (60, 60, 70)])
            d.rectangle((fx + 20 + gx * 36, fy + 22 + gy * 36, fx + 52 + gx * 36, fy + 54 + gy * 36), fill=c)

    # warm desk-lamp glow
    img.alpha_composite(radial_glow(bw, bh, ox + 870, oy + 1200, 760, (255, 170, 90), 0.38))
    img.alpha_composite(radial_glow(bw, bh, ox + 540, oy + 1000, 900, (209, 254, 23), 0.06))
    return img


def draw_host(img, t, talking, cx, top):
    """Red-hoodie host with the lime pixel mask. Drawn fresh each frame (breath + mask shimmer)."""
    d = ImageDraw.Draw(img)
    breath = math.sin(t * 2 * math.pi / 3.4) * 6
    top = top + breath
    sw = 330  # half shoulder width

    # torso / shoulders
    body = [(cx - sw - 40, top + 980), (cx - sw, top + 640), (cx - 170, top + 540),
            (cx + 170, top + 540), (cx + sw, top + 640), (cx + sw + 40, top + 980)]
    d.polygon(body, fill=RED)
    d.polygon([(cx - sw, top + 640), (cx - 170, top + 540), (cx - 120, top + 600), (cx - sw + 40, top + 980), (cx - sw - 40, top + 980)], fill=RED_D)
    d.polygon([(cx + 200, top + 580), (cx + sw, top + 640), (cx + sw + 40, top + 980), (cx + 260, top + 980)], fill=RED_L)

    # hood (outer)
    d.ellipse((cx - 250, top + 40, cx + 250, top + 640), fill=RED)
    d.chord((cx - 250, top + 40, cx + 250, top + 640), 120, 240, fill=RED_D)
    d.chord((cx - 250, top + 40, cx + 250, top + 640), -60, 40, fill=RED_L)
    # hood opening
    d.ellipse((cx - 175, top + 130, cx + 175, top + 590), fill=RED_D)
    d.ellipse((cx - 158, top + 150, cx + 158, top + 578), fill=(40, 10, 14))

    # drawstrings
    sway = math.sin(t * 1.7) * 4
    for sx in (-60, 60):
        d.line((cx + sx, top + 590, cx + sx + sway, top + 790), fill=(240, 236, 228), width=10)
        d.ellipse((cx + sx + sway - 10, top + 785, cx + sx + sway + 10, top + 815), fill=(240, 236, 228))

    # lime pixel mask over the face
    face = (cx - 140, top + 175, cx + 140, top + 555)
    cell = 28
    rnd = random.Random(int(t * 12))
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).ellipse(face, fill=255)
    tile = Image.new("RGBA", img.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    gx0 = int(face[0]) - (int(face[0]) % cell)
    gy0 = int(face[1]) - (int(face[1]) % cell)
    mouth_y = top + 450
    for gy in range(gy0, int(face[3]) + cell, cell):
        for gx in range(gx0, int(face[2]) + cell, cell):
            k = ((gx * 73856093) ^ (gy * 19349663)) & 0xFF
            shade = 0.72 + 0.28 * (k / 255)
            if rnd.random() < 0.06:
                shade = 0.55 + rnd.random() * 0.45
            if talking and abs(gy + cell / 2 - mouth_y) < cell * 1.6 and abs(gx + cell / 2 - cx) < 90:
                shade *= 0.55 + 0.45 * rnd.random()
            col = tuple(int(c * shade) for c in LIME)
            td.rectangle((gx, gy, gx + cell - 2, gy + cell - 2), fill=col + (255,))
    img.paste(tile, (0, 0), Image.composite(tile, Image.new("RGBA", img.size), mask).split()[3])
    # two "eye" pixels that blink
    blink = (t % 4.1) < 0.12
    for ex in (-56, 28):
        ey = top + 330
        if blink:
            d.rectangle((cx + ex, ey + 10, cx + ex + 28, ey + 18), fill=INK)
        else:
            d.rectangle((cx + ex, ey, cx + ex + 28, ey + 26), fill=INK)


def draw_desk(img, oy):
    d = ImageDraw.Draw(img)
    d.rectangle((0, oy, img.width, img.height), fill=(92, 62, 42))
    d.rectangle((0, oy, img.width, oy + 22), fill=(118, 82, 56))
    for i in range(6):
        y = oy + 60 + i * 70
        d.line((0, y, img.width, y + 12), fill=(84, 56, 38), width=3)
    # closed laptop on desk
    lx = img.width // 2
    d.polygon([(lx - 260, oy + 150), (lx + 260, oy + 150), (lx + 300, oy + 210), (lx - 300, oy + 210)], fill=(178, 182, 190))
    d.polygon([(lx - 300, oy + 210), (lx + 300, oy + 210), (lx + 300, oy + 226), (lx - 300, oy + 226)], fill=(120, 124, 132))
    d.rectangle((lx - 22, oy + 168, lx + 22, oy + 192), fill=LIME)  # sticker
    # mug
    d.rounded_rectangle((lx + 360, oy + 70, lx + 470, oy + 200), 16, fill=(236, 232, 224))
    d.arc((lx + 440, oy + 100, lx + 510, oy + 170), -90, 90, fill=(236, 232, 224), width=14)


ROOM = None


def masked_shot(t, local, talking, push=0.0):
    global ROOM
    if ROOM is None:
        ROOM = build_room()
    img = ROOM.copy()
    cx = img.width // 2
    draw_host(img, t, talking, cx, top=img.height * 0.5 - 760)
    draw_desk(img, int(img.height * 0.5 + 300))
    # handheld wobble + slow push-in
    scale = 1.0 + 0.05 * push
    jx = math.sin(t * 1.3) * 6 + math.sin(t * 3.1) * 2
    jy = math.cos(t * 1.1) * 5
    cw, ch = W / scale, H / scale
    x0 = (img.width - cw) / 2 + jx
    y0 = (img.height - ch) / 2 + jy - 40 * push
    return img.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.BILINEAR)


# ---------------------------------------------------------------- scene: hands open the laptop

def project(p, cam):
    x, y, z = p
    fx, cy_, cz, f = cam
    hc, th = 2.6, math.radians(34)
    yy, zz = y - hc, z + cz
    depth = -yy * math.sin(th) + zz * math.cos(th)
    up = yy * math.cos(th) + zz * math.sin(th)
    return (W / 2 + (x - fx) * f / depth, cy_ - up * f / depth)


def perspective_coeffs(dst, src):
    """Coefficients for PIL PERSPECTIVE mapping dst quad -> src quad."""
    m = []
    for (x, y), (u, v) in zip(dst, src):
        m.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        m.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    A = np.array(m, float)
    B = np.array([c for pt in src for c in pt], float)
    return np.linalg.solve(A, B)


def chat_screen(w, h, t, cursor_on, timer=None):
    """A blank, unbranded AI-chat page."""
    s = Image.new("RGB", (w, h), (24, 24, 27))
    d = ImageDraw.Draw(s)
    k = w / 1000
    # sidebar
    d.rectangle((0, 0, int(190 * k), h), fill=(16, 16, 18))
    for i in range(5):
        d.rounded_rectangle((int(24 * k), int((90 + i * 54) * k), int((150 - i * 12) * k), int((108 + i * 54) * k)), int(6 * k), fill=(38, 38, 42))
    # greeting
    g = font("SemiBold", int(46 * k))
    msg = "What do you want to learn today?"
    tw = d.textlength(msg, font=g)
    mid = int(190 * k) + (w - int(190 * k)) // 2
    d.text((mid - tw / 2, h * 0.36), msg, font=g, fill=(236, 236, 240))
    # input box
    bx0, bx1 = mid - int(330 * k), mid + int(330 * k)
    by0, by1 = int(h * 0.5), int(h * 0.5 + 92 * k)
    d.rounded_rectangle((bx0, by0, bx1, by1), int(40 * k), fill=(44, 44, 50), outline=(70, 70, 78), width=max(1, int(2 * k)))
    ph = font("Regular", int(28 * k))
    tx = bx0 + int(40 * k)
    if cursor_on:
        d.rectangle((tx, by0 + int(24 * k), tx + max(2, int(4 * k)), by1 - int(24 * k)), fill=WHITE)
    d.text((tx + int(14 * k), by0 + int(30 * k)), "Ask anything", font=ph, fill=(120, 120, 130))
    d.ellipse((bx1 - int(76 * k), by0 + int(16 * k), bx1 - int(16 * k), by1 - int(16 * k)), fill=(90, 90, 96))
    return s


def hands_shot(t, local):
    """3.0s -> 8.6s: close-up, hands lift the lid, screen wakes."""
    img = vertical_gradient(W, H, (40, 30, 26), (70, 48, 34)).convert("RGBA")
    d = ImageDraw.Draw(img)
    for i in range(14):
        y = 900 + i * 80
        d.line((0, y, W, y + 20), fill=(78, 54, 38), width=4)
    img.alpha_composite(radial_glow(W, H, 540, 700, 900, (255, 180, 110), 0.25))

    open_t = ease(local / 3.4)
    ang = math.radians(lerp(0, 108, open_t))
    cam = (0, 1180, 4.0, 1100)
    bw, bd = 3.2, 2.2  # base width, depth
    hinge_z = bd
    base = [(-bw / 2, 0, 0), (bw / 2, 0, 0), (bw / 2, 0, hinge_z), (-bw / 2, 0, hinge_z)]
    bp = [project(p, cam) for p in base]
    d.polygon(bp, fill=(170, 174, 182))
    # base front lip
    lip = [bp[0], bp[1], (bp[1][0], bp[1][1] + 26), (bp[0][0], bp[0][1] + 26)]
    d.polygon(lip, fill=(118, 122, 130))
    # keyboard + trackpad on the base
    if open_t > 0.02:
        for r in range(5):
            for c in range(12):
                u0, u1 = -1.35 + c * 0.225, -1.35 + c * 0.225 + 0.19
                v0, v1 = 1.05 + r * 0.19, 1.05 + r * 0.19 + 0.15
                q = [project((u0, 0.001, v0), cam), project((u1, 0.001, v0), cam),
                     project((u1, 0.001, v1), cam), project((u0, 0.001, v1), cam)]
                d.polygon(q, fill=(46, 46, 52))
        tp = [project(p, cam) for p in [(-0.5, 0.001, 0.15), (0.5, 0.001, 0.15), (0.5, 0.001, 0.8), (-0.5, 0.001, 0.8)]]
        d.polygon(tp, fill=(150, 154, 162))

    # lid: rotates about hinge (z = hinge_z) from lying on base (front edge at z=0)
    L = bd
    ly, lz = L * math.sin(ang), hinge_z - L * math.cos(ang)
    lid3 = [(-bw / 2, ly, lz), (bw / 2, ly, lz), (bw / 2, 0.02, hinge_z), (-bw / 2, 0.02, hinge_z)]
    lp = [project(p, cam) for p in lid3]
    hinge_y = lp[2][1]
    if lp[0][1] < hinge_y - 4:
        # we see the screen side
        d.polygon(lp, fill=(20, 20, 22))
        inset = 0.08
        scr3 = [(-bw / 2 + inset, ly - inset * math.sin(ang) * 0, lz), (bw / 2 - inset, ly, lz),
                (bw / 2 - inset, 0.12, hinge_z - 0.1 * math.cos(ang)), (-bw / 2 + inset, 0.12, hinge_z - 0.1 * math.cos(ang))]
        # inset toward the hinge along the lid
        def along(f):
            return (lerp(ly, 0.02, f), lerp(lz, hinge_z, f))
        (ya, za), (yb, zb) = along(0.05), along(0.93)
        scr3 = [(-bw / 2 + inset, ya, za), (bw / 2 - inset, ya, za), (bw / 2 - inset, yb, zb), (-bw / 2 + inset, yb, zb)]
        sp = [project(p, cam) for p in scr3]
        wake = ease((local - 2.4) / 1.2)
        sw_, sh_ = 1000, 640
        screen = chat_screen(sw_, sh_, t, cursor_on=(t * 2) % 2 < 1)
        if wake < 1:
            screen = Image.blend(Image.new("RGB", screen.size, (10, 10, 12)), screen, wake)
        coeffs = perspective_coeffs(sp, [(0, 0), (sw_, 0), (sw_, sh_), (0, sh_)])
        warped = screen.transform((W, H), Image.PERSPECTIVE, tuple(coeffs), Image.BICUBIC)
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).polygon(sp, fill=255)
        img.paste(warped, (0, 0), m)
        if wake > 0:
            img.alpha_composite(radial_glow(W, H, (sp[0][0] + sp[1][0]) / 2, (sp[0][1] + sp[2][1]) / 2, 700, (200, 210, 255), 0.18 * wake))
    else:
        d.polygon(lp, fill=(190, 194, 202))
        c = project((0, ly * 0.5 + 0.01, (lz + hinge_z) / 2), cam)
        d.rectangle((c[0] - 26, c[1] - 18, c[0] + 26, c[1] + 18), fill=LIME)

    # hands grip the lid's front corners, then drop to the keyboard
    grip = 1 - ease((local - 3.0) / 0.9)
    for side in (-1, 1):
        lidpt = project((side * 1.25, ly, lz), cam)
        kbpt = project((side * 0.75, 0, 1.5), cam)
        hx = lerp(kbpt[0], lidpt[0], grip)
        hy = lerp(kbpt[1] + 120, lidpt[1] + 30, grip)
        if local > 4.4:  # gone off-frame
            hy += (local - 4.4) * 900
        draw_hand(img, hx, hy, side)

    # slow push-in
    s = 1 + 0.06 * ease(local / 5.6)
    cw, ch = W / s, H / s
    return img.crop((int((W - cw) / 2), int((H - ch) / 2), int((W + cw) / 2), int((H + ch) / 2))).resize((W, H), Image.BILINEAR)


def draw_hand(img, x, y, side):
    d = ImageDraw.Draw(img)
    # sleeve comes from bottom of frame
    sx = x + 30 * side
    d.polygon([(sx - 80, y + 110), (sx + 80, y + 110), (sx + 260 * side + 150, H + 200), (sx + 260 * side - 150, H + 200)], fill=RED)
    d.polygon([(sx - 84, y + 100), (sx + 84, y + 100), (sx + 90, y + 150), (sx - 90, y + 150)], fill=RED_D)
    # palm + fingers
    d.ellipse((x - 85, y - 30, x + 85, y + 140), fill=SKIN)
    for i in range(4):
        fx = x - 60 + i * 38
        d.rounded_rectangle((fx, y - 70 + abs(i - 1.5) * 10, fx + 30, y + 40), 15, fill=SKIN)
        d.line((fx + 4, y + 20, fx + 26, y + 20), fill=SKIN_D, width=3)
    d.rounded_rectangle((x - 95 * side - 18, y + 10, x - 95 * side + 18, y + 100), 18, fill=SKIN_D)


# ---------------------------------------------------------------- scene: the blank screen

def screen_shot(t, local):
    """8.6s -> 15.6s: the blank page, cursor blinking; a timer starts on 'time how long'."""
    img = Image.new("RGBA", (W, H), (8, 8, 10, 255))
    s = 1.0 + 0.08 * ease(local / (T_BACK - T_SCREEN))
    sw_, sh_ = int(1000 * 1.25), int(1560 * 1.0)
    screen = chat_screen(sw_, sh_, t, cursor_on=(t * 1.9) % 2 < 1.15).resize((int(sw_ * s), int(sh_ * s)), Image.BILINEAR)
    img.paste(screen, ((W - screen.width) // 2 - int(118 * s), (H - screen.height) // 2 - 40))
    # screen vignette + scanline sheen
    img.alpha_composite(radial_glow(W, H, W / 2, H / 2, 1300, (0, 0, 0), 0.0))
    vg = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vg).rectangle((0, 0, W, H), fill=0)
    edge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ed = ImageDraw.Draw(edge)
    for i in range(40):
        a = int(160 * (1 - i / 40) ** 2)
        ed.rectangle((i * 6, i * 6, W - i * 6, H - i * 6), outline=(0, 0, 0, a), width=6)
    img.alpha_composite(edge)

    # stopwatch chip from 10.6s ("time how long it really takes me")
    tt = t - T_TIMER
    if tt > 0:
        a = ease_out(tt / 0.4)
        chip = Image.new("RGBA", (300, 96), (0, 0, 0, 0))
        cd = ImageDraw.Draw(chip)
        cd.rounded_rectangle((0, 0, 299, 95), 48, fill=LIME + (255,))
        secs = tt * 3.7  # sped-up clock, it's a gag
        cd.text((96, 20), f"{int(secs // 60):02d}:{int(secs % 60):02d}", font=font("Bold", 50), fill=INK)
        chip.alpha_composite(emoji("⏱", 54), (30, 21))
        chip.putalpha(chip.split()[3].point(lambda v: int(v * a)))
        img.alpha_composite(chip, (W - 300 - 70, int(330 - 30 * (1 - a))))
    # "stuck" ping on 12.4s
    st = t - T_STUCK
    if 0 < st < 1.8:
        a = ease_out(st / 0.3) * (1 - ease((st - 1.4) / 0.4))
        tag = Image.new("RGBA", (330, 96), (0, 0, 0, 0))
        tdr = ImageDraw.Draw(tag)
        tdr.rounded_rectangle((0, 0, 329, 95), 48, fill=(255, 255, 255, 255))
        tdr.text((96, 22), "stuck…", font=font("Bold", 46), fill=INK)
        tag.alpha_composite(emoji("😵", 54), (28, 21))
        tag.putalpha(tag.split()[3].point(lambda v: int(v * a)))
        img.alpha_composite(tag, (70, 470))
    return img


# ---------------------------------------------------------------- text overlays

def text_block(img, lines, y, size, weight="ExtraBold", highlight=None, alpha=1.0, stroke=10, rise=0):
    """Centered, stroked text lines. highlight: set of words drawn in lime."""
    f = font(weight, size)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i, line in enumerate(lines):
        words = line.split(" ")
        space = d.textlength(" ", font=f)
        widths = [d.textlength(w_, font=f) for w_ in words]
        x = (W - (sum(widths) + space * (len(words) - 1))) / 2
        ly = y + i * size * 1.18 + rise
        for w_, ww in zip(words, widths):
            col = LIME if highlight and w_.strip(".,?!") in highlight else WHITE
            d.text((x, ly), w_, font=f, fill=col, stroke_width=stroke, stroke_fill=INK)
            x += ww + space
    if alpha < 1:
        layer.putalpha(layer.split()[3].point(lambda v: int(v * alpha)))
    img.alpha_composite(layer)


HOOK = [
    (0.10, ["I'm not a tech person."], set()),
    (0.75, ["I know nothing", "about AI."], {"AI"}),
    (1.45, ["Let's fix that,", "in public."], {"in", "public"}),
]


def draw_hook(img, t):
    if t > 2.9:
        return
    fade = 1 - ease((t - 2.6) / 0.3)
    # dark band for legibility
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(band).rectangle((0, 210, W, 1000), fill=(0, 0, 0, int(120 * fade)))
    img.alpha_composite(band.filter(ImageFilter.GaussianBlur(40)))
    y = 290
    for start, lines, hl in HOOK:
        if t >= start:
            p = ease_out((t - start) / 0.28)
            text_block(img, lines, y, 92, "Black", hl, alpha=p * fade, stroke=8, rise=int(30 * (1 - p)))
        y += int(len(lines) * 92 * 1.18 + 44)


CAPTIONS = [
    (2.7, 4.7, "Everyone keeps telling me AI is going to change everything."),
    (4.7, 6.5, "Honestly? I don't even know where to start."),
    (6.5, 8.7, "So I'm going to learn it from zero, right here."),
    (8.7, 10.6, "Every week I'll try a free AI tool,"),
    (10.6, 12.4, "time how long it really takes me,"),
    (12.4, 14.0, "show you where I get stuck,"),
    (14.0, 15.7, "and tell you if it was worth it."),
    (15.7, 18.0, "No courses. No “make $10k with AI”."),
    (18.0, 19.8, "Just me figuring it out."),
    (19.8, 22.0, "What should I try first?"),
    (22.0, 24.6, "Tell me in the comments."),
]


def wrap(words, f, maxw, d):
    lines, cur = [], []
    for w_ in words:
        test = " ".join(cur + [w_])
        if cur and d.textlength(test, font=f) > maxw:
            lines.append(cur)
            cur = [w_]
        else:
            cur.append(w_)
    if cur:
        lines.append(cur)
    return lines


def draw_caption(img, t):
    for start, end, text in CAPTIONS:
        if start <= t < end:
            break
    else:
        return
    f = font("ExtraBold", 66)
    d = ImageDraw.Draw(img)
    words = text.split(" ")
    # word timing proportional to length
    lens = [len(w_) + 2 for w_ in words]
    span = (end - start) * 0.92
    acc, times = 0, []
    for n in lens:
        times.append(start + span * acc / sum(lens))
        acc += n
    current = max(i for i, tw in enumerate(times) if tw <= t)
    lines = wrap(list(range(len(words))), None, 0, d) if False else None
    # manual wrap on word indices
    maxw = W - 200
    rows, cur = [], []
    for i, w_ in enumerate(words):
        test = " ".join(words[j] for j in cur + [i])
        if cur and d.textlength(test, font=f) > maxw:
            rows.append(cur)
            cur = [i]
        else:
            cur.append(i)
    rows.append(cur)
    pop = ease_out((t - start) / 0.18)
    base_y = 1290 - (len(rows) - 1) * 40
    space = d.textlength(" ", font=f)
    for r, row in enumerate(rows):
        widths = [d.textlength(words[i], font=f) for i in row]
        x = (W - (sum(widths) + space * (len(row) - 1))) / 2
        y = base_y + r * 82 + int(16 * (1 - pop))
        for i, ww in zip(row, widths):
            col = LIME if i == current else WHITE
            if i > current:
                col = (225, 225, 225)
            d.text((x, y), words[i], font=f, fill=col, stroke_width=9, stroke_fill=INK)
            x += ww + space
    if text.startswith("Tell me"):
        bob = math.sin(t * 7) * 10
        img.alpha_composite(emoji("👇", 96), (W // 2 - 48, int(base_y + len(rows) * 82 + 30 + bob)))


ROOSTER = [
    "....RR......",
    "...RRR......",
    "..WWWW......",
    ".WWKWW......",
    "YWWWWW...WW.",
    ".RWWWW..WWW.",
    "..RWWWWWWWW.",
    "...WWWWWWWW.",
    "...WWWWWWW..",
    "....WWWWW...",
    ".....Y.Y....",
    "....YY.YY...",
]


def rooster(scale):
    pal = {"R": RED, "W": LIME, "K": INK, "Y": (255, 196, 40)}
    im = Image.new("RGBA", (12 * scale, 12 * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for y, row in enumerate(ROOSTER):
        for x, ch in enumerate(row):
            if ch in pal:
                d.rectangle((x * scale, y * scale, x * scale + scale - 1, y * scale + scale - 1), fill=pal[ch])
    return im


def draw_endcard(img, t):
    lt = t - T_END
    if lt < 0:
        return
    a = ease(lt / 0.5)
    dim = Image.new("RGBA", (W, H), (8, 8, 10, int(185 * a)))
    img.alpha_composite(dim)
    r = rooster(22)
    p = ease_out(lt / 0.6)
    ry = int(330 + 60 * (1 - p))
    rr = r.copy()
    rr.putalpha(rr.split()[3].point(lambda v: int(v * a)))
    img.alpha_composite(rr, ((W - r.width) // 2, ry))
    text_block(img, ["DAY 1"], 640, 190, "Black", {"DAY", "1"}, alpha=a, stroke=0, rise=int(30 * (1 - p)))
    text_block(img, ["learning AI", "from zero."], 880, 96, "ExtraBold", None, alpha=a, stroke=0, rise=int(30 * (1 - p)))
    p2 = ease_out((lt - 0.6) / 0.5)
    if p2 > 0:
        text_block(img, ["Follow along · one free tool a week"], 1150, 46, "SemiBold", None, alpha=p2, stroke=0)
        text_block(img, ["Stay free range."], 1240, 58, "Bold", {"free", "range"}, alpha=p2, stroke=0)


# ---------------------------------------------------------------- audio bed

def write_music(path):
    """Soft lo-fi pad + pluck, quiet enough to sit under a voiceover."""
    sr = 44100
    n = int(DURATION * sr)
    tt = np.arange(n) / sr
    out = np.zeros(n)
    bpm = 88
    beat = 60 / bpm
    chords = [[57, 60, 64, 67], [53, 57, 60, 64], [48, 52, 55, 59], [55, 59, 62, 65]]  # Am7 Fmaj7 Cmaj7 G7
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    bar = beat * 4
    for i in range(int(DURATION / bar) + 1):
        ch = chords[i % 4]
        s0 = int(i * bar * sr)
        s1 = min(n, int((i + 1) * bar * sr) + sr // 2)
        seg = tt[s0:s1] - i * bar
        env = np.minimum(1, seg / 0.6) * np.exp(-np.maximum(0, seg - bar) * 4)
        for m in ch:
            out[s0:s1] += 0.05 * env * (np.sin(2 * np.pi * hz(m) * seg) + 0.3 * np.sin(2 * np.pi * hz(m) * 2.003 * seg))
        for k in range(8):
            ps = int((i * bar + k * beat / 2) * sr)
            if ps >= n:
                break
            m = ch[[0, 2, 1, 3, 2, 1, 3, 2][k]] + 12
            L_ = min(n - ps, int(0.5 * sr))
            st = np.arange(L_) / sr
            out[ps:ps + L_] += 0.045 * np.exp(-st * 7) * np.sin(2 * np.pi * hz(m) * st)
    # soft kick on 1 and 3, after the hook
    for b in range(int(DURATION / beat)):
        if b % 2 == 0 and b * beat > 2.6:
            ps = int(b * beat * sr)
            L_ = min(n - ps, int(0.25 * sr))
            st = np.arange(L_) / sr
            out[ps:ps + L_] += 0.22 * np.exp(-st * 18) * np.sin(2 * np.pi * (50 + 60 * np.exp(-st * 30)) * st)
    fade = np.minimum(1, tt / 0.4) * np.minimum(1, (DURATION - tt) / 1.5)
    out = np.tanh(out * 1.4) * fade * 0.5
    data = (out * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


# ---------------------------------------------------------------- timeline

def speaking(t):
    if VOICE is None:
        return 0.3 < t < T_END
    return any(s0 <= t <= s0 + d for s0, d in VOICE["spans"])


def load_voice(paths, gap=0.16, lead=0.3):
    """Trim each line's silence, lay them end to end, and retime captions and cuts to the voice."""
    global VOICE, CAPTIONS, DURATION, T_HANDS, T_SCREEN, T_TIMER, T_STUCK, T_BACK, T_END
    import soundfile as sf
    clips, sr = [], None
    for p in paths:
        a, sr = sf.read(p)
        loud = np.where(np.abs(a) > 0.01)[0]
        clips.append(a[max(0, loud[0] - int(0.03 * sr)): loud[-1] + int(0.06 * sr)])
    starts, t = [], lead
    for i, c in enumerate(clips):
        starts.append(t)
        t += len(c) / sr + (gap * 2.2 if i in (6, 8) else gap)  # breathe before "No courses" and the CTA
    durs = [len(c) / sr for c in clips]
    T_HANDS = max(3.0, starts[0] + durs[0] + 0.1)
    T_SCREEN, T_TIMER, T_STUCK, T_BACK = starts[3], starts[4], starts[5], starts[7]
    T_END = starts[10] + durs[10] + 0.5
    DURATION = round(T_END + 3.4, 2)
    texts = [c[2] for c in CAPTIONS]
    CAPTIONS = [(max(starts[i], 2.7) if i == 0 else starts[i],
                 starts[i + 1] if i + 1 < len(starts) else T_END, texts[i]) for i in range(len(texts))]
    track = np.zeros(int(DURATION * sr))
    for s0, c in zip(starts, clips):
        i0 = int(s0 * sr)
        track[i0:i0 + len(c)] += c
    VOICE = {"spans": list(zip(starts, durs)), "track": track, "sr": sr}


def frame(t):
    if t < T_HANDS:
        img = masked_shot(t, t, talking=speaking(t), push=ease(t / T_HANDS)).convert("RGBA")
    elif t < T_SCREEN:
        img = hands_shot(t, t - T_HANDS)
    elif t < T_BACK:
        img = screen_shot(t, t - T_SCREEN)
    else:
        img = masked_shot(t, t - T_BACK, talking=speaking(t), push=0.4 + 0.6 * ease((t - T_BACK) / (T_END - T_BACK))).convert("RGBA")
    # whip-flash on cuts
    for cut in (T_HANDS, T_SCREEN, T_BACK):
        dt = t - cut
        if 0 <= dt < 0.12:
            img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(150 * (1 - dt / 0.12)))))
    draw_hook(img, t)
    draw_caption(img, t)
    draw_endcard(img, t)
    return img.convert("RGB")


def main():
    wav = OUT.with_suffix(".music.wav")
    write_music(wav)
    frames = int(DURATION * FPS)
    audio_in = ["-i", str(wav)]
    mix = ["-map", "0:v", "-map", "1:a"]
    if VOICE is not None:
        import soundfile as sf
        vwav = OUT.with_suffix(".voice.wav")
        sf.write(vwav, VOICE["track"], VOICE["sr"])
        audio_in += ["-i", str(vwav)]
        # music ducks under the voice, then the mix is normalised for Instagram loudness
        mix = ["-filter_complex",
               "[2:a]aresample=44100,asplit=2[vo][sc];[1:a]volume=0.8[mu];"
               "[mu][sc]sidechaincompress=threshold=0.02:ratio=8:attack=15:release=350[md];"
               "[vo][md]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
               "-map", "0:v", "-map", "[a]", "-ar", "44100"]
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", *audio_in, *mix, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-t", str(DURATION), "-movflags", "+faststart", str(OUT)],
        stdin=subprocess.PIPE,
    )
    for i in range(frames):
        t = i / FPS
        ff.stdin.write(frame(t).tobytes())
        if i % 150 == 0:
            print(f"{t:5.1f}s", flush=True)
    ff.stdin.close()
    ff.wait()
    print("wrote", OUT)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--voice", nargs="*", help="one WAV per caption line, in order; retimes the reel to the voice")
    ap.add_argument("--stills", type=Path, help="write PNG stills to this folder instead of a video")
    ap.add_argument("--at", nargs="*", type=float, default=[])
    args = ap.parse_args()
    OUT = args.out
    if args.voice:
        load_voice(args.voice)
    if args.stills:
        args.stills.mkdir(parents=True, exist_ok=True)
        for s in args.at:
            frame(s).save(args.stills / f"t{s}.png")
    else:
        main()
