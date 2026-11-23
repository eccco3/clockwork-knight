"""Stone inglenook fireplace on the fire-end wall (wall-local frame 'F')."""
import math
from mathutils import Vector
from hall_lib import *
from hall_shell import WALLS, HW, HL, EH, APEX, FIRE_W, FIRE_W2, S_at, BEAM

D1 = 1.6          # depth of the lower body
H1 = 2.15          # height of the lower body (mantel shelf sits on it)
OPEN_W = 3.0      # fire opening
OPEN_H = 1.55
BRES_H = 0.4     # oak bressummer
W2 = FIRE_W2          # upper breast
D2 = 1.0
BLK = 0.22        # facing block depth
HEARTH_H = 0.12
BACK = 0.35       # firebox back wall (from the hall wall face)


def _sub(rects, h):
    out = []
    hx0, hx1, hy0, hy1 = h
    for (x0, x1, y0, y1) in rects:
        if x1 <= hx0 or x0 >= hx1 or y1 <= hy0 or y0 >= hy1:
            out.append((x0, x1, y0, y1)); continue
        if x0 < hx0:
            out.append((x0, hx0, y0, y1))
        if x1 > hx1:
            out.append((hx1, x1, y0, y1))
        xa, xb = max(x0, hx0), min(x1, hx1)
        if y0 < hy0:
            out.append((xa, xb, y0, hy0))
        if y1 > hy1:
            out.append((xa, xb, hy1, y1))
    return out


def courses(b, H, lo=0.2, hi=0.31):
    out = []; y = 0
    while y < H - 1e-6:
        ch = b.r(lo, hi)
        if H - (y + ch) < 0.14:
            ch = H - y
        out.append(ch); y += ch
    return out


def masonry(b, W, crs, depth=BLK, blk=(0.34, 0.66), holes=(), mat='stone', gap=0.009, tint=(1, 1, 1), y0=0.0, quoin=False):
    """Coursed blocks over local x in [-W/2, W/2], starting at y0; face at z = 0, bodies behind."""
    with b.grp('ns_fire'):
        _masonry(b, W, crs, depth, blk, holes, mat, gap, tint, y0, quoin)


def _masonry(b, W, crs, depth, blk, holes, mat, gap, tint, y0, quoin):
    y = y0
    for ci, ch in enumerate(crs):
        x = -W / 2
        first = True
        while x < W / 2 - 1e-6:
            bw = b.r(*blk)
            if quoin and first:
                bw = 0.52 if ci % 2 == 0 else 0.3
            rem = W / 2 - (x + bw)
            if quoin and 0 < rem < 0.75:
                # leave room for a proper quoin at the far end
                last = 0.3 if ci % 2 == 0 else 0.52
                if rem < last + 0.2:
                    bw = W / 2 - x - last if (W / 2 - x - last) > 0.2 else W / 2 - x
            elif rem < 0.2:
                bw = W / 2 - x
            first = False
            rects = [(x, x + bw, y, y + ch)]
            for h in holes:
                rects = _sub(rects, h)
            for (xa, xb, ya, yb) in rects:
                if xb - xa < 0.04 or yb - ya < 0.04:
                    continue
                dz = b.r(-0.007, 0.006)
                b.box((xb - xa - gap, yb - ya - gap, depth), mat, pos=((xa + xb) / 2, (ya + yb) / 2, -depth / 2 + dz),
                      bevel=b.r(0.009, 0.018), tint=b.vary(tint, 0.14, 0.035))
            x += bw
        y += ch


