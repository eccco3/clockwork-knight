"""The minion's short spear: a turned shaft about his own height, shod and socketed in brass, with a leaf blade
of steel. It stands upright through the hollow of his right fist, its butt on the ground."""
from sculpt import gen
from sculpt.sdf import V
from sculpt.gen import Frame
from . import body
from .body import part

LENGTH = 1.215
SHAFT = 0.0095
# The leaf's outline, rounded through enough rings that its flats run smooth from socket to point. Its section is a
# flat diamond, whose faces meet across the midrib at 23 degrees: `sharp` creases there and at the edges only.
BLADE = [(1.045, 0.0), (1.046, 0.0070), (1.056, 0.0118), (1.066, 0.0150), (1.078, 0.0174), (1.090, 0.0185), (1.103, 0.0183),
         (1.118, 0.0170), (1.135, 0.0148), (1.152, 0.0122), (1.168, 0.0094), (1.183, 0.0064), (1.198, 0.0034), (LENGTH, 0.0)]


def parts():
    axis = Frame(body.GRIP * V(1, 1, 0), body.UP, body.LEFT)
    return [
        part("spear_shoe", "brass", gen.lathe([(0.0, 0.0), (0.001, 0.0075), (0.008, 0.0110), (0.034, 0.0114), (0.038, 0.0098),
                                               (0.038, 0.0)], 8), axis),
        part("spear_shaft", "wood", gen.lathe([(0.030, 0.0), (0.030, SHAFT), (1.020, SHAFT * 0.92), (1.020, 0.0)], 8), axis),
        part("spear_socket", "brass", gen.lathe([(1.000, 0.0), (1.000, 0.0118), (1.006, 0.0130), (1.012, 0.0118), (1.050, 0.0085),
                                                 (1.056, 0.0)], 8), axis),
        part("spear_blade", "steel", gen.lathe(BLADE, 4, sy=0.2), axis, sharp=15.0),
    ]
