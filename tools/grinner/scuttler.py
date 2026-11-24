"""The scuttler: the grinner that goes on all fours. Its crouch, its looping clips and its moves, keyed by hand on
the controls of `pose`, and the poses that test its skin.

It is the walking grinner's own body dropped onto its hands, which stay planted as its feet do: every clip puts
them where they should stand. It stands on its toes and finger pads, gallops at 5.1 m/s, a little faster than the
knight runs, and bites with a jaw that swings open. A move is a function of the seconds since it began; until
its first mark an attack is winding up, and both wind-ups keep hands and feet where it stands, as the flinch
begins, so a flinch can cut in at any moment of either.
"""
import numpy as np
from .body import FINGERS
from .keys import Curve, Kind, held, at, glide, thrown, trod, sided, both, borne, twice

HEEL, PALM = 52.0, 0.0                          # how far the heel is carried off the ground at rest, and the palm's heel
ARCHED = 22.0                                   # the fingers bent back from the palm, which sets their claws on the ground
_LIMB = dict(planted=1.0, hand_x=0.06, hand_y=-0.27, hand_yaw=22.0, elbow_out=28.0, thumb_in=-10.0,
             foot_x=0.05, foot_y=0.25, foot_yaw=14.0, knee=8.0)
CROUCH = dict(sided(_LIMB, dict(_LIMB, hand_y=-0.23, hand_yaw=30.0, foot_y=0.28, foot_yaw=18.0)),
              hips_y=0.17, hips_z=-0.15, hips_pitch=74.0, spine_pitch=8.0, chest_pitch=8.0, head_level=0.9,
              neck_roll=3.0, head_roll=6.0, head_pitch=4.0)


def _crouched(controls):
    return borne(controls, CROUCH)


def _foot(pitch, lift=0.0, **more):
    """A foot on its toes: `pitch` carries the heel, and the toes lie flat while it is on the ground."""
    return dict(more, foot_pitch=pitch, foot_z=lift, toe=max(pitch, 0.0) * float(np.clip(1.0 - lift / 0.05, 0.0, 1.0)))


def _hand(pitch, lift=0.0, hooked=0.15, splayed=0.6, **more):
    """A hand on its finger pads: `pitch` carries the heel of the palm, and the fingers lie flat while it is on
    the ground. `hooked` closes the claws and `splayed` fans them."""
    down = float(np.clip(1.0 - lift / 0.05, 0.0, 1.0))
    out = {"curl_" + name: 46.0 * hooked - 6.0 * splayed for name in FINGERS}
    out.update(more, hand_pitch=pitch, hand_z=lift, knuckle=(ARCHED + max(pitch, 0.0)) * down,
               spread=4.0 * hooked + 13.0 * splayed, thumb_curl=30.0 * hooked - 30.0 * down, thumb_in=-12.0 * splayed)
    return out


def _back(pitch, flex):
    """The trunk tipped nose down by `pitch` and its back rounded by `flex`, about the middle of the spine."""
    return dict(hips_pitch=pitch - flex, spine_pitch=flex, chest_pitch=flex)


def _add(out, more):
    for name, value in more.items():
        out[name] = out.get(name, 0.0) + value
    return out


# ---------------------------------------------------------------- run

STRIDE, GALLOP = 2.4, 14                        # metres and frames in one cycle
HIND, FORE = 0.30, 0.28                         # the share of the cycle each foot, and each hand, is down
LANDS = dict(foot_l=0.00, foot_r=0.07, hand_l=0.43, hand_r=0.53)
FOOT_REACH, HAND_REACH = -0.34, -0.29           # where they land, from where they stand at rest: ahead is negative
SWUNG = Curve((0.0, 0.0), (0.30, 0.22), (0.62, 0.72), (0.88, 1.05), (1.0, 1.0), loop=False)
THROWN = Curve((0.0, 0.0), (0.25, 0.14), (0.60, 0.70), (0.86, 1.06), (1.0, 1.0), loop=False)
PAD = dict(pitch=Curve((0.00, 38.0), (0.10, 26.0), (HIND - 0.07, 48.0), (HIND, 84.0), (0.42, 100.0), (0.62, 70.0), (0.85, 30.0)),
           lift=Curve((0.00, 0.0), (HIND, 0.0), (0.42, 0.13), (0.60, 0.26), (0.80, 0.17), (0.95, 0.03)),
           foot_x=Curve((0.00, 0.02), (HIND, 0.02), (0.65, 0.10), (0.90, 0.05)),
           knee=Curve((0.00, 6.0), (HIND, 2.0), (0.60, 26.0), (0.90, 12.0)),
           foot_yaw=Curve((0.00, 2.0), (HIND, -4.0), (0.70, 8.0)))
