"""Original, procedurally drawn textiles and painted devices for the hall (rug, banners,
tapestries, shields, clock face). Run:  blender --background --python tools/hall_tex.py
Images are written to assets/textures/hall_gen/*.png. Row 0 of every array is the BOTTOM
of the image (Blender convention), so v runs upward like the mesh UVs."""
import bpy, os, math
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'textures', 'hall_gen')
os.makedirs(OUT, exist_ok=True)
rs = np.random.RandomState(4)

RED = (0.40, 0.065, 0.055); DRED = (0.22, 0.035, 0.035); NAVY = (0.055, 0.08, 0.19); GOLD = (0.66, 0.47, 0.17)
CREAM = (0.74, 0.67, 0.52); TEAL = (0.08, 0.26, 0.27); GREEN = (0.09, 0.2, 0.1); BLACK = (0.035, 0.03, 0.03)
BROWN = (0.25, 0.14, 0.07); SKY = (0.2, 0.3, 0.42); WHITE = (0.8, 0.78, 0.72)


def save(name, img):
    h, w, _ = img.shape
    out = np.ones((h, w, 4), np.float32)
    out[..., :3] = np.clip(img, 0, 1)
    im = bpy.data.images.new(name, w, h, alpha=False)
    im.colorspace_settings.name = 'sRGB'
    im.pixels.foreach_set(out.ravel())
    im.filepath_raw = os.path.join(OUT, name + '.png')
    im.file_format = 'PNG'
    im.save()
    print('wrote', name, w, h)


