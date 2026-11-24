"""The grinner's clips, keyed by hand on the controls of `pose`, and the poses that test its skin.

A clip is a function of phase (0..1 round its loop) returning controls. Its keys are (phase, value) pairs on
looping curves that ease from key to key without overshooting, so a held value stays held.
"""
import numpy as np

STRIDE = 0.46                                  # metres walked in one waddle cycle
PLANTED = 0.64                                 # the share of the cycle each foot stands


class Curve:
    def __init__(self, *keys, loop=True):
        t, v = np.array(sorted(keys), dtype=np.float64).T
        if loop:
            t, v = np.concatenate([t - 1.0, t, t + 1.0]), np.tile(v, 3)
        else:
            t, v = np.concatenate([t[:1] - 1.0, t, t[-1:] + 1.0]), np.concatenate([v[:1], v, v[-1:]])
        h, rise = np.diff(t), np.diff(v) / np.diff(t)
        slope = np.zeros(len(t))
        eases = rise[:-1] * rise[1:] > 0
        with np.errstate(divide="ignore", invalid="ignore"):
            mean = 3.0 * (h[:-1] + h[1:]) / ((2.0 * h[1:] + h[:-1]) / rise[:-1] + (h[1:] + 2.0 * h[:-1]) / rise[1:])
        slope[1:-1] = np.where(eases, mean, 0.0)
        self.loop, self.t, self.v, self.slope = loop, t, v, slope

    def __call__(self, phase):
        x = phase % 1.0 if self.loop else float(np.clip(phase, self.t[1], self.t[-2]))
        i = int(np.clip(np.searchsorted(self.t, x, side="right") - 1, 0, len(self.t) - 2))
        h = self.t[i + 1] - self.t[i]
        s = (x - self.t[i]) / h
        return (2 * s ** 3 - 3 * s ** 2 + 1) * self.v[i] + (s ** 3 - 2 * s ** 2 + s) * h * self.slope[i] \
            + (-2 * s ** 3 + 3 * s ** 2) * self.v[i + 1] + (s ** 3 - s ** 2) * h * self.slope[i + 1]


def twice(*keys):
    """Keys for half the loop, repeated in the other half."""
    return Curve(*keys, *((t + 0.5, v) for t, v in keys))


def swaying(*keys):
    """Keys for half the loop, mirrored in the other half."""
    return Curve(*keys, *((t + 0.5, -v) for t, v in keys))


def sided(left, right):
    out = {name + "_l": value for name, value in left.items()}
    out.update({name + "_r": value for name, value in right.items()})
    return out


# ---------------------------------------------------------------- waddle

CARRIED = Curve((0.0, 0.0), (0.42, 0.50), (0.80, 0.94), (1.0, 1.0), loop=False)
STEP = dict(foot_z=Curve((0.0, 0.0), (PLANTED, 0.0), (0.80, 0.050), (0.93, 0.022)),
            foot_pitch=Curve((0.0, -7.0), (0.06, 0.0), (0.44, 0.0), (PLANTED, 24.0), (0.73, 32.0), (0.84, 8.0), (0.94, -9.0)),
            foot_x=Curve((0.0, 0.012), (PLANTED, 0.012), (0.82, 0.040)),
            foot_yaw=Curve((0.0, 4.0), (PLANTED, 4.0), (0.80, 10.0)),
            knee=Curve((0.0, 2.0), (PLANTED, 0.0), (0.80, 10.0)))
TOES_DOWN = Curve((0.0, 1.0), (PLANTED, 1.0), (0.72, 0.0), (0.97, 0.0))
TOES_LOOSE = Curve((0.0, 0.0), (PLANTED, 0.0), (0.76, -10.0), (0.93, 8.0))
SWING = dict(arm_fwd=Curve((0.07, -5.0), (0.57, 17.0)),
             elbow=Curve((0.20, 8.0), (0.68, 26.0)),
             wrist_curl=Curve((0.33, 2.0), (0.84, 20.0)),
             shoulder_up=Curve((0.30, 5.0), (0.80, -2.0)),
             shoulder_fwd=Curve((0.07, -3.0), (0.57, 5.0)),
             curl_pinky=Curve((0.44, 20.0), (0.94, 36.0)), curl_ring=Curve((0.42, 16.0), (0.92, 31.0)),
             curl_middle=Curve((0.40, 13.0), (0.90, 28.0)), curl_index=Curve((0.38, 10.0), (0.88, 24.0)),
             thumb_curl=Curve((0.40, 6.0), (0.90, 16.0)))