PAW = dict(pitch=Curve((0.00, -4.0), (0.06, 2.0), (0.16, 8.0), (FORE - 0.04, 44.0), (FORE, 62.0), (0.36, 78.0), (0.47, 100.0),
                       (0.60, 95.0), (0.80, 45.0), (0.93, -14.0)),
           lift=Curve((0.00, 0.0), (FORE, 0.0), (0.34, 0.10), (0.43, 0.18), (0.62, 0.23), (0.85, 0.12), (0.96, 0.03)),
           hooked=Curve((0.00, 0.10), (FORE, 0.20), (0.45, 1.0), (0.75, 0.6), (0.93, 0.0)),
           splayed=Curve((0.00, 1.0), (FORE, 0.5), (0.50, 0.0), (0.80, 0.4), (0.93, 1.1)),
           elbow_out=Curve((0.00, 0.0), (FORE, -6.0), (0.55, 16.0)),
           shoulder_up=Curve((0.00, 12.0), (FORE, -8.0), (0.60, -2.0), (0.90, 14.0)),
           hand_yaw=Curve((0.00, 0.0), (FORE, -8.0), (0.60, -14.0), (0.93, 4.0)))
BOUND = dict(hips_z=Curve((0.00, 0.0), (0.15, -0.035), (0.38, 0.025), (0.55, 0.04), (0.72, 0.03), (0.90, 0.02)),
             hips_y=Curve((0.15, 0.02), (0.40, -0.02), (0.62, -0.01), (0.86, 0.03)),
             hips_roll=Curve((0.03, -2.5), (0.14, 2.5), (0.36, 0.0), (0.80, 0.0)),
             hips_yaw=Curve((0.03, 3.0), (0.20, -2.0), (0.48, -3.0), (0.62, 2.0)),
             chest_roll=Curve((0.44, 3.5), (0.58, -3.5), (0.80, 0.0), (0.30, 0.0)),
             chest_yaw=Curve((0.44, 4.0), (0.60, -3.0), (0.84, 0.0), (0.30, 0.0)),
             head_pitch=Curve((0.14, -3.0), (0.55, 4.0)),
             head_roll=Curve((0.20, 1.5), (0.70, -1.5)),
             jaw=Curve((0.10, 3.0), (0.40, 11.0), (0.60, 7.0), (0.90, 2.0)))
BOUND_PITCH = Curve((0.11, -8.0), (0.48, 15.0), (0.70, 9.0), (0.88, 1.0))
BOUND_FLEX = Curve((0.00, 15.0), (0.16, 6.0), (0.37, -13.0), (0.52, -9.0), (0.68, 4.0), (0.86, 18.0))


def _swept(since, down, reach, swung):
    """Where a hand or foot is along the body, `since` its landing as a share of the cycle: swept back with the
    ground while it is down, then swung forward to land again."""
    if since < down:
        return reach + STRIDE * since
    return reach + STRIDE * down * (1.0 - swung((since - down) / (1.0 - down)))


def _pad(phase):
    since = phase % 1.0
    c = at(PAD, since)
    return _foot(c.pop("pitch"), c.pop("lift"), foot_y=_swept(since, HIND, FOOT_REACH, SWUNG), **c)


def _paw(phase):
    since = phase % 1.0
    c = at(PAW, since)
    return _hand(c.pop("pitch"), c.pop("lift"), c.pop("hooked"), c.pop("splayed"), hand_y=_swept(since, FORE, HAND_REACH, THROWN), **c)


def run(phase):
    """A gallop: the feet land one just after the other and drive the back straight, the hands reach out, land
    in turn and pull the body over them, and the back rounds to swing the feet in past the hands."""
    out = at(BOUND, phase)
    out.update(_back(BOUND_PITCH(phase), BOUND_FLEX(phase)), travel=STRIDE * phase)
    out.update(sided(dict(_pad(phase - LANDS["foot_l"]), **_paw(phase - LANDS["hand_l"])),
                     dict(_pad(phase - LANDS["foot_r"]), **_paw(phase - LANDS["hand_r"]))))
    return _crouched(out)


