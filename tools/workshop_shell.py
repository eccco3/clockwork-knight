"""Workshop shell, built onto the hall's shared long wall: a boarded floor, plastered walls framed
and panelled like the hall's, windows along both long walls onto the same foggy day, roof, trusses,
and a closed apartment in one back corner, framed and panelled outside. The doors between the rooms
are part of the hall's wall (hall_shell). Its boards, panelling and stone are the hall's materials,
worn where a craftsman works (WORK)."""
import math
import numpy as np
from hall_lib import *
import hall_shell as H
import hall_tex
from hall_props import WARM

BAY = 6.0                   # truss spacing along the length
WIDTH = 2 * H.HL            # across: the hall's length
LENGTH = 9 * BAY            # away from the hall
EAVES = H.EH                # top of the side walls
APEX = H.APEX               # underside of the roof boarding at the ridge
SOFFIT = EAVES + 0.25       # underside of the roof boarding above the inner wall face
NAVE = WIDTH / 2            # between the two rows of posts that carry the trusses
POST = 0.30                 # post section
PURLINS = (0.25, 0.5, 0.75)   # along each slope, as fractions of it
WINDOWS = [BAY / 4 + k * BAY / 2 for k in range(2 * round(LENGTH / BAY))]   # along both long walls (z): two a bay
APT_WIDTH = WIDTH / 3       # apartment: across the workshop
APT_LENGTH = 2 * BAY        # apartment: along the workshop
APT_HEIGHT = EAVES          # apartment: top of its walls, where its lid lies
APT_SIDE = 1                # the long wall the apartment stands against: +1 or -1 in workshop x
APT_DOOR_W, APT_DOOR_H = 1.0, 2.2
LAMP_X = (-8.0, 0.0, 8.0)   # plain lamps under every tie beam, across the workshop
LAMP_DROP = 0.5             # below the tie beam
LAMP_ENERGY = 5.0
LAMP_RANGE = 9.0            # short of the hall, whose characters these lamps would light through the wall
# where a craftsman stands at work (x, z): feet pale the boards there and on the ways to it from the
# middle, and grime darkens them under the bench beyond
WORK = [(-10.9, 4.5), (-10.9, 13.5), (-10.9, 25.5), (-10.9, 37.5), (10.9, 7.5), (10.9, 19.5), (10.9, 31.5), (-3.0, 46.0)]
WEAR = 'workshop_wear'      # the wear map, assets/textures/hall_gen/<WEAR>.png
WEAR_PX = 16                # its pixels a metre

# workshop frame: the origin lies on the floor at the middle of the shared wall's workshop face,
# x runs across (-WIDTH/2 .. WIDTH/2) and z along, away from the hall (0 .. LENGTH)
FRAME = H.WALLS[H.SHARED] @ T(0, 0, -H.WT) @ RY(PI)
PITCH = math.atan2(APEX - SOFFIT, WIDTH / 2)


def _tint(b, amount=0.09):
    return b.vary(H.BEAM, amount)


def _stations():
    """Where the trusses stand along the length."""
    n = round(LENGTH / BAY)
    return [k * LENGTH / n for k in range(1, n)]


def _under(x):
    """Height of the roof boarding's underside at workshop x."""
    return APEX - math.tan(PITCH) * abs(x)


def _floor(b):
    with b.ns():
        H.boards(b, -WIDTH / 2 - 0.25, WIDTH / 2 + 0.25, 0.0, LENGTH + 0.25)
    b.col((WIDTH + 3, 1.0, LENGTH + 3), pos=(0, -0.5, LENGTH / 2))


def _gable(b, y0, thick):
    """End wall above y0 (wall-local), up into the roof boarding."""
    h = WIDTH / 2
    b.prism([(-h, y0), (h, y0), (h, SOFFIT), (0, APEX + 0.05), (-h, SOFFIT)], thick, 'plaster', bevel=0, M=T(0, 0, -thick / 2), uv='world')


