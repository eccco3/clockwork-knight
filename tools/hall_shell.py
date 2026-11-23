"""Hall shell: floor, walls, timber frame, windows, door, roof."""
import math
from mathutils import Vector
from hall_lib import *

HW = 6.5          # half width (inner faces at x = +-HW)
HL = 12.0         # half length (inner faces at z = +-HL)
WT = 0.6          # wall thickness
EH = 4.8          # eaves height (top of side walls)
APEX = 9.35       # underside of the roof boarding at the ridge
EAVE_S = 5.05     # underside of the roof boarding above the inner wall face
PITCH = math.atan2(APEX - EAVE_S, HW)
TRUSS_Z = [-10.0, -6.0, -2.0, 2.0, 6.0, 10.0]
WSILL, WHEAD, WWID = 1.30, 3.90, 1.70
WIN_Z = {'R': [-4.0, 0.0, 4.0, 8.0], 'L': [4.0, 0.0, -4.0, -8.0]}   # in wall-local u (see WALLS)
PLINTH = 0.30
WAINS = 1.25
DOOR_W, DOOR_H = 2.0, 2.5
FIRE_W = 5.6      # chimney breast width on the fire wall
FIRE_W2 = 3.8     # upper breast width

# wall-local frames: x = along the wall, y = up, z = into the room, origin on the inner face
WALLS = {
    'R': T(HW, 0, 0) @ RY(-PI / 2),    # local x -> world +Z
    'L': T(-HW, 0, 0) @ RY(PI / 2),    # local x -> world -Z
    'D': T(0, 0, HL) @ RY(PI),         # door end, local x -> world -X
    'F': T(0, 0, -HL),                 # fire end, local x -> world +X
}
BEAM = (0.80, 0.66, 0.54)     # tint applied to the grey weathered-oak scan


def S_at(x):
    """Height of the roof boarding underside at world x."""
    return APEX - math.tan(PITCH) * abs(x)


def floor(b):
    with b.grp('ns_floor'):
        x = -HW - 0.25
        while x < HW + 0.25:
            w = b.r(0.21, 0.33)
            z = -HL - 0.25 - b.r(0, 3.5)
            while z < HL + 0.25:
                ln = b.r(2.8, 5.4)
                z0 = max(z, -HL - 0.25); z1 = min(z + ln, HL + 0.25)
                if z1 - z0 > 0.05:
                    b.box((w - 0.004, 0.03, z1 - z0 - 0.004), 'wood_floor',
                          pos=(x + w / 2, -0.015 + b.r(-0.001, 0.001), (z0 + z1) / 2),
                          bevel=0.0035, grain=2, tint=b.vary((1, 1, 1), 0.16, 0.035))
                z += ln
            x += w
        b.box((2 * HW + 1.4, 0.06, 2 * HL + 1.4), 'mortar', pos=(0, -0.055, 0), bevel=0, tint=(0.12, 0.1, 0.08))
    # floor + outer skin colliders
    b.col((2 * HW + 3, 1.0, 2 * HL + 3), pos=(0, -0.5, 0))


def _plaster_wall(b, half, openings, corner_ext):
    """Plaster boxes for one wall in wall-local space. openings: (u, width, y0, y1)."""
    cur = -half - corner_ext
    zc = -WT / 2
    for (u, w, y0, y1) in sorted(openings):
        a, c = u - w / 2, u + w / 2
        b.box((a - cur, EH, WT), 'plaster', pos=((a + cur) / 2, EH / 2, zc), bevel=0, uv='world')
        if y0 > 0.01:
            b.box((w, y0, WT), 'plaster', pos=(u, y0 / 2, zc), bevel=0, uv='world')
        b.box((w, EH - y1, WT), 'plaster', pos=(u, (EH + y1) / 2, zc), bevel=0, uv='world')
        cur = c
    end = half + corner_ext
    b.box((end - cur, EH, WT), 'plaster', pos=((end + cur) / 2, EH / 2, zc), bevel=0, uv='world')


def _wainscot(b, a, c):
    """Frame-and-panel wainscot between wall-local u = a..c, sitting on the stone plinth."""
    ln = c - a
    if ln < 0.2:
        return
    with b.grp('ns_walls'):
        _wainscot_body(b, a, c)