# ---------------------------------------------------------------- idle

BREATH = twice((0.02, 0.0), (0.20, 1.0), (0.27, 0.9))
WATCH = dict(hips_x=Curve((0.10, 0.018), (0.42, 0.020), (0.60, -0.014), (0.92, -0.016)),
             hips_roll=Curve((0.12, 2.0), (0.44, 2.4), (0.62, -1.6), (0.94, -1.8)),
             hips_yaw=Curve((0.14, -2.0), (0.64, 2.0)),
             chest_yaw=Curve((0.18, 3.0), (0.50, 2.0), (0.68, -3.0), (0.95, -2.0)),
             head_roll=Curve((0.00, -2.0), (0.22, -1.0), (0.26, -16.0), (0.30, -14.0), (0.52, -13.0), (0.57, 9.0), (0.61, 7.0),
                             (0.86, 6.0), (0.94, -2.0)),
             head_yaw=Curve((0.00, 0.0), (0.22, 2.0), (0.26, 14.0), (0.31, 12.0), (0.52, 11.0), (0.57, -18.0), (0.62, -16.0),
                            (0.86, -15.0), (0.94, 0.0)),
             head_pitch=Curve((0.00, 0.0), (0.22, 1.0), (0.27, -6.0), (0.52, -5.0), (0.58, 3.0), (0.86, 2.0), (0.94, 0.0)),
             neck_yaw=Curve((0.24, 0.0), (0.30, 5.0), (0.52, 5.0), (0.60, -6.0), (0.86, -6.0), (0.95, 0.0)),
             jaw=Curve((0.00, 0.0), (0.63, 0.0), (0.645, 9.0), (0.66, 0.0), (0.675, 8.0), (0.69, 0.0), (0.705, 6.0), (0.72, 0.0)))
RAISED = Curve((0.00, 0.0), (0.30, 0.0), (0.36, 1.0), (0.50, 1.0), (0.56, 0.0))
DRUM = Curve((0.00, 0.0), (0.05, 1.0), (0.10, 0.15), (0.14, 0.0), (0.99, 0.0))


def _resting(phase, raised=0.0):
    """A hand at rest drums its claws on the ground now and then; `raised` lifts it to hang from the wrist."""
    out = _hand(PALM + 38.0 * raised, 0.07 * raised, 0.1 + 0.5 * raised, 0.6 * (1.0 - raised), hand_y=-0.03 * raised,
                shoulder_up=5.0 * raised)
    for k, name in enumerate(FINGERS):
        out["curl_" + name] += 30.0 * DRUM(phase - 0.025 * k) * (1.0 - raised) + 26.0 * raised * DRUM(4.0 * phase - 0.07 * k)
    return out


def idle(phase):
    """Breathes low over its hands, shifts its weight, cocks its head one way and then the other, clacks its
    teeth, and lifts one hand to hang a moment before setting it down."""
    breath = BREATH(phase)
    raised = RAISED(phase)
    out = at(WATCH, phase)
    _add(out, _back(-1.5 * breath - 3.0 * raised, 2.5 * breath))
    _add(out, dict(hips_z=0.006 * breath - 0.008, hips_x=0.012 * raised, chest_roll=-2.5 * raised))
    out.update(sided(dict(_resting(phase - 0.10, raised), **_foot(HEEL - 3.0 * breath)),
                     dict(_resting(phase - 0.71), **_foot(HEEL + 2.0 - 3.0 * breath))))
    return _crouched(out)


# ---------------------------------------------------------------- pounce