def _corners():
    """Wall-local posts at the ends of an end wall, against the long walls."""
    return [POST / 2 - WIDTH / 2, WIDTH / 2 - POST / 2]


def _near_wall(b):
    """The workshop face of the hall's shared wall, around the doors between the rooms, and the
    gable above it."""
    ow, _ = H.door_opening(H.WS_DOOR_W, H.WS_DOOR_H)
    H.dress(b, -WIDTH / 2, WIDTH / 2, _corners() + [-z for z in H.TRUSS_Z], doors=[(-H.WS_DOOR_U, ow)])
    # the hall's wall and its eaves filling close the end below
    _gable(b, H.EH + H.EAVE_FILL - 0.01, H.WT / 2)
    H.gable_frame(b, WIDTH / 2, PITCH)


def _long_walls(b):
    for sx in (1, -1):
        # wall-local, mirrored on -x so that u runs along the workshop (z) on both
        with b.at(T(sx * WIDTH / 2, 0, 0) @ RY(-sx * PI / 2) @ SC(sx, 1, 1)):
            end = LENGTH - (APT_LENGTH if sx == APT_SIDE else 0)   # the apartment hides the rest
            wins = [z for z in WINDOWS if z + H.WWID / 2 < end]
            H.plaster_wall(b, 0, LENGTH + H.WT, [(z, H.WWID, H.WSILL, H.WHEAD) for z in wins], SOFFIT)
            H.dress(b, 0, end, [z for z in _stations() if z < end], wins)
            H.wall_col(b, 0, LENGTH + H.WT)


def _far_wall(b):
    # wall-local, mirrored for an apartment on -x so that it stands at u < 0
    with b.at(SC(APT_SIDE, 1, 1) @ T(0, 0, LENGTH) @ RY(PI)):
        H.plaster_wall(b, -WIDTH / 2, WIDTH / 2, [], EAVES)
        _gable(b, EAVES, H.WT)
        H.gable_frame(b, WIDTH / 2, PITCH)
        a = APT_WIDTH - WIDTH / 2
        H.dress(b, a, WIDTH / 2, [u for u in (-NAVE / 2, 0.0, NAVE / 2) if u > a] + _corners()[1:])
        H.wall_col(b, -WIDTH / 2, WIDTH / 2)


def _roof(b):
    ca = math.cos(PITCH)
    z0, z1 = -H.WT / 2, LENGTH + H.WT + H.EAVE_OUT
    sl = (WIDTH / 2 + H.WT + H.EAVE_OUT) / ca
    rl = WIDTH / 2 / ca
    for sx in (1, -1):
        # slope frame: origin at the apex, +X runs down the slope, +Y is the outward normal
        with b.at(SC(sx, 1, 1) @ T(0, APEX, 0) @ RZ(-PITCH)):
            b.box((sl, H.ROOF_T, z1 - z0), 'wood_roof', pos=(sl / 2, H.ROOF_T / 2, (z0 + z1) / 2), bevel=0, grain=2)
            for f in PURLINS:
                b.box((0.2, 0.2, LENGTH), 'wood_beam', pos=(rl * f, -0.1, LENGTH / 2), bevel=0.014, grain=2, tint=_tint(b, 0.05))
            for z in _stations():
                b.box((rl - 0.12, 0.3, 0.24), 'wood_beam', pos=(0.12 + (rl - 0.12) / 2, -0.35, z), bevel=0.018, grain=0, tint=_tint(b))
        with b.at(T(0, APEX, 0) @ RZ(-PITCH if sx > 0 else PI + PITCH)):
            b.col((sl, H.ROOF_T, z1 - z0), pos=(sl / 2, sx * H.ROOF_T / 2, (z0 + z1) / 2))
    b.box((0.2, 0.28, LENGTH), 'wood_beam', pos=(0, APEX - 0.3, LENGTH / 2), bevel=0.014, grain=2, tint=_tint(b, 0.05))


