"""Rosalyn's clips, keyed by hand on the controls of `pose`, and the poses that test her skin.

A clip is a function of phase (0..1 from its start to its end) returning controls. Idle loops; Blink plays
once, on her lids alone, over whatever else she is doing.
"""
from sculpt.keys import FPS, Curve, times, stepped, held, sided, both
from .body import FINGERS

# ---------------------------------------------------------------- how she stands

_ARM = dict(elbow=40.0, shoulder_up=-6.0, shoulder_fwd=4.0, spread=-8.0)
STANDING = dict(sided(dict(_ARM, hand_x=-0.257, hand_y=-0.1188, hand_z=0.054, hand_yaw=65.0, hand_roll=65.0, curl_pinky=38.5,
                           curl_ring=37.0, curl_middle=34.0, curl_index=31.0, thumb_lift=20.0, thumb_curl=8.0, thumb_in=12.0),
                      dict(_ARM, hand_x=-0.289, hand_y=-0.078, hand_z=0.107, hand_yaw=90.0, hand_roll=30.0, hand_pitch=10.0,
                           curl_pinky=20.0, curl_ring=18.0, curl_middle=16.0, curl_index=14.0, thumb_lift=-10.0, thumb_in=28.0)),
                hips_z=-0.003, skirt_hang=1.0)


def borne(controls):
    """The clip's controls on top of how she always stands: her right hand hanging before her, held across its
    knuckles by her left, whose palm and fingertips rest on it."""
    return {name: controls.get(name, 0.0) + STANDING.get(name, 0.0) for name in {*controls, *STANDING}}


# ---------------------------------------------------------------- idle

IDLE_SECONDS = 12.0
BREATH = times(3, (0.01, 0.0), (0.13, 1.0), (0.17, 0.9))
WEIGHT = Curve((0.00, 1.0), (0.24, 1.0), (0.335, -1.06), (0.40, -1.0), (0.74, -1.0), (0.835, 1.06), (0.90, 1.0))    # 1 on her left foot
DIP = Curve((0.22, 0.0), (0.285, 1.0), (0.36, 0.0), (0.72, 0.0), (0.785, 1.0), (0.86, 0.0))
SWISH = Curve((0.22, 0.0), (0.29, 1.0), (0.36, -0.45), (0.43, 0.15), (0.50, 0.0), (0.72, 0.0), (0.79, -1.0), (0.86, 0.45),
              (0.93, -0.15), (1.00, 0.0))                          # the skirt left behind as the hips cross, and settling
SACCADE = 0.08 / IDLE_SECONDS
GLANCES = ((0.00, 0.0, 0.0), (0.14, -8.0, -2.0), (0.21, -11.0, -5.0), (0.36, 3.0, 1.0), (0.55, 12.0, 2.5), (0.63, 7.0, -3.0),
           (0.80, 0.0, 0.0))                                       # when her eyes move: to how far left, and how far up
GAZE_YAW, GAZE_UP = (stepped(SACCADE, *((g[0], g[k]) for g in GLANCES)) for k in (1, 2))
TURN = Curve((0.03, 0.0), (0.20, -3.0), (0.30, -4.5), (0.44, 0.5), (0.64, 5.0), (0.76, 3.5), (0.90, 0.0))    # the head, after the eyes
NOD = Curve((0.05, 0.0), (0.28, 1.6), (0.45, -0.4), (0.70, 1.0), (0.88, -0.3))
TILT = Curve((0.10, 0.4), (0.33, -0.6), (0.60, 0.9), (0.85, 0.2))
LOOSEN = Curve((0.46, 0.0), (0.52, 1.0), (0.58, 0.3), (0.64, 0.9), (0.72, 0.0))                             # her left hand's hold


def idle(phase):
    """She breathes three times, shifts her weight to her right foot and back, and looks about her: her head
    follows her eyes a little and late, and her lids follow them down."""
    breath, weight, turn = BREATH(phase), WEIGHT(phase), TURN(phase)
    out = dict(chest_pitch=-1.2 * breath, spine_pitch=-0.5 * breath, head_level=0.5,
               hips_x=0.014 * weight, hips_z=-0.004 * DIP(phase), hips_roll=-2.0 * weight, hips_yaw=1.2 * weight,
               spine_roll=1.5 * weight, chest_roll=1.4 * weight, chest_yaw=-1.0 * weight,
               skirt_x=1.6 * SWISH(phase), hem_x=2.6 * SWISH(phase - 0.02), skirt_twist=-1.2 * weight,
               neck_yaw=0.4 * turn, head_yaw=0.6 * turn, head_pitch=NOD(phase) - 0.3 * breath,
               head_roll=TILT(phase) - 0.6 * weight, eye_yaw=GAZE_YAW(phase) - turn, eye_up=GAZE_UP(phase),
               blink=max(0.0, -GAZE_UP(phase)) / 45.0)
    out.update(both(dict(shoulder_up=0.9 * breath, elbow=1.0 * breath)))
    out.update({"curl_%s_l" % finger: -2.0 * LOOSEN(phase - 0.01 * k) for k, finger in enumerate(FINGERS)})
    return borne(out)


# ---------------------------------------------------------------- blink

BLINK_SECONDS = 0.30
SHUT = held((0.07, 1.0), (0.11, 1.0), (0.20, 0.25), (0.30, 0.0))


def blink(phase):
    return dict(blink=SHUT(phase * BLINK_SECONDS))


CLIPS = {"Idle": (idle, round(IDLE_SECONDS * FPS)), "Blink": (blink, round(BLINK_SECONDS * FPS))}

# ---------------------------------------------------------------- poses that test the skin

POSES = {
    "stand": STANDING,
    "asleep": borne(dict(blink=1.0, head_pitch=12.0)),
    "glance": borne(dict(eye_yaw=22.0, eye_up=-8.0, blink=0.4, head_yaw=-25.0, head_roll=8.0, neck_yaw=-10.0)),
    "bow": borne(dict(hips_pitch=14.0, spine_pitch=12.0, chest_pitch=10.0, head_pitch=16.0, hips_y=0.03)),
    "sway": borne(dict(hips_x=0.03, hips_roll=5.0, spine_roll=-4.0, chest_roll=-5.0, skirt_x=-6.0, hem_x=-8.0, skirt_twist=8.0)),
    "open": dict(both(dict(hand_x=-0.13, hand_y=-0.26, hand_z=0.17, hand_yaw=-90.0, hand_pitch=75.0, spread=6.0)),
                 skirt_hang=1.0),
    "grip": both(dict(curl_pinky=75.0, curl_ring=75.0, curl_middle=75.0, curl_index=75.0, thumb_curl=35.0, thumb_in=25.0,
                      thumb_lift=20.0)),
    "raise": dict(sided(dict(hand_x=0.20, hand_y=-0.02, hand_z=0.50, hand_roll=-90.0, spread=8.0),
                        dict(hand_x=-0.01, hand_y=-0.05, hand_z=0.55, hand_yaw=90.0, hand_pitch=160.0, curl_index=-6.0, curl_middle=35.0,
                             curl_ring=50.0, curl_pinky=55.0, thumb_curl=30.0)),
                  skirt_hang=1.0),
}
