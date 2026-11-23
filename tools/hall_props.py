"""Furniture, fittings and clutter for the hall. Everything sits outside the clear play area
(|x| <= 4, |z| <= 7), except the rug (flat) and the chandeliers (ring at 4.75 m)."""
import math
from mathutils import Vector
from hall_lib import *
from hall_shell import WALLS, HW, HL, EH, APEX, TRUSS_Z, WSILL, WHEAD, WWID, WAINS, PLINTH, BEAM, FIRE_W, FIRE_W2, S_at
import hall_fireplace as FP

WARM = [1.0, 0.72, 0.42]
BOOK_COLS = [(0.35, 0.08, 0.07), (0.1, 0.16, 0.3), (0.12, 0.25, 0.14), (0.4, 0.25, 0.1), (0.2, 0.12, 0.08), (0.45, 0.36, 0.2),
             (0.25, 0.07, 0.15), (0.08, 0.2, 0.22), (0.5, 0.42, 0.3), (0.16, 0.14, 0.13)]


def clutter(fn):
    """Small dressing goes into a group that does not cast shadows (keeps shadow passes cheap)."""
    def w(b, *a, **k):
        with b.grp('ns_clutter'):
            return fn(b, *a, **k)
    return w


# ---------------------------------------------------------------------------
# small parts
# ---------------------------------------------------------------------------
@clutter
def candle(b, h=0.16, r=0.017, lit=True):
    b.cyl(r, h, 'wax', 8, tint=b.vary((1, 1, 1), 0.05), bevel=0.003)
    # a couple of wax runs
    for k in range(2):
        a = b.r(0, TAU)
        ln = b.r(0.02, 0.06)
        b.cyl(0.004, ln, 'wax', 5, M=T(math.cos(a) * r, h - ln - 0.004, math.sin(a) * r), bevel=0.002)
    b.rod((0, h, 0), (0, h + 0.012, 0), 0.0016, 'iron', 4, bevel=0)
    if lit:
        b.mark('candle', (0, h + 0.014, 0))


def chain(b, p0, p1, pitch=0.075, wire=0.0065, mat='iron'):
    p0 = Vector(p0); p1 = Vector(p1)
    L = (p1 - p0).length
    n = max(1, round(L / pitch))
    F = frame(p0, p1)
    step = L / n
    for i in range(n):
        x = -L / 2 + (i + 0.5) * step
        oval = [(0.64 * step * math.cos(TAU * k / 8), 0.3 * step * math.sin(TAU * k / 8), 0) for k in range(8)]
        with b.at(F @ T(x, 0, 0) @ RX(PI / 2 if i % 2 else 0)):
            b.sweep(oval, circ_prof(wire, 4), mat, closed=True, up=(0, 0, 1))


@clutter
def candlestick(b, h=0.22, mat='brass', lit=True, ch=0.16):
    prof = [(0, 0), (0.055, 0), (0.06, 0.008), (0.035, 0.022), (0.014, 0.035), (0.012, h * 0.45), (0.022, h * 0.5), (0.012, h * 0.56),
            (0.011, h - 0.03), (0.03, h - 0.012), (0.032, h), (0.02, h), (0.018, h - 0.012), (0, h - 0.012)]
    b.lathe(prof, mat, 12)
    with b.at(T(0, h - 0.012, 0)):
        candle(b, ch, 0.014, lit)


@clutter
def tankard(b, mat='pewter'):
    h = 0.13
    prof = [(0, 0), (0.046, 0), (0.048, 0.006), (0.042, 0.012), (0.039, h), (0.041, h + 0.004), (0.036, h + 0.004), (0.034, 0.014), (0, 0.014)]
    b.lathe(prof, mat, 14)
    path = [(0.04, h - 0.02, 0), (0.075, h - 0.025, 0), (0.085, h * 0.5, 0), (0.07, 0.03, 0), (0.042, 0.03, 0)]
    b.sweep(path, rect_prof(0.014, 0.006, 0.002), mat, up=(0, 0, 1))


@clutter
def plate(b, r=0.12, mat='pewter'):
    prof = [(0, 0), (r * 0.6, 0), (r, 0.014), (r, 0.018), (r * 0.62, 0.007), (0, 0.007)]
    b.lathe(prof, mat, 18)


@clutter
def jug(b, s=1.0, tint=(0.5, 0.3, 0.18)):
    pr = [(0, 0), (0.06, 0), (0.07, 0.01), (0.1, 0.08), (0.105, 0.14), (0.085, 0.21), (0.05, 0.26), (0.045, 0.3), (0.058, 0.33),
          (0.05, 0.33), (0.038, 0.3), (0.042, 0.26), (0, 0.24)]
    b.lathe([(r * s, y * s) for r, y in pr], 'ceramic', 16, tint=tint)
    path = [(0.05 * s, 0.31 * s, 0), (0.11 * s, 0.31 * s, 0), (0.135 * s, 0.24 * s, 0), (0.12 * s, 0.15 * s, 0), (0.1 * s, 0.12 * s, 0)]
    b.sweep(path, circ_prof(0.011 * s, 6), 'ceramic', tint=tint, up=(0, 0, 1))


@clutter
def bowl(b, r=0.15, mat='wood_dark', tint=None):
    prof = [(0, 0), (r * 0.45, 0), (r * 0.5, 0.008), (r * 0.9, r * 0.38), (r, r * 0.5), (r * 0.95, r * 0.5), (r * 0.82, r * 0.36), (r * 0.4, 0.02), (0, 0.02)]
    b.lathe(prof, mat, 16, tint=tint)


@clutter
def fruit_bowl(b):
    bowl(b, 0.16)
    for (x, y, z) in ((0, 0.075, 0), (0.07, 0.085, 0.03), (-0.06, 0.085, 0.05), (0.0, 0.09, -0.07), (-0.05, 0.085, -0.04), (0.02, 0.135, 0.01)):
        col = b.vary((0.55, 0.08, 0.06), 0.2, 0.2) if b.r() < 0.6 else b.vary((0.45, 0.5, 0.12), 0.15, 0.1)
        b.ball(0.036, 'food', 10, 6, tint=col, M=T(x, y, z) @ RX(b.r(-0.4, 0.4)))
        b.rod((x, y + 0.03, z), (x + 0.005, y + 0.046, z), 0.002, 'food', 4, tint=(0.2, 0.12, 0.05), bevel=0)


@clutter
def book(b, w, h, d, col, bands=False):
    """Book lying on its back cover at the origin: w = thickness (y), h = height (x), d = depth (z). Spine at -z."""
    c = 0.004
    b.box((h - 0.008, w - 2 * c, d - 0.006), 'paper', pos=(0, w / 2, 0.002), bevel=0, tint=b.vary((1, 0.97, 0.9), 0.08))
    b.box((h, c, d), 'leather', pos=(0, c / 2, 0), bevel=0, tint=col)
    b.box((h, c, d), 'leather', pos=(0, w - c / 2, 0), bevel=0, tint=col)
    b.box((h, w, c * 1.6), 'leather', pos=(0, w / 2, -d / 2 + c * 0.2), bevel=0.003, tint=col)
    if bands:
        for f in (-0.3, 0.3, 0.38):
            b.box((0.006, w + 0.002, 0.004), 'brass', pos=(f * h, w / 2, -d / 2 - c * 0.5), bevel=0)