LEAP, LEAP_HEIGHT = 4.5, 0.22
POUNCE = dict(leap=0.38, hit=0.54, recover=0.82)
HANDS_OFF, HANDS_ON, FEET_ON = 0.30, 0.74, 0.82
TRAILED = Curve((0.0, 0.0), (0.22, 0.16), (0.60, 0.52), (0.90, 0.97), (1.0, 1.0), loop=False)
FLUNG = Curve((0.0, 0.0), (0.35, 0.70), (0.70, 1.0), (1.0, 1.0), loop=False)
STEPPED = Curve((0.0, 0.0), (0.5, 0.56), (1.0, 1.0), loop=False)
COIL = dict(hips_y=held((0.10, 0.07), (0.28, 0.11), (0.38, -0.04), (0.60, -0.02), (0.78, 0.02), (0.90, -0.05), (1.10, 0.0)),
            hips_z=held((0.10, -0.07), (0.28, -0.10), (0.38, 0.04), (0.62, 0.0), (0.74, -0.05), (0.86, -0.11), (0.94, -0.12), (1.12, -0.03),
                        (1.30, 0.0)),
            head_pitch=held((0.10, 8.0), (0.28, 10.0), (0.40, -6.0), (0.70, 0.0), (0.84, 10.0), (1.10, 0.0)),
            head_roll=held((0.10, -10.0), (0.28, -14.0), (0.40, 0.0), (0.84, 6.0), (1.10, 0.0)),
            jaw=held((0.24, 0.0), (0.38, 16.0), (0.54, 32.0), (0.72, 34.0), (0.80, 4.0), (0.90, 10.0), (1.10, 0.0)))
COIL_PITCH = held((0.10, 6.0), (0.26, 9.0), (0.34, -22.0), (0.42, -18.0), (0.56, -4.0), (0.70, 16.0), (0.78, 14.0), (0.90, 4.0),
                  (1.15, 0.0))
COIL_FLEX = held((0.10, 10.0), (0.28, 16.0), (0.40, -14.0), (0.56, -10.0), (0.70, 2.0), (0.80, 8.0), (0.90, 22.0), (1.00, 14.0),
                 (1.25, 0.0))
WIGGLE = held((0.08, 0.0), (0.13, 1.0), (0.25, 1.0), (0.31, 0.0))
SPRUNG = dict(lift=held((0.38, 0.0), (0.50, 0.30), (0.64, 0.38), (0.76, 0.14), (FEET_ON, 0.0)),
              pitch=held((0.10, -10.0), (0.28, -14.0), (0.34, 10.0), (0.39, 36.0), (0.52, 50.0), (0.70, 10.0), (FEET_ON, -12.0),
                         (0.90, -22.0), (1.10, -4.0), (1.30, 0.0)),
              knee=held((0.10, 10.0), (0.28, 14.0), (0.40, 0.0), (0.64, 18.0), (FEET_ON, 16.0), (1.20, 0.0)),
              foot_x=held((0.50, 0.0), (0.70, 0.07), (FEET_ON, 0.08), (1.30, 0.08)))
CAST = dict(lift=held((HANDS_OFF, 0.0), (0.40, 0.34), (0.54, 0.52), (0.66, 0.34), (HANDS_ON, 0.0), (0.82, 0.0), (0.90, 0.09),
                      (0.98, 0.0)),
            pitch=held((0.10, 10.0), (0.26, 26.0), (HANDS_OFF, 60.0), (0.40, 70.0), (0.54, 20.0), (0.66, -24.0), (HANDS_ON, -8.0),
                       (0.77, 10.0), (0.82, 52.0), (0.90, 70.0), (0.98, 0.0)),
            hooked=held((0.26, 0.2), (0.40, 0.7), (0.54, 0.0), (0.66, 0.3), (HANDS_ON, 0.9), (0.84, 0.8), (0.98, 0.0)),
            splayed=held((0.30, 0.0), (0.42, 0.2), (0.54, 1.4), (0.68, 1.2), (HANDS_ON, 0.6), (0.98, 0.0)),
            hand_x=held((HANDS_OFF, 0.0), (0.54, 0.08), (HANDS_ON, 0.05), (0.98, 0.0)),
            elbow_out=held((0.10, 10.0), (0.28, 16.0), (0.50, -10.0), (HANDS_ON, 0.0), (0.84, 24.0), (1.10, 0.0)),
            shoulder_up=held((0.28, -6.0), (0.44, 14.0), (0.66, 16.0), (0.80, -6.0), (1.10, 0.0)))


def _leapt(t):
    return LEAP * glide(t, HANDS_OFF, POUNCE["leap"], 0.76, 0.92)


def _sprung(t, late):
    c = at(SPRUNG, t - late)
    y = trod(t - late, _leapt, (0.0, LEAP), [(POUNCE["leap"], FEET_ON, TRAILED)])
    return _foot(HEEL + c.pop("pitch"), c.pop("lift"), foot_y=y, **c)