def _truss(b):
    """One frame across the workshop (x across, y up): a tie beam on the long walls' posts and two
    posts on stone pads, braces, queen struts and a king post under the principal rafters."""
    tie = 0.32
    b.box((WIDTH + 0.2, tie, 0.27), 'wood_beam', pos=(0, EAVES + tie / 2, 0), bevel=0.02, grain=0, tint=_tint(b))
    b.box((0.24, _under(0) - 0.4 - EAVES - tie, 0.24), 'wood_beam', pos=(0, (_under(0) - 0.4 + EAVES + tie) / 2, 0), bevel=0.018, grain=1, tint=_tint(b))
    for sx in (-1, 1):
        x = sx * NAVE / 2
        b.box((POST, EAVES - H.PLINTH, POST), 'wood_beam', pos=(x, (EAVES + H.PLINTH) / 2, 0), bevel=0.018, grain=1, tint=_tint(b))
        b.box((0.42, H.PLINTH, 0.42), 'stone', pos=(x, H.PLINTH / 2, 0), bevel=0.02, tint=b.vary((0.9, 0.88, 0.86), 0.1))
        b.col((POST, EAVES, POST), pos=(x, EAVES / 2, 0))
        top = _under(x) - 0.5 / math.cos(PITCH)
        b.box((0.2, top - EAVES - tie + 0.05, 0.2), 'wood_beam', pos=(x, (top + 0.05 + EAVES + tie) / 2, 0), bevel=0.014, grain=1, tint=_tint(b))
        for side in (-1, 1):
            b.beam((x + side * 0.1, EAVES - 1.3, 0), (x + side * 1.3, EAVES - 0.1, 0), 0.2, 0.2, 'wood_beam', bevel=0.014, tint=_tint(b))


def _trusses(b):
    for z in _stations():
        with b.at(T(0, 0, z)):
            _truss(b)
    # plates along the tops of the two rows of posts
    for sx in (-1, 1):
        b.box((POST, POST, LENGTH), 'wood_beam', pos=(sx * NAVE / 2, EAVES - POST / 2, LENGTH / 2), bevel=0.015, grain=2, tint=_tint(b, 0.04))


def _apartment(b):
    """A closed box in the far corner against the APT_SIDE wall, framed and panelled outside. Its
    door faces the hall."""
    z0 = LENGTH - APT_LENGTH
    x0 = WIDTH / 2 - APT_WIDTH      # its side wall's face, mirrored onto -x for an apartment there
    ow, oh = H.door_opening(APT_DOOR_W, APT_DOOR_H)
    jamb = ow / 2 + POST / 2
    with b.at(SC(APT_SIDE, 1, 1)):
        # front wall: u runs from the long wall to the free corner
        with b.at(T(x0 + APT_WIDTH / 2, 0, z0) @ RY(PI)):
            a, c = -APT_WIDTH / 2, APT_WIDTH / 2
            H.plaster_wall(b, a, c, [(0, ow, 0, oh)], APT_HEIGHT)
            H.dress(b, a, c, [a + POST / 2, -jamb, jamb, c], doors=[(0, ow)])
            H.doorway(b, APT_DOOR_W, APT_DOOR_H, 1)
            H.door_head(b, APT_DOOR_W, APT_DOOR_H, H.GEARS, faces=(1,))
        # side wall: u runs along the workshop (z); the front wall's corner post covers its end
        with b.at(T(x0, 0, 0) @ RY(-PI / 2)):
            H.plaster_wall(b, z0 + H.WT, LENGTH, [], APT_HEIGHT)
            H.dress(b, z0, LENGTH, [z for z in _stations() if z > z0] + [LENGTH - POST / 2])
        xc, zc = x0 + APT_WIDTH / 2, z0 + APT_LENGTH / 2
        b.box((APT_WIDTH, 0.2, APT_LENGTH), 'wood_roof', pos=(xc, APT_HEIGHT + 0.1, zc), bevel=0, grain=2)
        b.col((APT_WIDTH, APT_HEIGHT + 0.2, APT_LENGTH), pos=(xc, (APT_HEIGHT + 0.2) / 2, zc))