@clutter
def shelf_books(b, x0, x1, y, zback, gap_h, depth=0.24):
    """Fill a shelf compartment (wall-local: x along, y shelf top, books' spines face +z)."""
    x = x0 + b.r(0.0, 0.03)
    while x < x1 - 0.04:
        roll = b.r()
        if roll < 0.1 and x1 - x > 0.3:
            # horizontal stack
            n = b.rng.randint(2, 4); yy = y; hh = b.r(0.2, 0.26)
            for k in range(n):
                w = b.r(0.03, 0.055)
                with b.at(T(x + hh / 2, yy, zback + depth - 0.11 + b.r(-0.01, 0.01)) @ RY(PI + b.r(-0.12, 0.12))):
                    book(b, w, hh, b.r(0.15, 0.19), b.vary(b.rng.choice(BOOK_COLS), 0.2), b.r() < 0.4)
                yy += w
            x += hh + b.r(0.01, 0.05)
        elif roll < 0.2 and x1 - x > 0.25:
            kind = b.rng.randint(0, 3)
            cx = x + 0.1; cz = zback + depth - 0.12
            if kind == 0:
                with b.at(T(cx, y, cz)):
                    jug(b, b.r(0.6, 0.8), b.vary(b.rng.choice([(0.5, 0.3, 0.18), (0.2, 0.3, 0.35), (0.6, 0.55, 0.4)]), 0.15))
            elif kind == 1:
                with b.at(T(cx, y, cz)):
                    candlestick(b, 0.16, 'brass', False, 0.1)
            elif kind == 2:
                # brass cog on a little stand
                with b.at(T(cx, y, cz)):
                    b.box((0.12, 0.015, 0.07), 'wood_dark', pos=(0, 0.0075, 0), bevel=0.004)
                    pts = [((0.075 if k % 2 == 0 else 0.058) * math.cos(TAU * (k + 0.5 * (k % 2) * 0) / 24), 0.1 + (0.075 if k % 2 == 0 else 0.058) * math.sin(TAU * k / 24)) for k in range(24)]
                    b.prism(pts, 0.014, 'brass', bevel=0.002)
                    b.cyl(0.02, 0.03, 'brass', 8, M=T(0, 0.1, -0.015) @ RX(PI / 2))
            else:
                with b.at(T(cx, y, cz)):
                    bowl(b, 0.09, 'pewter')
            x += 0.2 + b.r(0.0, 0.06)
        elif roll < 0.27:
            x += b.r(0.05, 0.14)
        else:
            run = b.rng.randint(3, 9)
            lean = 0.0
            for k in range(run):
                w = b.r(0.024, 0.062)
                if x + w > x1 - 0.01:
                    break
                hh = min(gap_h - 0.03, b.r(0.19, 0.31))
                dd = b.r(0.14, 0.2)
                col = b.vary(b.rng.choice(BOOK_COLS), 0.22)
                last = (k == run - 1) and b.r() < 0.35 and x + w + 0.07 < x1
                ang = -0.22 if last else b.r(-0.012, 0.012)
                # upright: book's height along +y, thickness along x, spine toward +z
                with b.at(T(x + w / 2 + (0.03 if last else 0), y, zback + depth - dd / 2 - b.r(0.0, 0.025)) @ RZ(ang) @ T(0, hh / 2, 0) @ RZ(PI / 2) @ RY(PI) @ T(0, -w / 2, 0)):
                    book(b, w, hh, dd, col, b.r() < 0.45)
                x += w + (0.05 if last else 0.001)
            x += b.r(0.0, 0.03)


# ---------------------------------------------------------------------------
# lighting fixtures
# ---------------------------------------------------------------------------
def chandelier(b, x, z, y=4.78):
    R = 0.95
    with b.at(T(x, y, z)):
        def ring(r, yy, w, h):
            b.lathe([(r - w / 2, yy - h / 2), (r + w / 2, yy - h / 2), (r + w / 2, yy + h / 2), (r - w / 2, yy + h / 2), (r - w / 2, yy - h / 2)], 'iron', 32)
        ring(R, 0, 0.03, 0.07)
        ring(R * 0.56, 0.5, 0.026, 0.055)
        for k in range(4):
            b.box((2 * R, 0.02, 0.032), 'iron', rot=RY(k * PI / 4 + PI / 8), bevel=0.004)
        for k in range(3):
            b.box((2 * R * 0.56, 0.018, 0.028), 'iron', pos=(0, 0.5, 0), rot=RY(k * PI / 3), bevel=0.004)
        hub = [(0, -0.2), (0.022, -0.185), (0.03, -0.15), (0.012, -0.11), (0.02, -0.07), (0.065, -0.03), (0.07, 0.02), (0.03, 0.05), (0.02, 0.1),
               (0.02, 0.44), (0.045, 0.47), (0.045, 0.53), (0.02, 0.56), (0.016, 1.3), (0.03, 1.32), (0.0, 1.36)]
        b.lathe(hub, 'iron', 10)
        # S-scroll stays between the tiers
        for k in range(8):
            a = k * TAU / 8 + PI / 8
            with b.at(RY(-a)):
                pts = [(R - 0.02, 0.03, 0)]
                for i in range(1, 9):
                    t = i / 8
                    pts.append((R - 0.02 - (R * 0.44 - 0.02) * t, 0.03 + 0.47 * t + 0.09 * math.sin(t * PI), 0))
                b.sweep(pts, rect_prof(0.012, 0.012, 0.003), 'iron', up=(0, 0, 1))
        for (rr, n, y0, off) in ((R, 12, 0.035, 0.0), (R * 0.56, 6, 0.5275, 0.5)):
            for k in range(n):
                a = (k + off) * TAU / n
                with b.at(T(rr * math.cos(a), y0, rr * math.sin(a))):
                    b.lathe([(0, 0), (0.016, 0), (0.046, 0.02), (0.046, 0.026), (0.02, 0.012), (0, 0.012)], 'iron', 10)
                    with b.at(T(0, 0.012, 0)):
                        candle(b, b.r(0.1, 0.19), 0.017)
        # suspension: four chains to a gather ring, one chain up to the ridge
        gy = 1.5
        for k in range(4):
            a = k * TAU / 4 + PI / 8
            chain(b, (R * math.cos(a), 0.035, R * math.sin(a)), (0.03 * math.cos(a), gy - 0.02, 0.03 * math.sin(a)), 0.085)
        ringp = [(0.05 * math.cos(TAU * k / 12), gy + 0.03 + 0.05 * math.sin(TAU * k / 12), 0) for k in range(12)]
        b.sweep(ringp, circ_prof(0.009, 5), 'iron', closed=True, up=(0, 0, 1))
        chain(b, (0, gy + 0.07, 0), (0, APEX - 0.44 - y, 0), 0.11, 0.009)
        b.mark('light', (0, -0.35, 0), name='Chandelier', color=WARM, energy=2.6, range=13.0, shadow=True, size=0.0, fog=0.3)
        b.mark('light', (0, 0.9, 0), name='ChandelierUp', color=WARM, energy=0.9, range=7.0, shadow=False, size=0.0, fog=0.0, specular=0.0)


def sconce(b, light=True):
    """Wall-local: origin on the mounting face, +z into the room."""
    pts = [(-0.045, -0.13), (0, -0.19), (0.045, -0.13), (0.045, 0.1), (0, 0.16), (-0.045, 0.1)]
    b.prism(pts, 0.012, 'iron', bevel=0.003, M=T(0, 0, 0.006))
    path = [(0, -0.06, 0.012), (0, -0.1, 0.07), (0, -0.09, 0.15), (0, -0.03, 0.2), (0, 0.02, 0.2)]
    b.sweep(path, rect_prof(0.016, 0.016, 0.004), 'iron', up=(1, 0, 0))
    curl = [(0, 0.05 + 0.035 * math.cos(t), 0.05 + 0.035 * math.sin(t) * 1.0) for t in [PI * 1.5 - i * 0.55 for i in range(8)]]
    b.sweep([(0, 0.08, 0.012)] + curl, rect_prof(0.012, 0.01, 0.003), 'iron', up=(1, 0, 0))
    with b.at(T(0, 0.02, 0.2)):
        b.lathe([(0, 0), (0.02, 0), (0.06, 0.018), (0.06, 0.024), (0.022, 0.012), (0, 0.012)], 'iron', 12)
        with b.at(T(0, 0.012, 0)):
            candle(b, 0.17, 0.019)
    if light:
        b.mark('light', (0, 0.28, 0.62), name='Sconce', color=WARM, energy=0.5, range=4.6, shadow=False, size=0.0, fog=0.08)


def candle_stand(b, h=1.45):
    for k in range(3):
        a = k * TAU / 3 + 0.3
        pts = [(0.0, 0.3, 0.0)]
        for i in range(1, 7):
            t = i / 6
            rr = 0.3 * t
            pts.append((rr * math.cos(a), 0.3 * (1 - t) ** 1.8 + 0.012, rr * math.sin(a)))
        b.sweep(pts, rect_prof(0.02, 0.02, 0.004), 'iron', up=(0, 1, 0.01))
    prof = [(0.014, 0.28), (0.03, 0.3), (0.014, 0.33), (0.012, h * 0.5), (0.028, h * 0.52), (0.012, h * 0.55), (0.011, h - 0.05), (0.03, h - 0.03),
            (0.11, h - 0.005), (0.11, h), (0.035, h - 0.012), (0, h - 0.012)]
    b.lathe(prof, 'iron', 12)
    with b.at(T(0, h - 0.012, 0)):
        candle(b, b.r(0.2, 0.28), 0.032)
    b.col((0.24, h, 0.24), pos=(0, h / 2, 0), kind='cyl')
    b.mark('light', (0, h + 0.5, 0), name='Stand', color=WARM, energy=0.8, range=4.5, shadow=False, size=0.05, fog=0.08)


