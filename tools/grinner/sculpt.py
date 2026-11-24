"""Small numeric helpers shared by the grinner's sculpts and paints."""
import numpy as np
from knight import sdf as S


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def bump(x, c, w):
    return np.exp(-((x - c) / w) ** 2)


def lerp(a, b, t):
    return a + (b - a) * t


def _hash(i, j, k):
    h = np.sin(i * 127.1 + j * 311.7 + k * 74.7) * 43758.5453
    return h - np.floor(h)


def noise3(p):
    """Value noise in 0..1 over (N,3) points; one lattice cell per unit."""
    i = np.floor(p)
    f = p - i
    f = f * f * (3.0 - 2.0 * f)
    x, y, z = i[:, 0], i[:, 1], i[:, 2]
    out = 0.0
    for dx in (0, 1):
        wx = f[:, 0] if dx else 1.0 - f[:, 0]
        for dy in (0, 1):
            wy = f[:, 1] if dy else 1.0 - f[:, 1]
            for dz in (0, 1):
                wz = f[:, 2] if dz else 1.0 - f[:, 2]
                out = out + _hash(x + dx, y + dy, z + dz) * wx * wy * wz
    return out


def fbm(p, octaves=3):
    out, amp, total = 0.0, 1.0, 0.0
    for k in range(octaves):
        out = out + amp * noise3(p * (2.0 ** k) + 17.3 * k)
        total += amp
        amp *= 0.5
    return out / total


def along(p, a, b):
    """Distance travelled along a -> b (unclipped, metres) and distance from that line."""
    d = b - a
    n = np.linalg.norm(d)
    d = d / n
    h = (p - a) @ d
    return h, S.length(p - a - np.outer(h, d))


def mix(col, c, m):
    m = np.clip(m, 0.0, 1.0)[:, None]
    return col * (1.0 - m) + np.asarray(c) * m


def chunked(f, p, size=250000):
    """Evaluate f over p in pieces to bound memory; f may return an array or a tuple of arrays."""
    if len(p) <= size:
        return f(p)
    parts = [f(p[k:k + size]) for k in range(0, len(p), size)]
    if isinstance(parts[0], tuple):
        return tuple(np.concatenate([q[i] for q in parts]) for i in range(len(parts[0])))
    return np.concatenate(parts)
