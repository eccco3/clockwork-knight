"""The grinner's moves, each played once from rest: two attacks, a flinch and a death.

A move is a function of the seconds since it began, returning controls of `pose`. Its marks name the moments
its phases begin, in seconds; until the first mark an attack is winding up. Both wind-ups keep the feet where
the grinner stands, as the flinch begins, so a flinch can cut in at any moment of either.
"""
import numpy as np
from .body import FINGERS
from .keys import Curve, held, at, glide, thrown, trod, sided, borne

STEPPED = Curve((0.0, 0.0), (0.5, 0.56), (1.0, 1.0), loop=False)


def _claws(hooked, splayed=0.0):
    """A hand's fingers: `hooked` closes them into a rake, `splayed` opens and fans them."""
    out = {"curl_" + name: 40.0 * hooked - 22.0 * splayed for name in FINGERS}
    out.update(spread=6.0 * hooked + 13.0 * splayed, thumb_curl=28.0 * hooked - 6.0 * splayed, thumb_in=-22.0 * splayed)
    return out


def _foot(curves, t, foot_y):
    """A foot's controls; its toes stay flat on the ground while the heel peels off it."""
    out = at(curves, t)
    out.update(foot_y=foot_y, toe=max(out["foot_pitch"], 0.0) * float(np.clip(1.0 - out["foot_z"] / 0.04, 0.0, 1.0)))
    return out


# ---------------------------------------------------------------- pounce

LEAP, LEAP_HEIGHT, LANDS = 4.0, 0.30, 1.10
POUNCE = dict(leap=0.60, hit=0.94, recover=1.16)
TRAILING = Curve((0.0, 0.0), (0.22, -0.10), (0.50, 0.0), (0.86, 0.86), (1.0, 1.0), loop=False)
COIL = dict(hips_y=held((0.16, 0.10), (0.48, 0.13), (0.60, 0.02), (0.85, -0.02), (1.08, 0.02), (1.24, -0.02), (1.50, 0.0)),
            hips_z=held((0.16, -0.21), (0.48, -0.25), (0.60, -0.07), (1.06, -0.22), (1.20, -0.27), (1.45, -0.12), (1.78, 0.0)),
            hips_pitch=held((0.16, 30.0), (0.48, 37.0), (0.60, 50.0), (0.80, 40.0), (1.00, 20.0), (1.10, 24.0), (1.22, 40.0),
                            (1.50, 18.0), (1.85, 0.0)),
            spine_pitch=held((0.16, 8.0), (0.48, 10.0), (0.60, -4.0), (0.85, -10.0), (1.05, 6.0), (1.20, 16.0), (1.50, 6.0),
                             (1.85, 0.0)),
            chest_pitch=held((0.16, 6.0), (0.48, 8.0), (0.60, -6.0), (0.85, -12.0), (1.05, 10.0), (1.20, 18.0), (1.50, 6.0),
                             (1.85, 0.0)),
            spine_yaw=held((0.16, -6.0), (0.48, -9.0), (0.90, -11.0), (1.12, 14.0), (1.24, 14.0), (1.60, 0.0)),
            chest_yaw=held((0.16, -12.0), (0.48, -18.0), (0.90, -22.0), (1.12, 28.0), (1.24, 28.0), (1.60, 0.0)),
            chest_roll=held((0.48, 6.0), (0.90, 8.0), (1.12, -10.0), (1.24, -8.0), (1.60, 0.0)),
            head_pitch=held((0.16, -8.0), (0.48, -10.0), (0.85, -16.0), (1.12, 8.0), (1.24, 12.0), (1.60, -4.0), (1.85, 0.0)),
            head_roll=held((0.16, 9.0), (0.48, 11.0), (0.62, 0.0), (1.12, -8.0), (1.50, 0.0)),
            head_yaw=held((0.48, 6.0), (0.90, 8.0), (1.12, -12.0), (1.50, 0.0)))
WIGGLE = held((0.16, 0.0), (0.22, 1.0), (0.42, 1.0), (0.50, 0.0))
SPRING_L = dict(foot_z=held((0.60, 0.0), (0.72, 0.22), (0.90, 0.34), (1.02, 0.16), (1.10, 0.0)),
                foot_pitch=held((0.44, 0.0), (0.56, 25.0), (0.62, 55.0), (0.80, 60.0), (1.00, 10.0), (1.08, -12.0), (1.13, 0.0)),
                knee=held((0.16, 8.0), (0.48, 10.0), (0.62, 0.0), (1.10, 6.0), (1.22, 16.0), (1.50, 6.0), (1.85, 0.0)))