def _wainscot_body(b, a, c):
    ln = c - a
    h = WAINS - PLINTH
    mid = (a + c) / 2
    b.box((ln, h, 0.03), 'wood_panel', pos=(mid, PLINTH + h / 2, 0.015), bevel=0, grain=1, tint=(0.82, 0.8, 0.78))
    n = max(1, round(ln / 0.58))
    pw = ln / n
    tr, br, st = 0.09, 0.13, 0.085
    b.box((ln, tr, 0.024), 'wood_panel', pos=(mid, WAINS - tr / 2, 0.042), bevel=0.005, grain=0, tint=b.vary((1, 1, 1), 0.06))
    b.box((ln, br, 0.024), 'wood_panel', pos=(mid, PLINTH + br / 2, 0.042), bevel=0.005, grain=0, tint=b.vary((1, 1, 1), 0.06))
    for i in range(n + 1):
        u = a + i * pw
        u = min(max(u, a + st / 2), c - st / 2)
        b.box((st, h - tr - br, 0.022), 'wood_panel', pos=(u, PLINTH + br + (h - tr - br) / 2, 0.041), bevel=0.005, grain=1,
              tint=b.vary((1, 1, 1), 0.07))
    for i in range(n):
        u = a + (i + 0.5) * pw
        fw = pw - st - 0.07
        fh = h - tr - br - 0.07
        if fw > 0.1:
            b.box((fw, fh, 0.02), 'wood_panel', pos=(u, PLINTH + br + (h - tr - br) / 2, 0.036), bevel=0.012, grain=1,
                  tint=b.vary((1.06, 1.04, 1.0), 0.09))
    # cap rail and bed mould
    b.box((ln, 0.045, 0.095), 'wood_panel', pos=(mid, WAINS + 0.0225, 0.0475), bevel=0.012, grain=0, tint=(0.9, 0.88, 0.86))
    b.box((ln, 0.03, 0.06), 'wood_panel', pos=(mid, WAINS - 0.012, 0.045), bevel=0.01, grain=0, tint=(0.8, 0.78, 0.76))


def _plinth(b, a, c):
    with b.grp('ns_walls'):
        _plinth_body(b, a, c)


def _plinth_body(b, a, c):
    u = a
    while u < c - 1e-4:
        w = b.r(0.5, 0.95)
        if c - (u + w) < 0.3:
            w = c - u
        b.box((w - 0.008, PLINTH - 0.004, 0.16), 'stone', pos=(u + w / 2, PLINTH / 2, 0.08 - 0.075 + b.r(-0.004, 0.004)),
              bevel=b.r(0.012, 0.02), tint=b.vary((0.92, 0.9, 0.88), 0.12, 0.03))
        u += w
    b.box((c - a, PLINTH - 0.03, 0.1), 'mortar', pos=((a + c) / 2, (PLINTH - 0.03) / 2, 0.02), bevel=0)