def _lamps(b):
    """Bare lights, no fittings yet, so the room and the characters in it can be seen."""
    for z in _stations():
        for x in LAMP_X:
            b.mark('light', (x, EAVES - LAMP_DROP, z), name='WorkshopLamp', color=WARM, energy=LAMP_ENERGY, range=LAMP_RANGE,
                   shadow=False, size=0.3, fog=0.0, lights_characters=True)


def _ways():
    """Where feet go: from the hall's doors down the middle to the apartment's door, and from the
    middle across to each work spot."""
    door = (APT_SIDE * (WIDTH - APT_WIDTH) / 2, LENGTH - APT_LENGTH)
    return [[(-H.WS_DOOR_U, 0.0), (0.0, door[1] - 2.0), door]] + [[(0.0, max(z - 3.0, 0.0)), (x, z)] for x, z in WORK]


def _reach(x, z, a, c):
    """Distance from points (x, z) to the segment a..c."""
    dx, dz = c[0] - a[0], c[1] - a[1]
    t = np.clip(((x - a[0]) * dx + (z - a[1]) * dz) / max(dx * dx + dz * dz, 1e-9), 0, 1)
    return np.hypot(x - a[0] - t * dx, z - a[1] - t * dz)


def _wear(b):
    """The wear map over the floor plan, in world x (columns) and z (rows, top first): red where
    feet pale the boards, green where grime darkens them. builders/hall_materials.gd gives it to the
    worn materials through its mark."""
    (x0, _, z0), (sx, _, sz) = b.world_box((-WIDTH / 2, 0, 0), (WIDTH / 2, 0, LENGTH))
    w, h = round(sx * WEAR_PX), round(sz * WEAR_PX)
    X, Z = np.meshgrid(x0 + (np.arange(w) + 0.5) * sx / w, z0 + (np.arange(h) + 0.5) * sz / h)
    inv = b.M.inverted()
    x = inv[0][0] * X + inv[0][2] * Z + inv[0][3]       # each pixel in workshop x, z
    z = inv[2][0] * X + inv[2][2] * Z + inv[2][3]
    wobble = hall_tex.fbm(h, w, (round(sz / 2), round(sx / 2)), 4, 5) - 0.5
    speck = hall_tex.ss(0.6, 0.75, hall_tex.fbm(h, w, (round(sz * 3), round(sx * 3)), 3, 9))
    feet = np.zeros_like(x)
    for way in _ways():
        for a, c in zip(way, way[1:]):
            feet = np.maximum(feet, (0.3 + 0.4 * wobble) * (1 - hall_tex.ss(0.0, 1.4, _reach(x, z, a, c) + 0.8 * wobble)))
    grime = 0.3 * (1 - hall_tex.ss(0.0, 0.45, np.minimum(np.minimum(WIDTH / 2 - np.abs(x), z), LENGTH - z) + 0.3 * wobble))
    for wx, wz in WORK:
        feet = np.maximum(feet, 1 - hall_tex.ss(0.1, 1.0, np.hypot(x - wx, z - wz) + 0.5 * wobble))
        # under the bench beyond, spread along it
        d = np.hypot(x - wx - math.copysign(0.9, wx), 0.6 * (z - wz)) + wobble
        grime = np.maximum(grime, (1 - hall_tex.ss(0.2, 1.6, d)) * (0.5 + 0.5 * speck))
    img = np.stack([feet, grime, np.zeros_like(x)], -1)
    hall_tex.save(WEAR, img[::-1])
    b.mark('wear', rect=[x0, z0, sx, sz], image='res://assets/textures/hall_gen/%s.png' % WEAR)


def build_workshop(b):
    with b.grp('workshop'), b.at(FRAME), b.variant('worn'):
        _floor(b)
        _near_wall(b)
        _long_walls(b)
        _far_wall(b)
        _roof(b)
        _trusses(b)
        _apartment(b)
        _lamps(b)
        H.probe(b, -WIDTH / 2, WIDTH / 2, 0, LENGTH)
        _wear(b)
