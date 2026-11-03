"""Núcleo de dibujo a mano de La Libreta de Inés: Pen, Inés, fondos, cámara."""
import math, sys, os, subprocess, random
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, SS = 1920, 1080, 30, 2
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def HF(size): return ImageFont.truetype(os.path.join(HERE, "fonts", "PatrickHand-Regular.ttf"), int(size * SS))
def PF(size): return ImageFont.truetype(os.path.join(HERE, "fonts", "Poppins-Medium.ttf"), int(size * SS))

INK = (22, 18, 16); PLUM = (40, 24, 38); WHITE = (255, 255, 255)
SKIN = (196, 130, 88); HAIR = (38, 24, 20); BLOUSE = (232, 170, 40); JEANS = (70, 110, 165)
PURPLE = (150, 40, 190); RED = (210, 40, 40); GREEN = (30, 150, 80); LIPS = (170, 60, 70)
TEAR = (90, 170, 240)

_BL = []
_r = random.Random(7); _tb = 0.6
while _tb < 4000: _BL.append(_tb); _tb += _r.uniform(1.2, 3.2)
def blinking(t): return any(b <= t < b + 4 / 30 for b in _BL)

def clamp(x): return max(0.0, min(1.0, x))
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3
def back(x):
    x = clamp(x); c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

# ---------- wobbly drawing core ----------
class Pen:
    def __init__(self, d, boil, img=None):
        self.d, self.boil, self.n, self.ink, self.img, self.cap = d, boil, 0, INK, img, None
    def _rng(self):
        self.n += 1
        return random.Random(self.n * 7919 + self.boil * 104729)
    def wob(self, pts, closed=True, amp=2.2, step=10):
        r = self._rng(); ph1, ph2 = r.uniform(0, 6.3), r.uniform(0, 6.3)
        seq = pts + ([pts[0]] if closed else [])
        out = []; k = 0
        for (x0, y0), (x1, y1) in zip(seq, seq[1:]):
            L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(L / step))
            nx, ny = (-(y1 - y0) / (L or 1), (x1 - x0) / (L or 1))
            for i in range(n):
                f = i / n; k += 1
                o = amp * (0.6 * math.sin(k * 0.33 + ph1) + 0.4 * math.sin(k * 0.12 + ph2))
                out.append(((x0 + (x1 - x0) * f + nx * o) * SS, (y0 + (y1 - y0) * f + ny * o) * SS))
        if not closed: out.append((seq[-1][0] * SS, seq[-1][1] * SS))
        return out
    def poly(self, pts, fill=None, lw=4.5, amp=2.2):
        p = self.wob(pts, True, amp)
        if fill: self.d.polygon(p, fill=fill)
        if lw: self.d.line(p + [p[0]], fill=self.ink, width=int(lw * SS), joint="curve")
    def line(self, pts, lw=4.5, col=None, amp=1.8):
        p = self.wob(pts, False, amp)
        self.d.line(p, fill=col or self.ink, width=int(lw * SS), joint="curve")
    def ell(self, cx, cy, rx, ry, fill=None, lw=4.5, a0=0, a1=360, n=None, amp=1.8):
        n = n or max(16, int((rx + ry) / 4))
        pts = [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
                cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + (0 if a1 - a0 >= 360 else 1))]
        if a1 - a0 >= 360: self.poly(pts, fill, lw, amp)
        else: self.line(pts, lw, amp=amp)
    def rect(self, x0, y0, x1, y1, fill=None, lw=4.5, r=0):
        if r:
            pts = []
            for cx, cy, a in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
                for i in range(7): ang = math.radians(a + 15 * i); pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        else: pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        self.poly(pts, fill, lw)
    def limb(self, pts, w, col):
        p = self.wob(pts, False, 1.5, 8)
        self.d.line(p, fill=self.ink, width=int((w + 9) * SS), joint="curve")
        for q in (p[0], p[-1]):
            r = (w + 9) / 2 * SS; self.d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=self.ink)
        self.d.line(p, fill=col, width=int(w * SS), joint="curve")
        for q in (p[0], p[-1]):
            r = w / 2 * SS; self.d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=col)

def htext(d, xy, s, size, fill=INK, anchor="mm"):
    d.text((xy[0] * SS, xy[1] * SS), s, font=HF(size), fill=fill, anchor=anchor)