def _cast(t, late):
    c = at(CAST, t - late)
    y = trod(t - late, _leapt, (0.0, LEAP - 0.58, LEAP), [(HANDS_OFF, HANDS_ON, FLUNG), (0.82, 0.98, STEPPED)])
    return _hand(PALM + c.pop("pitch"), c.pop("lift"), 0.15 + c.pop("hooked"), 0.6 + c.pop("splayed"), hand_y=y, **c)


def pounce(t):
    """Sinks back on its haunches with a wiggle of the rump, throws itself four and a half metres with both
    hands spread ahead and its mouth wide, lands on the hands, brings the feet in round them and settles."""
    out = at(COIL, t)
    wiggle = WIGGLE(t) * np.sin(2.0 * np.pi * 7.0 * (t - 0.08))
    out.update(_back(COIL_PITCH(t), COIL_FLEX(t)), travel=_leapt(t), hips_x=0.016 * wiggle, hips_yaw=-6.0 * wiggle,
               spine_yaw=4.0 * wiggle)
    out["hips_z"] += LEAP_HEIGHT * thrown(t, POUNCE["leap"], 0.77)
    out.update(sided(dict(_sprung(t, 0.0), **_cast(t, 0.03)), dict(_sprung(t, 0.025), **_cast(t, 0.0))))
    return _crouched(out)


# ---------------------------------------------------------------- bite

BITE = dict(hit=0.30, recover=0.42)
LUNGE = dict(hips_y=held((0.10, 0.05), (0.24, 0.07), (0.34, -0.25), (0.44, -0.22), (0.62, -0.05), (0.95, 0.0)),
             hips_z=held((0.10, -0.03), (0.24, -0.05), (0.34, -0.02), (0.46, -0.04), (0.70, -0.01), (0.95, 0.0)),
             neck_pitch=held((0.10, -8.0), (0.24, -12.0), (0.33, 16.0), (0.44, 12.0), (0.70, 2.0), (0.95, 0.0)),
             head_pitch=held((0.10, -14.0), (0.24, -22.0), (0.33, 6.0), (0.40, 12.0), (0.50, 6.0), (0.75, 0.0)),
             head_roll=held((0.10, 12.0), (0.24, 18.0), (0.34, 8.0), (0.42, -10.0), (0.50, 12.0), (0.58, -8.0), (0.66, 4.0),
                            (0.80, 0.0)),
             head_yaw=held((0.10, -6.0), (0.24, -8.0), (0.34, 0.0), (0.42, 16.0), (0.50, -16.0), (0.58, 12.0), (0.66, -6.0),
                           (0.80, 0.0)),
             chest_yaw=held((0.24, -5.0), (0.34, 4.0), (0.42, 6.0), (0.50, -6.0), (0.58, 4.0), (0.80, 0.0)),
             head_level=held((0.24, 0.0), (0.33, -0.12), (0.46, -0.1), (0.75, 0.0)),
             jaw=held((0.06, 4.0), (0.20, 36.0), (0.30, 38.0), (0.36, 0.0), (0.44, 0.0), (0.50, 5.0), (0.56, 0.0), (0.95, 0.0)))
LUNGE_PITCH = held((0.10, -9.0), (0.24, -14.0), (0.34, 7.0), (0.44, 6.0), (0.66, 2.0), (0.95, 0.0))
LUNGE_FLEX = held((0.10, 8.0), (0.24, 12.0), (0.34, -12.0), (0.44, -8.0), (0.66, 3.0), (0.95, 0.0))
BRACED = dict(pitch=held((0.10, -6.0), (0.24, -10.0), (0.34, 22.0), (0.46, 18.0), (0.75, 2.0), (0.95, 0.0)),
              knee=held((0.24, 6.0), (0.34, -2.0), (0.95, 0.0)))
SLAP = dict(lift=held((0.08, 0.0), (0.16, 0.07), (0.25, 0.09), (0.32, 0.0), (0.62, 0.0), (0.70, 0.06), (0.78, 0.0)),
            pitch=held((0.06, 30.0), (0.16, 60.0), (0.25, 20.0), (0.31, -16.0), (0.34, 0.0), (0.60, 30.0), (0.70, 55.0), (0.78, 0.0)),
            hooked=held((0.10, 0.5), (0.25, 0.0), (0.32, 0.9), (0.60, 0.8), (0.78, 0.0)),
            splayed=held((0.16, 0.0), (0.25, 0.9), (0.32, 0.3), (0.78, 0.0)),
            hand_x=held((0.25, 0.04), (0.62, 0.04), (0.78, 0.0)))