def _window(b, name, u):
    """Mullioned oak window in a 1.7 x 2.6 opening; glass is created Godot-side from the mark."""
    w, y0, y1 = WWID, WSILL, WHEAD
    zf = -0.40          # frame plane
    fd = 0.11           # frame depth
    fw = 0.09
    tb = lambda: b.vary(BEAM, 0.08)
    with b.at(T(u, 0, 0)):
        # sill board, running back to the frame
        b.box((w + 0.16, 0.055, 0.52), 'wood_oak', pos=(0, y0 + 0.0275, -0.19), bevel=0.012, grain=0, tint=b.vary((1, 1, 1), 0.06))
        # frame
        b.box((fw, y1 - y0, fd), 'wood_beam', pos=(-w / 2 + fw / 2, (y0 + y1) / 2, zf), bevel=0.01, grain=1, tint=tb())
        b.box((fw, y1 - y0, fd), 'wood_beam', pos=(w / 2 - fw / 2, (y0 + y1) / 2, zf), bevel=0.01, grain=1, tint=tb())
        b.box((w, fw, fd), 'wood_beam', pos=(0, y1 - fw / 2, zf), bevel=0.01, grain=0, tint=tb())
        b.box((w, fw, fd), 'wood_beam', pos=(0, y0 + 0.055 + fw / 2, zf), bevel=0.01, grain=0, tint=tb())
        ytr = y0 + 1.75
        b.box((w - 2 * fw, 0.075, fd), 'wood_beam', pos=(0, ytr, zf), bevel=0.012, grain=0, tint=tb())
        lw = (w - 2 * fw) / 3
        for i in (1, 2):
            b.box((0.07, y1 - y0 - 0.1, fd * 0.9), 'wood_beam', pos=(-w / 2 + fw + i * lw, (y0 + y1) / 2, zf), bevel=0.014, grain=1, tint=tb())
        # arched heads in the upper lights
        for i in range(3):
            xa = -w / 2 + fw + i * lw + 0.03
            xb = xa + lw - 0.06
            yt = y1 - fw + 0.01
            ys = yt - 0.24
            xm = (xa + xb) / 2
            pts = [(xa, yt), (xa, ys)]
            n = 10
            for k in range(1, n):
                t = k / n
                pts.append((xa + (xb - xa) * t, ys + 0.2 * (1 - abs(2 * t - 1) ** 1.5)))
            pts += [(xb, ys), (xb, yt)]
            b.prism(pts, 0.05, 'wood_beam', bevel=0.006, tint=tb(), M=T(0, 0, zf), grain=0)
        # glass (one pane spanning the frame; lead pattern is in the shader)
        b.mark('glass', (0, (y0 + y1) / 2 + 0.03, zf - 0.01), size=[w - 0.1, y1 - y0 - 0.1], wall=name)
        # reveal lining boards (oak) on the jambs give a crisp inner edge
        for sx in (-1, 1):
            b.box((0.03, y1 - y0 - 0.06, 0.34), 'wood_oak', pos=(sx * (w / 2 - 0.015), (y0 + y1) / 2 + 0.03, -0.17), bevel=0.006, grain=1,
                  tint=b.vary((0.9, 0.88, 0.85), 0.06))
        b.box((w, 0.03, 0.34), 'wood_oak', pos=(0, y1 - 0.015, -0.17), bevel=0.006, grain=0, tint=b.vary((0.9, 0.88, 0.85), 0.06))


def _frame_side(b, name):
    """Timber frame on a long wall (wall-local)."""
    wins = WIN_Z[name]
    sgn = 1 if name == 'R' else -1
    posts = [sgn * z for z in TRUSS_Z]
    tb = lambda a=0.09: b.vary(BEAM, a)
    # principal posts
    for u in posts:
        b.box((0.30, EH - PLINTH, 0.34), 'wood_beam', pos=(u, (EH + PLINTH) / 2, 0.24 - 0.17), bevel=0.018, grain=1, tint=tb())
        b.box((0.42, PLINTH + 0.02, 0.36), 'stone', pos=(u, (PLINTH + 0.02) / 2, 0.14), bevel=0.02, tint=b.vary((0.9, 0.88, 0.86), 0.1))
        b.col((0.34, EH, 0.3), pos=(u, EH / 2, 0.13))
    # wall plate and head rail
    b.box((2 * HL, 0.25, 0.3), 'wood_beam', pos=(0, EH - 0.125, 0.0), bevel=0.015, grain=0, tint=tb(0.04))
    b.box((2 * HL, 0.16, 0.2), 'wood_beam', pos=(0, WHEAD + 0.08, -0.03), bevel=0.012, grain=0, tint=tb(0.04))
    # studs: window jambs, and intermediate studs
    bays = [(-HL, posts[0] if sgn > 0 else posts[-1])]
    ps = sorted(posts)
    edges = [-HL] + ps + [HL]
    for i in range(len(edges) - 1):
        a, c = edges[i], edges[i + 1]
        mid = (a + c) / 2
        win = [u for u in wins if a < u < c]
        if win:
            u = win[0]
            for sx in (-1, 1):
                b.box((0.15, WHEAD - WAINS, 0.16), 'wood_beam', pos=(u + sx * (WWID / 2 + 0.075), (WHEAD + WAINS) / 2, -0.02), bevel=0.012, grain=1, tint=tb())
            # short studs above the head rail
            n = 5
            for k in range(n):
                uu = a + 0.15 + (c - a - 0.3) * (k + 0.5) / n
                b.box((0.11, EH - 0.25 - WHEAD - 0.16, 0.14), 'wood_beam', pos=(uu, (EH - 0.25 + WHEAD + 0.16) / 2, -0.025), bevel=0.01, grain=1, tint=tb())
        else:
            span = c - a - 0.3
            n = max(1, round(span / 0.85))
            for k in range(1, n):
                uu = a + 0.15 + span * k / n
                b.box((0.13, EH - 0.25 - WAINS, 0.15), 'wood_beam', pos=(uu, (EH - 0.25 + WAINS) / 2, -0.025), bevel=0.01, grain=1, tint=tb())
            if span > 1.0:
                b.box((span, 0.14, 0.17), 'wood_beam', pos=(mid, 2.62, -0.02), bevel=0.012, grain=0, tint=tb(0.04))