def pop_htext(img, xy, s, size, fill, k, rot=0):
    if k <= 0.02: return
    f = HF(size * k); tw = int(f.getlength(s)) + 80
    tmp = Image.new("RGBA", (tw, int(size * k * 2.2 * SS)), (0, 0, 0, 0))
    ImageDraw.Draw(tmp).text((tw // 2, tmp.height // 2), s, font=f, fill=fill, anchor="mm")
    if rot: tmp = tmp.rotate(rot, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(tmp, (int(xy[0] * SS) - tmp.width // 2, int(xy[1] * SS) - tmp.height // 2))

# ---------- Inés, full body (origin = base of neck) ----------
def ines(pen, ox, oy, sc, t, pose="down", expr="meh", talk=True):
    P = lambda x, y: (ox + x * sc, oy + y * sc)
    def PP(lst): return [P(x, y) for x, y in lst]
    if pen.img is not None and sc < 1.5:  # tight contact shadow under the feet
        sh = Image.new("RGBA", pen.img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse([(ox - 150 * sc) * SS, (oy + 668 * sc) * SS, (ox + 150 * sc) * SS, (oy + 700 * sc) * SS], fill=(20, 10, 30, 70))
        pen.img.alpha_composite(sh)
    pen.ink = PLUM
    # hair back (curly, shoulder length)
    r = pen._rng(); bumps = []
    for i in range(28):
        a = math.radians(180 + 360 * i / 28)
        rr = 128 + 10 * math.sin(i * 1.7)
        y_ext = 40 if math.sin(a) > 0.2 else 0
        bumps.append(P(math.cos(a) * (rr + 8), -125 + math.sin(a) * (rr + 5) + y_ext))
    pen.poly(bumps, HAIR, 4.5, amp=4)
    # legs / jeans
    pen.poly(PP([(-80, 300), (80, 300), (96, 650), (14, 650), (2, 390), (-14, 650), (-96, 650)]), JEANS)
    pen.line(PP([(-50, 430), (-58, 520)]), 3, (40, 70, 110)); pen.line(PP([(50, 430), (58, 520)]), 3, (40, 70, 110))
    # sneakers
    for sx in (-56, 56):
        pen.poly(PP([(sx - 48, 648), (sx + 46, 648), (sx + 58, 682), (sx - 58, 682)]), WHITE)
        pen.line(PP([(sx - 58, 672), (sx + 58, 672)]), 3)
    # torso: blouse
    pen.poly(PP([(-100, 14), (100, 14), (112, 110), (82, 118), (74, 305), (-74, 305), (-82, 118), (-112, 110)]), BLOUSE)
    pen.line(PP([(-30, 16), (0, 60), (30, 16)]), 3.5)
    pen.line(PP([(-76, 270), (76, 270)]), 3)  # tucked waist
    # neck
    pen.poly(PP([(-18, -40), (18, -40), (20, 18), (-20, 18)]), SKIN, 0)
    # arms by pose
    w = 26 * sc
    def arm(sh, el, hd, palm=False, finger=None):
        pen.limb([P(*sh), P(*el), P(*hd)], w, SKIN)
        hx, hy = P(*hd)
        pen.ell(hx, hy, (24 if palm else 20) * sc, (20 if palm else 18) * sc, SKIN, 4)
        if palm:
            for dx in (-14, -5, 5, 14):
                pen.limb([(hx + dx * sc, hy - 8 * sc), (hx + dx * 1.5 * sc - 16 * sc, hy - 30 * sc)], 7 * sc, SKIN)
        if finger: pen.limb([(hx, hy - 8 * sc), P(*finger)], 9 * sc, SKIN)
    LS, RS = (-96, 40), (96, 40)
    if pose == "down":
        arm(LS, (-122, 170), (-128, 300)); arm(RS, (122, 170), (128, 300))
    elif pose == "hip":
        arm(LS, (-122, 170), (-128, 300)); arm(RS, (175, 175), (82, 268))
    elif pose == "present":
        arm(RS, (130, 180), (250, 230), palm=True); arm(LS, (-30, 215), (140, 245), palm=True)
    elif pose == "phone":
        arm(LS, (-122, 170), (-128, 300))
        arm(RS, (150, 190), (70, 105))
        px, py = P(70, 60); pen.rect(px - 22 * sc, py - 50 * sc, px + 22 * sc, py + 30 * sc, (60, 60, 70), 4, r=6 * sc)
        pen.ell(px, py + 40 * sc, 20 * sc, 16 * sc, SKIN, 4)
    elif pose == "point":
        arm(LS, (-122, 170), (-128, 300)); arm(RS, (165, 110), (170, -40), finger=(172, -95))
    elif pose == "cry":
        arm(LS, (-150, 150), (-70, -95)); arm(RS, (150, 150), (70, -95))
    # head
    pen.ell(*P(0, -125), 92 * sc, 104 * sc, SKIN)
    for sx in (-1, 1):
        pen.ell(*P(sx * 92, -118), 14 * sc, 22 * sc, SKIN, 4)
        pen.ell(*P(sx * 92, -92), 6 * sc, 6 * sc, (240, 200, 60), 3)
    # fringe / top curls over the forehead
    top = []
    for i in range(19):
        a = math.radians(180 + 180 * i / 18)
        top.append(P(math.cos(a) * 104, -140 + math.sin(a) * 100))
    for i in range(19):
        x = 104 - i * (208 / 18)
        top.append(P(x, -192 + (104 - x) * 0.27 + 5 * math.sin(x / 13)))
    pen.poly(top, HAIR, 4.5, amp=3)
    pen.ell(*P(55, -222), 26 * sc, 12 * sc, (230, 90, 70), 3.5)  # claw clip
    # eyes
    blink = expr in ("meh", "normal") and blinking(t)
    for sx in (-1, 1):
        ex, ey = P(sx * 38, -125)
        rx, ry = (30 if expr == "wide" else 26) * sc, (28 if expr == "wide" else 22) * sc
        if expr in ("happy", "cry") or blink:
            pen.ell(ex, ey, rx, ry * 0.7, None, 4.5, 200, 340)
            pen.line([(ex + sx * rx * 0.9, ey - ry * 0.3), (ex + sx * rx * 1.25, ey - ry * 0.65)], 3.5)
        else:
            pen.ell(ex, ey, rx, ry, WHITE, 4)
            look = -0.35 if expr == "meh" else 0
            pen.d.ellipse([(ex + look * rx - 7 * sc) * SS, (ey + 3 * sc - 7 * sc) * SS, (ex + look * rx + 7 * sc) * SS, (ey + 3 * sc + 7 * sc) * SS], fill=INK)
            if expr == "meh":  # half-closed lid
                pen.poly([(ex - rx, ey - 2), (ex + rx, ey - 2), (ex + rx * 0.7, ey - ry * 0.8), (ex, ey - ry - 2), (ex - rx * 0.7, ey - ry * 0.8)], SKIN, 0)
                pen.line([(ex - rx - 2, ey - 2 * sc), (ex + rx + 2, ey - 2 * sc)], 4.5)
            pen.line([(ex + sx * rx * 0.95, ey - ry * 0.35), (ex + sx * rx * 1.3, ey - ry * 0.7)], 3.5)
        by = -170 if expr == "wide" else -160
        tilt = {"cry": 8, "meh": -3}.get(expr, 0)
        pen.line([P(sx * 18, by - tilt), P(sx * 60, by + tilt)], 4.5)
        if expr == "cry":
            ph = (t * 3) % 1
            pen.rect(ex - 7 * sc, ey + 12 * sc, ex + 7 * sc, ey + (60 + 30 * ph) * sc, TEAR, 3, r=6 * sc)
    pen.line([P(-4, -105), P(4, -88), P(-6, -84)], 3.5)  # nose
    mo = talk and (math.sin(t * 16) + math.sin(t * 8.7)) > 0.3
    mx, my = P(0, -62)
    if expr == "happy":
        pen.ell(mx, my - 6 * sc, 24 * sc, 16 * sc, None, 4.5, 15, 165)
    elif expr in ("wide", "cry") or mo:
        pen.ell(mx, my, (12 if expr != "wide" else 16) * sc, (10 if not mo else 14) * sc, (120, 30, 40), 4)
    else:
        pen.ell(mx, my, 14 * sc, 6 * sc, LIPS, 3.5)
    pen.ink = INK

# ---------- backgrounds ----------
def bg_white(pen):
    pen.d.rectangle([0, 0, W * SS, H * SS], fill=WHITE)

def bg_sala(pen):
    d = pen.d
    d.rectangle([0, 0, W * SS, H * SS], fill=(118, 170, 140))
    pen.poly([(0, 0), (560, 0), (560, 760), (0, 860)], (96, 150, 120))           # left wall
    pen.poly([(0, 860), (560, 760), (1920, 760), (1920, 1080), (0, 1080)], (196, 120, 90))  # floor
    pen.poly([(200, 880), (1300, 830), (1700, 1040), (100, 1080)], (240, 200, 150))  # rug
    for k in range(3): pen.line([(260 + k * 40, 900 + k * 40), (1350 + k * 50, 860 + k * 50)], 7, (220, 150, 90), amp=6)
    pen.rect(1260, 140, 1840, 640, (180, 230, 245))                                 # window
    pen.line([(1550, 140), (1550, 640)], 6); pen.line([(1260, 390), (1840, 390)], 6)
    pen.poly([(1230, 110), (1330, 110), (1300, 700), (1220, 700)], (250, 235, 205))  # curtain
    pen.rect(110, 160, 420, 470, (250, 240, 220))                                   # frame w/ cat
    pen.ell(265, 340, 70, 60, (60, 60, 60)); pen.poly([(210, 300), (225, 250), (245, 290)], (60, 60, 60)); pen.poly([(285, 290), (305, 250), (320, 300)], (60, 60, 60))
    pen.rect(40, 600, 640, 820, (225, 120, 150), r=40)                              # sofa
    pen.rect(70, 520, 610, 650, (215, 105, 140), r=40)
    pen.ell(1100, 700, 60, 30, (200, 90, 70)); pen.poly([(1060, 700), (1140, 700), (1125, 780), (1075, 780)], (200, 90, 70))
    for a in (-60, -20, 20, 60): pen.limb([(1100, 700), (1100 + a * 2, 560 - abs(a))], 22, (50, 140, 70))

def gloria(pen, x, y, shake=0.0, t=0):
    x += math.sin(t * 60) * 8 * shake
    pen.rect(x - 170, y - 420, x + 170, y + 330, (240, 240, 232), r=40)
    pen.line([(x - 170, y - 150), (x + 170, y - 150)], 5)
    for yy in (-300, 60): pen.rect(x + 110, y + yy - 60, x + 130, y + yy + 60, (170, 170, 170), 4, r=8)
    pen.rect(x - 120, y - 385, x + 40, y - 320, (255, 220, 90), 4, r=10)
    htext(pen.d, (x - 40, y - 352), "Gloria", 44)
    htext(pen.d, (x - 10, y + 230), "2008", 44, (150, 150, 150))
    pen.ell(x - 60, y + 110, 26, 26, RED, 4)

def bg_cocina(pen):
    d = pen.d
    d.rectangle([0, 0, W * SS, H * SS], fill=(250, 215, 120))
    for i in range(0, 1920, 110):
        for j in range(380, 700, 110): pen.rect(i + 6, j + 6, i + 104, j + 104, (250, 235, 190), 3)
    pen.poly([(0, 700), (1920, 700), (1920, 1080), (0, 1080)], (120, 150, 190))
    pen.rect(60, 560, 860, 720, (150, 90, 60))
    pen.rect(120, 470, 260, 560, (230, 230, 230), r=12)

# ---------- shots ----------
CAP = {}
def caption(d, s):
    CAP["s"] = s

def draw_caption(d, s):
    f = PF(34)
    w = d.textlength(s, font=f) / SS
    d.rounded_rectangle([(960 - w / 2 - 26) * SS, 980 * SS, (960 + w / 2 + 26) * SS, 1040 * SS], radius=16 * SS, fill=(20, 18, 16))
    d.text((960 * SS, 1010 * SS), s, font=f, fill=WHITE, anchor="mm")

def frame(fn, t, idx=0):
    img = Image.new("RGBA", (W * SS, H * SS), WHITE + (255,))
    pen = Pen(ImageDraw.Draw(img), int(t * 8), img)
    CAP.clear()
    kicks = fn(img, pen, t) or []
    # camera: every hold creeps in (~0.07 %/frame), punch-in kick of +2 % on impacts
    f = t * FPS
    z = 1 + 0.0005 * f
    dx = dy = 0
    for k in kicks:  # impact flip-shake: sign flips every frame, decays over 7 frames
        kf = f - k * FPS
        if 0 <= kf < 7:
            amp = 20 * (1 - kf / 7) * SS
            sgn = 1 if int(kf) % 2 == 0 else -1
            dx += sgn * amp; dy -= sgn * amp * 0.6
            z += 0.02 * (1 - kf / 7)
    cw, ch = img.width / z, img.height / z
    x0 = (img.width - cw) / 2 - dx; y0 = (img.height - ch) * 0.15 - dy
    img = img.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W * SS, H * SS), Image.BICUBIC)
    d = ImageDraw.Draw(img)
    if "s" in CAP: draw_caption(d, CAP["s"])
    if idx == 1 and f < 4:  # white flash right after the hook
        a = int(255 * (1 - f / 4))
        img.alpha_composite(Image.new("RGBA", img.size, (255, 255, 255, a)))
    return img

