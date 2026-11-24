"""Builds Rosalyn: sculpts every piece, bakes her dress and hair from the sculpt, exports GLB.

  blender --background --python build_rosalyn.py -- [--out rosalyn.glb] [--shots dir] [--detail 1.0] [--size 2048]
          [--clay a.png] [--only a,b] [--wire] [--views 0,-40,-90,180] [--zoom full|upper|head|face|hand|feet]

--clay alone renders the bare game mesh, for judging forms quickly. --out and --shots run the whole build.
--detail scales every lattice, and with it the triangle count: 1.0 fills the budget, 0.7 halves it.
Rest pose in Blender space: +X is her left, -Y is forward, +Z up. Unrigged.
"""
import sys, os, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sculpt import bl, build, pieces as P
from sculpt.bl import argv, opt
from sculpt.pieces import under, either, on_left
from sculpt.sdf import V
from sculpt.gen import Frame
from rosalyn import body, head

NAME = "rosalyn"                                # her working name: the files this build writes are called after it
BUDGET = 300000                                 # triangles at --detail 1.0
HEAD = body.HEAD


def in_head(f):
    return lambda p: f(HEAD.l(p))


def wrap_head(detail):
    v, q, n, lat = head.wrap(detail)
    return HEAD.w(v), q, HEAD.dir(n), lat


nothing = lambda v: np.zeros(len(v), dtype=bool)
SPECS = {
    "head": dict(mat="wood_face", mesh=wrap_head, field=in_head(head.field), mirror=False, hidden=under(body.chest, 0.0015)),
    "chest": dict(mat="wood", boxes=body.chest_boxes, field=body.chest, mirror=False,
                  hidden=either(under(in_head(head.field), 0.0015), under(on_left(body.arm), 0.0015))),
    "arm": dict(mat="wood", boxes=body.arm_boxes, field=body.arm, mirror=True, hidden=nothing),
    "leg": dict(mat="wood", boxes=body.leg_boxes, field=body.leg, mirror=True, hidden=nothing),
}

def carved(name, mat, made, frame, mirror=False):
    """A small part made by formula in `frame`, whose z is its wood's grain or its metal's brushing."""
    v, faces, *n = made
    return dict(name=name, mat=mat, v=frame.w(v), q=faces, n=frame.dir(n[0]) if n else None, mirror=mirror, grain=frame)


def small_parts():
    eye = Frame(HEAD.w(head.EYE * V(-1, 1, 1)), body.FWD, body.LEFT)
    return [carved("eye", "eye", head.eyeball(), eye, mirror=True)]


ZOOMS = {"full": ((0, 0, 0.93), 2.02, (520, 1000)), "upper": ((0, 0, 1.36), 1.05, (640, 640)),
         "head": ((0, -0.03, 1.635), 0.34, (600, 600)), "face": ((0, -0.03, 1.605), 0.19, (720, 720)),
         "hand": ((0.36, -0.06, 0.86), 0.30, (720, 720)), "feet": ((0, 0, 0.17), 0.60, (720, 720)),
         "eye": ((0.032, -0.08, 1.630), 0.055, (720, 720)), "mouth": ((0, -0.10, 1.570), 0.075, (720, 720))}


def turnaround(path, views, zoom, samples=40):
    """The knight's preview lighting and scale, so the two stand side by side."""
    target, scale, res = ZOOMS[zoom]
    dim = float(opt("--light", "1.0"))
    bl.turnaround(path, views, target, scale, res, bl.studio((2.6, 1.2, 2.4), (900 * dim, 220 * dim, 600 * dim)), samples)


def main():
    t0 = time.time()
    bl.reset_scene()
    detail = float(opt("--detail", "1.0"))
    names = opt("--only").split(",") if opt("--only") else list(SPECS)
    views = [float(a) for a in opt("--views", "0,-40,-90,180").split(",")]
    pieces = [P.sculpt(name, SPECS[name], detail) for name in names]
    for pc in pieces:
        pc["q"] = P.outward(pc["v"], pc["q"], pc["n"])
    pieces += small_parts()
    count = P.triangles(pieces)
    print("SCULPTED tris=%d  t=%.1fs" % (count, time.time() - t0))
    if opt("--clay"):
        build.clay_objects(pieces, "--wire" in argv, black=("eye",))
        for zoom in opt("--zoom", "full").split(","):
            turnaround(opt("--clay").replace(".png", "_%s.png" % zoom), views, zoom)
    print("DONE t=%.1fs" % (time.time() - t0))


main()