def side_walls(b):
    for name in ('R', 'L'):
        with b.grp('walls'), b.at(WALLS[name]):
            wins = WIN_Z[name]
            _plaster_wall(b, HL, [(u, WWID, WSILL, WHEAD) for u in wins], WT)
            _plinth(b, -HL, HL)
            _wainscot(b, -HL, HL)
            _frame_side(b, name)
            for u in wins:
                _window(b, name, u)
            b.col((2 * HL + 2 * WT, EH + 5.5, WT + 0.4), pos=(0, (EH + 5.5) / 2, -WT / 2 - 0.2 + 0.03))
            # beam filling between the rafter feet (closes the eaves)
            b.box((2 * HL + 2 * WT, 0.42, WT - 0.03), 'plaster', pos=(0, EH + 0.2, -WT / 2 - 0.015), bevel=0, uv='world')
            # wainscot/plinth thickness
            b.col((2 * HL, WAINS + 0.05, 0.1), pos=(0, (WAINS + 0.05) / 2, 0.05))


def _gable(b, mat='plaster'):
    """Triangular gable (wall-local), sitting on the end wall."""
    top = APEX + 0.05
    xo = (APEX - EH) / math.tan(PITCH)
    poly = [(-xo, EH), (xo, EH), (0, top)]
    b.prism(poly, WT, mat, bevel=0, M=T(0, 0, -WT / 2), uv='world')


def _gable_frame(b, skip=None):
    """Raking beams + studs on the inside of a gable. skip: (u0, u1) range to leave clear."""
    tb = lambda a=0.09: b.vary(BEAM, a)
    # tie-level beam
    if skip is None:
        b.box((2 * HW, 0.3, 0.26), 'wood_beam', pos=(0, EH + 0.15, 0.03), bevel=0.016, grain=0, tint=tb(0.04))
    else:
        for sx in (-1, 1):
            ln = HW - skip[1]
            b.box((ln, 0.3, 0.26), 'wood_beam', pos=(sx * (skip[1] + ln / 2), EH + 0.15, 0.03), bevel=0.016, grain=0, tint=tb(0.04))
    # raking beams under the roof boarding
    for sx in (-1, 1):
        x1 = sx * (HW - 0.05); x0 = sx * ((skip[1] + 0.05) if skip else 0.12)
        off = 0.42
        b.beam((x0, S_at(x0) - off, 0.02), (x1, S_at(x1) - off, 0.02), 0.24, 0.26, 'wood_beam', up=(0, 1, 0), bevel=0.016, tint=tb(0.05))
    # studs
    n = 9
    for k in range(-n, n + 1):
        u = k * (HW - 0.2) / (n + 0.6)
        if skip and skip[0] - 0.1 < u < skip[1] + 0.1:
            continue
        ytop = S_at(u) - 0.52
        if ytop - (EH + 0.3) < 0.25:
            continue
        b.box((0.13 if k else 0.22, ytop - (EH + 0.3) + 0.1, 0.15), 'wood_beam', pos=(u, (ytop + EH + 0.3) / 2, -0.02), bevel=0.01, grain=1, tint=tb())
    # collar-level rail
    yc = 6.9
    xr = (APEX - 0.6 - yc) / math.tan(PITCH)
    if skip is None:
        b.box((2 * xr, 0.16, 0.17), 'wood_beam', pos=(0, yc, -0.015), bevel=0.012, grain=0, tint=tb(0.05))
    else:
        for sx in (-1, 1):
            ln = xr - skip[1]
            if ln > 0.1:
                b.box((ln, 0.16, 0.17), 'wood_beam', pos=(sx * (skip[1] + ln / 2), yc, -0.015), bevel=0.012, grain=0, tint=tb(0.05))


