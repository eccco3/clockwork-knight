"""Procedural mesh helpers for the great hall generator (run inside Blender's Python).

Geometry is authored directly in Godot space (X right, Y up, Z toward the door end,
metres) and exported with export_yup=False, so numbers here are numbers in Godot.
Everything is accumulated per (group, material) and turned into a handful of merged
mesh objects at the end.
"""
import bpy, math, random
from contextlib import contextmanager
from mathutils import Matrix, Vector
from mathutils.geometry import tessellate_polygon

PI = math.pi
TAU = 2 * math.pi


def T(x=0.0, y=0.0, z=0.0):
    return Matrix.Translation((x, y, z))


def RX(a):
    return Matrix.Rotation(a, 4, 'X')


def RY(a):
    return Matrix.Rotation(a, 4, 'Y')


def RZ(a):
    return Matrix.Rotation(a, 4, 'Z')


def SC(x, y=None, z=None):
    if y is None:
        y = z = x
    return Matrix.Diagonal((x, y, z, 1.0))


def V(x, y, z):
    return Vector((x, y, z))


def frame(p0, p1, up=(0, 1, 0)):
    """Matrix whose +X runs from p0 to p1, centred between them."""
    p0 = Vector(p0); p1 = Vector(p1)
    x = (p1 - p0).normalized()
    upv = Vector(up)
    if abs(x.dot(upv)) > 0.999:
        upv = Vector((0, 0, 1)) if abs(x.z) < 0.9 else Vector((1, 0, 0))
    z = x.cross(upv).normalized()
    y = z.cross(x)
    m = (p0 + p1) * 0.5
    return Matrix(((x.x, y.x, z.x, m.x), (x.y, y.y, z.y, m.y), (x.z, y.z, z.z, m.z), (0, 0, 0, 1)))


# material -> (metres covered by one texture tile, texture axis the grain runs along)
MATS = {}


def defmat(name, size=1.0, grain='v'):
    MATS[name] = (size, grain)


def rect_prof(w, h, c=0.01):
    """Chamfered rectangle profile (CCW), w along 'side', h along 'up'."""
    a, b = w / 2, h / 2
    c = min(c, 0.45 * min(w, h))
    if c <= 0:
        return [(-a, -b), (a, -b), (a, b), (-a, b)]
    return [(-a + c, -b), (a - c, -b), (a, -b + c), (a, b - c), (a - c, b), (-a + c, b), (-a, b - c), (-a, -b + c)]


def circ_prof(r, n=8):
    return [(r * math.cos(TAU * i / n), r * math.sin(TAU * i / n)) for i in range(n)]


def arc_pts(cx, cy, rx, ry, a0, a1, n):
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n), cy + ry * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def _inset(poly, c):
    n = len(poly)
    out = []
    for i in range(n):
        p0 = Vector(poly[i - 1]); p1 = Vector(poly[i]); p2 = Vector(poly[(i + 1) % n])
        e0 = (p1 - p0).normalized(); e1 = (p2 - p1).normalized()
        n0 = Vector((-e0.y, e0.x)); n1 = Vector((-e1.y, e1.x))  # inward normals for CCW polygon
        bis = n0 + n1
        if bis.length < 1e-6:
            bis = n0
        bis.normalize()
        d = max(0.3, bis.dot(n0))
        q = p1 + bis * (c / d)
        out.append((q.x, q.y))
    return out


def _area(poly):
    return 0.5 * sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1] for i in range(len(poly)))


class Geo:
    __slots__ = ('v', 'f', 'uv', 'col')

    def __init__(self):
        self.v = []; self.f = []; self.uv = []; self.col = []


