"""Pieces: the parts a textured figure is sculpted in, each a dict.

A sculpted piece's spec gives mat, mirror, boost, hidden (points -> bool, culled from the game mesh), field,
detail and paint for the bake (and normals, if its detail is a mesh), seam for the unwrap, and how to mesh it:
boxes (a polycube for lattice.fit, with an optional pin) or mesh (sub -> verts, quads, normals, lattice
points). `sculpt` adds name, v, q, n, lat and sub. A small part made by formula carries v, q, n, chart, size
and paint instead.
"""
import time
import numpy as np
from . import sdf as S, lattice

MIRROR = np.array([-1.0, 1.0, 1.0])


def under(field, depth):
    return lambda v: field(v) < -depth


def either(*tests):
    return lambda v: np.any([t(v) for t in tests], axis=0)


def on_left(field):
    return lambda v: field(S.mirror_x(v))


def sculpt(name, spec, sub=1):
    t0 = time.time()
    if "mesh" in spec:
        v, q, n, lat = spec["mesh"](sub)
    else:
        pin = (lambda c: spec["pin"](c, sub)) if "pin" in spec else None
        v, q, n, lat = lattice.fit(spec["field"], spec["boxes"](sub), relax=40, pin=pin)
    total = len(q)
    v, q, n, lat = lattice.cull(v, q, spec["hidden"](v), (n, lat))
    a, b, c = v[q[:, 0]], v[q[:, 1]], v[q[:, 2]]
    flipped = int(((np.cross(b - a, c - a) * n[q[:, 0]]).sum(-1) < 0).sum())
    el = lattice.edges_of(q)
    el = S.length(v[el[:, 0]] - v[el[:, 1]])
    print("PIECE %-7s quads=%d of %d  flipped=%d  edge %.1f..%.1f mm (median %.1f)  t=%.1fs" % (
        name, len(q), total, flipped, el.min() * 1e3, el.max() * 1e3, np.median(el) * 1e3, time.time() - t0))
    return dict(spec, name=name, v=v, q=q, n=n, lat=lat, sub=sub)


def outward(v, faces, n):
    """Faces as tuples, each wound to face the way its normals point."""
    out = []
    for f in faces:
        f = tuple(int(i) for i in dict.fromkeys(f))
        a, b, c = v[f[0]], v[f[1]], v[f[2]]
        out.append(f if np.cross(b - a, c - a) @ n[list(f)].sum(0) >= 0 else f[::-1])
    return out


def sides(pc):
    """The piece's instances: (verts, faces, normals) for itself and, if paired, its mirror image."""
    yield pc["v"], pc["q"], pc["n"]
    if pc["mirror"]:
        yield pc["v"] * MIRROR, [f[::-1] for f in pc["q"]], None if pc["n"] is None else pc["n"] * MIRROR


def triangles(pieces):
    return sum(sum(len(f) - 2 for f in pc["q"]) * (2 if pc["mirror"] else 1) for pc in pieces)


def occluder(pieces):
    """Everything that can shade a surface point: the nearest of the broad sculpts."""
    solids = [(pc["field"], pc["v"].min(0) - 0.08, pc["v"].max(0) + 0.08, pc["mirror"]) for pc in pieces if "field" in pc]

    def f(p):
        d = np.full(len(p), 1.0)
        for field, lo, hi, paired in solids:
            x = S.mirror_x(p) if paired else p
            m = np.all((x > lo) & (x < hi), axis=1)
            if m.any():
                d[m] = np.minimum(d[m], field(x[m]))
        return d
    return f