# ---------------------------------------------------------------------------
# furniture
# ---------------------------------------------------------------------------
def rug(b, cx, cz, W=5.2, L=9.6):
    with b.grp('ns_rug'), b.at(T(cx, 0, cz)):
        b.box((W, 0.012, L), 'wool', pos=(0, 0.006, 0), bevel=0.004, tint=(0.07, 0.08, 0.14))
        n = 12
        P = [[Vector((-W / 2 + 0.006 + (W - 0.012) * i / n, 0.0128, L / 2 - 0.006 - (L - 0.012) * j / n)) for j in range(n + 1)] for i in range(n + 1)]
        b.grid(P, 'rug', uvfn=lambda i, j: (i / n, j / n))
        for sz in (-1, 1):
            x = -W / 2 + 0.012
            while x < W / 2 - 0.012:
                ln = b.r(0.07, 0.1)
                b.box((0.011, 0.004, ln), 'wool', pos=(x + b.r(-0.002, 0.002), 0.003, sz * (L / 2 + ln / 2 - 0.004)), bevel=0,
                      rot=RY(b.r(-0.12, 0.12)), tint=b.vary((0.72, 0.64, 0.48), 0.12))
                x += 0.02


def hearth_rug(b, cx, cz, W=2.7, D=1.75):
    with b.grp('ns_rug'), b.at(T(cx, 0, cz)):
        b.box((W, 0.014, D), 'wool', pos=(0, 0.007, 0), bevel=0.005, tint=(0.07, 0.08, 0.14))
        n = 8
        m = 0.07
        P = [[Vector((-W / 2 + m + (W - 2 * m) * i / n, 0.0148, D / 2 - m - (D - 2 * m) * j / n)) for j in range(n + 1)] for i in range(n + 1)]
        b.grid(P, 'rug', tint=(0.62, 0.58, 0.55), uvfn=lambda i, j: (0.215 + 0.57 * j / n, 0.26 + 0.48 * i / n))
        for sx in (-1, 1):
            z = -D / 2 + 0.012
            while z < D / 2 - 0.012:
                ln = b.r(0.06, 0.09)
                b.box((ln, 0.004, 0.011), 'wool', pos=(sx * (W / 2 + ln / 2 - 0.004), 0.003, z + b.r(-0.002, 0.002)), bevel=0,
                      rot=RY(b.r(-0.12, 0.12)), tint=b.vary((0.72, 0.64, 0.48), 0.12))
                z += 0.02


def trestle_table(b, L=4.4, W=0.95):
    top_y = 0.76
    n = 4
    for k in range(n):
        pw = W / n
        b.box((L + b.r(-0.02, 0.02), 0.055, pw - 0.004), 'wood_table', pos=(0, top_y - 0.0275, -W / 2 + (k + 0.5) * pw), bevel=0.007, grain=0,
              tint=b.vary((1, 1, 1), 0.1))
    for x in (-L / 2 + 0.55, 0.0, L / 2 - 0.55):
        with b.at(T(x, 0, 0)):
            for sz in (-1, 1):
                b.beam((0, 0.0, sz * 0.38), (0, top_y - 0.11, sz * 0.13), 0.075, 0.1, 'wood_dark', up=(1, 0, 0), bevel=0.008, tint=b.vary((1, 1, 1), 0.08))
            b.box((0.1, 0.07, W - 0.12), 'wood_dark', pos=(0, top_y - 0.09, 0), bevel=0.008, grain=2)
            b.box((0.06, 0.09, 0.5), 'wood_dark', pos=(0, 0.3, 0), bevel=0.008, grain=2)
            b.box((0.03, 0.14, 0.03), 'wood_oak', pos=(0.055, 0.3, 0), bevel=0.004, rot=RZ(0.12))
    b.box((L - 0.7, 0.11, 0.05), 'wood_dark', pos=(0, 0.3, 0), bevel=0.008, grain=0)
    b.col((L, top_y, W), pos=(0, top_y / 2, 0))


def bench(b, L=4.0, W=0.3, h=0.45):
    b.box((L, 0.05, W), 'wood_table', pos=(0, h - 0.025, 0), bevel=0.008, grain=0, tint=b.vary((0.95, 0.95, 0.95), 0.08))
    for x in (-L / 2 + 0.35, 0.0, L / 2 - 0.35):
        pts = [(-W / 2 + 0.01, 0), (-0.05, 0), (0, 0.1), (0.05, 0), (W / 2 - 0.01, 0), (W / 2 - 0.04, h - 0.05), (-W / 2 + 0.04, h - 0.05)]
        b.prism(pts, 0.045, 'wood_dark', bevel=0.006, M=T(x, 0, 0) @ RY(PI / 2), grain=1)
    b.box((L - 0.7, 0.08, 0.035), 'wood_dark', pos=(0, 0.25, 0), bevel=0.006, grain=0)
    b.col((L, h, W), pos=(0, h / 2, 0))


@clutter
def table_setting(b, L=4.4, W=0.95):
    y = 0.76
    # linen runner
    n = 16
    P = [[Vector((-L * 0.42 + L * 0.84 * i / n, y + 0.003 + 0.0015 * math.sin(i * 1.7 + j), -0.19 + 0.38 * j / 2)) for j in range(3)] for i in range(n + 1)]
    b.grid(P, 'linen', tint=(0.5, 0.12, 0.1), flip=True, uvfn=lambda i, j: (i * 0.5, j * 0.4))
    for sx in (-1, 1):
        with b.at(T(sx * 1.05, y + 0.004, 0)):
            # three-branch candelabrum
            b.lathe([(0, 0), (0.075, 0), (0.08, 0.01), (0.04, 0.03), (0.016, 0.05), (0.014, 0.2), (0.026, 0.22), (0.014, 0.25), (0.012, 0.36), (0, 0.37)], 'brass', 12)
            for s2 in (-1, 0, 1):
                if s2:
                    pts = [(0, 0.24, 0), (s2 * 0.05, 0.2, 0), (s2 * 0.11, 0.2, 0), (s2 * 0.14, 0.25, 0), (s2 * 0.14, 0.3, 0)]
                    b.sweep(pts, circ_prof(0.007, 6), 'brass', up=(0, 0, 1))
                with b.at(T(s2 * 0.14, 0.3 if s2 else 0.36, 0)):
                    b.lathe([(0, 0), (0.012, 0), (0.028, 0.014), (0.028, 0.02), (0.016, 0.01), (0, 0.01)], 'brass', 10)
                    with b.at(T(0, 0.01, 0)):
                        candle(b, b.r(0.11, 0.17), 0.012)
            b.mark('light', (0, 0.75, 0), name='Table', color=WARM, energy=0.6, range=3.6, shadow=False, size=0.05, fog=0.15)
    with b.at(T(0, y + 0.004, 0.02)):
        fruit_bowl(b)
    places = [(-1.75, 0.27), (-0.7, 0.3), (0.5, 0.28), (1.7, 0.3), (-1.4, -0.29), (-0.2, -0.3), (0.95, -0.28), (1.9, -0.27)]
    for i, (x, z) in enumerate(places):
        with b.at(T(x, y, z) @ RY(b.r(0, TAU))):
            plate(b, b.r(0.11, 0.125))
        if i % 4 != 3:
            with b.at(T(x + b.r(0.16, 0.22), y, z + (0.08 if z < 0 else -0.08)) @ RY(b.r(0, TAU))):
                tankard(b)
    with b.at(T(-0.55, y, -0.03) @ RY(0.8)):
        jug(b, 0.95, (0.42, 0.25, 0.14))
    with b.at(T(0.62, y, 0.06) @ RY(2.5)):
        jug(b, 0.8, (0.2, 0.28, 0.32))
    # bread board
    with b.at(T(1.45, y, 0.0) @ RY(0.3)):
        b.box((0.36, 0.02, 0.22), 'wood_oak', pos=(0, 0.01, 0), bevel=0.006, grain=0, tint=(1.3, 1.2, 1.1))
        b.ball(0.085, 'food', 12, 7, tint=(0.5, 0.3, 0.13), M=T(-0.04, 0.062, 0) @ SC(1.35, 1, 1), sy=0.62)
        b.cyl(0.07, 0.05, 'food', 14, tint=(0.75, 0.58, 0.2), M=T(0.12, 0.02, 0.02), bevel=0.008)
    with b.at(T(-1.15, y, 0.02)):
        b.cyl(0.1, 0.07, 'food', 16, tint=(0.72, 0.55, 0.18), bevel=0.012)


