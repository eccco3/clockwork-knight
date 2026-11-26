"""How a guard floats over a joint: the knight's pauldron over her shoulder.

A guard's bone lies on its limb's at rest. It hangs from a riser, a bone far from it whose parent is the limb's,
so both turn about the joint. The guard turns as its limb has turned from rest. Where it would then come within
CLEAR of the body under it, or closer than it rests, it rides off the body: it turns on past its limb or stops
short of it, by as much as LEAD of the limb's turn, and the riser turns about its x and carries it up. It rides as
little as keeps it that clear of the body and of its limb, or else as leaves it least far into either, a turn of
LEAD costing as much as a lift of HIGHEST. Its turn comes and goes over EASE frames, then its lift, as far as that
turn needs, likewise. Where that leaves it more than SLACK further short of clear than its own ride, the frames
within EASE of there ride together, on from the frames either side, as cheaply as they can: each frame pays for
its ride, INTO the metre it comes short of clear, and STEADY the square of its change of ride from the frame
before. Only turns move it, as they move the rest of her, and `bake` keys them into the clips, so the game works
nothing out.

Lengths are metres and angles radians."""
import numpy as np

from knight.clips import add, eased

CLEAR = 0.003                      # air kept between a guard and the body under it, or its limb
LEAD = 0.4                         # how much further than its limb a guard may turn, or less far, as a share of the limb's turn
SHARES = sorted(1.0 + LEAD * np.linspace(-1.0, 1.0, 17), key=lambda share: abs(share - 1.0))     # tried nearest first
RISE, HIGHEST = 0.002, 0.060       # how far up its joint is carried between the lifts tried, and at most
EASE = 3.0                         # frames
SLACK = 0.0005
INTO, STEADY = 5000.0, 3.0


class Guard:
    def __init__(self, bone, limb, solid, points, body, onto):
        """`solid` is a sculpt of the `limb` bone's pieces and `points` are the vertices of the guard's; `body` is a
        sculpt of what the `onto` bone carries under the guard, all at rest."""
        self.bone, self.limb, self.solid, self.points, self.body, self.onto = bone, limb, solid, points, body, onto
        self.air = min(CLEAR, body(points).min())        # what it keeps from the body: as at rest, where it lies closer
        self.room = min(CLEAR, solid(points).min())      # and from its limb


def _about(axis, angles):
    """Turns about a unit axis: matrices (n, 3, 3)."""
    x, y, z = axis
    cross = np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])
    return np.eye(3) + np.sin(angles)[:, None, None] * cross + (1.0 - np.cos(angles))[:, None, None] * (cross @ cross)


def _spun(points, pivot, turns):
    """`points` turned about `pivot` by each of `turns`, all of them in a row: (n * len(points), 3)."""
    return ((points - pivot) @ turns.transpose(0, 2, 1) + pivot).reshape(-1, 3)


class _Pose:
    """A guard in one frame: its limb's turn from rest, `turn` about `axis` as the limb's bone sees it, `rest` the
    limb's matrix at rest, `seen` taking what the limb sees to what the body sees, and `riser` the riser's matrix,
    unturned, as the body sees it."""

    def __init__(self, guard, turn, axis, rest, seen, riser):
        self.guard, self.turn, self.axis, self.rest, self.seen, self.riser = guard, turn, axis, rest, seen, riser

    def clear(self):
        """Whether the guard, turned as its limb is, keeps clear of the body; it rests clear of the limb so."""
        g, seen = self.guard, self.seen
        return g.body(g.points @ seen[:3, :3].T + seen[:3, 3]).min() >= g.air

    def short(self, share, lifts):
        """How far short of clear the guard comes, of the body or its limb, turned `share` of its limb's turn and
        lifted by each of `lifts`: negative where it comes too close."""
        g, rest, seen, riser = self.guard, self.rest, self.seen, self.riser
        held = _spun(g.points, rest[:3, 3], _about(rest[:3, :3] @ self.axis, np.array([(share - 1.0) * self.turn])))
        up = riser[:3, 0] / np.linalg.norm(riser[:3, 0])
        back = np.linalg.inv(seen)
        body = g.body(_spun(held @ seen[:3, :3].T + seen[:3, 3], riser[:3, 3], _about(up, lifts)))
        limb = g.solid(_spun(held, back[:3, :3] @ riser[:3, 3] + back[:3, 3], _about(back[:3, :3] @ up, lifts)))
        return np.minimum(body.reshape(len(lifts), -1).min(axis=1) - g.air, limb.reshape(len(lifts), -1).min(axis=1) - g.room)

    def ride(self, lifts):
        """Its share of the limb's turn and its lift, of `lifts`, and how far short of clear they leave it: the least
        ride that clears, else the closest."""
        if self.clear():
            return 1.0, 0.0, 0.0
        best, cost, closest = None, np.inf, -np.inf
        for share in SHARES:
            if abs(share - 1.0) / LEAD >= cost:
                break
            short = self.short(share, lifts)
            clear = np.flatnonzero(short >= 0.0)
            if len(clear) and abs(share - 1.0) / LEAD + lifts[clear[0]] / lifts[-1] < cost:
                best, cost = (share, lifts[clear[0]], 0.0), abs(share - 1.0) / LEAD + lifts[clear[0]] / lifts[-1]
            elif cost == np.inf and short.max() > closest:
                best, closest = (share, lifts[np.argmax(short)], short.max()), short.max()
        return best

    def lift(self, share, lifts):
        """The least of `lifts` that clears the guard turned `share` of its limb's turn, else the closest."""
        if share == 1.0 and self.clear():
            return 0.0
        short = self.short(share, lifts)
        clear = np.flatnonzero(short >= 0.0)
        return lifts[clear[0]] if len(clear) else lifts[np.argmax(short)]


