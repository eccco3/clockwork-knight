"""Bakes the sculpt into textures for the game mesh: albedo, tangent-space normals, and
occlusion / roughness / metallic.

Every texel is placed on the game mesh, moved along the mesh normal onto the detailed sculpt, and
coloured there by the piece's paint; the sculpt's gradient becomes the normal. Grain too fine for a
sculpt (weave, pores) is added in texture space, where its scale is even.
"""
import numpy as np
from . import sdf as S
from .num import chunked

REACH = 0.006                                   # how far the detailed sculpt may sit from the game mesh


def rasterize(uv, size, pad=0.75):
    """uv (T,3,2) in 0..1 -> every texel within `pad` pixels of a triangle: texel index, triangle,
    barycentrics and depth inside the triangle in pixels."""
    px = uv * size
    texel, tri, bary, depth = [], [], [], []
    for t in range(len(px)):
        a, b, c = px[t]
        x0, y0 = np.floor(px[t].min(0) - pad).astype(int).clip(0, size)
        x1, y1 = np.ceil(px[t].max(0) + pad).astype(int).clip(0, size)
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if x1 <= x0 or y1 <= y0 or abs(den) < 1e-9:
            continue
        X, Y = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        w0 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / den
        w1 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / den
        w = np.stack([w0, w1, 1.0 - w0 - w1], axis=-1)
        edge = np.array([np.hypot(*(b - c)), np.hypot(*(c - a)), np.hypot(*(a - b))])
        inside = (w * (abs(den) / np.maximum(edge, 1e-9))).min(-1)
        keep = inside > -pad
        texel.append((Y[keep].astype(int) * size + X[keep].astype(int)))
        tri.append(np.full(int(keep.sum()), t))
        bary.append(w[keep])
        depth.append(inside[keep])
    texel, tri, bary, depth = np.concatenate(texel), np.concatenate(tri), np.concatenate(bary), np.concatenate(depth)
    return texel, tri, bary, depth


def overlap(texel, depth):
    """Texels that lie well inside more than one triangle: islands laid over each other."""
    deep = texel[depth > 1.5]
    return len(deep) - len(np.unique(deep))


def deepest(texel, tri, bary, depth, size):
    """One triangle per texel: the one it lies deepest in."""
    order = np.argsort(depth)
    winner = np.full(size * size, -1)
    winner[texel[order]] = order
    pick = winner[winner >= 0]
    return texel[pick], tri[pick], bary[pick]


def onto(detail, p, n):
    """Slide points along n onto the zero level of `detail`, at most REACH either way."""
    lo, hi = np.full(len(p), -REACH), np.full(len(p), REACH)
    f_lo, f_hi = detail(p + n * lo[:, None]), detail(p + n * hi[:, None])
    ok = (f_lo < 0) & (f_hi > 0)
    for _ in range(11):
        mid = 0.5 * (lo + hi)
        inside = detail(p + n * mid[:, None]) < 0
        lo, hi = np.where(inside, mid, lo), np.where(inside, hi, mid)
    return p + n * np.where(ok, 0.5 * (lo + hi), 0.0)[:, None]


def normal(detail, p, eps):
    k = np.array([[1, -1, -1], [-1, -1, 1], [-1, 1, -1], [1, 1, 1]], dtype=np.float64)
    g = np.zeros_like(p)
    for d in k:
        g += d * detail(p + d * eps)[:, None]
    return S.normalize(g)


def occlusion(field, p, n):
    """How enclosed each point is, from how far the sculpt stands off along its normal: 1 open .. 0 buried."""
    occ = np.zeros(len(p))
    for h, w in ((0.004, 0.30), (0.012, 0.30), (0.030, 0.22), (0.070, 0.18)):
        occ += w * np.clip(1.0 - field(p + n * h) / h, 0.0, 1.0)
    return np.clip(1.0 - 1.15 * occ, 0.0, 1.0)


def weave(u, v, pitch):
    """Plain weave: height and unit-scaled slopes of crossing threads `pitch` texture units apart."""
    k = 2 * np.pi / pitch
    return np.sin(k * u) * np.sin(k * v), np.cos(k * u) * np.sin(k * v), np.sin(k * u) * np.cos(k * v)


def pores(u, v, pitch):
    k = 2 * np.pi / pitch
    a, b = k * (u + 0.37 * np.sin(k * v * 0.31)), k * (v + 0.41 * np.sin(k * u * 0.27))
    return np.sin(a) * np.sin(b), np.cos(a) * np.sin(b), np.sin(a) * np.cos(b)


def front_view(field, paint, half_width, bottom, top, width=1024, front=0.112):
    """`paint` (points -> RGB) as seen from the front of a sculpt that faces +y and is symmetric in x:
    (H, W, 3), row 0 at z = top, column 0 at x = -half_width. Each texel is traced back from y = front
    along -y to the first surface it meets."""
    half = width // 2
    height = int(round(width * (top - bottom) / (2 * half_width)))
    xs = (np.arange(half) + 0.5) / half * half_width
    zs = top - (np.arange(height) + 0.5) / height * (top - bottom)
    X, Z = np.meshgrid(xs, zs)
    x, z = X.ravel(), Z.ravel()
    y = np.full(len(x), front)
    live = np.arange(len(x))
    for _ in range(40):                                         # sphere tracing; converged texels drop out
        dd = field(np.stack([x[live], y[live], z[live]], axis=1))
        y[live] -= np.clip(dd, 0.0, None) * 0.85
        live = live[(dd > 2e-5) & (y[live] > 0.0)]
        if len(live) == 0:
            break
    rgb = paint(np.stack([x, y, z], axis=1)).reshape(height, half, 3)
    return np.concatenate([rgb[:, ::-1], rgb], axis=1)