def chair(b, tint=(1, 1, 1), cushion=(0.34, 0.09, 0.08)):
    """High-backed hall chair facing +z."""
    sw, sd, sh = 0.58, 0.52, 0.44
    wd = 'wood_dark'
    tv = lambda: b.vary(tint, 0.07)
    for sx in (-1, 1):
        # back post with finial
        b.box((0.06, 1.36, 0.06), wd, pos=(sx * (sw / 2 - 0.03), 0.68, -sd / 2 + 0.03), bevel=0.008, grain=1, tint=tv())
        b.lathe([(0, 0), (0.02, 0), (0.034, 0.025), (0.03, 0.05), (0.012, 0.065), (0.02, 0.085), (0, 0.1)], wd, 8, tint=tv(),
                M=T(sx * (sw / 2 - 0.03), 1.36, -sd / 2 + 0.03))
        # front leg up to the arm
        b.box((0.06, 0.66, 0.06), wd, pos=(sx * (sw / 2 - 0.03), 0.33, sd / 2 - 0.03), bevel=0.008, grain=1, tint=tv())
        # arm
        b.box((0.075, 0.04, sd + 0.04), wd, pos=(sx * (sw / 2 - 0.03), 0.68, 0.01), bevel=0.012, grain=2, tint=tv())
        # side rails
        b.box((0.03, 0.07, sd - 0.12), wd, pos=(sx * (sw / 2 - 0.03), sh - 0.06, 0), bevel=0.005, grain=2, tint=tv())
        b.box((0.03, 0.05, sd - 0.12), wd, pos=(sx * (sw / 2 - 0.03), 0.14, 0), bevel=0.005, grain=2, tint=tv())
    b.box((sw - 0.12, 0.07, 0.03), wd, pos=(0, sh - 0.06, sd / 2 - 0.03), bevel=0.005, grain=0, tint=tv())
    b.box((sw - 0.12, 0.05, 0.03), wd, pos=(0, 0.14, sd / 2 - 0.03), bevel=0.005, grain=0, tint=tv())
    b.box((sw - 0.12, 0.05, 0.03), wd, pos=(0, 0.14, -sd / 2 + 0.03), bevel=0.005, grain=0, tint=tv())
    b.box((sw - 0.1, 0.03, sd - 0.06), wd, pos=(0, sh - 0.015, 0), bevel=0.006, grain=0, tint=tv())
    # back: rails, panel, arched crest
    b.box((sw - 0.12, 0.08, 0.035), wd, pos=(0, sh + 0.1, -sd / 2 + 0.03), bevel=0.006, grain=0, tint=tv())
    b.box((sw - 0.12, 0.72, 0.018), wd, pos=(0, sh + 0.5, -sd / 2 + 0.03), bevel=0.003, grain=1, tint=b.vary(tint, 0.05))
    b.box((sw - 0.24, 0.56, 0.014), wd, pos=(0, sh + 0.48, -sd / 2 + 0.042), bevel=0.01, grain=1, tint=b.vary((tint[0] * 1.08, tint[1] * 1.05, tint[2]), 0.05))
    hw = sw / 2 - 0.06
    pts = [(-hw, 0), (hw, 0)] + [(hw * math.cos(PI * k / 10), 0.07 + 0.11 * math.sin(PI * k / 10)) for k in range(0, 11)]
    b.prism(pts, 0.04, wd, bevel=0.008, tint=tv(), M=T(0, sh + 0.86, -sd / 2 + 0.03), grain=0)
    # cushions
    b.cushion(sw - 0.13, 0.1, sd - 0.09, 'velvet', tint=b.vary(cushion, 0.08), M=T(0, sh + 0.045, 0.005), puff=1.0)
    b.cushion(sw - 0.18, 0.09, 0.42, 'velvet', tint=b.vary(cushion, 0.08), M=T(0, sh + 0.33, -sd / 2 + 0.1) @ RX(PI / 2 - 0.12))
    b.col((sw, 0.7, sd), pos=(0, 0.35, 0))
    b.col((sw, 0.75, 0.1), pos=(0, 1.05, -sd / 2 + 0.04))


def side_table(b):
    prof = [(0, 0.5), (0.3, 0.5), (0.31, 0.508), (0.31, 0.53), (0.3, 0.54), (0, 0.54)]
    b.lathe(prof, 'wood_red', 24)
    b.lathe([(0.07, 0.04), (0.085, 0.06), (0.035, 0.12), (0.03, 0.26), (0.05, 0.3), (0.03, 0.34), (0.035, 0.47), (0.1, 0.5)], 'wood_red', 12)
    for k in range(3):
        a = k * TAU / 3
        pts = [(0.05 * math.cos(a), 0.09, 0.05 * math.sin(a)), (0.16 * math.cos(a), 0.06, 0.16 * math.sin(a)), (0.25 * math.cos(a), 0.015, 0.25 * math.sin(a))]
        b.sweep(pts, rect_prof(0.035, 0.04, 0.008), 'wood_red', up=(0, 1, 0))
    with b.at(T(0.08, 0.54, 0.05)):
        candlestick(b, 0.2)
    with b.at(T(-0.12, 0.54, -0.06) @ RY(0.7)):
        tankard(b)
    with b.at(T(-0.02, 0.54, 0.15) @ RY(0.4)):
        book(b, 0.04, 0.24, 0.17, (0.3, 0.07, 0.06), True)
    b.col((0.6, 0.54, 0.6), pos=(0, 0.27, 0), kind='cyl')
    b.mark('light', (0.08, 1.05, 0.05), name='SideTable', color=WARM, energy=0.5, range=3.0, shadow=False, size=0.03, fog=0.1)


def footstool(b):
    for sx in (-1, 1):
        for sz in (-1, 1):
            b.lathe([(0, 0), (0.02, 0), (0.028, 0.03), (0.018, 0.08), (0.03, 0.14), (0.028, 0.2), (0, 0.2)], 'wood_dark', 8, M=T(sx * 0.19, 0, sz * 0.13))
    b.box((0.48, 0.05, 0.36), 'wood_dark', pos=(0, 0.215, 0), bevel=0.01, grain=0)
    b.cushion(0.46, 0.12, 0.34, 'velvet', tint=(0.15, 0.25, 0.16), M=T(0, 0.29, 0))
    b.col((0.48, 0.32, 0.36), pos=(0, 0.16, 0))


def bookshelf(b, W=2.6, H=2.75, D=0.42):
    """Wall-local, back against z = 0."""
    wd = 'wood_dark'
    tv = lambda: b.vary((1, 1, 1), 0.06)
    z0 = 0.02
    b.box((W, H - 0.1, 0.02), wd, pos=(0, H / 2, z0 + 0.01), bevel=0, grain=1, tint=(0.7, 0.7, 0.7))
    for x in (-W / 2 + 0.025, 0.0, W / 2 - 0.025):
        b.box((0.05, H - 0.12, D), wd, pos=(x, (H - 0.12) / 2 + 0.06, z0 + D / 2), bevel=0.006, grain=1, tint=tv())
    # plinth, cornice
    b.box((W + 0.04, 0.14, D + 0.02), wd, pos=(0, 0.07, z0 + D / 2 + 0.01), bevel=0.012, grain=0, tint=tv())
    b.box((W + 0.1, 0.07, D + 0.06), wd, pos=(0, H - 0.035, z0 + D / 2 + 0.02), bevel=0.02, grain=0, tint=tv())
    b.box((W + 0.05, 0.05, D + 0.03), wd, pos=(0, H - 0.09, z0 + D / 2 + 0.01), bevel=0.012, grain=0, tint=tv())
    ys = [0.14, 0.62, 1.06, 1.48, 1.9, 2.3]
    for i, y in enumerate(ys):
        b.box((W - 0.06, 0.03, D - 0.03), wd, pos=(0, y - 0.015, z0 + D / 2), bevel=0.004, grain=0, tint=tv())
        gap = (ys[i + 1] if i + 1 < len(ys) else H - 0.12) - y - 0.03
        for (xa, xb) in ((-W / 2 + 0.06, -0.035), (0.035, W / 2 - 0.06)):
            shelf_books(b, xa, xb, y, z0 + 0.03, gap, D - 0.07)
    b.col((W, H, D + 0.04), pos=(0, H / 2, D / 2))