def build_fireplace(b):
    with b.grp('fire'), b.at(WALLS['F']):
        crs1 = courses(b, H1)
        soot = (0.07, 0.06, 0.052)
        # ---- lower body ---------------------------------------------------
        holes = [(-OPEN_W / 2, OPEN_W / 2, -1, OPEN_H), (-OPEN_W / 2 - 0.5, OPEN_W / 2 + 0.5, OPEN_H, OPEN_H + BRES_H)]
        with b.at(T(0, 0, D1)):
            masonry(b, FIRE_W, crs1, holes=holes, quoin=True)
        for sx in (-1, 1):
            # outer flank
            with b.at(T(sx * FIRE_W / 2, 0, (D1 - BLK) / 2) @ RY(sx * PI / 2)):
                masonry(b, D1 - BLK, crs1)
            # inner reveal of the opening (sooty)
            with b.at(T(sx * OPEN_W / 2, 0, (D1 - BLK + BACK) / 2) @ RY(-sx * PI / 2)):
                masonry(b, D1 - BLK - BACK, courses(b, OPEN_H, 0.12, 0.18), depth=0.12, blk=(0.22, 0.4), tint=soot)
            # mortar core of the jamb
            jw = (FIRE_W - OPEN_W) / 2
            b.box((jw - 0.2, H1, D1 - 0.03), 'mortar', pos=(sx * (OPEN_W / 2 + jw / 2), H1 / 2, (D1 - 0.03) / 2), bevel=0)
            b.col((jw, H1 + 0.1, D1), pos=(sx * (OPEN_W / 2 + jw / 2), (H1 + 0.1) / 2, D1 / 2))
        # core above the opening
        b.box((OPEN_W + 0.3, H1 - OPEN_H - 0.05, D1 - 0.02), 'mortar', pos=(0, (H1 + OPEN_H + 0.05) / 2, (D1 - 0.02) / 2), bevel=0)
        b.col((OPEN_W, H1 - OPEN_H, D1), pos=(0, (H1 + OPEN_H) / 2, D1 / 2))
        # firebox back (brick-sized sooty blocks) and throat
        with b.at(T(0, 0, BACK)):
            masonry(b, OPEN_W, courses(b, OPEN_H + 0.1, 0.1, 0.14), depth=0.1, blk=(0.24, 0.36), tint=(0.05, 0.043, 0.038), gap=0.007)
        b.box((OPEN_W + 0.2, 0.3, D1 - BACK), 'mortar', pos=(0, OPEN_H + 0.19, (D1 + BACK) / 2 - 0.2), bevel=0, tint=(0.12, 0.11, 0.1))
        b.box((OPEN_W + 0.3, OPEN_H + 0.2, 0.1), 'mortar', pos=(0, OPEN_H / 2, BACK - 0.06), bevel=0, tint=(0.1, 0.09, 0.08))
        for sx in (-1, 1):
            b.box((0.1, OPEN_H + 0.1, D1 - BACK), 'mortar', pos=(sx * (OPEN_W / 2 + 0.07), OPEN_H / 2, (D1 + BACK) / 2 - 0.1), bevel=0, tint=(0.12, 0.11, 0.1))
        # cast-iron fireback
        pts = [(-0.6, 0), (0.6, 0), (0.6, 0.7), (0.36, 0.9), (0, 0.98), (-0.36, 0.9), (-0.6, 0.7)]
        ring = [(0.2 * math.cos(TAU * k / 20), HEARTH_H + 0.45 + 0.2 * math.sin(TAU * k / 20), BACK + 0.052) for k in range(20)]
        # ---- bressummer + mantel shelf -------------------------------------
        b.box((OPEN_W + 1.0, BRES_H, 0.42), 'wood_beam', pos=(0, OPEN_H + BRES_H / 2, D1 - 0.21 + 0.07), bevel=0.028, grain=0,
              tint=(0.86, 0.7, 0.56))
        # stone corbels under the shelf
        for x in (-FIRE_W / 2 + 0.35, -FIRE_W / 4 + 0.1, 0.0, FIRE_W / 4 - 0.1, FIRE_W / 2 - 0.35):
            pts = [(0, 0), (0.0, -0.2), (0.07, -0.2), (0.16, -0.07), (0.16, 0)]
            b.prism(pts, 0.2, 'stone', bevel=0.012, M=T(x, H1, D1) @ RY(-PI / 2), tint=b.vary((0.95, 0.93, 0.9), 0.08))
        # shelf: three slabs
        sw = FIRE_W / 2 + 0.12
        for (x0, x1) in ((-sw, -sw / 3), (-sw / 3, sw / 3), (sw / 3, sw)):
            b.box((x1 - x0 - 0.008, 0.09, D1 + 0.19), 'stone', pos=((x0 + x1) / 2, H1 + 0.045, (D1 + 0.19) / 2 - 0.01), bevel=0.02,
                  tint=b.vary((0.98, 0.96, 0.93), 0.06))
        b.col((FIRE_W + 0.24, 0.1, D1 + 0.2), pos=(0, H1 + 0.045, (D1 + 0.19) / 2))
        # ---- upper breast ---------------------------------------------------
        y2 = H1 + 0.09
        H2 = APEX - 0.1 - y2
        crs2 = courses(b, H2, 0.22, 0.34)
        with b.at(T(0, 0, D2)):
            masonry(b, W2, crs2, y0=y2, blk=(0.38, 0.72), quoin=True)
        for sx in (-1, 1):
            with b.at(T(sx * W2 / 2, 0, (D2 - BLK) / 2) @ RY(sx * PI / 2)):
                masonry(b, D2 - BLK, crs2, y0=y2)
        b.box((W2 - 0.03, H2, D2 - 0.015), 'mortar', pos=(0, y2 + H2 / 2, (D2 - 0.015) / 2), bevel=0)
        b.col((W2, H2, D2), pos=(0, y2 + H2 / 2, D2 / 2))
        # string course with a chamfer, a little way up
        b.box((W2 + 0.1, 0.11, D2 + 0.05), 'stone', pos=(0, 4.86, (D2 + 0.05) / 2), bevel=0.03, tint=(0.97, 0.95, 0.92))
        # ---- hearth ----------------------------------------------------------
        b.group = 'ns_fire'
        hx = OPEN_W / 2 + 1.0
        z0, z1 = BACK, D1 + 0.95
        x = -hx
        while x < hx - 1e-6:
            w = b.r(0.5, 0.85)
            if hx - (x + w) < 0.3:
                w = hx - x
            z = z0
            while z < z1 - 1e-6:
                d = b.r(0.45, 0.8)
                if z1 - (z + d) < 0.3:
                    d = z1 - z
                inside = z + d / 2 < D1 - 0.1 and abs(x + w / 2) < OPEN_W / 2
                tn = b.vary((0.11, 0.1, 0.09) if inside else (0.95, 0.9, 0.86), 0.12, 0.03)
                b.box((w - 0.008, HEARTH_H, d - 0.008), 'stone_flag', pos=(x + w / 2, HEARTH_H / 2 + b.r(-0.003, 0.003), z + d / 2),
                      bevel=b.r(0.01, 0.018), tint=tn)
                z += d
            x += w
        b.box((2 * hx - 0.04, HEARTH_H - 0.03, z1 - z0 - 0.04), 'mortar', pos=(0, (HEARTH_H - 0.03) / 2, (z0 + z1) / 2), bevel=0)
        b.col((2 * hx, HEARTH_H, z1 - D1), pos=(0, HEARTH_H / 2, (z1 + D1) / 2))
        # keep the player out of the firebox
        b.col((OPEN_W, OPEN_H, D1 - 0.25), pos=(0, OPEN_H / 2, (D1 - 0.25) / 2))

        # ---- fire dogs, logs, embers ----------------------------------------
        fz = BACK + 0.55      # fire centre (wall-local z)
        for sx in (-1, 1):
            x = sx * 0.36
            with b.at(T(x, HEARTH_H, fz)):
                # front upright with scroll feet and ball finial
                b.box((0.035, 0.5, 0.035), 'iron', pos=(0, 0.25, 0.38), bevel=0.006)
                b.ball(0.045, 'iron', 10, 6, M=T(0, 0.53, 0.38))
                b.ball(0.028, 'iron', 8, 5, M=T(0, 0.3, 0.38))
                foot = [(sx2 * 0.14, 0.0, 0.38) for sx2 in (-1,)]
                for s2 in (-1, 1):
                    path = [(s2 * t * 0.15, 0.13 * (1 - t) ** 2 + 0.012, 0.38) for t in (0, 0.25, 0.5, 0.75, 1.0)]
                    b.sweep(path, rect_prof(0.03, 0.03, 0.005), 'iron', up=(0, 0, 1))
                # billet bar running back
                b.box((0.03, 0.03, 0.72), 'iron', pos=(0, 0.13, 0.02), bevel=0.005)
                b.box((0.03, 0.13, 0.03), 'iron', pos=(0, 0.065, -0.32), bevel=0.005)
        # logs on the dogs
        logs = [
            ((-0.48, 0.2, 0.02), (0.5, 0.21, -0.03), 0.085),
            ((-0.42, 0.2, 0.2), (0.46, 0.2, 0.24), 0.075),
            ((-0.5, 0.2, -0.2), (0.44, 0.21, -0.17), 0.08),
            ((-0.4, 0.345, 0.12), (0.42, 0.35, 0.08), 0.07),
            ((-0.36, 0.34, -0.09), (0.47, 0.36, -0.13), 0.075),
            ((-0.3, 0.47, 0.03), (0.38, 0.455, -0.02), 0.06),
        ]
        for i, (p0, p1, r) in enumerate(logs):
            p0 = Vector(p0) + Vector((0, HEARTH_H, fz)); p1 = Vector(p1) + Vector((0, HEARTH_H, fz))
            _log(b, p0, p1, r, charred=True)
            b.mark('firelog', tuple((p0 + p1) / 2), r=r)
        # ember bed
        n = 14
        P = []
        for i in range(n + 1):
            row = []
            for j in range(n + 1):
                u = -1 + 2 * i / n; v = -1 + 2 * j / n
                d = math.sqrt(u * u + v * v)
                h = max(0.0, 1 - d ** 2.2) * 0.1 + (b.r(-0.012, 0.014) if d < 0.95 else 0)
                row.append(Vector((u * 0.62, HEARTH_H + max(h, 0.002) - 0.004, fz + v * 0.4)))
            P.append(row)
        b.grid(P, 'ember', flip=True)
        b.mark('fire', (0, HEARTH_H, fz))


