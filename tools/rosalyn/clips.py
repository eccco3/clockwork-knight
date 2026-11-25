"""Rosalyn's clips, keyed by hand on the controls of `pose`, and the poses that test her skin.

A clip is a function of phase (0..1 from its start to its end) returning controls. Idle and the speech clips
loop, all twelve seconds long and all on the same breathing body, so the game can blend any of them into any
other in step; Blink plays once, on her lids alone, over whatever else she is doing. RESET is how she stands,
which the game blends from.

She speaks without moving her wooden mouth: SPEECH are the clips she talks through, by turns of her head, her
eyes and brows, her shoulders and her hands, which stay clasped but for a lift or a tap.
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


def plus(*poses):
    """Controls added up, pose on pose."""
    return {name: sum(p.get(name, 0.0) for p in poses) for name in set().union(*poses)}


def borne(*poses):
    """The clip's controls on top of how she always stands: her right hand hanging before her, held across its
    knuckles by her left, whose palm and fingertips rest on it."""
    return plus(STANDING, *poses)


# ---------------------------------------------------------------- the body every loop shares

LOOP_SECONDS = 12.0
BREATH = times(3, (0.01, 0.0), (0.13, 1.0), (0.17, 0.9))
WEIGHT = Curve((0.00, 1.0), (0.24, 1.0), (0.335, -1.06), (0.40, -1.0), (0.74, -1.0), (0.835, 1.06), (0.90, 1.0))    # 1 on her left foot
DIP = Curve((0.22, 0.0), (0.285, 1.0), (0.36, 0.0), (0.72, 0.0), (0.785, 1.0), (0.86, 0.0))
SWISH = Curve((0.22, 0.0), (0.29, 1.0), (0.36, -0.45), (0.43, 0.15), (0.50, 0.0), (0.72, 0.0), (0.79, -1.0), (0.86, 0.45),
              (0.93, -0.15), (1.00, 0.0))                          # the skirt left behind as the hips cross, and settling
SACCADE = 0.08 / LOOP_SECONDS


def body(phase):
    """She breathes three times and shifts her weight to her right foot and back."""
    breath, weight = BREATH(phase), WEIGHT(phase)
    out = dict(chest_pitch=-1.2 * breath, spine_pitch=-0.5 * breath, head_level=0.5, head_pitch=-0.3 * breath,
               head_roll=-0.6 * weight, hips_x=0.014 * weight, hips_z=-0.004 * DIP(phase), hips_roll=-2.0 * weight,
               hips_yaw=1.2 * weight, spine_roll=1.5 * weight, chest_roll=1.4 * weight, chest_yaw=-1.0 * weight,
               skirt_x=1.6 * SWISH(phase), hem_x=2.6 * SWISH(phase - 0.02), skirt_twist=-1.2 * weight)
    out.update(both(dict(shoulder_up=0.9 * breath, elbow=1.0 * breath)))
    return out


# ---------------------------------------------------------------- idle

GLANCES = ((0.00, 0.0, 0.0), (0.14, -8.0, -2.0), (0.21, -11.0, -5.0), (0.36, 3.0, 1.0), (0.55, 12.0, 2.5), (0.63, 7.0, -3.0),
           (0.80, 0.0, 0.0))                                       # when her eyes move: to how far left, and how far up
GAZE_YAW, GAZE_UP = (stepped(SACCADE, *((g[0], g[k]) for g in GLANCES)) for k in (1, 2))
TURN = Curve((0.03, 0.0), (0.20, -3.0), (0.30, -4.5), (0.44, 0.5), (0.64, 5.0), (0.76, 3.5), (0.90, 0.0))    # the head, after the eyes
NOD = Curve((0.05, 0.0), (0.28, 1.6), (0.45, -0.4), (0.70, 1.0), (0.88, -0.3))
TILT = Curve((0.10, 0.4), (0.33, -0.6), (0.60, 0.9), (0.85, 0.2))
LOOSEN = Curve((0.46, 0.0), (0.52, 1.0), (0.58, 0.3), (0.64, 0.9), (0.72, 0.0))                             # her left hand's hold


def idle(phase):
    """She looks about her: her head follows her eyes a little and late, and her lids follow them down."""
    turn = TURN(phase)
    out = dict(neck_yaw=0.4 * turn, head_yaw=0.6 * turn, head_pitch=NOD(phase), head_roll=TILT(phase),
               eye_yaw=GAZE_YAW(phase) - turn, eye_up=GAZE_UP(phase), blink=max(0.0, -GAZE_UP(phase)) / 45.0)
    out.update({"curl_%s_l" % finger: -2.0 * LOOSEN(phase - 0.01 * k) for k, finger in enumerate(FINGERS)})
    return borne(body(phase), out)


# ---------------------------------------------------------------- speech

def secs(*keys):
    """A looping curve keyed in seconds of the loop."""
    return Curve(*((t / LOOP_SECONDS, v) for t, v in keys))


BEAT = ((-0.16, 0.0), (0.0, 1.0), (0.38, 0.0))                    # a stressed word's nod: down quickly, back slower


def beats(*hits):
    """A looping curve that dips by each hit's size at its second, quickly, and eases back: what lands on the
    stressed words. Hits stand at least 0.6 s apart."""
    return secs(*((t + dt, size * k) for t, size in hits for dt, k in BEAT))


def glances(*keys):
    """Where her eyes go from the one she speaks to: at each second, how far to her left and how far up."""
    return [stepped(SACCADE, *((t / LOOP_SECONDS, g[k]) for t, *g in keys)) for k in (0, 1)]


def speaking(**say):
    """A speech clip from curves of phase, in degrees but where said: her head turned to her left (`turn`), tilted
    to her left (`tilt`), the chin raised (`chin`) and the nods on her words (`nod`); her eyes' glances away
    (`look`, from `glances`) and her lids lowered (`lids`, 0..1); both brows raised (`brows`, metres), the left
    or the right more (`brow_l`, `brow_r`), and their inner ends lifted (`knit`); her shoulders raised (`shrug`),
    her chest bowed toward the listener (`lean`); her left hand lifted off her right and opened (`lift`, 0..1),
    its fingers raised in a tap (`tap`, 0..1), and both hands' hold tightened (`grip`).
    Her eyes keep to the one she speaks to while her head moves, and her lids follow them down."""
    look = say.pop("look", None)

    def clip(phase):
        c = {name: curve(phase) for name, curve in say.items()}
        g = lambda name: c.get(name, 0.0)
        pitch = g("nod") - g("chin")
        eye_yaw, eye_up = (curve(phase) for curve in look) if look else (0.0, 0.0)
        out = dict(neck_yaw=0.4 * g("turn"), head_yaw=0.6 * g("turn"), head_roll=g("tilt"), head_pitch=pitch,
                   chest_pitch=g("lean"), eye_yaw=eye_yaw - g("turn"), eye_up=eye_up + 0.8 * pitch + 0.5 * g("lean"),
                   blink=g("lids") + max(0.0, -eye_up) / 45.0)
        out.update(sided(dict(brow_up=g("brows") + g("brow_l")), dict(brow_up=g("brows") + g("brow_r"))))
        out.update(both(dict(brow_tilt=g("knit"), shoulder_up=g("shrug"), shoulder_fwd=0.3 * g("shrug"))))
        lift, tap = g("lift"), g("tap")
        out.update(hand_z_l=0.040 * lift, hand_y_l=-0.035 * lift, hand_pitch_l=-22.0 * lift, spread_l=6.0 * lift,
                   thumb_in_l=-10.0 * lift)
        for finger in FINGERS:
            out["curl_%s_l" % finger] = g("grip") - 26.0 * lift - 14.0 * tap
            out["curl_%s_r" % finger] = g("grip")
        return borne(body(phase), out)
    return clip


TELL = speaking(                                    # an even telling: she recalls, then sets it out word by word
    turn=secs((0.0, 0.0), (1.2, -2.0), (3.4, -3.0), (4.4, 1.5), (7.4, 3.0), (8.6, 0.5), (11.0, -1.0)),
    tilt=secs((0.0, 1.0), (1.6, 4.0), (3.3, 3.5), (4.6, -2.5), (7.5, -3.0), (8.7, 1.0), (10.8, 2.0)),
    nod=beats((1.5, 2.5), (2.6, 2.0), (3.3, 1.5), (5.0, 2.5), (6.1, 2.0), (7.2, 1.5), (9.4, 2.5), (10.3, 2.0), (11.1, 3.0)),
    chin=secs((0.0, 0.0), (8.2, 0.0), (8.6, 2.0), (9.2, 1.0), (10.0, 0.0)),
    look=glances((0.3, -8.0, 4.0), (1.1, 0.0, 0.0), (4.3, 6.0, -3.0), (4.9, 0.0, 0.0), (8.2, -5.0, 6.0), (8.7, 0.0, 0.0)),
    brows=secs((0.0, 0.0), (1.1, 0.0), (1.4, 0.0040), (2.2, 0.0010), (3.6, 0.0), (8.4, 0.0), (8.8, 0.0050), (9.8, 0.0022),
               (11.0, 0.0)),
    knit=secs((0.0, 0.0), (4.8, 0.0), (5.2, 9.0), (6.2, 5.0), (7.6, 0.0)),
    shrug=secs((0.0, 0.0), (6.0, 0.0), (6.4, 3.0), (7.0, 0.5), (7.6, 0.0)),
    lean=secs((0.0, 0.0), (0.4, -1.0), (1.5, 1.0), (3.6, 0.5), (4.2, -0.8), (5.0, 1.2), (7.8, 0.4), (8.3, -1.0), (9.4, 1.5),
              (11.6, 0.0)),
    lift=secs((0.0, 0.0), (5.4, 0.0), (5.9, 1.0), (6.9, 0.8), (7.5, 0.0)))

ASK = speaking(                                     # a question: her head on one side, a brow up, her chin raised at the end
    turn=secs((0.0, 1.0), (1.0, 3.0), (3.6, 4.0), (4.6, 1.0), (7.6, -1.5), (8.4, -2.5), (11.4, 1.0)),
    tilt=secs((0.0, -1.0), (0.8, -2.0), (2.8, -6.0), (3.8, -5.5), (4.8, -1.5), (7.6, -1.0), (8.6, 4.0), (10.6, 6.5),
              (11.6, 1.0)),
    chin=secs((0.0, 0.0), (2.8, 0.0), (3.3, 3.5), (3.9, 3.0), (4.6, 0.0), (9.9, 0.0), (10.5, 4.0), (11.2, 3.0), (11.8, 0.0)),
    nod=beats((1.6, 2.0), (5.2, 2.5), (6.0, 2.0), (7.0, 1.5), (9.0, 2.0)),
    look=glances((0.6, -4.0, 5.0), (1.0, 0.0, 0.0), (5.5, 9.0, -7.0), (6.4, 0.0, 0.0)),
    lids=secs((0.0, 0.0), (5.5, 0.0), (5.8, 0.12), (6.4, 0.0)),
    brows=secs((0.0, 0.0012), (1.0, 0.0025), (2.9, 0.0035), (3.4, 0.0035), (4.6, 0.0008), (6.8, 0.0012), (9.9, 0.0020),
               (10.4, 0.0060), (11.2, 0.0052), (11.8, 0.0016)),
    brow_l=secs((0.0, 0.0), (1.0, 0.0), (1.5, 0.0025), (3.6, 0.0025), (4.4, 0.0)),
    knit=secs((0.0, 3.0), (2.0, 5.0), (4.6, 2.0), (5.0, 10.0), (6.6, 8.0), (7.6, 2.5), (10.4, 7.0), (11.6, 3.0)),
    shrug=secs((0.0, 0.0), (10.0, 0.0), (10.5, 2.5), (11.3, 1.5), (11.9, 0.0)),
    lean=secs((0.0, 0.5), (1.5, 2.0), (3.6, 2.5), (4.6, 0.5), (8.0, 0.0), (10.4, 1.5), (11.8, 0.5)))

MUSE = speaking(                                    # warm and thoughtful: soft lids, a look down and away, a shrug
    turn=secs((0.0, -1.0), (2.0, -4.0), (3.6, -2.0), (5.0, 1.5), (7.4, 2.0), (9.6, 0.0), (11.2, -1.0)),
    tilt=secs((0.0, 2.0), (1.8, 5.0), (3.8, 4.0), (5.0, -1.0), (7.6, -4.0), (9.0, 6.0), (10.4, 5.0), (11.6, 2.0)),
    chin=secs((0.0, 0.0), (0.8, -1.5), (2.2, -3.0), (3.0, 0.0)),
    nod=beats((3.4, 1.5), (6.6, 2.0), (10.9, 2.5)),
    look=glances((0.6, -10.0, -6.0), (2.4, 0.0, 0.0), (7.8, 7.0, 3.0), (8.3, 0.0, 0.0)),
    lids=secs((0.0, 0.18), (3.0, 0.22), (6.0, 0.15), (9.0, 0.20), (11.0, 0.18)),
    brows=secs((0.0, 0.0008), (4.6, 0.0012), (5.2, 0.0032), (6.0, 0.0016), (8.8, 0.0016), (9.2, 0.0050), (10.2, 0.0024),
               (11.6, 0.0008)),
    knit=secs((0.0, 5.0), (2.0, 7.0), (4.0, 3.0), (9.2, 10.0), (10.4, 7.0), (11.6, 5.0)),
    shrug=secs((0.0, 0.0), (8.8, 0.0), (9.3, 4.5), (10.0, 4.0), (10.6, 0.5), (11.0, 0.0)),
    lean=secs((0.0, 0.0), (1.8, 1.2), (4.0, 0.3), (9.3, -1.0), (10.6, 0.0)),
    tap=secs((0.0, 0.0), (4.8, 0.0), (5.0, 1.0), (5.2, 0.0), (5.6, 1.0), (5.8, 0.0)))

INSIST = speaking(                                  # firm: brows down, short hard nods, a shake of the head, the hold tightening
    turn=secs((0.0, 0.0), (1.0, -1.5), (3.5, -2.0), (4.5, 0.0), (4.85, 4.0), (5.15, -4.0), (5.45, 3.0), (5.75, -2.0),
              (6.0, 0.0), (8.0, 0.5), (11.5, 0.0)),
    tilt=secs((0.0, 0.5), (2.0, -1.0), (4.0, 0.0), (6.4, 2.0), (8.0, 0.5), (11.0, -0.5)),
    chin=secs((0.0, 0.0), (0.4, 1.5), (1.0, 0.5), (3.6, 0.0), (6.2, 2.0), (7.2, 0.0)),
    nod=beats((1.2, 4.0), (1.9, 3.0), (2.6, 3.5), (6.6, 3.0), (9.0, 3.5), (9.8, 3.5), (10.6, 4.5)),
    look=glances((3.7, -6.0, -4.0), (4.2, 0.0, 0.0)),
    brows=secs((0.0, 0.0), (0.8, -0.0022), (2.9, -0.0022), (3.6, 0.0), (6.2, 0.0), (6.5, 0.0045), (7.3, 0.0015),
               (8.4, -0.0012), (11.0, -0.0022), (11.6, 0.0)),
    knit=secs((0.0, 0.0), (0.8, -9.0), (2.9, -7.0), (3.6, 0.0), (8.4, -5.0), (11.0, -9.0), (11.6, 0.0)),
    shrug=secs((0.0, 0.0), (0.4, 1.5), (1.4, 0.0)),
    lean=secs((0.0, 0.0), (0.4, -1.5), (1.2, 1.5), (3.0, 1.0), (4.0, 0.0), (6.4, 2.5), (7.4, 1.5), (8.4, 0.5), (10.6, 2.0),
              (11.6, 0.0)),
    grip=secs((0.0, 0.0), (6.3, 0.0), (6.6, 6.0), (7.8, 4.0), (8.4, 0.0)))

SPEECH = {"Tell": TELL, "Ask": ASK, "Muse": MUSE, "Insist": INSIST}

# ---------------------------------------------------------------- blink

BLINK_SECONDS = 0.30
SHUT = held((0.07, 1.0), (0.11, 1.0), (0.20, 0.25), (0.30, 0.0))


def blink(phase):
    return dict(blink=SHUT(phase * BLINK_SECONDS))


LOOP = round(LOOP_SECONDS * FPS)
CLIPS = {"Idle": (idle, LOOP), **{name: (clip, LOOP) for name, clip in SPEECH.items()},
         "Blink": (blink, round(BLINK_SECONDS * FPS)), "RESET": (lambda phase: STANDING, 1)}

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