PROP = dict(pitch=held((0.24, 0.0), (0.34, 26.0), (0.46, 22.0), (0.75, 0.0)), elbow_out=held((0.24, 8.0), (0.34, -8.0), (0.75, 0.0)),
            hooked=held((0.24, 0.0), (0.34, 0.5), (0.75, 0.0)))
SLAPPED = 0.14


def _still(t):
    return 0.0


def bite(t):
    """Rears its head back and sideways as the jaw drops open and one hand comes off the ground, drives head and
    chest forward and down as the hand slaps down ahead, snaps shut, worries what it has, and draws back."""
    out = at(LUNGE, t)
    out.update(_back(LUNGE_PITCH(t), LUNGE_FLEX(t)))
    slap, prop, foot = at(SLAP, t), at(PROP, t), at(BRACED, t)
    reach = trod(t, _still, (0.0, SLAPPED, 0.0), [(0.08, 0.32, STEPPED), (0.62, 0.78, STEPPED)])
    left = _hand(PALM + prop.pop("pitch"), 0.0, 0.15 + prop.pop("hooked"), **prop)
    right = _hand(PALM + slap.pop("pitch"), slap.pop("lift"), 0.15 + slap.pop("hooked"), 0.6 + slap.pop("splayed"), hand_y=reach, **slap)
    out.update(sided(dict(left, **_foot(HEEL + foot["pitch"], knee=foot["knee"])),
                     dict(right, **_foot(HEEL + foot["pitch"], knee=foot["knee"]))))
    return _crouched(out)


# ---------------------------------------------------------------- flinch

KNOCKED = -0.24
SHY = dict(hips_z=held((0.06, -0.04), (0.18, -0.07), (0.36, -0.03), (0.55, 0.0)),
           hips_y=held((0.06, 0.05), (0.18, 0.06), (0.40, 0.0)),
           hips_yaw=held((0.08, 5.0), (0.26, 3.0), (0.50, 0.0)),
           chest_yaw=held((0.07, -14.0), (0.24, -8.0), (0.42, 3.0), (0.55, 0.0)),
           chest_roll=held((0.07, 8.0), (0.24, 4.0), (0.50, 0.0)),
           neck_pitch=held((0.05, -8.0), (0.20, -3.0), (0.50, 0.0)),
           head_pitch=held((0.05, -18.0), (0.15, -9.0), (0.28, 7.0), (0.42, -2.0), (0.55, 0.0)),
           head_yaw=held((0.05, 26.0), (0.18, 16.0), (0.32, -6.0), (0.46, 0.0)),
           head_roll=held((0.06, -14.0), (0.28, 4.0), (0.55, 0.0)),
           jaw=held((0.05, 22.0), (0.16, 16.0), (0.30, 0.0), (0.55, 0.0)))
SHY_PITCH = held((0.06, -11.0), (0.18, -7.0), (0.34, 4.0), (0.55, 0.0))
SHY_FLEX = held((0.06, 10.0), (0.20, 12.0), (0.38, 3.0), (0.55, 0.0))
STARTLED = held((0.07, 1.0), (0.30, 0.0))
SKIP = dict(lift=Curve((0.0, 0.0), (0.45, 1.0), (1.0, 0.0), loop=False), pitch=Curve((0.0, 0.0), (0.3, 1.0), (0.8, -0.3), (1.0, 0.0), loop=False))


def _knocked(t):
    return KNOCKED * glide(t, 0.03, 0.10, 0.28, 0.42)


def _skip(t, lift, land, high):
    """One short step back: how high the hand or foot is, and how far it is tipped, as shares of `high`."""
    s = (t - lift) / (land - lift)
    return (high * SKIP["lift"](s), SKIP["pitch"](s)) if 0.0 < s < 1.0 else (0.0, 0.0)