def _steady(poses, own, shares, lift, lifts):
    """Rides afresh, together, the frames within EASE of any where `shares` and `lift`, as eased, leave the guard
    more than SLACK further short of clear than its `own` ride, each stretch on from the frames either side of it."""
    worse = np.zeros(len(poses), bool)
    for i, (p, (share, up, short)) in enumerate(zip(poses, own)):
        if (shares[i], lift[i]) != (share, up):
            worse[i] = p.short(shares[i], lift[i:i + 1])[0] < min(short, 0.0) - SLACK
    near = [worse[max(0, i - int(EASE)):i + int(EASE) + 1].any() for i in range(len(poses))]
    edges = np.flatnonzero(np.diff(np.concatenate([[0], near, [0]]).astype(int)))
    places = np.array([((share - 1.0) / LEAD, up / lifts[-1]) for share in SHARES for up in lifts])
    moves = lambda i: STEADY * ((places - ((shares[i] - 1.0) / LEAD, lift[i] / lifts[-1])) ** 2).sum(axis=1)
    between = STEADY * ((places[:, None, :] - places[None, :, :]) ** 2).sum(axis=2)
    for first, end in zip(edges[::2], edges[1::2]):
        costs = np.abs(places).sum(axis=1) + INTO * np.maximum(0.0, -np.array(
            [np.concatenate([p.short(share, lifts) for share in SHARES]) for p in poses[first:end]]))
        total, came = costs[0] + (moves(first - 1) if first > 0 else 0.0), []
        for cost in costs[1:]:
            through = total[:, None] + between
            came.append(np.argmin(through, axis=0))
            total = through[came[-1], np.arange(len(cost))] + cost
        path = [int(np.argmin(total + (moves(end) if end < len(poses) else 0.0)))]
        for back in reversed(came):
            path.append(int(back[path[-1]]))
        for i, k in zip(range(first, end), reversed(path)):
            shares[i], lift[i] = SHARES[k // len(lifts)], lifts[k % len(lifts)]


def bake(arm, clips, guards, pose):
    """Keys every guard's turn, and its riser's, into each of the `clips`, actions by name. `pose(arm, clip, frame)`
    puts the rig in a frame."""
    bones = arm.data.bones
    rest = lambda name: np.array(bones[name].matrix_local)
    posed = lambda name: np.array(arm.pose.bones[name].matrix)
    risers = {g.bone: bones[g.bone].parent.name for g in guards}
    lifts = {g.bone: np.arange(0.0, HIGHEST + 1e-9, RISE) / np.linalg.norm(bones[g.bone].head_local - bones[risers[g.bone]].head_local)
             for g in guards}
    for name, action in clips.items():
        first, last = (int(f) for f in action.frame_range)
        frames = np.arange(first, last + 1)
        poses = {g.bone: [] for g in guards}
        for frame in frames:
            pose(arm, name, frame)
            for g in guards:
                q = np.array(arm.pose.bones[g.limb].rotation_quaternion)
                q = q if q[0] >= 0.0 else -q
                sine = np.linalg.norm(q[1:])
                axis = q[1:] / sine if sine > 1e-9 else np.array([1.0, 0.0, 0.0])
                under = rest(g.onto) @ np.linalg.inv(posed(g.onto))         # the pose now set, as the body rests
                poses[g.bone].append(_Pose(g, 2.0 * np.arctan2(sine, q[0]), axis, rest(g.limb),
                                           under @ posed(g.limb) @ np.linalg.inv(rest(g.limb)), under @ posed(risers[g.bone])))
        for g in guards:
            mine, tried = poses[g.bone], lifts[g.bone]
            own = [p.ride(tried) for p in mine]
            shares = 1.0 + eased(frames, [share - 1.0 for share, _, _ in own], EASE)
            lift = eased(frames, [up if share == ridden else p.lift(share, tried)
                                  for p, (ridden, up, _), share in zip(mine, own, shares)], EASE)
            _steady(mine, own, shares, lift, tried)
            half = 0.5 * shares * np.array([p.turn for p in mine])
            axis = np.array([p.axis for p in mine])
            add(action, g.bone, "rotation_quaternion", frames, np.concatenate([np.cos(half)[:, None], np.sin(half)[:, None] * axis], axis=1))
            add(action, risers[g.bone], "rotation_quaternion", frames,
                np.stack([np.cos(0.5 * lift), np.sin(0.5 * lift), 0.0 * lift, 0.0 * lift], axis=1))