def sideboard(b, W=2.0, H=0.95, D=0.52):
    wd = 'wood_red'
    tv = lambda: b.vary((1, 1, 1), 0.07)
    z0 = 0.02
    b.box((W - 0.04, H - 0.14, D - 0.04), wd, pos=(0, 0.1 + (H - 0.14) / 2, z0 + D / 2), bevel=0.004, grain=0, tint=(0.8, 0.8, 0.8))
    b.box((W + 0.06, 0.045, D + 0.05), 'wood_table', pos=(0, H - 0.0225, z0 + D / 2 + 0.01), bevel=0.012, grain=0, tint=tv())
    b.box((W, 0.1, D), wd, pos=(0, 0.05, z0 + D / 2), bevel=0.01, grain=0, tint=tv())
    n = 4
    dw = (W - 0.1) / n
    for k in range(n + 1):
        b.box((0.06, H - 0.15, 0.03), wd, pos=(-W / 2 + 0.05 + k * dw, 0.1 + (H - 0.15) / 2, z0 + D + 0.0), bevel=0.006, grain=1, tint=tv())
    for yy in (0.13, H - 0.08):
        b.box((W - 0.04, 0.06, 0.028), wd, pos=(0, yy, z0 + D), bevel=0.006, grain=0, tint=tv())
    for k in range(n):
        x = -W / 2 + 0.05 + (k + 0.5) * dw
        b.box((dw - 0.1, H - 0.34, 0.02), wd, pos=(x, 0.1 + (H - 0.15) / 2, z0 + D - 0.002), bevel=0.012, grain=1, tint=b.vary((1.08, 1.05, 1.0), 0.06))
        ring = [(x + (0.16 if k % 2 == 0 else -0.16) + 0.022 * math.cos(TAU * i / 10), 0.52 + 0.022 * math.sin(TAU * i / 10), z0 + D + 0.022) for i in range(10)]
        b.sweep(ring, circ_prof(0.004, 5), 'iron', closed=True, up=(0, 0, 1))
    # things on top
    with b.at(T(0, H, z0 + D / 2)):
        for sx in (-1, 1):
            with b.at(T(sx * 0.78, 0, 0.02)):
                candlestick(b, 0.26)
        b.mark('light', (0, 0.6, 0.15), name='Sideboard', color=WARM, energy=0.8, range=3.8, shadow=False, size=0.05, fog=0.15)
        for k, x in enumerate((-0.42, 0.0, 0.42)):
            with b.at(T(x, 0.005, -0.17) @ RX(-PI / 2 + 0.2)):
                plate(b, 0.15)
        with b.at(T(-0.3, 0, 0.08)):
            jug(b, 1.0, (0.22, 0.3, 0.33))
        with b.at(T(0.3, 0, 0.1)):
            fruit_bowl(b)
        with b.at(T(0.03, 0, 0.14) @ RY(1.0)):
            tankard(b)
    b.col((W, H, D + 0.04), pos=(0, H / 2, D / 2))


def chest(b, W=1.1, D=0.56, H=0.42, tint=(1, 1, 1)):
    wd = 'wood_red'
    b.box((W, H, D), wd, pos=(0, H / 2 + 0.03, 0), bevel=0.01, grain=0, tint=b.vary(tint, 0.06))
    for sx in (-1, 1):
        for sz in (-1, 1):
            b.box((0.07, 0.07, 0.07), wd, pos=(sx * (W / 2 - 0.05), 0.03, sz * (D / 2 - 0.05)), bevel=0.01)
    # barrel lid
    n = 10
    arc = [(-D / 2, 0)] + [(-(D / 2) * math.cos(PI * k / n), 0.02 + 0.17 * math.sin(PI * k / n)) for k in range(n + 1)] + [(D / 2, 0)]
    b.prism(arc, W + 0.02, wd, bevel=0.008, tint=b.vary(tint, 0.06), M=T(0, H + 0.035, 0) @ RY(PI / 2), grain=2)
    for x in (-W / 2 + 0.1, 0.0, W / 2 - 0.1):
        arc2 = [(-D / 2 - 0.006, -H * 0.55)] + [(-(D / 2 + 0.006) * math.cos(PI * k / n), 0.026 + 0.176 * math.sin(PI * k / n)) for k in range(n + 1)] + [(D / 2 + 0.006, -H * 0.55)]
        inner = [(p[0] * 0.985, p[1] - 0.006) for p in arc2[1:-1]]
        # strap as a swept band over the lid and down the front/back
        path = [(x, H + 0.035 + p[1], p[0]) for p in arc2]
        b.sweep(path, rect_prof(0.05, 0.006, 0.002), 'iron', up=(0, 0, -1))
    b.box((0.1, 0.13, 0.012), 'iron', pos=(0, H - 0.02, D / 2 + 0.008), bevel=0.003)
    b.cyl(0.012, 0.012, 'iron', 8, M=T(0, H - 0.04, D / 2 + 0.012) @ RX(PI / 2))
    for sx in (-1, 1):
        ring = [(sx * (W / 2 + 0.012), H * 0.6 + 0.045 * math.sin(TAU * i / 10) - 0.02, 0.06 * math.cos(TAU * i / 10)) for i in range(10)]
        b.sweep(ring, circ_prof(0.006, 5), 'iron', closed=True, up=(1, 0, 0))
    b.col((W, H + 0.2, D), pos=(0, (H + 0.2) / 2, 0))


def barrel(b, h=0.95, r0=0.27, r1=0.34, lying=False, tap=False):
    n = 18; m = 8
    for k in range(n):
        tn = b.vary((1, 1, 1), 0.13, 0.03)
        P = []
        for i in (0, 1):
            a = (k + i) * TAU / n - (0.004 if i else -0.004)
            col = []
            for j in range(m + 1):
                t = j / m
                rr = r0 + (r1 - r0) * math.sin(PI * t) ** 0.9
                col.append(Vector((rr * math.cos(a), t * h, rr * math.sin(a))))
            P.append(col)
        b.grid(P, 'wood_oak', tint=tn, uvfn=lambda i, j, k=k: (k * 0.11 + i * 0.1, j / m * h), flip=True)
    b.lathe([(r0 - 0.012, h - 0.025), (0, h - 0.025)], 'wood_oak', n, tint=(0.85, 0.85, 0.85))
    for t in (0.06, 0.26, 0.74, 0.94):
        rr = r0 + (r1 - r0) * math.sin(PI * t) ** 0.9 + 0.003
        y = t * h
        b.lathe([(rr - 0.004, y - 0.022), (rr + 0.004, y - 0.022), (rr + 0.004, y + 0.022), (rr - 0.004, y + 0.022)], 'iron', n)
    if tap:
        b.rod((r0 - 0.02, 0.16, 0), (r1 + 0.12, 0.16, 0), 0.016, 'wood_dark', 8)
        b.box((0.02, 0.07, 0.035), 'wood_dark', pos=(r1 + 0.08, 0.2, 0), bevel=0.005)
    b.col((2 * r1, h, 2 * r1), pos=(0, h / 2, 0), kind='cyl')


def firewood_rack(b, W=1.7, H=1.15, D=0.5):
    """Wall-local stack of logs between two uprights."""
    for sx in (-1, 1):
        b.box((0.07, H + 0.1, 0.07), 'wood_beam', pos=(sx * (W / 2 + 0.035), (H + 0.1) / 2, D / 2), bevel=0.008, grain=1, tint=BEAM)
        b.box((0.07, 0.06, D), 'wood_beam', pos=(sx * (W / 2 + 0.035), 0.03, D / 2), bevel=0.008, grain=2, tint=BEAM)
    b.box((W + 0.14, 0.05, 0.06), 'wood_beam', pos=(0, 0.06, D / 2), bevel=0.008, grain=0, tint=BEAM)
    y = 0.09
    row = 0
    while y < H:
        r = b.r(0.065, 0.095)
        x = -W / 2 + r + (0.07 if row % 2 else 0.0)
        while x < W / 2 - r * 0.8:
            rr = r * b.r(0.82, 1.1)
            ln = b.r(0.42, 0.5)
            z0 = b.r(0.0, 0.05)
            FP._log(b, (x, y + rr, z0 + 0.01), (x + b.r(-0.01, 0.01), y + rr + b.r(-0.006, 0.006), z0 + ln), rr)
            x += rr * 2 + 0.006
        y += r * 1.75
        row += 1
    b.col((W + 0.14, H + 0.1, D + 0.06), pos=(0, (H + 0.1) / 2, D / 2))


def log_basket(b):
    prof = [(0, 0), (0.24, 0), (0.26, 0.02), (0.33, 0.36), (0.34, 0.4), (0.32, 0.4), (0.31, 0.36), (0.24, 0.04), (0, 0.04)]
    b.lathe(prof, 'hessian', 18, tint=(0.75, 0.6, 0.42))
    for y in (0.1, 0.22, 0.34):
        rr = 0.26 + (y / 0.36) * 0.07 + 0.006
        b.lathe([(rr, y - 0.012), (rr + 0.008, y), (rr, y + 0.012)], 'hessian', 18, tint=(0.5, 0.38, 0.25))
    for (x, z, a, t) in ((0.0, 0.0, 0.2, 0.1), (0.12, 0.05, -0.25, 0.2), (-0.11, -0.04, 0.35, -0.2), (0.02, -0.13, -0.1, 0.3), (-0.03, 0.13, 0.15, -0.3)):
        d = Vector((math.sin(a) * math.cos(t), math.cos(a), math.sin(a) * math.sin(t) + t * 0.3)).normalized()
        p0 = Vector((x, 0.07, z))
        FP._log(b, p0, p0 + d * b.r(0.45, 0.55), b.r(0.055, 0.075))
    b.col((0.68, 0.45, 0.68), pos=(0, 0.225, 0), kind='cyl')