def flinch(t):
    """Head and chest snap up and away from the blow with a hiss, and it skitters back a step on each hand and
    foot, low to the ground."""
    out = at(SHY, t)
    out.update(_back(SHY_PITCH(t), SHY_FLEX(t)), travel=_knocked(t))

    def limb(hand, foot, startled):
        z, tip = _skip(t, *hand, 0.10)
        out_ = _hand(PALM + 60.0 * tip, z, 0.15 + 0.5 * startled, 0.6 + 0.6 * startled,
                     hand_y=trod(t, _knocked, (0.0, KNOCKED), [(*hand, STEPPED)]), shoulder_up=10.0 * startled)
        z, tip = _skip(t, *foot, 0.05)
        return dict(out_, **_foot(HEEL + 18.0 * tip, z, foot_y=trod(t, _knocked, (0.0, KNOCKED), [(*foot, STEPPED)])))
    startled = STARTLED(t)
    out.update(sided(limb((0.16, 0.32), (0.10, 0.24), 0.5 * startled), limb((0.04, 0.20), (0.22, 0.38), startled)))
    return _crouched(out)


# ---------------------------------------------------------------- death

REELED = -0.34
THROES = dict(hips_y=held((0.10, 0.06), (0.44, 0.12), (0.66, 0.05), (0.92, -0.10), (1.06, -0.13), (1.40, -0.14)),
              hips_z=held((0.10, -0.03), (0.44, -0.09), (0.66, -0.10), (0.90, -0.28), (0.98, -0.33), (1.06, -0.315), (1.16, -0.325)),
              hips_x=held((0.50, 0.02), (0.96, 0.05)),
              hips_roll=held((0.44, -4.0), (0.90, 6.0), (1.00, 10.0), (1.24, 9.0)),
              hips_yaw=held((0.44, 6.0), (0.96, -6.0)),
              chest_yaw=held((0.08, -16.0), (0.44, 10.0), (0.90, -4.0), (1.16, -6.0)),
              chest_roll=held((0.44, 10.0), (0.90, -4.0), (1.16, -6.0)),
              neck_pitch=held((0.06, -10.0), (0.44, -6.0), (0.90, 4.0), (0.98, -6.0), (1.08, -12.0), (1.30, -8.0)),
              neck_yaw=held((0.80, 0.0), (1.00, 12.0), (1.40, 18.0)),
              head_pitch=held((0.06, -26.0), (0.24, -12.0), (0.46, -24.0), (0.86, 0.0), (0.98, -12.0), (1.10, -4.0), (1.30, -8.0)),
              head_yaw=held((0.06, 24.0), (0.36, -10.0), (0.80, 10.0), (0.98, 52.0), (1.08, 66.0), (1.16, 60.0), (1.40, 64.0),
                            (1.76, 64.0), (1.84, 56.0), (2.00, 66.0)),
              head_roll=held((0.06, -12.0), (0.44, 8.0), (0.90, -6.0), (1.30, -10.0)),
              head_level=held((0.56, 0.0), (0.92, -0.80), (1.10, -0.90)),
              jaw=held((0.05, 30.0), (0.30, 22.0), (0.46, 34.0), (0.90, 14.0), (0.98, 2.0), (1.16, 6.0), (1.60, 8.0), (1.76, 22.0),
                       (1.90, 12.0), (2.20, 17.0)))
THROES_PITCH = held((0.08, -14.0), (0.24, -30.0), (0.46, -42.0), (0.66, -26.0), (0.90, 6.0), (0.98, 9.0), (1.08, 3.0), (1.20, 5.0))
THROES_FLEX = held((0.08, 10.0), (0.46, 16.0), (0.74, 4.0), (0.96, -5.0), (1.16, -2.0), (1.74, -2.0), (1.80, 3.0), (1.92, -1.0))
PAWING = dict(planted=held((0.08, 0.0), (0.16, -1.0), (0.66, -1.0), (0.84, 0.0)),
              arm_fwd=held((0.12, 60.0), (0.30, 110.0), (0.46, 80.0), (0.66, 120.0), (0.86, 100.0)),
              arm_out=held((0.12, 30.0), (0.30, 55.0), (0.46, 30.0), (0.66, 50.0), (0.86, 40.0)),
              elbow=held((0.12, 80.0), (0.30, 40.0), (0.46, 90.0), (0.66, 40.0), (0.86, 60.0)),
              wrist_curl=held((0.12, 30.0), (0.30, -30.0), (0.46, 30.0), (0.66, -20.0), (0.86, 0.0)))
