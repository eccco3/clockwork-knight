"""The minion's short spear: a turned shaft about his own height, shod and socketed in brass, with a leaf blade
of steel. It stands upright through the hollow of his right fist, its butt on the ground."""
from sculpt import gen
from sculpt.sdf import V
from sculpt.gen import Frame
from . import body
from .body import part

LENGTH = 1.215
SHAFT = 0.0095


def parts():
    axis = Frame(body.GRIP * V(1, 1, 0), body.UP, body.LEFT)
    return [
        part("spear_shoe", "brass", gen.lathe([(0.0, 0.0), (0.001, 0.0075), (0.008, 0.0110), (0.034, 0.0114), (0.038, 0.0098),
                                               (0.038, 0.0)], 8), axis),
        part("spear_shaft", "wood", gen.lathe([(0.030, 0.0), (0.030, SHAFT), (1.020, SHAFT * 0.92), (1.020, 0.0)], 8), axis),
        part("spear_socket", "brass", gen.lathe([(1.000, 0.0), (1.000, 0.0118), (1.006, 0.0130), (1.012, 0.0118), (1.050, 0.0085),
                                                 (1.056, 0.0)], 8), axis),
        part("spear_blade", "steel", gen.lathe([(1.045, 0.0), (1.046, 0.0070), (1.066, 0.0150), (1.095, 0.0185), (1.135, 0.0150),
                                                (1.180, 0.0080), (LENGTH, 0.0)], 4, sy=0.2), axis, sharp=25.0),
    ]
