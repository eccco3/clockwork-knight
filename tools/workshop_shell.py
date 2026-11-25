"""Workshop shell, built onto the hall's shared long wall: floor, walls, roof, trusses, and a closed
apartment in one back corner. A coarse first pass of plain timbers and slabs, to judge the space;
the doors between the rooms are part of the hall's wall (hall_shell)."""
import math
from hall_lib import *
import hall_shell as H
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
APT_WIDTH = WIDTH / 3       # apartment: across the workshop
APT_LENGTH = 2 * BAY        # apartment: along the workshop
APT_HEIGHT = EAVES          # apartment: top of its walls, where its lid lies
APT_SIDE = 1                # the long wall the apartment stands against: +1 or -1 in workshop x
APT_DOOR_W, APT_DOOR_H = 1.0, 2.2
LAMP_X = (-8.0, 0.0, 8.0)   # plain lamps under every tie beam, across the workshop
LAMP_DROP = 0.5             # below the tie beam
LAMP_ENERGY = 5.0
LAMP_RANGE = 9.0            # short of the hall, whose characters these lamps would light through the wall

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
    b.box((WIDTH + 2 * H.WT, 0.06, LENGTH + H.WT), 'wood_floor', pos=(0, -0.03, (LENGTH + H.WT) / 2), bevel=0, grain=2)
    b.col((WIDTH + 3, 1.0, LENGTH + 3), pos=(0, -0.5, LENGTH / 2))


def _gable(b, y0, thick):
    """End wall above y0 (wall-local), up into the roof boarding."""
    h = WIDTH / 2
    b.prism([(-h, y0), (h, y0), (h, SOFFIT), (0, APEX + 0.05), (-h, SOFFIT)], thick, 'plaster', bevel=0, M=T(0, 0, -thick / 2), uv='world')


def _walls(b):
    span = LENGTH + H.WT      # the long walls take the far corners
    for sx in (1, -1):
        with b.at(T(sx * WIDTH / 2, 0, span / 2) @ RY(-sx * PI / 2)):
            H.plaster_wall(b, span / 2, [], 0, SOFFIT)
            H.wall_col(b, span / 2)
            b.box((LENGTH, 0.25, POST), 'wood_beam', pos=(-sx * H.WT / 2, EAVES - 0.125, 0), bevel=0.015, grain=0, tint=_tint(b, 0.04))
    with b.at(T(0, 0, LENGTH) @ RY(PI)):
        H.plaster_wall(b, WIDTH / 2, [], 0, EAVES)
        _gable(b, EAVES, H.WT)
        H.wall_col(b, WIDTH / 2)
    # the hall's wall and its eaves filling close the near end below
    _gable(b, H.EH + H.EAVE_FILL - 0.01, H.WT / 2)


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
    """One frame across the workshop (x across, y up): wall posts, two posts carrying the tie beam,
    braces, queen struts and a king post under the principal rafters."""
    tie = 0.32
    b.box((WIDTH + 0.2, tie, 0.27), 'wood_beam', pos=(0, EAVES + tie / 2, 0), bevel=0.02, grain=0, tint=_tint(b))
    b.box((0.24, _under(0) - 0.4 - EAVES - tie, 0.24), 'wood_beam', pos=(0, (_under(0) - 0.4 + EAVES + tie) / 2, 0), bevel=0.018, grain=1, tint=_tint(b))
    for sx in (-1, 1):
        for x, deep in ((sx * (WIDTH / 2 - 0.17), 0.34), (sx * NAVE / 2, POST)):
            b.box((deep, EAVES, POST), 'wood_beam', pos=(x, EAVES / 2, 0), bevel=0.018, grain=1, tint=_tint(b))
            b.col((deep, EAVES, POST), pos=(x, EAVES / 2, 0))
        x = sx * NAVE / 2
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
    """A closed box in the far corner against the APT_SIDE wall. Its door faces the hall."""
    s = APT_SIDE
    xc = s * (WIDTH - APT_WIDTH) / 2
    x0 = s * (WIDTH / 2 - APT_WIDTH)
    z0 = LENGTH - APT_LENGTH
    with b.at(T(xc, 0, z0) @ RY(PI)):
        ow, oh = H.door_opening(APT_DOOR_W, APT_DOOR_H)
        H.plaster_wall(b, APT_WIDTH / 2, [(0, ow, 0, oh)], 0, APT_HEIGHT)
        H.doorway(b, APT_DOOR_W, APT_DOOR_H, 1)
        b.box((APT_WIDTH, 0.25, POST), 'wood_beam', pos=(0, APT_HEIGHT - 0.125, 0), bevel=0.015, grain=0, tint=_tint(b, 0.04))
    side = APT_LENGTH - H.WT      # the front wall takes the corner
    with b.at(T(x0, 0, z0 + H.WT + side / 2) @ RY(-s * PI / 2)):
        H.plaster_wall(b, side / 2, [], 0, APT_HEIGHT)
        b.box((side, 0.25, POST), 'wood_beam', pos=(0, APT_HEIGHT - 0.125, 0), bevel=0.015, grain=0, tint=_tint(b, 0.04))
    b.box((POST, APT_HEIGHT, POST), 'wood_beam', pos=(x0, APT_HEIGHT / 2, z0), bevel=0.018, grain=1, tint=_tint(b))
    b.box((APT_WIDTH, 0.2, APT_LENGTH), 'wood_roof', pos=(xc, APT_HEIGHT + 0.1, z0 + APT_LENGTH / 2), bevel=0, grain=2)
    b.col((APT_WIDTH, APT_HEIGHT + 0.2, APT_LENGTH), pos=(xc, (APT_HEIGHT + 0.2) / 2, z0 + APT_LENGTH / 2))


def _lamps(b):
    """Bare lights, no fittings yet, so the room and the characters in it can be seen."""
    for z in _stations():
        for x in LAMP_X:
            b.mark('light', (x, EAVES - LAMP_DROP, z), name='WorkshopLamp', color=WARM, energy=LAMP_ENERGY, range=LAMP_RANGE,
                   shadow=False, size=0.3, fog=0.0, lights_characters=True)


def build_workshop(b):
    with b.grp('workshop'), b.at(FRAME):
        _floor(b)
        _walls(b)
        _roof(b)
        _trusses(b)
        _apartment(b)
        _lamps(b)