SPLAYED = dict(hand_x=held((0.66, 0.0), (0.86, 0.08), (1.00, 0.17), (1.16, 0.19), (1.76, 0.19), (2.10, 0.13)),
               hand_y=held((0.66, 0.0), (0.86, -0.26), (1.00, -0.20), (1.16, -0.17), (1.76, -0.17), (2.10, -0.08)),
               hand_yaw=held((0.66, 0.0), (1.00, 30.0), (1.76, 34.0), (2.10, 12.0)),
               lift=held((0.10, 0.0), (0.16, 0.30), (0.68, 0.34), (0.86, 0.0)),
               pitch=held((0.86, 0.0), (1.00, 0.0), (1.76, 0.0), (2.10, 10.0)),
               hooked=held((0.10, 0.0), (0.30, 0.9), (0.66, 0.2), (0.90, 0.0), (1.30, 0.1), (1.76, 0.2), (2.10, 1.2)),
               splayed=held((0.10, 0.6), (0.66, 0.9), (0.96, 0.5), (1.76, 0.2), (2.10, -0.4)),
               elbow_out=held((0.80, 0.0), (1.00, 44.0), (1.76, 50.0), (2.10, 36.0)))
DRAGGED = dict(foot_y=held((0.88, 0.0), (1.00, 0.20), (1.14, 0.25), (1.50, 0.25), (1.58, 0.12), (1.70, 0.29), (1.82, 0.22), (1.94, 0.30)),
               foot_x=held((0.88, 0.0), (1.04, 0.12), (1.50, 0.13), (1.94, 0.16)),
               foot_yaw=held((0.88, 0.0), (1.04, 40.0), (1.94, 52.0)),
               pitch=held((0.10, -10.0), (0.46, -24.0), (0.74, -4.0), (0.94, 22.0), (1.08, 34.0), (1.50, 34.0), (1.58, 10.0),
                          (1.70, 38.0), (1.94, 40.0)),
               knee=held((0.88, 0.0), (1.04, 50.0), (1.50, 56.0), (1.58, 30.0), (1.70, 60.0), (1.94, 62.0)))


def _reeled(t):
    return REELED * glide(t, 0.03, 0.12, 0.36, 0.52)


def death(t):
    """Thrown back on its haunches shrieking, it paws the air, pitches forward onto its chest and chin as its
    arms give way under it, kicks once, and its claws draw in and close."""
    out = at(THROES, t)
    out.update(_back(THROES_PITCH(t), THROES_FLEX(t)), travel=_reeled(t))

    def limb(late, kicks, back):
        c, d = at(SPLAYED, t - late), at(DRAGGED, t - late if kicks else min(t - late, 1.50))
        arm = dict(at(PAWING, t - 2.0 * late), **_hand(PALM + c.pop("pitch"), c.pop("lift"), 0.15 + c.pop("hooked"), 0.6 + c.pop("splayed"), **c))
        step = trod(t, _reeled, (0.0, back), [(0.12 + late, 0.30 + late, STEPPED)])
        z, tip = _skip(t, 0.12 + late, 0.30 + late, 0.06)
        return dict(arm, **_foot(HEEL + d.pop("pitch") + 16.0 * tip, z, foot_y=step + d.pop("foot_y"), **d))
    left, right = limb(0.05, True, REELED + 0.04), limb(0.0, False, REELED - 0.03)
    left["hand_y"] += trod(t, _reeled, (0.0, REELED), [(0.14, 0.86, STEPPED)])
    right["hand_y"] += trod(t, _reeled, (0.0, REELED), [(0.10, 0.82, STEPPED)])
    out.update(sided(left, right))
    return _crouched(out)


# ---------------------------------------------------------------- poses that test the skin

GAPE = dict(jaw=38.0, head_pitch=-18.0, neck_pitch=-8.0, head_roll=10.0)
POSES = {"prowl": _crouched(both(dict(_hand(PALM), **_foot(HEEL)))),
         "gape": _crouched(dict(both(dict(_hand(PALM), **_foot(HEEL))), **GAPE)),
         "stretch": dict(run(0.40), travel=0.0), "gather": dict(run(0.92), travel=0.0)}
MOVES = {"Pounce": (pounce, 1.3, POUNCE), "Bite": (bite, 0.95, BITE), "Flinch": (flinch, 0.55, {}), "Death": (death, 2.3, {})}
SCUTTLER = Kind("scuttler", {"Idle": (idle, 180), "Run": (run, GALLOP)}, MOVES, POSES, jaw=True)