SPRING_R = dict(foot_z=held((0.57, 0.0), (0.69, 0.24), (0.87, 0.30), (0.99, 0.14), (1.07, 0.0), (1.42, 0.0), (1.53, 0.07),
                            (1.64, 0.0)),
                foot_pitch=held((0.42, 0.0), (0.54, 25.0), (0.59, 55.0), (0.78, 62.0), (0.98, 10.0), (1.05, -12.0), (1.10, 0.0),
                                (1.38, 0.0), (1.46, 22.0), (1.56, 4.0), (1.62, -6.0), (1.66, 0.0)),
                knee=SPRING_L["knee"])
STEPS_L = (0.0, LEAP), [(0.60, LANDS, TRAILING)]
STEPS_R = (0.0, LEAP - 0.18, LEAP), [(0.57, 1.07, TRAILING), (1.42, 1.64, STEPPED)]
RAKE = dict(arm_fwd=held((0.16, -35.0), (0.48, -45.0), (0.62, 40.0), (0.80, 150.0), (0.94, 165.0), (1.06, 80.0), (1.14, 38.0),
                         (1.24, 30.0), (1.60, 4.0), (1.85, 0.0)),
            arm_out=held((0.16, 30.0), (0.48, 38.0), (0.80, 25.0), (0.94, 20.0), (1.14, -20.0), (1.24, -24.0), (1.60, 0.0)),
            elbow=held((0.16, 70.0), (0.48, 85.0), (0.80, 75.0), (0.94, 60.0), (1.06, 20.0), (1.14, 50.0), (1.26, 78.0),
                       (1.85, 0.0)),
            shoulder_up=held((0.16, 8.0), (0.80, 14.0), (0.94, 14.0), (1.14, -4.0), (1.60, 0.0)),
            shoulder_fwd=held((0.16, -8.0), (0.48, -10.0), (0.94, -6.0), (1.12, 14.0), (1.24, 12.0), (1.60, 0.0)),
            wrist_curl=held((0.16, -18.0), (0.80, -28.0), (0.94, -30.0), (1.10, 25.0), (1.24, 30.0), (1.60, 0.0)))
RAKE_CLAWS = held((0.16, 0.7), (0.80, 0.5), (0.94, 1.0), (1.24, 1.0), (1.60, 0.0)), \
    held((0.62, 0.0), (0.80, 0.6), (0.92, 0.5), (1.00, 0.0))
REACH = dict(arm_fwd=held((0.16, -25.0), (0.48, -30.0), (0.62, 55.0), (0.80, 85.0), (0.94, 78.0), (1.10, 10.0), (1.22, -28.0),
                          (1.50, -8.0), (1.85, 0.0)),
             arm_out=held((0.16, 22.0), (0.48, 26.0), (0.62, 10.0), (0.94, 14.0), (1.22, 34.0), (1.50, 10.0), (1.85, 0.0)),
             elbow=held((0.16, 65.0), (0.48, 75.0), (0.62, 30.0), (0.80, 18.0), (0.94, 28.0), (1.22, 62.0), (1.50, 25.0),
                        (1.85, 0.0)),
             wrist_curl=held((0.16, -10.0), (0.80, -22.0), (1.22, 10.0), (1.60, 0.0)))
REACH_CLAWS = held((0.16, 0.5), (1.24, 0.5), (1.60, 0.0)), held((0.62, 0.0), (0.80, 0.7), (1.10, 0.3), (1.30, 0.0))


def _leapt(t):
    return LEAP * glide(t, 0.50, POUNCE["leap"], LANDS, 1.20)


def pounce(t):
    """Coils with a wiggle of the hips, springs four metres with the right claw cocked overhead, rakes it down
    across as the feet come under to land, and stands up out of the crouch."""
    out = at(COIL, t)
    wiggle = WIGGLE(t) * np.sin(2.0 * np.pi * 4.5 * (t - 0.16))
    out.update(hips_x=0.014 * wiggle, hips_yaw=-5.0 * wiggle, travel=_leapt(t), head_level=0.85)
    out["hips_z"] += LEAP_HEIGHT * thrown(t, POUNCE["leap"], LANDS)
    out["spine_yaw"] += 3.0 * wiggle
    out.update(sided(dict(at(REACH, t), **_claws(*(c(t) for c in REACH_CLAWS)), **_foot(SPRING_L, t, trod(t, _leapt, *STEPS_L))),
                     dict(at(RAKE, t), **_claws(*(c(t) for c in RAKE_CLAWS)), **_foot(SPRING_R, t, trod(t, _leapt, *STEPS_R)))))
    return borne(out)