def _corner_posts(b):
    for sx in (-1, 1):
        b.box((0.3, EH - PLINTH, 0.3), 'wood_beam', pos=(sx * (HW - 0.12), (EH + PLINTH) / 2, 0.12), bevel=0.018, grain=1, tint=b.vary(BEAM, 0.08))
        b.box((0.4, PLINTH + 0.02, 0.4), 'stone', pos=(sx * (HW - 0.14), (PLINTH + 0.02) / 2, 0.14), bevel=0.02, tint=b.vary((0.9, 0.88, 0.86), 0.1))


def door_wall(b):
    with b.grp('walls'), b.at(WALLS['D']):
        tb = lambda a=0.09: b.vary(BEAM, a)
        _plaster_wall(b, HW, [(0, DOOR_W, 0, DOOR_H)], 0)
        _gable(b)
        _gable_frame(b)
        _corner_posts(b)
        jw = 0.22
        for sx in (-1, 1):
            a = DOOR_W / 2 + jw
            _plinth(b, min(sx * a, sx * HW), max(sx * a, sx * HW))
            _wainscot(b, min(sx * a, sx * (HW - 0.27)), max(sx * a, sx * (HW - 0.27)))
            # studs
            for k in range(1, 5):
                u = sx * (a + (HW - a) * k / 5)
                b.box((0.13, EH - WAINS, 0.15), 'wood_beam', pos=(u, (EH + WAINS) / 2, -0.025), bevel=0.01, grain=1, tint=tb())
            ln = HW - a
            b.box((ln, 0.14, 0.17), 'wood_beam', pos=(sx * (a + ln / 2), 3.0, -0.02), bevel=0.012, grain=0, tint=tb(0.04))
            # door jamb posts
            b.box((jw, DOOR_H + 0.1, 0.5), 'wood_beam', pos=(sx * (DOOR_W / 2 + jw / 2), (DOOR_H + 0.1) / 2, -0.12), bevel=0.02, grain=1, tint=tb(0.05))
        # lintel
        b.box((DOOR_W + 2 * jw + 0.3, 0.3, 0.52), 'wood_beam', pos=(0, DOOR_H + 0.15, -0.12), bevel=0.022, grain=0, tint=tb(0.05))
        # carved lintel: chamfered label with a row of rosettes
        b.box((DOOR_W + 0.3, 0.035, 0.03), 'wood_beam', pos=(0, DOOR_H + 0.27, 0.14), bevel=0.012, grain=0, tint=tb(0.05))
        b.box((DOOR_W + 0.3, 0.035, 0.03), 'wood_beam', pos=(0, DOOR_H + 0.03, 0.14), bevel=0.012, grain=0, tint=tb(0.05))
        for k in range(-3, 4):
            x = k * 0.33
            pet = []
            for i in range(16):
                rr = 0.085 if i % 2 == 0 else 0.05
                pet.append((x + rr * math.cos(TAU * i / 16), DOOR_H + 0.15 + rr * math.sin(TAU * i / 16)))
            b.prism(pet, 0.03, 'wood_beam', bevel=0.01, tint=tb(0.05), M=T(0, 0, 0.145))
            b.ball(0.028, 'wood_beam', 8, 5, tint=tb(0.05), M=T(x, DOOR_H + 0.15, 0.158), sy=0.6)
        # studs above lintel
        for k in range(-2, 3):
            b.box((0.13, EH - DOOR_H - 0.3, 0.15), 'wood_beam', pos=(k * 0.5, (EH + DOOR_H + 0.3) / 2, -0.025), bevel=0.01, grain=1, tint=tb())
        # arched head spandrels (four-centred arch)
        ys = DOOR_H - 0.42
        for sx in (-1, 1):
            pts = [(sx * DOOR_W / 2, DOOR_H), (sx * DOOR_W / 2, ys)]
            n = 10
            for k in range(1, n + 1):
                t = k / n
                x = DOOR_W / 2 * (1 - t)
                y = ys + 0.40 * (1 - (1 - t) ** 2.6) ** (1 / 2.0)
                pts.append((sx * x, min(y, DOOR_H - 0.02)))
            pts.append((0, DOOR_H))
            b.prism(pts, 0.14, 'wood_beam', bevel=0.012, tint=tb(0.05), M=T(0, 0, -0.16), grain=0)
        # door leaves: planks, ledges, iron straps
        zd = -0.30
        for sx in (-1, 1):
            lw = DOOR_W / 2 - 0.006
            npl = 5
            for k in range(npl):
                pw = lw / npl
                x = sx * (0.003 + (k + 0.5) * pw)
                b.box((pw - 0.004, DOOR_H, 0.06), 'wood_panel', pos=(x, DOOR_H / 2, zd), bevel=0.008, grain=1, tint=b.vary((0.95, 0.9, 0.86), 0.1))
            for y in (0.35, 1.25, 2.1):
                # strap hinge: tapered plate with a finial
                x0 = sx * (DOOR_W / 2 - 0.02); x1 = sx * 0.2
                pts = [(x0, y - 0.045), (x1, y - 0.02), (x1 - sx * 0.07, y), (x1, y + 0.02), (x0, y + 0.045)]
                b.prism(pts, 0.012, 'iron', bevel=0.003, M=T(0, 0, zd + 0.036))
                for k in range(5):
                    xs = x0 + (x1 - x0) * (k + 0.5) / 5
                    b.ball(0.012, 'iron', 6, 4, M=T(xs, y, zd + 0.044), sy=0.6)
            # studs rows
            for y in (0.8, 1.7):
                for k in range(npl):
                    b.ball(0.014, 'iron', 6, 4, M=T(sx * (0.003 + (k + 0.5) * lw / npl), y, zd + 0.033), sy=0.6)
            # ring handle + plate
            pl = [(-0.055, -0.12), (0, -0.17), (0.055, -0.12), (0.055, 0.12), (0, 0.17), (-0.055, 0.12)]
            b.prism(pl, 0.01, 'iron', bevel=0.003, M=T(sx * 0.14, 1.12, zd + 0.035))
            b.ball(0.022, 'iron', 8, 5, M=T(sx * 0.14, 1.17, zd + 0.045), sy=0.7)
            ring = [(sx * 0.14 + 0.075 * math.cos(TAU * k / 16), 1.095 + 0.075 * math.sin(TAU * k / 16), zd + 0.06) for k in range(16)]
            b.sweep(ring, circ_prof(0.0095, 6), 'iron', closed=True, up=(0, 0, 1))
        # threshold stone
        b.box((DOOR_W + 0.5, 0.05, 0.6), 'stone', pos=(0, 0.012, -0.05), bevel=0.02, tint=(0.85, 0.83, 0.8))
        # blocking behind the door (keeps the dusk out)
        b.box((DOOR_W + 0.4, DOOR_H + 0.4, 0.2), 'mortar', pos=(0, DOOR_H / 2, -0.5), bevel=0, tint=(0.1, 0.09, 0.08))
        b.col((2 * HW, EH + 5.5, WT + 0.4), pos=(0, (EH + 5.5) / 2, -WT / 2 - 0.2 + 0.03))
        for sx in (-1, 1):
            b.col((HW - DOOR_W / 2, WAINS + 0.05, 0.1), pos=(sx * (DOOR_W / 2 + (HW - DOOR_W / 2) / 2), (WAINS + 0.05) / 2, 0.05))
        b.col((DOOR_W + 0.6, DOOR_H + 0.4, 0.3), pos=(0, DOOR_H / 2, -0.13))
        b.mark('door', (0, 0, 0))