def ss(a, b, x):
    t = np.clip((x - a) / (b - a + 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


def paint(img, mask, col):
    m = np.clip(mask, 0, 1)[..., None]
    img *= (1 - m)
    img += m * np.array(col, np.float32)


def fill(sd, px):
    """Coverage of the region sd < 0 with ~1px antialiasing."""
    return 1 - ss(-px, px, sd)


def band(sd, lo, hi, px):
    return fill(sd - hi, px) * (1 - fill(sd - lo, px))


def vnoise(h, w, cells, seed=0):
    r = np.random.RandomState(seed)
    g = r.rand(cells[0] + 2, cells[1] + 2).astype(np.float32)
    ys = np.linspace(0, cells[0], h, endpoint=False); xs = np.linspace(0, cells[1], w, endpoint=False)
    y0 = ys.astype(int); x0 = xs.astype(int)
    fy = (ys - y0)[:, None]; fx = (xs - x0)[None, :]
    fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
    a = g[y0][:, x0]; b = g[y0][:, x0 + 1]; c = g[y0 + 1][:, x0]; d = g[y0 + 1][:, x0 + 1]
    return a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy


def fbm(h, w, base, octaves=4, seed=0):
    out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        out += amp * vnoise(h, w, (base[0] * 2 ** o, base[1] * 2 ** o), seed + o * 13)
        tot += amp; amp *= 0.5
    return out / tot


def weave(img, strength=0.07, seed=0, wear=0.12):
    """Thread-level variation + soft uneven fading so nothing reads as a flat print."""
    h, w, _ = img.shape
    r = np.random.RandomState(seed)
    warp = r.rand(1, w).astype(np.float32); weft = r.rand(h, 1).astype(np.float32)
    grain = (warp * 0.5 + weft * 0.5 - 0.5) * 2
    speck = r.rand(h, w).astype(np.float32) - 0.5
    img *= (1 + strength * grain + strength * 0.8 * speck)[..., None]
    fade = fbm(h, w, (4, 3), 4, seed + 5)
    img *= (1 - wear + 2 * wear * fade)[..., None]
    # sun-bleach toward warm grey
    grey = img.mean(axis=2, keepdims=True)
    k = (0.18 * fbm(h, w, (3, 2), 3, seed + 9))[..., None]
    img[:] = img * (1 - k) + (grey * np.array([1.08, 1.0, 0.9], np.float32)) * k


def grid(w, h, sx, sy):
    """Coordinate arrays in metres centred on the image; y up."""
    xs = (np.arange(w, dtype=np.float32) + 0.5) / w * sx - sx / 2
    ys = (np.arange(h, dtype=np.float32) + 0.5) / h * sy - sy / 2
    return np.meshgrid(xs, ys)


def sd_box(x, y, hx, hy):
    dx = np.abs(x) - hx; dy = np.abs(y) - hy
    return np.minimum(np.maximum(dx, dy), 0) + np.hypot(np.maximum(dx, 0), np.maximum(dy, 0))


def sd_star(x, y, r, n=5, inner=0.45):
    a = np.arctan2(x, y); d = np.hypot(x, y)
    seg = TAU / n
    a = np.abs((a + seg / 2) % seg - seg / 2)
    # edge from outer tip (angle 0, radius r) to inner notch (angle seg/2, radius r*inner)
    p0 = np.array([0.0, r]); p1 = np.array([math.sin(seg / 2) * r * inner, math.cos(seg / 2) * r * inner])
    px = np.sin(a) * d; py = np.cos(a) * d
    ex, ey = p1 - p0
    nx, ny = ey, -ex
    ln = math.hypot(nx, ny)
    return -((px - p0[0]) * nx + (py - p0[1]) * ny) / ln


TAU = 2 * math.pi


def sd_gear(x, y, r, teeth=10, depth=0.16):
    a = np.arctan2(y, x); d = np.hypot(x, y)
    t = np.cos(a * teeth)
    prof = r * (1 - depth * 0.5 + depth * 0.5 * np.clip(t * 3.0, -1, 1))
    return d - prof


def sd_sword(x, y, L):
    """Upright sword centred at origin, total length L."""
    blade = sd_box(x, y - L * 0.12, L * 0.035, L * 0.36)
    tip = (np.abs(x) * 2.2 + (y - L * 0.48)) / 2.4 - L * 0.016
    blade = np.where(y > L * 0.44, np.maximum(tip, -(y - L * 0.40)), blade)
    guard = sd_box(x, y + L * 0.25, L * 0.14, L * 0.018)
    grip = sd_box(x, y + L * 0.34, L * 0.02, L * 0.08)
    pom = np.hypot(x, y + L * 0.44) - L * 0.035
    return np.minimum(np.minimum(blade, guard), np.minimum(grip, pom))


# ---------------------------------------------------------------------------
def rug():
    W, L = 5.2, 9.6
    w, h = 1024, 1888
    X, Y = grid(w, h, W, L)
    px = W / w
    ax, ay = np.abs(X), np.abs(Y)
    img = np.zeros((h, w, 3), np.float32) + np.array(RED, np.float32)
    de = np.minimum(W / 2 - ax, L / 2 - ay)         # distance in from the edge
    # ---- field lattice ----
    p = 0.46
    u = (X + Y) / p; v = (X - Y) / p
    fu = np.abs((u % 1) - 0.5); fv = np.abs((v % 1) - 0.5)
    paint(img, 1 - ss(0.018, 0.04, np.minimum(fu, fv)), DRED)
    # flowers on the nodes
    cu = (u + 0.5) % 1 - 0.5; cv = (v + 0.5) % 1 - 0.5
    lx = (cu + cv) * p / 2; ly = (cu - cv) * p / 2
    ang = np.arctan2(ly, lx); rad = np.hypot(lx, ly)
    paint(img, fill(rad - 0.062 * (0.72 + 0.28 * np.cos(ang * 4)), px), NAVY)
    paint(img, fill(rad - 0.02, px), GOLD)
    # leaf sprigs in the cell centres
    cu2 = u % 1 - 0.5; cv2 = v % 1 - 0.5
    lx2 = (cu2 + cv2) * p / 2; ly2 = (cu2 - cv2) * p / 2
    paint(img, fill(np.abs(lx2) + np.abs(ly2) * 2.2 - 0.04, px), TEAL)
    paint(img, fill(np.abs(lx2) * 2.2 + np.abs(ly2) - 0.04, px), TEAL)
    paint(img, fill(np.hypot(lx2, ly2) - 0.014, px), CREAM)
    # ---- corner spandrels ----
    fx, fy = W / 2 - 0.62, L / 2 - 0.62
    cx, cy = ax - fx, ay - fy
    ca = np.arctan2(cy, cx); cr = np.hypot(cx, cy)
    sp = cr - 1.25 * (1 + 0.05 * np.cos(ca * 12))
    paint(img, fill(sp, px), NAVY)
    paint(img, band(sp, -0.07, -0.035, px), GOLD)
    paint(img, band(sp, -0.5, -0.46, px), GOLD)
    paint(img, fill(cr - 0.72 * (1 + 0.1 * np.cos(ca * 12)), px), RED)
    paint(img, fill(cr - 0.4 * (1 + 0.12 * np.cos(ca * 12 + math.pi)), px), CREAM)
    paint(img, fill(cr - 0.2, px), TEAL)
    # ---- central medallion ----
    a = np.arctan2(Y, X); r = np.hypot(X / 1.0, Y / 1.45)
    md = r - 1.28 * (1 + 0.045 * np.cos(a * 16) + 0.03 * np.cos(a * 4))
    paint(img, fill(md, px), NAVY)
    paint(img, band(md, -0.08, -0.04, px), GOLD)
    paint(img, band(md, -0.36, -0.32, px), CREAM)
    paint(img, fill(r - 0.8 * (1 + 0.07 * np.cos(a * 8)), px), RED)
    paint(img, band(r - 0.8 * (1 + 0.07 * np.cos(a * 8)), -0.05, -0.02, px), GOLD)
    paint(img, fill(r - 0.52 * (0.75 + 0.25 * np.cos(a * 8)), px), CREAM)
    paint(img, fill(r - 0.34 * (0.7 + 0.3 * np.cos(a * 8 + math.pi)), px), TEAL)
    paint(img, fill(r - 0.15, px), GOLD)
    paint(img, fill(r - 0.07, px), DRED)
    # little blossoms riding the medallion band
    ra = (a * 16 / TAU) % 1 - 0.5
    paint(img, fill(np.hypot(ra * 0.5, (r - 1.06)) - 0.05, px) * fill(md + 0.1, px), GOLD)
    # pendants on the long axis
    for s in (-1, 1):
        py = Y - s * 2.55
        pd = np.abs(X) * 1.25 + np.abs(py) * 0.8 - 0.42
        paint(img, fill(pd, px), NAVY)
        paint(img, band(pd, -0.07, -0.035, px), GOLD)
        paint(img, fill(np.abs(X) * 1.25 + np.abs(py) * 0.8 - 0.2, px), CREAM)
        paint(img, fill(np.hypot(X, py) - 0.07, px), RED)
    # ---- borders ----
    paint(img, fill(de - 0.56, px), DRED)
    paint(img, fill(de - 0.53, px), CREAM)
    paint(img, fill(de - 0.495, px), GOLD)
    paint(img, fill(de - 0.47, px), NAVY)
    # main border motif: travel coordinate s along the border, t across it
    on_side = (W / 2 - ax) < (L / 2 - ay)
    s = np.where(on_side, Y, X)
    t = de - 0.29
    q = 0.42
    sl = (s + q / 2) % q - q / 2
    dia = np.abs(sl) * 1.0 + np.abs(t) * 1.25 - 0.15
    inb = fill(de - 0.47, px) * (1 - fill(de - 0.11, px))
    paint(img, fill(dia, px) * inb, RED)
    paint(img, band(dia, -0.035, -0.012, px) * inb, GOLD)
    paint(img, fill(np.hypot(sl, t) - 0.045 * (0.7 + 0.3 * np.cos(np.arctan2(t, sl) * 6)), px) * inb, CREAM)
    sl2 = s % q - q / 2
    paint(img, fill(np.hypot(sl2, t) - 0.035, px) * inb, TEAL)
    paint(img, fill(np.hypot(sl2, np.abs(t) - 0.1) - 0.018, px) * inb, GOLD)
    vine = np.abs(t - 0.115 * np.sin(s / q * TAU)) - 0.008
    paint(img, fill(vine, px) * inb * (1 - fill(dia - 0.02, px)), CREAM)
    paint(img, fill(de - 0.11, px), GOLD)
    paint(img, fill(de - 0.085, px), CREAM)
    paint(img, fill(de - 0.06, px), DRED)
    # reciprocal 'running dog' on the outer guard
    tri = np.abs(((s / 0.09) % 1) - 0.5) * 0.06
    paint(img, fill((de - 0.02) - tri, px) * fill(de - 0.06, px), NAVY)
    weave(img, 0.09, 3, 0.13)
    # trodden path down the middle and brighter pile near the edges
    wear = 0.1 * np.exp(-(X / 1.3) ** 2) * (0.6 + 0.8 * fbm(h, w, (6, 3), 3, 21))
    img *= (1 - wear)[..., None]
    save('rug', img)


def _banner_base(w, h, col, border, sx, sy, px):
    X, Y = grid(w, h, sx, sy)
    img = np.zeros((h, w, 3), np.float32) + np.array(col, np.float32)
    de = np.minimum(sx / 2 - np.abs(X), sy / 2 - np.abs(Y))
    paint(img, fill(de - 0.05, px), border)
    paint(img, band(de, 0.065, 0.078, px), border)
    return img, X, Y


def banners():
    """2 x 2 atlas of heraldic banners, each 0.9 m x 1.8 m."""
    w, h = 512, 1024
    sx, sy = 0.9, 1.8
    px = sx / w
    tiles = []
    # 1: crimson, gold cog and sword
    img, X, Y = _banner_base(w, h, RED, GOLD, sx, sy, px)
    g = sd_gear(X, Y - 0.15, 0.27, 12, 0.2)
    paint(img, fill(g, px), GOLD)
    paint(img, fill(np.hypot(X, Y - 0.15) - 0.17, px), RED)
    for k in range(6):
        a = k * TAU / 6
        paint(img, fill(sd_box(X * math.cos(a) + (Y - 0.15) * math.sin(a), -X * math.sin(a) + (Y - 0.15) * math.cos(a), 0.2, 0.014), px) *
              fill(np.hypot(X, Y - 0.15) - 0.19, px), GOLD)
    paint(img, fill(sd_sword(X, -(Y - 0.02), 1.0), px), CREAM)
    paint(img, fill(np.hypot(X, Y - 0.15) - 0.045, px), GOLD)
    tiles.append(img)
    # 2: navy, gold chevron, three stars
    img, X, Y = _banner_base(w, h, NAVY, CREAM, sx, sy, px)
    chev = np.abs((Y + 0.0) + np.abs(X) * 0.9 - 0.2) - 0.07
    paint(img, fill(chev, px), GOLD)
    for (cx, cy) in ((-0.2, 0.5), (0.2, 0.5), (0, -0.42)):
        paint(img, fill(sd_star(X - cx, Y - cy, 0.12), px), GOLD)
    tiles.append(img)
    # 3: green, cream tower and key-stripe
    img, X, Y = _banner_base(w, h, GREEN, GOLD, sx, sy, px)
    tw = sd_box(X, Y + 0.05, 0.16, 0.3)
    paint(img, fill(tw, px), CREAM)
    for k in (-1, 0, 1):
        paint(img, fill(sd_box(X - k * 0.13, Y - 0.3, 0.045, 0.06), px), CREAM)
    door = np.maximum(sd_box(X, Y + 0.25, 0.06, 0.1), -1e9)
    paint(img, fill(np.minimum(door, np.hypot(X, Y + 0.15) - 0.06), px), GREEN)
    paint(img, fill(sd_box(X, Y - 0.08, 0.02, 0.05), px), GREEN)
    for s in (-1, 1):
        paint(img, fill(sd_star(X - s * 0.27, Y - 0.6, 0.07), px), GOLD)
    paint(img, fill(np.abs(Y + 0.6) - 0.035, px) * fill(np.abs(X) - 0.36, px), GOLD)
    tiles.append(img)
    # 4: gold and black per pale, counter-changed cog
    img, X, Y = _banner_base(w, h, GOLD, BLACK, sx, sy, px)
    paint(img, fill(X, px) * fill(np.maximum(np.abs(X) - 0.37, np.abs(Y) - 0.82), px), BLACK)
    g = sd_gear(X, Y - 0.05, 0.3, 10, 0.22)
    ring = np.maximum(g, -(np.hypot(X, Y - 0.05) - 0.17))
    paint(img, fill(ring, px) * fill(X, px), GOLD)
    paint(img, fill(ring, px) * (1 - fill(X, px)), BLACK)
    for s in (-1, 1):
        paint(img, fill(np.abs(Y - s * 0.62) - 0.03, px) * fill(np.abs(X) - 0.36, px) * fill(X, px), GOLD)
        paint(img, fill(np.abs(Y - s * 0.62) - 0.03, px) * fill(np.abs(X) - 0.36, px) * (1 - fill(X, px)), BLACK)
    tiles.append(img)
    for i, t in enumerate(tiles):
        weave(t, 0.1, 30 + i, 0.14)
    top = np.concatenate([tiles[0], tiles[1]], axis=1)
    bot = np.concatenate([tiles[2], tiles[3]], axis=1)
    save('banners', np.concatenate([bot, top], axis=0))      # row 0 = bottom


def tapestry():
    """Two woven hangings side by side (each 2.4 m x 2.8 m): the Tree, and the Keep."""
    w, h = 880, 1024
    sx, sy = 2.4, 2.8
    px = sx / w
    out = []
    for which in (0, 1):
        X, Y = grid(w, h, sx, sy)
        ground = (0.07, 0.13, 0.14) if which == 0 else (0.1, 0.1, 0.2)
        img = np.zeros((h, w, 3), np.float32) + np.array(ground, np.float32)
        de = np.minimum(sx / 2 - np.abs(X), sy / 2 - np.abs(Y))
        r = np.random.RandomState(40 + which)
        # millefleur scatter
        for k in range(260):
            cx = r.uniform(-sx / 2, sx / 2); cy = r.uniform(-sy / 2, sy / 2)
            d = np.hypot(X - cx, Y - cy)
            a = np.arctan2(Y - cy, X - cx)
            col = [CREAM, GOLD, (0.5, 0.12, 0.1), (0.35, 0.4, 0.55), (0.6, 0.5, 0.3)][k % 5]
            rr = r.uniform(0.018, 0.034)
            paint(img, fill(d - rr * (0.65 + 0.35 * np.cos(a * 5 + k)), px), col)
            paint(img, fill(d - rr * 0.3, px), GOLD if k % 5 else DRED)
            paint(img, fill(sd_box(X - cx, Y - cy + rr * 2.2, 0.004, rr * 1.4), px), (0.16, 0.3, 0.14))
        if which == 0:
            # hillock
            hill = np.hypot(X, (Y + 2.6) / 1.0) - 1.75
            paint(img, fill(hill, px), (0.13, 0.25, 0.11))
            paint(img, band(hill, -0.05, -0.02, px), (0.3, 0.4, 0.16))
            # trunk + boughs
            trunk = sd_box(X + 0.05 * np.sin(Y * 3), Y + 0.35, 0.09 - 0.03 * (Y + 0.35), 0.6)
            paint(img, fill(trunk, px), BROWN)
            for s in (-1, 1):
                for (bx, by, ln, an) in ((0.0, 0.15, 0.55, 0.75), (0.0, -0.1, 0.45, 1.05)):
                    ca, sa = math.cos(an), math.sin(an)
                    lx = (X * s - bx) * sa + (Y - by) * ca; ly = -(X * s - bx) * ca + (Y - by) * sa
                    paint(img, fill(sd_box(lx - ln / 2, ly, ln / 2, 0.035), px), BROWN)
            # canopy: overlapping leaf clusters, two greens, golden fruit
            cl = []
            for k in range(46):
                a = r.uniform(0, TAU); rad = r.uniform(0, 1) ** 0.6 * 0.82
                cl.append((math.cos(a) * rad * 1.05, 0.62 + math.sin(a) * rad * 0.78, r.uniform(0.16, 0.26)))
            for (cx, cy, cr) in cl:
                d = np.hypot(X - cx, Y - cy) - cr
                paint(img, fill(d, px), (0.1, 0.24, 0.11))
            for (cx, cy, cr) in cl:
                d = np.hypot(X - cx - 0.02, Y - cy - 0.03) - cr * 0.72
                paint(img, fill(d, px), (0.17, 0.36, 0.14))
                d = np.hypot(X - cx - 0.04, Y - cy - 0.06) - cr * 0.36
                paint(img, fill(d, px), (0.3, 0.46, 0.17))
            for k in range(26):
                a = r.uniform(0, TAU); rad = r.uniform(0, 1) ** 0.6 * 0.8
                cx, cy = math.cos(a) * rad, 0.62 + math.sin(a) * rad * 0.75
                paint(img, fill(np.hypot(X - cx, Y - cy) - 0.035, px), GOLD)
                paint(img, fill(np.hypot(X - cx + 0.01, Y - cy - 0.01) - 0.014, px), CREAM)
            # two birds as simple chevrons
            for (cx, cy) in ((-0.75, 1.0), (0.82, 0.86)):
                paint(img, fill(np.abs((Y - cy) - np.abs(X - cx) * 0.6) - 0.012, px) * fill(np.abs(X - cx) - 0.09, px), CREAM)
        else:
            # night sky, moon and stars
            paint(img, fill(-(Y + 0.2), px), (0.09, 0.11, 0.26))
            for k in range(30):
                cx = r.uniform(-1.0, 1.0); cy = r.uniform(0.0, 1.2)
                paint(img, fill(sd_star(X - cx, Y - cy, r.uniform(0.02, 0.04), 4, 0.35), px), CREAM)
            moon = np.maximum(np.hypot(X - 0.65, Y - 0.85) - 0.17, -(np.hypot(X - 0.72, Y - 0.9) - 0.15))
            paint(img, fill(moon, px), (0.8, 0.74, 0.5))
            # hill
            hill = np.hypot(X / 1.5, Y + 2.25) - 1.6
            paint(img, fill(hill, px), (0.1, 0.2, 0.12))
            # keep with two towers
            wall = (0.56, 0.5, 0.4); shade = (0.36, 0.31, 0.25)
            paint(img, fill(sd_box(X, Y + 0.25, 0.42, 0.33), px), wall)
            for k in range(-3, 4):
                paint(img, fill(sd_box(X - k * 0.13, Y - 0.11, 0.04, 0.05), px), wall)
            for s in (-1, 1):
                paint(img, fill(sd_box(X - s * 0.55, Y + 0.05, 0.15, 0.55), px), wall)
                paint(img, fill(sd_box(X - s * 0.55 - 0.09, Y + 0.05, 0.06, 0.55), px), shade)
                for k in (-1, 0, 1):
                    paint(img, fill(sd_box(X - s * 0.55 - k * 0.1, Y - 0.64, 0.032, 0.05), px), wall)
                roof = np.maximum(np.abs(X - s * 0.55) * 1.9 + (Y - 0.6) - 0.36, -(Y - 0.6))
                paint(img, fill(sd_box(X - s * 0.55, Y - 0.2, 0.025, 0.07), px), BLACK)
            gate = np.minimum(sd_box(X, Y + 0.44, 0.11, 0.14), np.hypot(X, Y + 0.3) - 0.11)
            paint(img, fill(gate, px), BLACK)
            paint(img, band(gate, 0.0, 0.025, px), shade)
            # pennants
            for s in (-1, 1):
                paint(img, fill(sd_box(X - s * 0.55, Y - 0.82, 0.008, 0.14), px), CREAM)
                fl = np.maximum(np.abs(Y - 0.9) * 1.6 + (X - s * 0.55) * s - 0.16, -(X - s * 0.55) * s)
                paint(img, fill(fl, px), RED)
            # winding road
            road = np.abs(X - 0.25 * np.sin((Y + 0.6) * 5.0) * np.clip(-(Y + 0.6), 0, 1)) - (0.05 + 0.1 * np.clip(-(Y + 0.6), 0, 1))
            paint(img, fill(road, px) * fill(Y + 0.58, px) * fill(hill, px), (0.5, 0.43, 0.3))
        # border: gold-on-red running leaf with corner rosettes
        paint(img, fill(de - 0.24, px), DRED)
        paint(img, band(de, 0.205, 0.225, px), GOLD)
        on_side = (sx / 2 - np.abs(X)) < (sy / 2 - np.abs(Y))
        s = np.where(on_side, Y, X); t = de - 0.115
        q = 0.3
        sl = (s + q / 2) % q - q / 2
        inb = fill(de - 0.2, px) * (1 - fill(de - 0.03, px))
        leaf = np.hypot(sl * 0.8, t * 1.5) - 0.07 * (0.6 + 0.4 * np.cos(np.arctan2(t, sl) * 2))
        paint(img, fill(leaf, px) * inb, GOLD)
        paint(img, fill(np.hypot(sl, t) - 0.02, px) * inb, RED)
        sl2 = s % q - q / 2
        paint(img, fill(np.hypot(sl2, t) - 0.022, px) * inb, CREAM)
        paint(img, fill(np.abs(t - 0.06 * np.sin(s / q * TAU)) - 0.006, px) * inb * (1 - fill(leaf - 0.01, px)), (0.5, 0.4, 0.2))
        paint(img, fill(de - 0.03, px), GOLD)
        paint(img, fill(de - 0.014, px), NAVY)
        weave(img, 0.13, 50 + which, 0.16)
        # woven ribbing: fine horizontal ridges
        img *= (0.94 + 0.06 * np.sin(Y * 900))[..., None]
        out.append(img)
    save('tapestry', np.concatenate(out, axis=1))


def shields():
    """2 x 2 atlas of painted shield faces (square tiles; the mesh cuts the heater outline)."""
    w = 512
    X, Y = grid(w, w, 1.0, 1.0)
    px = 1.0 / w
    tiles = []
    # per fess red/cream with gear
    img = np.zeros((w, w, 3), np.float32) + np.array(RED, np.float32)
    paint(img, fill(Y - 0.08, px), CREAM)
    g = np.maximum(sd_gear(X, Y - 0.08, 0.22, 10, 0.22), -(np.hypot(X, Y - 0.08) - 0.11))
    paint(img, fill(g, px) * fill(-(Y - 0.08), px), CREAM)
    paint(img, fill(g, px) * fill(Y - 0.08, px), RED)
    tiles.append(img)
    # navy with gold bend and stars
    img = np.zeros((w, w, 3), np.float32) + np.array(NAVY, np.float32)
    paint(img, fill(np.abs(X + Y - 0.05) * 0.707 - 0.09, px), GOLD)
    for (cx, cy) in ((0.2, 0.28), (-0.2, -0.2)):
        paint(img, fill(sd_star(X - cx, Y - cy, 0.1), px), GOLD)
    tiles.append(img)
    # green with cream chevron
    img = np.zeros((w, w, 3), np.float32) + np.array(GREEN, np.float32)
    paint(img, fill(np.abs(Y - 0.1 + np.abs(X) * 0.9 - 0.15) - 0.07, px), CREAM)
    paint(img, fill(sd_star(X, Y + 0.22, 0.09), px), GOLD)
    tiles.append(img)
    # gold/black quarterly
    img = np.zeros((w, w, 3), np.float32) + np.array(GOLD, np.float32)
    paint(img, fill(-(X * (Y - 0.08)), px * 0.5), BLACK)
    paint(img, fill(np.hypot(X, Y - 0.08) - 0.1, px), RED)
    tiles.append(img)
    for i, t in enumerate(tiles):
        # painted-board wear: scuffs and chipped edges
        f = fbm(w, w, (10, 10), 4, 70 + i)
        t *= (0.82 + 0.3 * f)[..., None]
        chips = ss(0.7, 0.78, fbm(w, w, (22, 22), 3, 80 + i))
        paint(t, chips * 0.6, (0.3, 0.2, 0.12))
    top = np.concatenate([tiles[0], tiles[1]], axis=1)
    bot = np.concatenate([tiles[2], tiles[3]], axis=1)
    save('shields', np.concatenate([bot, top], axis=0))


def clockface():
    w = 512
    X, Y = grid(w, w, 1.0, 1.0)
    px = 1.0 / w
    img = np.zeros((w, w, 3), np.float32) + np.array((0.62, 0.45, 0.2), np.float32)   # brass spandrel plate
    d = np.hypot(X, Y)
    a = np.arctan2(X, Y)   # clockwise from 12
    paint(img, fill(d - 0.46, px), (0.8, 0.76, 0.62))
    paint(img, band(d, 0.44, 0.46, px), BLACK)
    paint(img, band(d, 0.3, 0.31, px), BLACK)
    # minute ticks
    ma = (a / TAU * 60) % 1 - 0.5
    paint(img, fill(np.abs(ma) * d * TAU / 60 - 0.003, px) * band(d, 0.41, 0.44, px), BLACK)
    numerals = ['XII', 'I', 'II', 'III', 'IIII', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI']
    for i, nm in enumerate(numerals):
        an = i * TAU / 12
        cx, cy = math.sin(an) * 0.365, math.cos(an) * 0.365
        # local frame: up = radial out
        lx = (X - cx) * math.cos(an) - (Y - cy) * math.sin(an)
        ly = (X - cx) * math.sin(an) + (Y - cy) * math.cos(an)
        wid = {'I': 0.022, 'V': 0.05, 'X': 0.05}
        tot = sum(wid[c] for c in nm)
        x0 = -tot / 2
        for c in nm:
            xc = x0 + wid[c] / 2
            hh = 0.04
            if c == 'I':
                m = fill(sd_box(lx - xc, ly, 0.005, hh), px)
            elif c == 'V':
                m = fill(np.abs(np.abs(lx - xc) - (ly + hh) * 0.28) - 0.005, px) * fill(np.abs(ly) - hh, px)
            else:
                m = fill(np.abs(np.abs(lx - xc) - np.abs(ly) * 0.5) - 0.005, px) * fill(np.abs(ly) - hh, px)
            paint(img, m, BLACK)
            x0 += wid[c]
    # hands at ten past ten
    for (an, ln, th) in ((TAU * (10 + 10 / 60) / 12, 0.22, 0.014), (TAU * 10 / 60, 0.34, 0.01)):
        lx = X * math.cos(an) - Y * math.sin(an)
        ly = X * math.sin(an) + Y * math.cos(an)
        hand = sd_box(lx, ly - ln / 2 + 0.03, th * (1.2 - ly / ln * 0.8), ln / 2 + 0.03)
        paint(img, fill(hand, px), (0.06, 0.07, 0.12))
    paint(img, fill(d - 0.03, px), (0.62, 0.45, 0.2))
    # corner flourishes on the brass plate
    for sx_ in (-1, 1):
        for sy_ in (-1, 1):
            dd = np.hypot(X - sx_ * 0.42, Y - sy_ * 0.42)
            aa = np.arctan2(Y - sy_ * 0.42, X - sx_ * 0.42)
            paint(img, fill(dd - 0.06 * (0.7 + 0.3 * np.cos(aa * 6)), px), (0.42, 0.28, 0.1))
    f = fbm(w, w, (8, 8), 4, 91)
    img *= (0.88 + 0.2 * f)[..., None]
    save('clockface', img)


def endgrain():
    w = 256
    X, Y = grid(w, w, 1.0, 1.0)
    d = np.hypot(X + 0.03, Y - 0.02)
    n = fbm(w, w, (5, 5), 4, 3)
    rings = 0.5 + 0.5 * np.sin((d + n * 0.05) * 95)
    img = np.zeros((w, w, 3), np.float32) + np.array((0.62, 0.45, 0.27), np.float32)
    img *= (0.72 + 0.3 * rings)[..., None]
    a = np.arctan2(Y, X)
    crack = ss(0.985, 1.0, np.cos(a * 3 + n * 2)) * ss(0.05, 0.3, d)
    paint(img, crack * 0.7, (0.12, 0.08, 0.05))
    paint(img, ss(0.4, 0.5, d), (0.2, 0.14, 0.09))
    save('endgrain', img)


if __name__ == '__main__':
    rug(); banners(); tapestry(); shields(); clockface(); endgrain()
