"""Her brass: a wire choker with a small gear at the throat, the winding key between her shoulder blades,
a gear clasp on the sash and a buckle on each slipper. Made by formula and set on the sculpted surfaces.
"""
import numpy as np
from sculpt import sdf as S, gen
from sculpt.sdf import V
from sculpt.gen import Frame
from . import body, dress
from .body import UP, FWD, BACK, LEFT

KEY_Z = 1.392


def _on(field, origin, toward):
    """The point where the ray from `origin` (inside) toward `toward` leaves `field`."""
    return S.hug(field, origin, S.normalize(toward), UP, 1, 0.0, 0.0, off=0.0)[0]


def parts():
    """Every part as a piece: world-space verts and faces, the frame its brushing runs in, the bone it rides,
    and its thickness if it is a plate."""
    out = []

    def add(name, bone, made, frame, mirror=False, thickness=0.0):
        out.append(dict(name=name, mat="brass", v=frame.w(made[0]), q=made[1], n=None, grain=frame, mirror=mirror,
                        thickness=thickness, bone=bone))

    here = Frame(V(0, 0, 0), UP, LEFT)
    side = S.normalize(np.cross(body.NECK_DIR, LEFT))
    ring = S.hug(body.torso, body.CHOKER, LEFT, side, 72, 0.0, 2 * np.pi * 71 / 72, off=0.0004)
    add("choker", "head", gen.tube(ring, 0.0023, 10, closed=True), here)
    throat = Frame(_on(body.torso, body.CHOKER, -side) - body.NECK_DIR * 0.0105 + FWD * 0.0012, FWD, LEFT)
    add("choker_gear", "head", gen.gear(10, 0.0058, 0.0074, r_hole=0.0016), throat, thickness=-0.0020)
    add("choker_boss", "head", gen.dome(0.0024, 0.0018, 10, 2), Frame(throat.w((0, 0, 0.0008)), FWD, LEFT))

    spine = Frame(_on(body.torso, V(0, 0.02, KEY_Z), BACK) - BACK * 0.002, BACK, LEFT)
    add("key_plate", "chest", gen.lathe_ring([(0.0, 0.008), (0.0, 0.0135), (0.0026, 0.0143), (0.0046, 0.0122), (0.0046, 0.008)], 24), spine)
    add("key_shaft", "chest", gen.lathe([(0.0, 0.0), (0.0, 0.0085), (0.0035, 0.0085), (0.0052, 0.0040), (0.030, 0.0034),
                                (0.0335, 0.0050), (0.036, 0.0034), (0.036, 0.0)], 16), spine)
    add("key_neck", "chest", gen.box((0.0048, 0.0018, 0.0065)), Frame(spine.w((0, 0, 0.0395)), BACK, LEFT))
    for sx in (1, -1):
        bow = Frame(spine.w((sx * 0.0150, 0, 0.0465)), spine.dir((0, 1, 0)), spine.dir((1, 0, 0)))
        add("key_bow_%d" % sx, "chest", gen.lathe_ring([(-0.0018, 0.0086), (-0.0018, 0.0134), (0.0, 0.0145), (0.0018, 0.0134),
                                               (0.0018, 0.0086), (0.0, 0.0078)], 24), bow)

    waist = 0.5 * (dress.SASH[0] + dress.SASH[1])
    clasp = Frame(_on(dress.cloth, V(0, 0.008, waist), FWD), FWD, LEFT)
    add("clasp", "spine", gen.gear(14, 0.0150, 0.0182, r_hole=0.0045, spokes=5), Frame(clasp.w((0, 0, 0.0030)), FWD, LEFT), thickness=-0.0035)
    add("clasp_boss", "spine", gen.dome(0.0058, 0.0040, 12, 3), Frame(clasp.w((0, 0, 0.0030)), FWD, LEFT))

    vamp = body.from_foot(_on(lambda l: body.shoe(body.from_foot(l)), V(0, 0.092, 0.012), UP))[0]
    toes = body.from_foot((0, 1, 0))[0] - body.from_foot((0, 0, 0))[0]
    add("buckle", "foot", gen.lathe_ring([(0.0, 0.0050), (0.0, 0.0078), (0.0016, 0.0082), (0.0028, 0.0070), (0.0028, 0.0050)], 4,
                                 sx=1.25), Frame(vamp - UP * 0.0006, UP + toes * 0.25, toes), mirror=True)
    return out