def fire_wall(b):
    with b.grp('walls'), b.at(WALLS['F']):
        tb = lambda a=0.09: b.vary(BEAM, a)
        _plaster_wall(b, HW, [], 0)
        _gable(b)
        _gable_frame(b, skip=(-FIRE_W2 / 2 - 0.15, FIRE_W2 / 2 + 0.15))
        _corner_posts(b)
        for sx in (-1, 1):
            a = FIRE_W / 2
            _plinth(b, min(sx * a, sx * HW), max(sx * a, sx * HW))
            _wainscot(b, min(sx * a, sx * (HW - 0.27)), max(sx * a, sx * (HW - 0.27)))
            for k in range(1, 5):
                u = sx * (a + (HW - a) * k / 5)
                b.box((0.13, EH - WAINS, 0.15), 'wood_beam', pos=(u, (EH + WAINS) / 2, -0.025), bevel=0.01, grain=1, tint=tb())
            ln = HW - a
            b.box((ln, 0.14, 0.17), 'wood_beam', pos=(sx * (a + ln / 2), 3.0, -0.02), bevel=0.012, grain=0, tint=tb(0.04))
        b.col((2 * HW, EH + 5.5, WT + 0.4), pos=(0, (EH + 5.5) / 2, -WT / 2 - 0.2 + 0.03))


