"""The walking grinner: its looping clips, keyed by hand on the controls of `pose`, and the poses that test its
skin. Idle and Waddle loop; the moves of `moves` play once, and their marks say when their windows open and close.
"""
from .body import FINGERS
from .keys import Curve, Kind, twice, swaying, sided, both, borne
from .moves import MOVES

STRIDE = 0.46                                  # metres walked in one waddle cycle
PLANTED = 0.64                                 # the share of the cycle each foot stands

# ---------------------------------------------------------------- waddle

CARRIED = Curve((0.0, 0.0), (0.42, 0.50), (0.80, 0.94), (1.0, 1.0), loop=False)
STEP = dict(foot_z=Curve((0.0, 0.0), (PLANTED, 0.0), (0.80, 0.065), (0.93, 0.028)),
            foot_pitch=Curve((0.0, -5.0), (0.05, 0.0), (0.44, 0.0), (PLANTED, 24.0), (0.73, 32.0), (0.84, 8.0), (0.94, -8.0)),
            foot_x=Curve((0.0, 0.0), (PLANTED, 0.0), (0.82, 0.028)),
            foot_yaw=Curve((0.0, 0.0), (PLANTED, 0.0), (0.80, 6.0)),
            knee=Curve((0.0, 2.0), (PLANTED, 0.0), (0.80, 10.0)))
TOES_DOWN = Curve((0.0, 1.0), (PLANTED, 1.0), (0.78, 0.0), (0.97, 0.0))
TOES_LOOSE = Curve((0.0, 0.0), (PLANTED, 0.0), (0.76, -10.0), (0.93, 8.0))
DRAG = Curve((0.38, -5.0), (0.88, 12.0))
SWING = dict(arm_fwd=Curve((0.07, -14.0), (0.57, 6.0)),
             arm_out=Curve((0.02, -3.0), (0.52, 6.0)),
             elbow=Curve((0.20, -3.0), (0.68, 11.0)),
             wrist_curl=Curve((0.33, -6.0), (0.84, 12.0)),
             shoulder_up=Curve((0.30, 5.0), (0.80, -2.0)),
             shoulder_fwd=Curve((0.07, -3.0), (0.57, 5.0)))
ROCK = dict(hips_x=swaying((0.00, 0.004), (0.14, 0.040), (0.30, 0.052), (0.42, 0.042)),
            hips_roll=swaying((0.02, 0.0), (0.18, 6.5), (0.32, 7.5), (0.44, 5.0)),
            hips_yaw=swaying((0.04, -7.0), (0.30, 0.0)),
            hips_z=twice((0.09, -0.004), (0.34, 0.010)),
            hips_y=twice((0.10, 0.008), (0.36, -0.006)),
            hips_pitch=twice((0.10, 1.5), (0.36, -1.0)),
            spine_roll=swaying((0.06, 0.0), (0.36, 2.5)),
            chest_roll=swaying((0.09, 0.0), (0.39, 3.0)),
            spine_yaw=swaying((0.08, 4.0), (0.33, 0.0)),
            chest_yaw=swaying((0.10, 5.0), (0.35, 0.0)),
            chest_pitch=twice((0.14, 1.5), (0.40, -0.5)),
            head_pitch=twice((0.17, 1.0), (0.42, -3.0)),
            head_roll=swaying((0.14, 0.0), (0.44, -2.5)))


def _step(phase):
    phase = phase % 1.0
    out = {name: curve(phase) for name, curve in STEP.items()}
    out["foot_y"] = STRIDE * (phase - 0.5 * PLANTED - CARRIED((phase - PLANTED) / (1.0 - PLANTED)))
    out["toe"] = max(out["foot_pitch"], 0.0) * TOES_DOWN(phase) + TOES_LOOSE(phase)
    return out


def _swing(phase):
    out = {name: curve(phase) for name, curve in SWING.items()}
    out.update({"curl_" + name: DRAG(phase - 0.02 * k) for k, name in enumerate(FINGERS)})
    return out


def waddle(phase):
    """Left foot planted at phase 0, right at 0.5; each arm swings with the other side's leg."""
    out = {name: curve(phase) for name, curve in ROCK.items()}
    out.update(sided(_step(phase), _step(phase + 0.5)))
    out.update(sided(_swing(phase), _swing(phase + 0.5)))
    out.update(travel=STRIDE * phase, head_level=0.85)
    return borne(out)


# ---------------------------------------------------------------- idle