class Builder:
    def __init__(self, seed=11):
        self.geo = {}
        self.stack = [Matrix.Identity(4)]
        self.rng = random.Random(seed)
        self.group = 'shell'
        self.variant_name = None
        self.colliders = []
        self.marks = {}
        self.tris = 0

    # ---- transform stack -------------------------------------------------
    @property
    def M(self):
        return self.stack[-1]

    @contextmanager
    def at(self, m):
        self.stack.append(self.stack[-1] @ m)
        try:
            yield
        finally:
            self.stack.pop()

    @contextmanager
    def grp(self, name):
        old = self.group
        self.group = name
        try:
            yield
        finally:
            self.group = old

    def ns(self):
        """The current group's fine dressing, which casts no shadows (see builders/hall_import.gd)."""
        return self.grp(self.group if self.group.startswith('ns_') else 'ns_' + self.group)

    @contextmanager
    def variant(self, name):
        """Materials that have a `<material>_<name>` variant use it inside the block."""
        old = self.variant_name
        self.variant_name = name
        try:
            yield
        finally:
            self.variant_name = old

    def yaw(self):
        """World heading of local +Z: the angle about +Y that turns +Z onto it."""
        z = self.M.to_3x3() @ Vector((0, 0, 1))
        return round(math.atan2(z.x, z.z), 5)

    def world_box(self, p0, p1):
        """World corner (least x, y, z) and size of the box between local corners p0 and p1, in a
        frame turned by quarter turns."""
        a, c = self.M @ Vector(p0), self.M @ Vector(p1)
        return [round(min(a[i], c[i]), 4) for i in range(3)], [round(abs(c[i] - a[i]), 4) for i in range(3)]

    # ---- randomness ------------------------------------------------------
    @contextmanager
    def seeded(self, key):
        """A random stream of the block's own, so what it draws never shifts the variation of
        anything built after it."""
        old = self.rng
        self.rng = random.Random(repr(key))
        try:
            yield
        finally:
            self.rng = old

    def r(self, a=0.0, b=1.0):
        return self.rng.uniform(a, b)

    def vary(self, base=(1, 1, 1), amt=0.12, hue=0.04):
        k = 1.0 + self.rng.uniform(-amt, amt)
        h = self.rng.uniform(-hue, hue)
        return (base[0] * k * (1 + h), base[1] * k, base[2] * k * (1 - h))

    # ---- low level emit --------------------------------------------------
    def _g(self, mat):
        if mat not in MATS:
            raise KeyError("unknown material " + mat)
        if self.variant_name and mat + '_' + self.variant_name in MATS:
            mat += '_' + self.variant_name
        key = (self.group, mat)
        g = self.geo.get(key)
        if g is None:
            g = self.geo[key] = Geo()
        return g

    def emit(self, mat, verts, faces, uvs, tint=None, M=None):
        g = self._g(mat)
        Mw = self.M if M is None else self.M @ M
        flip = Mw.to_3x3().determinant() < 0
        base = len(g.v)
        for p in verts:
            q = Mw @ p
            g.v.append((q.x, q.y, q.z))
        tint = tint or (1, 1, 1)
        for f, fu in zip(faces, uvs):
            if flip:
                f = f[::-1]; fu = fu[::-1]
            g.f.append(tuple(base + i for i in f))
            g.uv.append(fu)
            g.col.append(tint)
            self.tris += len(f) - 2

    def _uvp(self, p, n, grain, info, off):
        size, g = info
        d = max(range(3), key=lambda i: abs(n[i]))
        a, b = [i for i in range(3) if i != d]
        if grain == b:
            a, b = b, a
        along = p[a] / size
        across = p[b] / size
        if g == 'v':
            return (across + off[0], along + off[1])
        return (along + off[0], across + off[1])

    def emit_auto(self, mat, verts, faces, grain=0, tint=None, uv='local', M=None, center=None, uvoff=None, orient=True):
        """Emit faces with box-projected UVs. Faces are oriented away from `center` when orient."""
        info = MATS[mat]
        Mw = self.M if M is None else self.M @ M
        if center is None:
            center = Vector((0, 0, 0))
            for p in verts:
                center += p
            center /= max(1, len(verts))
        wv = [Mw @ p for p in verts] if uv == 'world' else None
        R = Mw.to_3x3()
        if uvoff is None:
            uvoff = (0.0, 0.0) if uv == 'world' else (self.rng.random(), self.rng.random())
        out_f = []; out_uv = []
        for f in faces:
            n = Vector((0, 0, 0))
            c = Vector((0, 0, 0))
            for i in range(len(f)):
                a = verts[f[i]]; b2 = verts[f[(i + 1) % len(f)]]
                n.x += (a.y - b2.y) * (a.z + b2.z)
                n.y += (a.z - b2.z) * (a.x + b2.x)
                n.z += (a.x - b2.x) * (a.y + b2.y)
                c += a
            c /= len(f)
            if orient and n.dot(c - center) < 0:
                f = f[::-1]; n = -n
            if uv == 'world':
                nw = R @ n
                out_uv.append([self._uvp(wv[i], nw, grain, info, uvoff) for i in f])
            else:
                out_uv.append([self._uvp(verts[i], n, grain, info, uvoff) for i in f])
            out_f.append(f)
        self.emit(mat, verts, out_f, out_uv, tint, M)

    # ---- primitives ------------------------------------------------------
    def box(self, size, mat, pos=(0, 0, 0), bevel=0.008, grain=None, tint=None, uv='local', rot=None, M=None, uvoff=None):
        sx, sy, sz = size
        hx, hy, hz = sx / 2, sy / 2, sz / 2
        if grain is None:
            grain = max(range(3), key=lambda i: size[i])
        L = T(*pos)
        if rot is not None:
            L = L @ rot
        if M is not None:
            L = M @ L
        c = min(bevel, 0.45 * min(sx, sy, sz))
        if c <= 1e-5:
            verts = [Vector((x * hx, y * hy, z * hz)) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
            faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        else:
            h = (hx, hy, hz)
            verts = []; idx = {}
            for s0 in (-1, 1):
                for s1 in (-1, 1):
                    for s2 in (-1, 1):
                        s = (s0, s1, s2)
                        for ax in range(3):
                            idx[(s, ax)] = len(verts)
                            verts.append(Vector([s[i] * (h[i] if i == ax else h[i] - c) for i in range(3)]))
            faces = []
            for ax in range(3):
                a, b2 = [i for i in range(3) if i != ax]
                for sg in (-1, 1):
                    f = []
                    for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                        s = [0, 0, 0]; s[ax] = sg; s[a] = sa; s[b2] = sb
                        f.append(idx[(tuple(s), ax)])
                    faces.append(tuple(f))
            for cax in range(3):
                a, b2 = [i for i in range(3) if i != cax]
                for sa in (-1, 1):
                    for sb in (-1, 1):
                        s0 = [0, 0, 0]; s0[a] = sa; s0[b2] = sb; s0[cax] = -1
                        s1 = list(s0); s1[cax] = 1
                        faces.append((idx[(tuple(s0), a)], idx[(tuple(s1), a)], idx[(tuple(s1), b2)], idx[(tuple(s0), b2)]))
            for s0 in (-1, 1):
                for s1 in (-1, 1):
                    for s2 in (-1, 1):
                        s = (s0, s1, s2)
                        faces.append((idx[(s, 0)], idx[(s, 1)], idx[(s, 2)]))
        self.emit_auto(mat, verts, faces, grain, tint, uv, L, Vector((0, 0, 0)), uvoff)

    def beam(self, p0, p1, w, h, mat, up=(0, 1, 0), bevel=0.012, tint=None, ext=0.0, uvoff=None):
        """Box from p0 to p1; h is measured along `up`, w across."""
        p0 = Vector(p0); p1 = Vector(p1)
        L = (p1 - p0).length + 2 * ext
        self.box((L, h, w), mat, bevel=bevel, grain=0, tint=tint, M=frame(p0, p1, up), uvoff=uvoff)

    def lathe(self, prof, mat, segs=16, tint=None, M=None, uvoff=None, squash=1.0):
        """Revolve (r, y) profile around Y. Order the profile so the outside is on the right
        when walking along it (bottom centre -> out -> up -> top centre)."""
        info = MATS[mat]
        verts = []; rings = []
        for (r, y) in prof:
            if r < 1e-6:
                rings.append([len(verts)]); verts.append(Vector((0, y, 0)))
            else:
                rings.append(list(range(len(verts), len(verts) + segs)))
                for j in range(segs):
                    a = TAU * j / segs
                    verts.append(Vector((r * math.cos(a), y, r * math.sin(a) * squash)))
        cum = [0.0]
        for i in range(1, len(prof)):
            cum.append(cum[-1] + math.hypot(prof[i][0] - prof[i - 1][0], prof[i][1] - prof[i - 1][1]))
        rmax = max(p[0] for p in prof)
        ucount = max(1, round(TAU * rmax / info[0]))
        if uvoff is None:
            uvoff = (self.rng.random(), self.rng.random())

        def uvof(i, j):
            around = j / segs * ucount + uvoff[0]
            along = cum[i] / info[0] + uvoff[1]
            return (around, along) if info[1] == 'v' else (along, around)

        faces = []; uvs = []
        for i in range(len(prof) - 1):
            A = rings[i]; B = rings[i + 1]
            if len(A) == 1 and len(B) == 1:
                continue
            for j in range(segs):
                j2 = (j + 1) % segs
                if len(A) == 1:
                    faces.append((A[0], B[j], B[j2])); uvs.append([uvof(i, j + 0.5), uvof(i + 1, j), uvof(i + 1, j + 1)])
                elif len(B) == 1:
                    faces.append((A[j], B[0], A[j2])); uvs.append([uvof(i, j), uvof(i + 1, j + 0.5), uvof(i, j + 1)])
                else:
                    faces.append((A[j], B[j], B[j2], A[j2]))
                    uvs.append([uvof(i, j), uvof(i + 1, j), uvof(i + 1, j + 1), uvof(i, j + 1)])
        self.emit(mat, verts, faces, uvs, tint, M)

    def cyl(self, r, h, mat, segs=12, tint=None, M=None, bevel=0.004, y0=0.0):
        c = min(bevel, r * 0.4, h * 0.4)
        if c < 1e-5:
            prof = [(0, y0), (r, y0), (r, y0 + h), (0, y0 + h)]
        else:
            prof = [(0, y0), (r - c, y0), (r, y0 + c), (r, y0 + h - c), (r - c, y0 + h), (0, y0 + h)]
        self.lathe(prof, mat, segs, tint, M)

    def rod(self, p0, p1, r, mat, segs=8, tint=None, bevel=0.003):
        """Cylinder between two points."""
        p0 = Vector(p0); p1 = Vector(p1)
        L = (p1 - p0).length
        F = frame(p0, p1)
        self.cyl(r, L, mat, segs, tint, F @ RZ(-PI / 2) @ T(0, -L / 2, 0), bevel)

    def ball(self, r, mat, segs=12, rings=8, tint=None, M=None, sy=1.0):
        prof = [(r * math.sin(PI * i / rings), -r * sy * math.cos(PI * i / rings)) for i in range(rings + 1)]
        prof[0] = (0, prof[0][1]); prof[-1] = (0, prof[-1][1])
        self.lathe(prof, mat, segs, tint, M)

    def sweep(self, path, prof, mat, tint=None, up=(0, 1, 0), caps=True, M=None, closed=False, scale=None):
        """Sweep 2D profile (CCW; x = side, y = up) along a 3D polyline. scale: optional per-point factor."""
        info = MATS[mat]
        path = [Vector(p) for p in path]
        n = len(path); m = len(prof)
        tang = []
        for i in range(n):
            if closed:
                t = path[(i + 1) % n] - path[i - 1]
            else:
                t = path[min(i + 1, n - 1)] - path[max(i - 1, 0)]
            tang.append(t.normalized())
        upv = Vector(up)
        nrm = upv - tang[0] * upv.dot(tang[0])
        if nrm.length < 1e-4:
            nrm = Vector((1, 0, 0)) - tang[0] * tang[0].x
        nrm.normalize()
        verts = []
        plen = [0.0]
        for i in range(1, m + 1):
            plen.append(plen[-1] + math.hypot(prof[i % m][0] - prof[i - 1][0], prof[i % m][1] - prof[i - 1][1]))
        cum = [0.0]
        for i in range(n):
            if i > 0:
                cum.append(cum[-1] + (path[i] - path[i - 1]).length)
                nrm = nrm - tang[i] * nrm.dot(tang[i])
                nrm.normalize()
            side = tang[i].cross(nrm)
            k = scale[i] if scale else 1.0
            for (a, b2) in prof:
                verts.append(path[i] + side * (a * k) + nrm * (b2 * k))
        if closed:
            cum.append(cum[-1] + (path[0] - path[-1]).length)
        off = (self.rng.random(), self.rng.random())

        def uvof(i, j):
            along = cum[i] / info[0] + off[1]
            around = plen[j] / info[0] + off[0]
            return (around, along) if info[1] == 'v' else (along, around)

        faces = []; uvs = []
        segs = n if closed else n - 1
        # winding test on first quad
        a = verts[0]; b2 = verts[m]; c = verts[m + 1]
        nq = (b2 - a).cross(c - a)
        flip = nq.dot(a - path[0]) < 0
        for i in range(segs):
            i2 = (i + 1) % n
            for j in range(m):
                j2 = (j + 1) % m
                f = (i * m + j, i2 * m + j, i2 * m + j2, i * m + j2)
                u = [uvof(i, j), uvof(i + 1, j), uvof(i + 1, j + 1), uvof(i, j + 1)]
                if flip:
                    f = f[::-1]; u = u[::-1]
                faces.append(f); uvs.append(u)
        if caps and not closed:
            f0 = tuple(range(m)); f1 = tuple((n - 1) * m + j for j in range(m))
            u = [(p[0] / info[0], p[1] / info[0]) for p in prof]
            # start cap faces -tangent, end cap faces +tangent
            n0 = (verts[1] - verts[0]).cross(verts[2] - verts[0])
            if n0.dot(tang[0]) > 0:
                faces.append(f0[::-1]); uvs.append(u[::-1]); faces.append(f1); uvs.append(u)
            else:
                faces.append(f0); uvs.append(u); faces.append(f1[::-1]); uvs.append(u[::-1])
        self.emit(mat, verts, faces, uvs, tint, M)

    def prism(self, poly, depth, mat, bevel=0.006, tint=None, M=None, grain=0, uv='local', uvoff=None):
        """Extrude a 2D polygon (local XY) along local Z, centred, with a chamfer on both caps."""
        poly = list(poly)
        if _area(poly) < 0:
            poly.reverse()
        n = len(poly)
        c = min(bevel, depth * 0.45)
        h = depth / 2
        if c > 1e-5:
            ins = _inset(poly, c)
            rings = [(ins, h), (poly, h - c), (poly, -h + c), (ins, -h)]
        else:
            rings = [(poly, h), (poly, -h)]
        verts = []
        for pts, z in rings:
            for p in pts:
                verts.append(Vector((p[0], p[1], z)))
        faces = []
        convex = True
        for i in range(n):
            a = Vector(poly[i - 1]); b2 = Vector(poly[i]); c2 = Vector(poly[(i + 1) % n])
            if (b2 - a).cross(c2 - b2) < -1e-9:
                convex = False; break
        last = (len(rings) - 1) * n
        if convex:
            faces.append(tuple(range(n)))
            faces.append(tuple(last + i for i in reversed(range(n))))
        else:
            tris = tessellate_polygon([[Vector((p[0], p[1], 0)) for p in rings[0][0]]])
            for t in tris:
                t = tuple(t)
                a, b2, c2 = (Vector(rings[0][0][k]) for k in t)
                if (b2 - a).cross(c2 - a) < 0:
                    t = t[::-1]
                faces.append(t)
                faces.append(tuple(last + k for k in reversed(t)))
        for k in range(len(rings) - 1):
            for i in range(n):
                i2 = (i + 1) % n
                faces.append((k * n + i, (k + 1) * n + i, (k + 1) * n + i2, k * n + i2))
        self.emit_auto(mat, verts, faces, grain, tint, uv, M, uvoff=uvoff, orient=False)

    def grid(self, P, mat, tint=None, uvfn=None, M=None, flip=False):
        """P[i][j] -> Vector. uvfn(i, j) -> (u, v); default spans 0..1 (i -> u, j -> v)."""
        ni = len(P); nj = len(P[0])
        verts = [P[i][j] for i in range(ni) for j in range(nj)]
        if uvfn is None:
            uvfn = lambda i, j: (i / (ni - 1), j / (nj - 1))
        faces = []; uvs = []
        for i in range(ni - 1):
            for j in range(nj - 1):
                f = (i * nj + j, (i + 1) * nj + j, (i + 1) * nj + j + 1, i * nj + j + 1)
                u = [uvfn(i, j), uvfn(i + 1, j), uvfn(i + 1, j + 1), uvfn(i, j + 1)]
                if flip:
                    f = f[::-1]; u = u[::-1]
                faces.append(f); uvs.append(u)
        self.emit(mat, verts, faces, uvs, tint, M)

    def cushion(self, sx, sy, sz, mat, tint=None, M=None, n=8, puff=1.0, uvscale=None):
        """Pillow: sx by sz footprint, sy thick, pinched seam around the edge. Origin at centre."""
        info = MATS[mat]
        for sgn in (1, -1):
            P = []
            for i in range(n + 1):
                row = []
                u = -1 + 2 * i / n
                for j in range(n + 1):
                    v = -1 + 2 * j / n
                    k = max(0.0, (1 - u ** 4) * (1 - v ** 4)) ** 0.45
                    pin = 1.0 - 0.06 * (u * u * v * v)
                    row.append(Vector((u * sx / 2 * pin, sgn * (sy / 2) * k * puff, v * sz / 2 * pin)))
                P.append(row)
            self.grid(P, mat, tint, lambda i, j: (i / n * sx / info[0], j / n * sz / info[0]), M, flip=(sgn > 0))

    # ---- annotations -----------------------------------------------------
    def col(self, size, pos=(0, 0, 0), rot=None, kind='box'):
        """Register a static collider (box: full size; cyl: size=(radius*2, height, radius*2))."""
        L = T(*pos)
        if rot is not None:
            L = L @ rot
        Mw = self.M @ L
        if Mw.to_3x3().determinant() < 0:
            Mw = Mw @ SC(-1, 1, 1)
        self.colliders.append({
            'kind': kind, 'size': [round(s, 4) for s in size],
            'xf': [round(Mw[r][c], 5) for r in range(3) for c in range(4)],
        })

    def mark(self, kind, pos=(0, 0, 0), **extra):
        p = self.M @ Vector(pos)
        d = {'pos': [round(p.x, 4), round(p.y, 4), round(p.z, 4)]}
        d.update(extra)
        self.marks.setdefault(kind, []).append(d)

    # ---- output ----------------------------------------------------------
    def build_objects(self):
        import numpy as np
        objs = []
        coll = bpy.context.scene.collection
        for (group, mat), g in sorted(self.geo.items()):
            if not g.f:
                continue
            name = "%s_%s" % (group, mat)
            me = bpy.data.meshes.new(name)
            me.from_pydata(g.v, [], g.f)
            uvl = me.uv_layers.new(name="UVMap")
            flat = np.array([c for fu in g.uv for uv in fu for c in uv], dtype=np.float32)
            uvl.data.foreach_set('uv', flat)
            ca = me.color_attributes.new("Col", 'FLOAT_COLOR', 'CORNER')
            fc = []
            for f, c in zip(g.f, g.col):
                fc.extend([c[0], c[1], c[2], 1.0] * len(f))
            ca.data.foreach_set('color', np.array(fc, dtype=np.float32))
            me.color_attributes.active_color = ca
            me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
            me.update()
            me.set_sharp_from_angle(angle=math.radians(50))
            m = bpy.data.materials.get('hall_' + mat) or bpy.data.materials.new('hall_' + mat)
            me.materials.append(m)
            ob = bpy.data.objects.new(name, me)
            coll.objects.link(ob)
            mod = ob.modifiers.new('wn', 'WEIGHTED_NORMAL')
            mod.keep_sharp = True; mod.weight = 60; mod.mode = 'FACE_AREA'
            bpy.context.view_layer.objects.active = ob
            ob.select_set(True)
            bpy.ops.object.modifier_apply(modifier='wn')
            ob.select_set(False)
            objs.append(ob)
        return objs