# ---------------------------------------------------------------- swipe

SWIPE = dict(hit=0.40, recover=0.58)
REAR = dict(hips_z=held((0.14, -0.06), (0.36, 0.015), (0.40, 0.01), (0.52, -0.13), (0.66, -0.15), (0.95, -0.04), (1.20, 0.0)),
            hips_y=held((0.30, 0.05), (0.40, 0.04), (0.52, -0.07), (0.66, -0.08), (1.00, -0.01), (1.20, 0.0)),
            hips_pitch=held((0.14, 6.0), (0.36, -8.0), (0.52, 22.0), (0.66, 26.0), (1.00, 6.0), (1.20, 0.0)),
            spine_pitch=held((0.36, -8.0), (0.52, 12.0), (0.66, 14.0), (1.00, 3.0), (1.20, 0.0)),
            chest_pitch=held((0.14, 4.0), (0.36, -12.0), (0.52, 14.0), (0.66, 18.0), (1.00, 4.0), (1.20, 0.0)),
            chest_yaw=held((0.36, -6.0), (0.56, 6.0), (1.00, 0.0)),
            head_pitch=held((0.36, -6.0), (0.52, 4.0), (1.00, 0.0)),
            head_roll=held((0.14, -8.0), (0.36, -12.0), (0.52, 6.0), (0.70, 8.0), (1.20, 0.0)))
TIPTOE = dict(foot_z=held((1.20, 0.0)), foot_pitch=held((0.26, 0.0), (0.36, 14.0), (0.45, 0.0)),
              knee=held((0.40, 0.0), (0.54, 10.0), (1.00, 0.0)))
SLASH = dict(arm_out=held((0.14, 25.0), (0.36, 72.0), (0.42, 68.0), (0.52, -14.0), (0.60, -24.0), (0.72, -20.0), (1.00, -4.0),
                          (1.20, 0.0)),
             elbow=held((0.14, 45.0), (0.36, 78.0), (0.44, 34.0), (0.52, 18.0), (0.62, 50.0), (0.74, 62.0), (1.00, 20.0),
                        (1.20, 0.0)),
             wrist_curl=held((0.36, -28.0), (0.50, 10.0), (0.62, 34.0), (1.00, 6.0), (1.20, 0.0)),
             shoulder_up=held((0.36, 14.0), (0.52, -2.0), (0.66, 4.0), (1.00, 0.0)),
             shoulder_fwd=held((0.36, -12.0), (0.52, 16.0), (0.66, 18.0), (1.00, 0.0)))
SLASH_HIGH = held((0.14, -14.0), (0.36, -36.0), (0.42, 14.0), (0.52, 92.0), (0.60, 98.0), (0.72, 80.0), (1.00, 12.0), (1.20, 0.0))
SLASH_LOW = held((0.14, -14.0), (0.36, -34.0), (0.42, 6.0), (0.52, 60.0), (0.60, 64.0), (0.72, 54.0), (1.00, 10.0), (1.20, 0.0))
SLASH_CLAWS = held((0.46, 0.0), (0.54, 0.9), (0.66, 1.0), (1.00, 0.2), (1.20, 0.0)), \
    held((0.14, 0.4), (0.36, 1.0), (0.44, 0.6), (0.52, 0.0))
LATE = 0.03


def _slash(t, arm_fwd):
    return dict(at(SLASH, t), arm_fwd=arm_fwd(t), **_claws(*(c(t) for c in SLASH_CLAWS)), **_foot(TIPTOE, t, 0.0))


def swipe(t):
    """Rears up on its toes with both arms flung wide, then brings the claws together across its front, the
    right above the left, and unfolds."""
    out = at(REAR, t)
    out.update(head_level=0.7, **sided(_slash(t - LATE, SLASH_LOW), _slash(t, SLASH_HIGH)))
    return borne(out)


# ---------------------------------------------------------------- flinch