BREATH = twice((0.02, 0.0), (0.20, 1.0), (0.27, 0.9))
STAND = dict(hips_x=Curve((0.12, 0.014), (0.40, 0.016), (0.62, -0.010), (0.92, -0.012)),
             hips_roll=Curve((0.14, 1.8), (0.42, 2.0), (0.64, -1.2), (0.94, -1.4)),
             hips_yaw=Curve((0.16, -1.5), (0.66, 1.5)),
             chest_roll=Curve((0.20, 1.0), (0.70, -1.0)),
             head_roll=Curve((0.00, -1.0), (0.33, 0.0), (0.37, 11.0), (0.40, 9.5), (0.72, 9.0), (0.84, -1.0)),
             head_yaw=Curve((0.00, 0.0), (0.33, 1.0), (0.37, -9.0), (0.41, -7.5), (0.72, -7.0), (0.86, 0.0)),
             head_pitch=Curve((0.00, -2.0), (0.33, -2.0), (0.38, 3.0), (0.72, 2.0), (0.86, -2.0)),
             neck_roll=Curve((0.34, -1.0), (0.40, 3.0), (0.72, 3.0), (0.86, -1.0)))
DRUM = Curve((0.00, 0.0), (0.05, 1.0), (0.10, 0.15), (0.14, 0.0), (0.99, 0.0))
LOLL = Curve((0.30, 1.0), (0.80, -1.0))


def _hand(phase, breath):
    """The arm lolls, and now and then its claws close one after another, little finger first."""
    out = {"curl_" + name: 34.0 * DRUM(phase - 0.025 * k) for k, name in enumerate(FINGERS)}
    out.update(thumb_curl=10.0 * DRUM(phase - 0.09), wrist_curl=5.0 * DRUM(phase - 0.04) + 3.0 * LOLL(phase - 0.08),
               arm_fwd=-5.0 + 2.5 * LOLL(phase), arm_out=-4.0 + 1.5 * LOLL(phase + 0.2), elbow=2.0 * LOLL(phase - 0.05),
               shoulder_up=3.0 * breath)
    return out


def idle(phase):
    breath = BREATH(phase)
    out = {name: curve(phase) for name, curve in STAND.items()}
    out.update(sided(_hand(phase - 0.14, breath), _hand(phase - 0.62, breath)))
    out.update(hips_z=-0.004 * breath, hips_pitch=0.8 - 0.8 * breath, spine_pitch=-1.6 * breath, chest_pitch=1.0 - 2.8 * breath,
               head_level=0.6)
    return borne(out)


# ---------------------------------------------------------------- poses that test the skin

CLAWED = dict(curl_pinky=70.0, curl_ring=70.0, curl_middle=70.0, curl_index=70.0, thumb_curl=70.0, thumb_in=20.0)
SPLAYED = dict(curl_pinky=-8.0, curl_ring=-8.0, curl_middle=-8.0, curl_index=-8.0, spread=16.0, thumb_in=-25.0)
POSES = {
    "crouch": dict(sided(dict(CLAWED, arm_fwd=55.0, elbow=70.0, foot_x=0.03, foot_yaw=12.0, knee=8.0),
                         dict(SPLAYED, arm_fwd=70.0, elbow=35.0, wrist_curl=-30.0, foot_x=0.03, foot_yaw=12.0, knee=8.0)),
                   hips_z=-0.17, hips_y=0.03, hips_pitch=24.0, chest_pitch=10.0, head_pitch=-26.0),
    "stride": dict(sided(dict(foot_y=-0.20, foot_pitch=-12.0, arm_fwd=-38.0, elbow=10.0, arm_out=-8.0),
                         dict(foot_y=0.21, foot_pitch=38.0, toe=38.0, arm_fwd=48.0, elbow=45.0, arm_out=-8.0)),
                   hips_z=-0.05, hips_yaw=-14.0, hips_roll=4.0, spine_yaw=10.0, chest_yaw=12.0, hips_pitch=8.0),
    "reach": dict(sided(dict(SPLAYED, arm_out=65.0, shoulder_up=18.0, elbow=20.0, wrist_curl=-20.0),
                        dict(CLAWED, arm_fwd=120.0, arm_out=10.0, shoulder_up=12.0, shoulder_fwd=14.0, elbow=30.0)),
                  chest_roll=-8.0, spine_roll=-5.0, chest_yaw=12.0, head_yaw=-25.0, head_roll=14.0),
    "kick": dict(sided(dict(foot_y=-0.20, foot_z=0.26, foot_pitch=30.0, knee=14.0, arm_out=25.0),
                       dict(arm_out=18.0, arm_fwd=-20.0, foot_pitch=0.0)),
                 hips_x=-0.05, hips_roll=-7.0, hips_z=-0.02, spine_roll=5.0, chest_roll=5.0, hips_pitch=-6.0),
    "claw": both(dict(CLAWED, wrist_curl=25.0)),
    "splay": both(dict(SPLAYED, wrist_curl=-20.0)),
}

GRINNER = Kind("grinner", {"Idle": (idle, 180), "Waddle": (waddle, 48)}, MOVES, POSES)