def dilate(img, filled, steps):
    """Bleed filled texels outward so filtering never reaches an empty one."""
    img, filled = img.copy(), filled.copy()
    for _ in range(steps):
        acc = np.zeros_like(img)
        cnt = np.zeros(filled.shape)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            src = np.roll(np.roll(filled, dy, 0), dx, 1)
            acc += np.roll(np.roll(img, dy, 0), dx, 1) * src[..., None]
            cnt += src
        new = ~filled & (cnt > 0)
        img[new] = acc[new] / cnt[new][:, None]
        filled |= new
    return img


def bake(pieces, size, occluder, grain, scale, log=print):
    """Textures for the pieces sharing one material. Each piece gives tris (T,3), uv (T,3,2), v, n, tan
    (T,3,3), sign (T,3) and either detail + paint (sculpted) or chart + paint (made by formula).
    grain(u, v, pitch) is the material's fine relief and `scale` its texture units per metre.
    Returns albedo, normal and occlusion-roughness-metallic images, (size, size, 3) in 0..1, row 0 at v = 0."""
    uv = np.concatenate([pc["uv"] for pc in pieces])
    owner = np.concatenate([np.full(len(pc["uv"]), k) for k, pc in enumerate(pieces)])
    first = np.cumsum([0] + [len(pc["uv"]) for pc in pieces])
    texel, tri, bary, depth = rasterize(uv, size)
    sculpted = np.array(["chart" not in pc for pc in pieces])[owner[tri]]
    log("BAKE raster: %d texels overlap" % overlap(texel[sculpted], depth[sculpted]))
    texel, tri, bary = deepest(texel, tri, bary, depth, size)
    log("BAKE raster %d texels of %d" % (len(texel), size * size))
    albedo, nrm, orm = np.zeros((size * size, 3)), np.zeros((size * size, 3)), np.zeros((size * size, 3))
    for k, pc in enumerate(pieces):
        m = owner[tri] == k
        if not m.any():
            continue
        tx, tr, w = texel[m], tri[m] - first[k], bary[m]
        corner = pc["tris"][tr]
        p0 = (pc["v"][corner] * w[..., None]).sum(1)
        n0 = S.normalize((pc["n"][corner] * w[..., None]).sum(1))
        tan = S.normalize((pc["tan"][tr] * w[..., None]).sum(1))
        bit = np.cross(n0, tan) * pc["sign"][tr][:, :1]
        u, v = (tx % size + 0.5) / size, (tx // size + 0.5) / size
        if "chart" in pc:
            col, rough, metal, *rest = pc["paint"]((pc["chart"][corner] * w[..., None]).sum(1))
            n, ao, fiber = n0, np.ones(len(tx)), rest[0] if rest else np.zeros(len(tx))
        else:
            ps = chunked(lambda a: onto(pc["detail"], a[:, :3], a[:, 3:]), np.concatenate([p0, n0], axis=1))
            n = chunked(lambda a: normal(pc["detail"], a, 0.6 / (scale * size)), ps)
            col, rough, metal, fiber = chunked(pc["paint"], ps)
            half = (tx % size % 2 == 0) & (tx // size % 2 == 0)             # occlusion at half resolution
            both = np.concatenate([ps, n], axis=1)
            ao_img = np.full(size * size, np.nan)
            ao_img[tx[half]] = chunked(lambda a: occlusion(occluder, a[:, :3], a[:, 3:]), both[half])
            ao = ao_img[(tx // size // 2 * 2) * size + tx % size // 2 * 2]
            lone = np.isnan(ao)
            ao[lone] = chunked(lambda a: occlusion(occluder, a[:, :3], a[:, 3:]), both[lone])
        h, hu, hv = grain(u, v, pc.get("pitch", 0.0018) * scale)
        amp = fiber * pc.get("grain", 0.0)
        ts = np.stack([(n * tan).sum(-1) - amp * hu, (n * bit).sum(-1) - amp * hv, (n * n0).sum(-1)], axis=1)
        ts[:, 2] = np.maximum(ts[:, 2], 0.05)
        albedo[tx] = np.clip(col * (1.0 + pc.get("grain_tint", 0.0) * fiber * h)[:, None], 0, 1)
        nrm[tx] = S.normalize(ts) * 0.5 + 0.5
        orm[tx] = np.stack([ao, np.clip(rough, 0.03, 1.0), metal], axis=1)
        log("BAKE %-7s %d texels" % (pc["name"], len(tx)))
    filled = np.zeros(size * size, dtype=bool)
    filled[texel] = True
    filled = filled.reshape(size, size)
    return [dilate(img.reshape(size, size, 3), filled, 12) for img in (albedo, nrm, orm)]
