"""Rosalyn's clips, keyed by hand on the controls of `pose`, and the poses that test her skin.

A clip is a function of phase (0..1 from its start to its end) returning controls. Idle loops; Blink plays
once, on her lids alone, over whatever else she is doing.
"""
from sculpt.keys import FPS, Curve, times, held, sided, both
from .body import FINGERS

# ---------------------------------------------------------------- how she stands

_HELD = dict(hand_yaw=90.0, hand_roll=48.0, hand_pitch=10.0, elbow=10.0)
STANDING = dict(sided(dict(_HELD, hand_x=-0.2895, hand_y=-0.104, hand_z=0.082, curl_pinky=44.0, curl_ring=40.0, curl_middle=31.0,
                           curl_index=24.0, thumb_lift=22.0),
                      dict(_HELD, hand_x=-0.3005, hand_y=-0.077, hand_z=0.069, curl_pinky=16.0, curl_ring=14.0, curl_middle=12.0,
                           curl_index=10.0, spread=-4.0)),
                hips_z=-0.006, skirt_hang=1.0)


def borne(controls):
    """The clip's controls on top of how she always stands: hands clasped before her, the left over the right."""
    return {name: controls.get(name, 0.0) + STANDING.get(name, 0.0) for name in {*controls, *STANDING}}


# ---------------------------------------------------------------- idle

BREATH = times(3, (0.01, 0.0), (0.13, 1.0), (0.17, 0.9))


def idle(phase):
    breath = BREATH(phase)
    return borne(dict(chest_pitch=-1.2 * breath, spine_pitch=-0.5 * breath, head_level=0.5))


# ---------------------------------------------------------------- blink

BLINK_SECONDS = 0.30
SHUT = held((0.07, 1.0), (0.11, 1.0), (0.20, 0.25), (0.30, 0.0))


def blink(phase):
    return dict(blink=SHUT(phase * BLINK_SECONDS))


CLIPS = {"Idle": (idle, 360), "Blink": (blink, round(BLINK_SECONDS * FPS))}

# ---------------------------------------------------------------- poses that test the skin

POSES = {
    "stand": STANDING,
    "asleep": borne(dict(blink=1.0, head_pitch=12.0)),
    "glance": borne(dict(eye_yaw=22.0, eye_up=-8.0, blink=0.4, head_yaw=-25.0, head_roll=8.0, neck_yaw=-10.0)),
    "bow": borne(dict(hips_pitch=14.0, spine_pitch=12.0, chest_pitch=10.0, head_pitch=16.0, hips_y=0.03)),
    "sway": borne(dict(hips_x=0.03, hips_roll=5.0, spine_roll=-4.0, chest_roll=-5.0, skirt_x=-6.0, hem_x=-8.0, skirt_twist=8.0)),
    "open": dict(sided(dict(hand_x=-0.10, hand_y=-0.22, hand_z=0.25, hand_yaw=-60.0, hand_pitch=40.0, spread=10.0),
                       dict(hand_x=0.05, hand_y=-0.05, hand_z=0.40, hand_yaw=30.0, shoulder_up=12.0, curl_index=-8.0,
                            curl_middle=40.0, curl_ring=55.0, curl_pinky=60.0, thumb_curl=30.0)),
                 chest_yaw=10.0, skirt_hang=1.0),
}