@clutter
def polearm(b, kind=0, L=2.3):
    """Upright along +y from the origin."""
    b.cyl(0.017, L, 'wood_oak', 8, tint=b.vary((0.9, 0.85, 0.8), 0.1), bevel=0.003)
    st = b.vary((0.9, 0.9, 0.92), 0.05)
    if kind == 0:   # spear
        b.lathe([(0.021, L - 0.12), (0.024, L - 0.1), (0.019, L)], 'pewter', 8, tint=st)
        pts = [(0, 0), (0.035, 0.07), (0.022, 0.2), (0, 0.34), (-0.022, 0.2), (-0.035, 0.07)]
        b.prism(pts, 0.012, 'pewter', bevel=0.005, tint=st, M=T(0, L, 0))
    elif kind == 1:  # halberd
        b.lathe([(0.021, L - 0.3), (0.024, L - 0.28), (0.02, L)], 'pewter', 8, tint=st)
        axe = [(0.015, -0.2), (0.11, -0.25), (0.16, -0.14), (0.165, -0.03), (0.12, 0.06), (0.015, 0.0)]
        b.prism(axe, 0.01, 'pewter', bevel=0.004, tint=st, M=T(0, L, 0))
        hook = [(-0.015, -0.16), (-0.1, -0.2), (-0.13, -0.26), (-0.06, -0.12), (-0.015, -0.06)]
        b.prism(hook, 0.01, 'pewter', bevel=0.004, tint=st, M=T(0, L, 0))
        spike = [(0, 0), (0.016, 0.03), (0, 0.3), (-0.016, 0.03)]
        b.prism(spike, 0.012, 'pewter', bevel=0.005, tint=st, M=T(0, L, 0))
    else:           # glaive
        b.lathe([(0.021, L - 0.1), (0.024, L - 0.08), (0.02, L)], 'pewter', 8, tint=st)
        bl = [(-0.012, 0), (0.03, 0.02), (0.05, 0.2), (0.035, 0.42), (-0.01, 0.52), (-0.012, 0.3)]
        b.prism(bl, 0.01, 'pewter', bevel=0.004, tint=st, M=T(0, L, 0))


def weapon_rack(b, W=1.5):
    """Wall-local rack of polearms."""
    for sx in (-1, 1):
        b.box((0.07, 1.5, 0.1), 'wood_dark', pos=(sx * W / 2, 0.75, 0.05), bevel=0.008, grain=1)
        b.box((0.07, 0.06, 0.4), 'wood_dark', pos=(sx * W / 2, 0.03, 0.2), bevel=0.008, grain=2)
    b.box((W + 0.1, 0.07, 0.1), 'wood_dark', pos=(0, 1.38, 0.12), bevel=0.008, grain=0)
    b.box((W + 0.1, 0.09, 0.26), 'wood_dark', pos=(0, 0.13, 0.22), bevel=0.01, grain=0)
    n = 5
    for k in range(n):
        x = -W / 2 + 0.17 + k * (W - 0.34) / (n - 1)
        b.box((0.03, 0.05, 0.07), 'wood_dark', pos=(x - 0.035, 1.38, 0.2), bevel=0.005)
        b.box((0.03, 0.05, 0.07), 'wood_dark', pos=(x + 0.035, 1.38, 0.2), bevel=0.005)
        with b.at(T(x, 0.175, 0.3) @ RX(-0.085) @ RY(b.r(-0.5, 0.5))):
            polearm(b, [0, 1, 2, 0, 1][k], b.r(2.15, 2.4))
    b.col((W + 0.1, 1.5, 0.45), pos=(0, 0.75, 0.22))