def _log(b, p0, p1, r, charred=False, segs=10, mat='bark'):
    if charred:
        mat = 'log_burn'
    """Round log with bark and cut end faces."""
    p0 = Vector(p0); p1 = Vector(p1)
    L = (p1 - p0).length
    F = frame(p0, p1) @ RZ(-PI / 2) @ T(0, -L / 2, 0)
    tn = b.vary((0.2, 0.17, 0.15) if charred else (0.95, 0.9, 0.85), 0.15)
    k = b.r(0.9, 1.08)
    prof = [(r * 0.96, 0), (r, 0.02), (r * k, L * 0.5), (r, L - 0.02), (r * 0.96, L)]
    b.lathe(prof, mat, segs, tn, F, squash=b.r(0.86, 1.0))
    et = (0.1, 0.08, 0.07) if charred else b.vary((0.9, 0.86, 0.8), 0.14)
    rot = b.r(0, TAU)
    for (y, sgn) in ((0.0, -1), (L, 1)):
        verts = [Vector((0, y, 0))] + [Vector((r * 0.96 * math.cos(TAU * k / segs), y, r * 0.96 * math.sin(TAU * k / segs))) for k in range(segs)]
        uvc = [(0.5, 0.5)] + [(0.5 + 0.47 * math.cos(TAU * k / segs + rot), 0.5 + 0.47 * math.sin(TAU * k / segs + rot)) for k in range(segs)]
        faces = []; uvs = []
        for k in range(segs):
            f = (0, 1 + (k + 1) % segs, 1 + k) if sgn > 0 else (0, 1 + k, 1 + (k + 1) % segs)
            faces.append(f); uvs.append([uvc[i] for i in f])
        b.emit('endgrain', verts, faces, uvs, et, F)