def roof(b):
    a = PITCH
    ca = math.cos(a)
    with b.grp('roof'):
        tb = lambda v=0.09: b.vary(BEAM, v)
        zlen = 2 * HL + 2 * WT + 0.3
        for sx in (1, -1):
            # slope frame: origin at the apex, +X runs down the slope, +Y is the outward normal
            with b.at(SC(sx, 1, 1) @ T(0, APEX, 0) @ RZ(-a)):
                sl = (HW + WT + 0.5) / ca
                # boarding (planks along the hall)
                b.box((sl, 0.4, zlen), 'wood_roof', pos=(sl / 2, 0.2, 0), bevel=0, grain=2, uvoff=(0.13 * sx, 0.37))
                # common rafters
                rl = (HW + 0.12) / ca
                z = -HL + 0.25
                while z < HL - 0.1:
                    b.box((rl - 0.12, 0.12, 0.09), 'wood_beam', pos=(0.12 + (rl - 0.12) / 2, -0.06, z), bevel=0.008, grain=0, tint=tb(0.1))
                    z += 0.5
                # purlins
                for f in (0.335, 0.67):
                    b.box((0.2, 0.2, 2 * HL), 'wood_beam', pos=(rl * f, -0.22, 0), bevel=0.014, grain=2, tint=tb(0.05))
                # principal rafters
                for zt in TRUSS_Z:
                    b.box((6.9 - 0.12, 0.3, 0.24), 'wood_beam', pos=(0.12 + (6.9 - 0.12) / 2, -0.44, zt), bevel=0.018, grain=0, tint=tb())
            # truss members on this side
            for zt in TRUSS_Z:
                with b.at(SC(sx, 1, 1) @ T(0, 0, zt)):
                    # strut
                    xs = 3.2
                    b.beam((0.1, 5.22, 0), (xs, S_at(xs) - 0.66, 0), 0.19, 0.2, 'wood_beam', bevel=0.014, tint=tb())
                    # arch brace: quarter ellipse from the post up to the tie beam
                    pts = arc_pts(4.2, 3.3, 1.95, 1.39, 0.0, PI / 2, 12)
                    b.sweep([(p[0], p[1], 0) for p in pts], rect_prof(0.2, 0.22, 0.015), 'wood_beam', tint=tb(), up=(-1, 0, 0))
                    # small spandrel strut between brace and corner
                    b.beam((5.55, 4.25, 0), (6.2, 4.8, 0), 0.12, 0.12, 'wood_beam', bevel=0.01, tint=tb())
        # tie beams, king posts
        for zt in TRUSS_Z:
            b.box((2 * HW + 0.2, 0.32, 0.27), 'wood_beam', pos=(0, EH + 0.16, zt), bevel=0.02, grain=0, tint=tb())
            b.box((0.24, 8.9 - EH - 0.32, 0.24), 'wood_beam', pos=(0, (8.9 + EH + 0.32) / 2, zt), bevel=0.018, grain=1, tint=tb())
            # jowled foot and head
            for (y, hh) in ((EH + 0.32 + 0.11, 0.22), (8.62, 0.34)):
                pts = [(-0.21, -hh / 2), (0.21, -hh / 2), (0.16, hh / 2), (-0.16, hh / 2)] if y < 6 else [(-0.16, -hh / 2), (0.16, -hh / 2), (0.23, hh / 2), (-0.23, hh / 2)]
                b.prism(pts, 0.25, 'wood_beam', bevel=0.012, tint=tb(), M=T(0, y, zt), grain=1)
        # ridge beam
        b.box((0.2, 0.28, 2 * HL), 'wood_beam', pos=(0, APEX - 0.30, 0), bevel=0.014, grain=2, tint=tb(0.05))
        b.col((1.2, 0.5, 2 * HL + 2 * WT), pos=(0, APEX + 0.1, 0))
        # roof skin collider (keeps cameras inside): two slabs
        for sx in (1, -1):
            with b.at(SC(1, 1, 1) @ T(0, APEX, 0) @ RZ(-a if sx > 0 else PI + a)):
                sl = (HW + WT + 0.5) / ca
                b.col((sl, 0.4, zlen), pos=(sl / 2, 0.2 if sx > 0 else -0.2, 0))


def build_shell(b):
    floor(b)
    side_walls(b)
    door_wall(b)
    fire_wall(b)
    roof(b)