@clutter
def shield(b, tile=0, s=1.0, boss=True):
    """Wall-local heater shield hanging flat; tile picks the device from the atlas."""
    n = 10
    pts = [(-0.26, 0.3), (0.26, 0.3)]
    for k in range(1, n + 1):
        t = k / n
        pts.append((0.26 * (1 - t ** 1.9), 0.3 - 0.68 * t ** 0.75 if False else 0.3 - 0.2 - 0.48 * t))
    for k in range(n - 1, 0, -1):
        t = k / n
        pts.append((-0.26 * (1 - t ** 1.9), 0.3 - 0.2 - 0.48 * t))
    pts = [(-0.26, 0.3), (0.26, 0.3), (0.26, 0.1)] + [(0.26 * (1 - (k / n) ** 1.9), 0.1 - 0.48 * (k / n)) for k in range(1, n + 1)] + \
          [(-0.26 * (1 - (k / n) ** 1.9), 0.1 - 0.48 * (k / n)) for k in range(n - 1, 0, -1)] + [(-0.26, 0.1)]
    pts = [(x * s, y * s) for x, y in pts][::-1]
    b.prism(pts, 0.03, 'wood_dark', bevel=0.006, M=T(0, 0, 0.03), tint=(0.5, 0.45, 0.4))
    # painted face: fan with atlas UVs
    u0 = (tile % 2) * 0.5; v0 = 0.5 - (tile // 2) * 0.5
    ins = [(x * 0.965, y * 0.965 + 0.003 * s) for x, y in pts]
    verts = [Vector((0, 0.0, 0.0462))] + [Vector((x, y, 0.0458)) for x, y in ins]
    uvf = lambda p: (u0 + (p.x / s / 0.56 + 0.5) * 0.5, v0 + ((p.y / s + 0.08) / 0.82 + 0.5) * 0.5)
    faces = []; uvs = []
    m = len(ins)
    for i in range(m):
        f = (0, 1 + i, 1 + (i + 1) % m)
        faces.append(f); uvs.append([uvf(verts[j]) for j in f])
    b.emit('shield', verts, faces, uvs)
    if boss:
        b.lathe([(0.06 * s, 0), (0.055 * s, 0.012), (0.035 * s, 0.035), (0, 0.045)], 'iron', 10, M=T(0, 0.0, 0.046) @ RX(PI / 2))


@clutter
def sword(b, L=1.05):
    """Along +y, guard near the origin; blade up."""
    st = (0.92, 0.92, 0.95)
    pts = [(-0.026, 0), (0.026, 0), (0.02, L * 0.72), (0, L * 0.8), (-0.02, L * 0.72)]
    b.prism(pts, 0.008, 'pewter', bevel=0.0035, tint=st)
    b.box((0.2, 0.022, 0.022), 'brass', pos=(0, 0, 0), bevel=0.005)
    b.cyl(0.013, 0.14, 'leather', 8, tint=(0.15, 0.08, 0.05), M=T(0, -0.15, 0))
    b.ball(0.024, 'brass', 8, 6, M=T(0, -0.17, 0))


@clutter
def hanging(b, W, H, mat, uv, folds=5, depth=0.03, tail=0.0, n=(14, 14), rod=True):
    """Wall-local cloth hanging from y = 0 downward, centred on x; uv = (u0, v0, u1, v1)."""
    ni, nj = n
    P = []
    for i in range(ni + 1):
        u = i / ni
        col = []
        for j in range(nj + 1):
            v = j / nj
            x = (u - 0.5) * W * (1 - 0.015 * math.sin(v * PI))
            yb = -H * v
            if tail > 0:
                yb -= tail * v * (abs(u - 0.5) * 2)
            z = 0.02 + depth * (0.5 + 0.5 * math.sin(u * TAU * folds * 0.5 + 0.6)) * (0.25 + 0.75 * v) + 0.012 * math.sin(v * 7 + u * 3)
            col.append(Vector((x, yb, z)))
        P.append(col)
    u0, v0, u1, v1 = uv
    b.grid(P, mat, uvfn=lambda i, j: (u0 + (u1 - u0) * i / ni, v1 + (v0 - v1) * j / nj), flip=True)
    if rod:
        b.rod((-W / 2 - 0.1, 0.03, 0.05), (W / 2 + 0.1, 0.03, 0.05), 0.014, 'iron', 8)
        for sx in (-1, 1):
            b.ball(0.028, 'iron', 8, 6, M=T(sx * (W / 2 + 0.1), 0.03, 0.05))
            b.box((0.02, 0.02, 0.07), 'iron', pos=(sx * (W / 2 - 0.05), 0.03, 0.025), bevel=0.004)
        k = max(3, int(W / 0.22))
        for i in range(k + 1):
            x = -W / 2 + 0.03 + (W - 0.06) * i / k
            ring = [(x, 0.03 + 0.024 * math.sin(TAU * t / 8), 0.05 + 0.024 * math.cos(TAU * t / 8)) for t in range(8)]
            b.sweep(ring, circ_prof(0.003, 4), 'brass', closed=True, up=(1, 0, 0))


def clock(b):
    """Longcase clock, wall-local (back on z = 0)."""
    wd = 'wood_red'
    b.box((0.5, 0.5, 0.3), wd, pos=(0, 0.25, 0.15), bevel=0.012, grain=1)
    b.box((0.54, 0.07, 0.33), wd, pos=(0, 0.035, 0.155), bevel=0.014, grain=0)
    b.box((0.36, 1.05, 0.22), wd, pos=(0, 1.02, 0.12), bevel=0.01, grain=1)
    b.box((0.24, 0.8, 0.02), wd, pos=(0, 1.02, 0.235), bevel=0.012, grain=1, tint=(1.1, 1.06, 1.0))
    b.box((0.42, 0.05, 0.26), wd, pos=(0, 0.52, 0.13), bevel=0.014, grain=0)
    b.box((0.44, 0.05, 0.27), wd, pos=(0, 1.56, 0.135), bevel=0.014, grain=0)
    b.box((0.48, 0.5, 0.28), wd, pos=(0, 1.83, 0.14), bevel=0.01, grain=1)
    b.box((0.56, 0.06, 0.33), wd, pos=(0, 2.1, 0.155), bevel=0.02, grain=0)
    hw = 0.2
    pts = [(-hw, 0), (hw, 0)] + [(hw * math.cos(PI * k / 10), 0.1 * math.sin(PI * k / 10)) for k in range(0, 11)]
    b.prism(pts, 0.26, wd, bevel=0.01, M=T(0, 2.13, 0.14), grain=0)
    for sx in (-1, 1):
        b.cyl(0.02, 0.44, wd, 8, M=T(sx * 0.215, 1.61, 0.265))
        b.ball(0.03, 'brass', 8, 6, M=T(sx * 0.22, 2.16, 0.14))
    b.ball(0.034, 'brass', 8, 6, M=T(0, 2.27, 0.14))
    # face
    s = 0.19
    verts = [Vector((-s, 1.83 - s, 0.2815)), Vector((s, 1.83 - s, 0.2815)), Vector((s, 1.83 + s, 0.2815)), Vector((-s, 1.83 + s, 0.2815))]
    b.emit('clockface', verts, [(0, 1, 2, 3)], [[(0, 0), (1, 0), (1, 1), (0, 1)]])
    b.lathe([(s * 1.0, 0), (s * 1.06, 0.004), (s * 1.06, 0.012), (s * 0.99, 0.012)], 'brass', 24, M=T(0, 1.83, 0.281) @ RX(PI / 2) @ SC(1, 1, 1))
    # pendulum window
    b.lathe([(0.055, 0), (0.065, 0.004), (0.065, 0.01), (0.055, 0.01)], 'brass', 16, M=T(0, 1.02, 0.245) @ RX(PI / 2))
    b.cyl(0.055, 0.004, 'brass', 16, M=T(0, 1.02, 0.244) @ RX(PI / 2), tint=(0.5, 0.45, 0.4), bevel=0.001)
    b.col((0.56, 2.2, 0.34), pos=(0, 1.1, 0.16))


def window_seat(b, W=1.95, D=0.52, H=0.46):
    wd = 'wood_panel'
    b.box((W, H - 0.04, D), wd, pos=(0, (H - 0.04) / 2, D / 2), bevel=0.006, grain=0, tint=(0.8, 0.8, 0.8))
    b.box((W + 0.04, 0.04, D + 0.03), wd, pos=(0, H - 0.02, D / 2 + 0.01), bevel=0.012, grain=0)
    n = 3
    pw = W / n
    for k in range(n + 1):
        b.box((0.08, H - 0.05, 0.022), wd, pos=(min(max(-W / 2 + k * pw, -W / 2 + 0.04), W / 2 - 0.04), (H - 0.05) / 2, D + 0.008), bevel=0.005, grain=1,
              tint=b.vary((1, 1, 1), 0.06))
    for yy in (0.05, H - 0.09):
        b.box((W, 0.08, 0.022), wd, pos=(0, yy, D + 0.008), bevel=0.005, grain=0)
    for k in range(n):
        b.box((pw - 0.16, H - 0.25, 0.018), wd, pos=(-W / 2 + (k + 0.5) * pw, H / 2 - 0.02, D + 0.004), bevel=0.01, grain=1, tint=b.vary((1.06, 1.04, 1.0), 0.06))
    cols = [(0.34, 0.09, 0.08), (0.13, 0.18, 0.29), (0.48, 0.36, 0.15), (0.15, 0.25, 0.16)]
    seat = b.rng.choice(cols[:2])
    cw = (W - 0.06) / 3
    for k in range(3):
        b.cushion(cw - 0.01, 0.15, D - 0.03, 'velvet', tint=b.vary(seat, 0.06), M=T(-W / 2 + 0.03 + (k + 0.5) * cw, H + 0.06, D / 2 + 0.005), n=8, puff=1.0)
    for sx in (-1, 1):
        b.cushion(0.44, 0.2, 0.44, 'velvet', tint=b.vary(b.rng.choice(cols[2:]), 0.1),
                  M=T(sx * (W / 2 - 0.32), H + 0.33, 0.17) @ RY(sx * 0.3) @ RX(PI / 2 - 0.32) @ RY(b.r(-0.25, 0.25)), n=8, puff=1.1)
    b.col((W, H + 0.1, D + 0.03), pos=(0, (H + 0.1) / 2, D / 2))


def sack(b, s=1.0):
    prof = [(0, 0), (0.24, 0.0), (0.31, 0.06), (0.33, 0.2), (0.3, 0.36), (0.2, 0.48), (0.08, 0.53), (0.06, 0.55), (0.13, 0.63), (0.1, 0.64), (0.0, 0.57)]
    b.lathe([(r * s, y * s) for r, y in prof], 'hessian', 12, tint=b.vary((0.7, 0.6, 0.45), 0.1), squash=0.8)
    b.lathe([(0.062 * s, 0.535 * s), (0.074 * s, 0.55 * s), (0.062 * s, 0.565 * s)], 'rope', 8)


def bucket(b):
    n = 14; m = 4; h = 0.34
    for k in range(n):
        tn = b.vary((1, 1, 1), 0.13, 0.03)
        P = []
        for i in (0, 1):
            a = (k + i) * TAU / n - (0.004 if i else -0.004)
            P.append([Vector(((0.15 + 0.035 * j / m) * math.cos(a), j / m * h, (0.15 + 0.035 * j / m) * math.sin(a))) for j in range(m + 1)])
        b.grid(P, 'wood_oak', tint=tn, uvfn=lambda i, j, k=k: (k * 0.13 + i * 0.08, j / m * h), flip=True)
        P2 = [[Vector((p.x * 0.9, p.y, p.z * 0.9)) for p in col] for col in P]
        b.grid(P2, 'wood_oak', tint=(tn[0] * 0.8, tn[1] * 0.8, tn[2] * 0.8), uvfn=lambda i, j, k=k: (k * 0.13 + i * 0.08, j / m * h), flip=False)
    b.lathe([(0.1665, h), (0.185, h)][::-1], 'wood_oak', n, tint=(0.8, 0.8, 0.8))
    b.lathe([(0.14, 0.03), (0, 0.03)], 'wood_oak', n, tint=(0.7, 0.7, 0.7))
    for y in (0.06, 0.27):
        rr = 0.15 + 0.035 * y / h + 0.003
        b.lathe([(rr - 0.003, y - 0.016), (rr + 0.004, y - 0.016), (rr + 0.004, y + 0.016), (rr - 0.003, y + 0.016)], 'iron', n)
    path = [(0.18 * math.cos(t), h - 0.02 + 0.2 * math.sin(t), 0.0) for t in [PI * i / 10 for i in range(11)]]
    b.sweep(path, circ_prof(0.007, 5), 'rope', up=(0, 0, 1))
    b.col((0.4, h, 0.4), pos=(0, h / 2, 0), kind='cyl')


def crate(b, s=0.6):
    wd = 'wood_beam'
    tn = lambda: b.vary((1.25, 1.1, 0.95), 0.1)
    b.box((s - 0.03, s - 0.03, s - 0.03), wd, pos=(0, s / 2, 0), bevel=0.004, tint=(0.6, 0.55, 0.5))
    for ax in range(3):
        for s1 in (-1, 1):
            for s2 in (-1, 1):
                size = [0.07, 0.07, 0.07]; size[ax] = s
                pos = [0, s / 2, 0]
                o = [i for i in range(3) if i != ax]
                pos[o[0]] += s1 * (s / 2 - 0.035); pos[o[1]] += s2 * (s / 2 - 0.035)
                b.box(tuple(size), wd, pos=tuple(pos), bevel=0.006, grain=ax, tint=tn())
    b.col((s, s, s), pos=(0, s / 2, 0))


# ---------------------------------------------------------------------------
# placement
# ---------------------------------------------------------------------------
def build_props(b):
    b.group = 'props'
    rug(b, 0.0, -0.6)
    hearth_rug(b, 0.0, -8.3)

    with b.grp('ns_lightfix'):
        for z in (-8.0, 0.0, 8.0):
            chandelier(b, 0.0, z)
        # sconces on the principal posts
        for name in ('R', 'L'):
            sgn = 1 if name == 'R' else -1
            with b.at(WALLS[name]):
                for i, zt in enumerate(TRUSS_Z):
                    if abs(zt) == 6.0:
                        continue
                    with b.at(T(sgn * zt, 2.25, 0.245)):
                        sconce(b, light=True)
        with b.at(WALLS['D']):
            for sx in (-1, 1):
                with b.at(T(sx * 1.55, 2.0, 0.07)):
                    sconce(b, light=True)
        for (x, z) in ((-3.7, -10.15), (3.7, -10.15), (-2.2, 11.2), (2.2, 11.2)):
            with b.at(T(x, 0, z)):
                candle_stand(b)

    with b.grp('props'):
        # --- long table on the west side --------------------------------------
        with b.at(T(-5.3, 0, 2.0) @ RY(PI / 2)):
            trestle_table(b)
            table_setting(b)
            with b.at(T(0, 0, 0.78)):
                bench(b)
            with b.at(T(0, 0, -0.78)):
                bench(b)
        # --- fireside ---------------------------------------------------------
        with b.at(T(-2.75, 0, -8.35) @ RY(PI - 0.62)):
            chair(b)
        with b.at(T(2.75, 0, -8.35) @ RY(PI + 0.62)):
            chair(b, cushion=(0.13, 0.18, 0.29))
        with b.at(T(3.7, 0, -8.9)):
            side_table(b)
        with b.at(T(-2.25, 0, -9.3) @ RY(0.5)):
            footstool(b)
        with b.at(T(2.98, 0, -9.7) @ RY(0.4)):
            log_basket(b)
        # fire tools leaning by the jamb
        with b.at(WALLS['F'] @ T(-FIRE_W / 2 + 0.55, 0, FP.D1 + 0.02)):
            for k, x in enumerate((-0.12, 0.0, 0.12)):
                with b.at(T(x, FP.HEARTH_H, 0.13) @ RX(-0.12)):
                    b.cyl(0.009, 0.85, 'iron', 6)
                    b.lathe([(0.009, 0.8), (0.02, 0.82), (0.012, 0.87), (0, 0.89)], 'iron', 8)
                    if k == 0:
                        b.box((0.11, 0.14, 0.012), 'iron', pos=(0, 0.02, 0.0), bevel=0.003)
                    elif k == 1:
                        b.box((0.02, 0.02, 0.09), 'iron', pos=(0, 0.01, 0.04), bevel=0.004)
        with b.at(WALLS['F']):
            with b.at(T(-4.75, 0, 0.06)):
                firewood_rack(b)
            with b.at(T(4.35, 0, 0.07)):
                clock(b)
            # banners either side of the breast
            for i, sx in enumerate((-1, 1)):
                with b.at(T(sx * 4.75, 4.4, 0.1)):
                    t = (0, 3)[i]
                    hanging(b, 0.95, 1.75, 'banner', ((t % 2) * 0.5, 0.5 - (t // 2) * 0.5, (t % 2) * 0.5 + 0.5, 1.0 - (t // 2) * 0.5),
                            folds=4, depth=0.035, tail=0.22, n=(10, 12))
            # shield and crossed swords on the upper breast
            with b.at(T(0, 3.55, FP.D2 + 0.012)):
                for s2 in (-1, 1):
                    with b.at(T(0, -0.05, 0.012) @ RZ(s2 * 0.8) @ T(0, -0.62, 0)):
                        sword(b, 1.9)
                with b.at(T(0, 0, 0.03)):
                    shield(b, 0, 1.45)
            # mantel shelf dressing
            ym = FP.H1 + 0.09
            with b.at(T(0, ym, FP.D2 + 0.33)):
                for sx in (-1, 1):
                    with b.at(T(sx * 2.25, 0, 0.3)):
                        candlestick(b, 0.3, 'brass', True, 0.2)
                    with b.at(T(sx * 1.2, 0, 0.0)):
                        candlestick(b, 0.2, 'pewter', True, 0.15)
                with b.at(T(-1.75, 0, 0.1) @ RY(0.5)):
                    tankard(b)
                with b.at(T(-0.55, 0, 0.0)):
                    jug(b, 0.85, (0.2, 0.28, 0.32))
                yy = 0.0
                for k in range(3):
                    w = b.r(0.035, 0.05)
                    with b.at(T(0.5, yy, 0.05) @ RY(PI + b.r(-0.15, 0.15))):
                        book(b, w, 0.26, 0.18, b.vary(BOOK_COLS[k * 3], 0.15), True)
                    yy += w
                with b.at(T(1.72, 0, 0.1)):
                    bowl(b, 0.12, 'pewter')
                b.mark('light', (0, 0.55, 0.4), name='Mantel', color=WARM, energy=0.7, range=4.0, shadow=False, size=0.05, fog=0.1)
        # --- book nooks either side of the fire --------------------------------
        with b.at(WALLS['L'] @ T(8.0, 0, 0.05)):
            bookshelf(b)
        with b.at(WALLS['R'] @ T(-8.0, 0, 0.05)):
            bookshelf(b)
        # --- east wall: window seats, chest, weapon rack, sideboard -------------
        with b.at(WALLS['R']):
            for u in (-4.0, 0.0, 4.0):
                with b.at(T(u, 0, 0.055)):
                    window_seat(b)
            with b.at(T(8.0, 0, 0.06)):
                sideboard(b)
            with b.at(T(-2.0, 0, 0.75) ):
                pass
            for i, zt in enumerate((-6.0, 6.0)):
                with b.at(T(zt, 2.62, 0.245)):
                    shield(b, (i + 1) % 4, 1.25)
            with b.at(T(10.9, 0, 0.06)):
                weapon_rack(b, 1.3)
        # --- west wall -----------------------------------------------------------
        with b.at(WALLS['L']):
            for i, zt in enumerate((-6.0, 6.0)):
                with b.at(T(-zt, 2.62, 0.245)):
                    shield(b, (0, 3)[i], 1.25)
            with b.at(T(4.0, 0, 0.055)):
                window_seat(b)
            # sill dressing on the windows above the table
            for u, kind in ((0.0, 0), (-4.0, 1), (-8.0, 2), (4.0, 3)):
                with b.at(T(u, WSILL + 0.055, -0.16)):
                    if kind != 3:
                        with b.at(T(-0.45, 0, 0)):
                            candlestick(b, 0.14, 'pewter', True, 0.14)
                    if kind == 0:
                        with b.at(T(0.3, 0, 0.0)):
                            jug(b, 0.7, (0.5, 0.42, 0.3))
                    elif kind == 1:
                        with b.at(T(0.35, 0, 0) @ RY(0.3)):
                            book(b, 0.05, 0.24, 0.17, BOOK_COLS[1], True)
                    elif kind == 2:
                        with b.at(T(0.3, 0, 0)):
                            bowl(b, 0.11, 'pewter')
        with b.at(T(-5.7, 0, 8.0) @ RY(PI / 2 + 0.05)):
            chest(b, 1.2)
        # --- door end ------------------------------------------------------------
        with b.at(T(-5.75, 0, 11.2)):
            barrel(b)
        with b.at(T(-5.0, 0, 11.35)):
            barrel(b, 0.9, 0.26, 0.32, tap=False)
        with b.at(T(-5.6, 0, 10.45)):
            barrel(b, 0.8, 0.24, 0.3)
        with b.at(T(-4.3, 0, 11.4)):
            barrel(b, 0.62, 0.2, 0.25)
        with b.at(T(-4.75, 0, 10.7)):
            bucket(b)
        with b.at(T(-3.5, 0, 11.45) @ RY(0.1)):
            crate(b, 0.62)
        with b.at(T(-3.45, 0.62, 11.47) @ RY(0.5)):
            crate(b, 0.42)
        with b.at(T(5.45, 0, 9.75) @ RY(-PI / 2 - 0.08)):
            chest(b, 1.0, 0.5, 0.4, (0.9, 0.95, 1.0))
        with b.at(WALLS['D']):
            for i, sx in enumerate((-1, 1)):
                with b.at(T(sx * 3.95, 4.15, 0.07)):
                    hanging(b, 2.3, 2.7, 'tapestry', (0.5 * i, 0.0, 0.5 * i + 0.5, 1.0), folds=6, depth=0.03, n=(16, 14))
            # bench below the east tapestry
            with b.at(T(-3.95, 0, 0.3)):
                bench(b, 2.0, 0.34)
            # banners high on the gable
            for i, sx in enumerate((-1, 1)):
                with b.at(T(sx * 1.9, 7.3, 0.14)):
                    t = (1, 2)[i]
                    hanging(b, 0.95, 1.8, 'banner', ((t % 2) * 0.5, 0.5 - (t // 2) * 0.5, (t % 2) * 0.5 + 0.5, 1.0 - (t // 2) * 0.5),
                            folds=4, depth=0.035, tail=0.22, n=(10, 12))