RECOIL = dict(hips_z=held((0.07, -0.05), (0.20, -0.08), (0.42, -0.05), (0.60, 0.0)),
              hips_y=held((0.07, 0.05), (0.20, 0.06), (0.42, 0.0)),
              hips_pitch=held((0.07, -6.0), (0.22, -3.0), (0.42, 5.0), (0.60, 0.0)),
              spine_pitch=held((0.07, -7.0), (0.22, -4.0), (0.42, 4.0), (0.60, 0.0)),
              chest_pitch=held((0.08, -12.0), (0.24, -6.0), (0.44, 6.0), (0.60, 0.0)),
              chest_yaw=held((0.08, -14.0), (0.26, -8.0), (0.46, 3.0), (0.60, 0.0)),
              head_pitch=held((0.06, -20.0), (0.16, -10.0), (0.30, 8.0), (0.46, -2.0), (0.60, 0.0)),
              head_yaw=held((0.06, 22.0), (0.20, 14.0), (0.34, -6.0), (0.50, 0.0)),
              head_roll=held((0.08, -12.0), (0.30, 4.0), (0.60, 0.0)))
THROWN_UP = dict(arm_out=held((0.09, 32.0), (0.26, 18.0), (0.46, -3.0), (0.60, 0.0)),
                 arm_fwd=held((0.09, 28.0), (0.28, 10.0), (0.60, 0.0)),
                 elbow=held((0.09, 55.0), (0.30, 30.0), (0.60, 0.0)),
                 shoulder_up=held((0.07, 16.0), (0.30, 4.0), (0.60, 0.0)),
                 wrist_curl=held((0.09, -25.0), (0.30, 10.0), (0.60, 0.0)))
STARTLED = held((0.08, 1.0), (0.30, 0.0))
BACK_R = dict(foot_z=held((0.07, 0.0), (0.15, 0.05), (0.24, 0.0)),
              foot_pitch=held((0.07, 0.0), (0.13, 14.0), (0.21, -6.0), (0.26, 0.0)), knee=held((0.60, 0.0)))
BACK_L = dict(foot_z=held((0.24, 0.0), (0.33, 0.05), (0.42, 0.0)),
              foot_pitch=held((0.24, 0.0), (0.30, 14.0), (0.39, -6.0), (0.44, 0.0)), knee=held((0.60, 0.0)))
KNOCKED = -0.16


def _knocked(t):
    return KNOCKED * glide(t, 0.04, 0.12, 0.30, 0.42)


def flinch(t):
    """Head and chest snap away from the blow, the arms fly up, and two short steps back catch it."""
    out = at(RECOIL, t)
    arm = lambda t, much: {name: much * value for name, value in dict(at(THROWN_UP, t), **_claws(0.0, STARTLED(t))).items()}
    out.update(travel=_knocked(t), head_level=0.3)
    out.update(sided(dict(arm(t - 0.02, 0.8), **_foot(BACK_L, t, trod(t, _knocked, (0.0, KNOCKED), [(0.24, 0.42, STEPPED)]))),
                     dict(arm(t, 1.0), **_foot(BACK_R, t, trod(t, _knocked, (0.0, KNOCKED), [(0.07, 0.24, STEPPED)])))))
    return borne(out)


# ---------------------------------------------------------------- death

REELED = -0.30
HEAD_FREE = Curve((0.0, 0.5), (0.5, 0.0), loop=False)
FALL = dict(hips_y=held((0.08, 0.05), (0.55, 0.09), (0.80, 0.30), (0.95, 0.46), (1.08, 0.52), (1.40, 0.535)),
            hips_z=held((0.08, -0.04), (0.55, -0.08), (0.80, -0.30), (0.95, -0.47), (1.02, -0.50)),
            hips_x=held((0.55, 0.02), (1.10, 0.04)),
            hips_pitch=held((0.08, -8.0), (0.55, -13.0), (0.80, -34.0), (0.95, -58.0), (1.10, -92.0), (1.20, -87.0),
                            (1.32, -90.0)),
            hips_yaw=held((0.50, -4.0), (1.10, -8.0)),
            spine_pitch=held((0.08, -6.0), (0.55, -3.0), (0.85, 14.0), (1.10, 2.0), (1.30, 0.0)),
            chest_pitch=held((0.08, -10.0), (0.55, -5.0), (0.85, 16.0), (1.10, 0.0), (1.18, -3.0), (1.40, 0.0), (1.70, -3.0),
                             (2.20, 1.0)),
            chest_yaw=held((0.08, -12.0), (0.50, -6.0), (1.10, 6.0), (1.50, 8.0)),
            neck_pitch=held((0.06, -10.0), (0.40, -4.0), (0.85, 10.0), (1.14, -8.0), (1.50, -6.0)),
            head_pitch=held((0.06, -24.0), (0.30, -15.0), (0.85, 26.0), (1.06, 10.0), (1.14, -16.0), (1.24, -6.0), (1.50, -10.0)),
            head_yaw=held((0.06, -20.0), (0.40, -8.0), (1.10, 0.0), (1.50, 26.0), (1.90, 32.0)),
            head_roll=held((0.06, 10.0), (0.40, 0.0), (1.50, -6.0)))