ROCK = dict(hips_x=swaying((0.06, 0.0), (0.24, 0.046), (0.40, 0.050)),
            hips_roll=swaying((0.08, 0.0), (0.30, 6.5), (0.42, 6.0)),
            hips_yaw=swaying((0.04, -7.0), (0.30, 0.0)),
            hips_z=twice((0.09, -0.034), (0.34, -0.012)),
            hips_y=twice((0.10, 0.008), (0.36, -0.006)),
            hips_pitch=twice((0.10, 8.5), (0.36, 5.5)),
            spine_roll=swaying((0.12, 0.0), (0.34, 2.5)),
            chest_roll=swaying((0.15, 0.0), (0.37, 3.0)),
            spine_yaw=swaying((0.08, 5.0), (0.33, 0.0)),
            chest_yaw=swaying((0.10, 7.0), (0.35, 0.0)),
            chest_pitch=twice((0.14, 4.0), (0.40, 2.0)),
            head_pitch=twice((0.17, 1.0), (0.42, -3.0)),
            head_roll=swaying((0.20, 0.0), (0.44, -2.5)))


def _step(phase):
    phase = phase % 1.0
    out = {name: curve(phase) for name, curve in STEP.items()}
    out["foot_y"] = STRIDE * (phase - 0.5 * PLANTED - CARRIED((phase - PLANTED) / (1.0 - PLANTED)))
    out["toe"] = max(out["foot_pitch"], 0.0) * TOES_DOWN(phase) + TOES_LOOSE(phase)
    return out


def _swing(phase):
    return dict({name: curve(phase) for name, curve in SWING.items()}, arm_out=-9.0, arm_hang=0.75, spread=4.0)


def waddle(phase):
    """Left foot planted at phase 0, right at 0.5; each arm swings with the other side's leg."""
    out = {name: curve(phase) for name, curve in ROCK.items()}
    out.update(sided(_step(phase), _step(phase + 0.5)))
    out.update(sided(_swing(phase), _swing(phase + 0.5)))
    out.update(travel=STRIDE * phase, head_level=0.85, head_roll=out["head_roll"] + 4.0)
    return out


# ---------------------------------------------------------------- idle

BREATH = twice((0.02, 0.0), (0.20, 1.0), (0.27, 0.9))
STAND = dict(hips_x=Curve((0.12, 0.014), (0.40, 0.016), (0.62, -0.010), (0.92, -0.012)),
             hips_roll=Curve((0.14, 1.8), (0.42, 2.0), (0.64, -1.2), (0.94, -1.4)),
             hips_yaw=Curve((0.16, -1.5), (0.66, 1.5)),
             head_roll=Curve((0.00, 3.0), (0.33, 4.0), (0.37, 15.0), (0.40, 13.5), (0.72, 13.0), (0.84, 3.0)),
             head_yaw=Curve((0.00, 0.0), (0.33, 1.0), (0.37, -9.0), (0.41, -7.5), (0.72, -7.0), (0.86, 0.0)),
             head_pitch=Curve((0.00, -2.0), (0.33, -2.0), (0.38, 3.0), (0.72, 2.0), (0.86, -2.0)),
             neck_roll=Curve((0.34, 1.0), (0.40, 5.0), (0.72, 5.0), (0.86, 1.0)))
DRUM = Curve((0.00, 0.0), (0.05, 1.0), (0.10, 0.15), (0.14, 0.0), (0.99, 0.0))
FINGERS = dict(pinky=(24.0, 0.00), ring=(19.0, 0.025), middle=(16.0, 0.05), index=(13.0, 0.075))


def _hand(phase, drum_at):
    out = {"curl_" + name: curl + 34.0 * DRUM(phase - drum_at - lag) for name, (curl, lag) in FINGERS.items()}
    out.update(thumb_curl=8.0 + 10.0 * DRUM(phase - drum_at - 0.09), wrist_curl=10.0 + 5.0 * DRUM(phase - drum_at - 0.04),
               elbow=10.0, arm_out=-9.0, arm_fwd=4.0, arm_hang=0.8, spread=4.0)
    return out


def idle(phase):
    breath = BREATH(phase)
    out = {name: curve(phase) for name, curve in STAND.items()}
    out.update(sided(_hand(phase, 0.14), _hand(phase, 0.62)))
    out.update(sided(dict(foot_x=0.012, foot_yaw=4.0, shoulder_up=2.5 * breath), dict(foot_x=0.012, foot_yaw=4.0, shoulder_up=2.5 * breath)))
    out.update(hips_z=-0.016 - 0.004 * breath, hips_pitch=5.0 - 0.8 * breath, spine_pitch=-1.4 * breath,
               chest_pitch=2.0 - 2.2 * breath, head_level=0.6)
    return out


CLIPS = {"Idle": (idle, 180), "Waddle": (waddle, 48)}

# ---------------------------------------------------------------- poses that test the skin

CLAWED = dict(curl_pinky=70.0, curl_ring=70.0, curl_middle=70.0, curl_index=70.0, thumb_curl=40.0, thumb_in=20.0)
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
    "claw": sided(dict(CLAWED, wrist_curl=25.0), dict(SPLAYED, wrist_curl=-20.0)),
    "splay": sided(dict(SPLAYED, wrist_curl=-20.0), dict(CLAWED, wrist_curl=25.0)),
}