FLAIL = dict(arm_hang=held((0.10, -0.3), (0.55, -0.75)),
             arm_fwd=held((0.10, 15.0), (0.50, 25.0), (0.85, 60.0), (1.08, 70.0), (1.22, -13.0), (1.34, 4.0), (1.46, -13.0)),
             arm_out=held((0.10, 50.0), (0.50, 60.0), (0.85, 35.0), (1.08, 40.0), (1.24, 52.0)),
             elbow=held((0.10, 50.0), (0.50, 35.0), (0.85, 45.0), (1.08, 30.0), (1.24, 0.0), (1.36, 14.0), (1.50, -4.0)),
             shoulder_up=held((0.08, 14.0), (0.50, 8.0), (1.10, 12.0), (1.40, 4.0)),
             wrist_curl=held((0.10, -25.0), (0.50, 0.0), (1.08, -20.0), (1.24, 4.0), (1.50, -8.0)))
SLACK = held((0.08, -0.8), (0.50, -0.3), (1.10, -0.5), (1.40, 0.3))
TWITCH = held((1.70, 0.0), (1.78, 1.0), (1.90, 0.2), (2.00, 0.6), (2.20, 0.0))
DROP_R = dict(foot_z=held((0.10, 0.0), (0.21, 0.08), (0.32, 0.0), (0.98, 0.0), (1.14, 0.30), (1.34, 0.0), (1.42, 0.03), (1.50, 0.0)),
              foot_pitch=held((0.10, 0.0), (0.18, 18.0), (0.28, -8.0), (0.34, 0.0), (0.80, 0.0), (0.98, -25.0), (1.14, -50.0),
                              (1.34, -68.0), (1.50, -62.0)),
              foot_yaw=held((0.98, 0.0), (1.34, 22.0), (1.60, 30.0)),
              foot_x=held((0.98, 0.0), (1.34, 0.05)),
              knee=held((0.60, 0.0), (0.95, 60.0), (1.14, 120.0), (1.50, 118.0)))
DROP_L = dict(foot_z=held((0.34, 0.0), (0.44, 0.06), (0.54, 0.0), (1.02, 0.0), (1.20, 0.22), (1.42, 0.0)),
              foot_pitch=held((0.34, 0.0), (0.41, 16.0), (0.50, -8.0), (0.56, 0.0), (0.84, 0.0), (1.02, -25.0), (1.20, -50.0),
                              (1.42, -66.0), (1.60, -58.0)),
              foot_yaw=held((1.02, 0.0), (1.42, 16.0), (1.95, 34.0)),
              foot_x=held((1.02, 0.0), (1.42, 0.03)),
              knee=held((0.60, 0.0), (0.95, 50.0), (1.20, 130.0), (1.60, 126.0), (1.95, 80.0)))


def _reeled(t):
    return REELED * glide(t, 0.03, 0.12, 0.40, 0.56)


def death(t):
    """Reels two steps back with its arms thrown up, sits down hard, slams onto its back as the legs kick up
    and drop, and lies with its head rolled aside; one hand closes a last time."""
    out = at(FALL, t)
    out.update(travel=_reeled(t), head_level=HEAD_FREE(t))
    left = dict(at(FLAIL, t - 0.06), **_claws(0.35 * max(SLACK(t), 0.0), max(-SLACK(t), 0.0)),
                **_foot(DROP_L, t, trod(t, _reeled, (0.0, -0.22), [(0.34, 0.54, STEPPED)])))
    right = dict(at(FLAIL, t), **_claws(0.35 * max(SLACK(t), 0.0) + 0.6 * TWITCH(t), max(-SLACK(t), 0.0)),
                 **_foot(DROP_R, t, trod(t, _reeled, (0.0, -0.32), [(0.10, 0.32, STEPPED)])))
    left["arm_out"] *= 0.7
    out.update(sided(left, right))
    return borne(out)


MOVES = {"Pounce": (pounce, 1.9, POUNCE), "Swipe": (swipe, 1.2, SWIPE), "Flinch": (flinch, 0.6, {}), "Death": (death, 2.4, {})}
