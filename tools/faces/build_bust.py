"""Builds a bust wearing a face drawn from the face model: the face, a neck and a tunic, the skin and the cloth
baked from the sculpt, exported as GLB.

  blender --background --python build_bust.py -- [--out bust.glb] [--seed 1] [--sex women|men] [--size 2048]
          [--shots dir] [--clay a.png] [--views 0,-40,-90,180] [--zoom bust,face,neck]

The face is the first the face grid draws with --seed (build_faces.py --grid), as lopsided as there, with its
brows and the short hair (HAIRS "crop"), whatever the sex: long hair falls clear of the head, and the bust has
no piece for it. The face model is fitted first if it is missing or stale. --clay alone renders the bare
pieces, for judging forms quickly; --out and --shots run the whole build, --shots rendering it clay and painted.

The face ends at the edge loop round its neck's cut. The neck carries on from that loop, ring after ring, at
first along the face's own slope, evened out round the loop, and then bending gently down its axis into the
tunic, its rings evened out as they bend so that the loop's kinks fade: the two share the loop and its
normals, so they meet with no step and shade as one. Both are meshes, so their fields, for the bake and
for what each hides, are their meshes', and the bake takes its normals from the meshes' normals; the face's
paint comes from the face model's mean head, so the eyes, lips and hairline are as sharp as the texels.
World frame as the figures': +X the bust's left, -Y forward, +Z up, the eyes as high as a standing figure's.
"""
import bpy, sys, os, time, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sculpt import bl, bake, build, mesher, scan, sdf as S, pieces as P
from sculpt.bl import opt
from sculpt.gen import Frame
from sculpt.num import smoothstep, fbm
from sculpt.pieces import under
from sculpt.sdf import V
from faces import build_faces as B, fit
from faces.model import normals
from faces.sexes import Sex

NAME = "bust"
HEAD = Frame(B.STAND.o, B.STAND.dir(B.level(V(0, 0, 1)[None])[0]), B.STAND.dir(V(1, 0, 0)))   # the face model's, level
STEP, DOWN, BEND = 0.003, 0.100, 0.035         # the neck's rings: how far apart, how deep, and how far they take to turn down
EVEN = 0.006                                   # the neck sets off down the face's slope evened out over about this far round
CLOTH_DEPTH = 0.001                            # a piece's quads this far inside another are culled
CLOTH = V(0.16, 0.20, 0.27)
TUNIC_DIMS = 64, 40, 44
BAKED = {"skin": dict(grain=bake.pores), "cloth": dict(grain=bake.weave)}
ZOOMS = {"bust": ((0, 0.03, 1.50), 0.62, (600, 680)), "face": ((0, -0.02, 1.60), 0.30, (640, 640)),
         "neck": ((0, 0.04, 1.46), 0.16, (640, 640))}


def ending(quads, kept):
    """The quads whose corners are all kept and, of those with one corner not, the triangle of the other three
    (a quad with its last corner twice): a mesh cut along a snapped edge loop, ending on it."""
    lost = (~kept[quads]).sum(1)
    cut = quads[lost == 1]
    turn = np.argmin(kept[cut], axis=1)[:, None] + np.array([1, 2, 3, 3])
    return np.concatenate([quads[lost == 0], np.take_along_axis(cut, turn % 4, 1)])


def solid(v, quads):
    """The field of the mesh, its holes capped."""
    shells, loops = scan.closed(quads.tolist(), len(v))
    return scan.Solid(scan.centred(v, loops), shells), loops


def evened(values, p, width):
    """Values at the points p of a loop, each averaged with its neighbours' about `width` either side along it."""
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
    d = np.abs(s[:, None] - s[None])
    d = np.minimum(d, s[-1] + np.linalg.norm(p[0] - p[-1]) - d)
    w = np.exp(-0.5 * (d / width) ** 2)
    return w @ values / w.sum(1, keepdims=True)


def neck(v, n, loop):
    """The neck carried on from the face's edge loop (head frame), first down the face's own slope, evened
    out round the loop, and then straight down, each ring as evened out as it is bent, so that the loop's
    kinks fade: verts, quads, normals and lattice points, the first ring the loop itself."""
    down = V(0, 0, -1)
    slope = S.normalize(evened(down - n[loop] * (n[loop] @ down)[:, None], v[loop], EVEN))
    rings, at = [v[loop]], v[loop]
    for depth in np.arange(1, round(DOWN / STEP) + 1) * STEP:
        bend = smoothstep(0.0, BEND, depth - STEP / 2)
        at = at + S.normalize(slope * (1.0 - bend) + down * bend) * STEP
        rings.append(at + bend * (evened(at, at, EVEN) - at))
    around = len(loop)
    k, i = np.meshgrid(np.arange(len(rings)), np.arange(around), indexing="ij")
    at = lambda k, i: k * around + i % around
    quads = np.stack([at(k, i), at(k + 1, i), at(k + 1, i + 1), at(k, i + 1)], -1)[:-1].reshape(-1, 4)
    v, first = np.concatenate(rings), quads[:around]
    if (np.cross(v[first[:, 2]] - v[first[:, 0]], v[first[:, 3]] - v[first[:, 1]]) * n[loop]).sum() < 0:
        quads = quads[:, ::-1]
    return v, quads, normals(v, quads), np.stack([i, 0 * i, k], -1).reshape(-1, 3)


def tunic(p):
    """The chest, the shoulders sloping from the neck and the tops of the arms, cut off as a bust's are, in a
    close tunic."""
    x = S.mirror_x(p)
    chest = S.ellipsoid(p, V(0, 0.030, 1.265), V(0.150, 0.115, 0.175))
    back = S.ellipsoid(p, V(0, 0.085, 1.390), V(0.130, 0.075, 0.085))
    shoulder = S.cone(x, V(0, 0.060, 1.405), V(0.155, 0.050, 1.385), 0.050, 0.040)
    arm = S.capsule(x, V(0.160, 0.048, 1.380), V(0.168, 0.052, 1.200), 0.046)
    d = S.smin(S.smin(S.smin(chest, back, 0.050), shoulder, 0.040), arm, 0.030)
    return S.smax(S.smax(d, 1.225 - p[:, 2], 0.010), x[:, 0] - 0.195, 0.015)


def encoded(colour):
    """Colours as the face model's renders give them, linear, as a texture's sRGB, so the bust's skin is theirs."""
    return np.where(colour <= 0.0031308, 12.92 * colour, 1.055 * np.maximum(colour, 0.0031308) ** (1.0 / 2.4) - 0.055)


def smooth(mesh, loops, n):
    """Points -> the vertex normals n of a mesh, where its solid (see `solid`) lies nearest them."""
    def at(p):
        corners, weights = mesh.bind(p)
        return S.normalize(scan.carry(scan.centred(n, loops), corners, weights))
    return at


def middle(n, *lines):
    """Seams along the lattice's middle (i = n[0] / 2) wherever one of `lines` (lattice points -> bool) holds."""
    def on(c):
        return (c[:, 0] == n[0] // 2) & np.any([line(c) for line in lines], axis=0)
    return lambda a, b, sub: on(a) & on(b)


def figure(model, coefficients, lopsided):
    """The bust's pieces: the face, its neck and the tunic."""
    brow = coefficients[len(model.directions):]
    v, quads, n, lat = model.mesh(coefficients, lopsided)
    v = v + n * B.groom(model.mean, brow)[0][:, None]
    quads = ending(quads, ~fit.cap(model.mean))
    face, loops = solid(HEAD.w(v), quads)
    n = normals(v, quads)
    nv, nq, nn, nlat = neck(v, n, loops[0])
    n[loops[0]] = nn[:len(loops[0])] = S.normalize(n[loops[0]] + nn[:len(loops[0])])
    throat, throat_loops = solid(HEAD.w(nv), nq)
    head, along, round_neck, round_along = HEAD.w(v), HEAD.dir(n), HEAD.w(nv), HEAD.dir(nn)

    def paint(p):
        corners, weights = face.bind(p)
        at = scan.carry(scan.centred(model.mean, loops), corners, weights)
        eye = scan.carry(scan.centred(model.eyes[:, None] * 1.0, loops), corners, weights)[:, 0] > 0.5
        hair = B.groom(at, brow)[1]
        skin = B.paint(at, eye)
        colour = encoded(skin + hair[:, None] * (np.array(B.HAIR) - skin))
        return colour, np.where(eye, 0.15, 0.50 + 0.35 * hair), np.zeros(len(p)), np.zeros(len(p))

    def bare(p):
        return np.tile(encoded(np.array(B.SKIN)), (len(p), 1)), np.full(len(p), 0.50), np.zeros(len(p)), np.zeros(len(p))

    def cloth(p):
        colour = np.tile(CLOTH, (len(p), 1)) * (0.94 + 0.12 * fbm(p * 22.0))[:, None]
        return colour, np.full(len(p), 0.85), np.zeros(len(p)), np.ones(len(p))

    def tunic_mesh(sub):
        v, q, n = mesher.wrap(tunic, V(-0.12, 0.04, 1.33), V(0.12, 0.04, 1.33), (0.20, 0.12, 0.13), TUNIC_DIMS, relax=12)
        return v, q, n, np.rint((mesher.cube_lattice(*TUNIC_DIMS)[0] + 1.0) / 2.0 * np.array(TUNIC_DIMS)).astype(np.int64)
    ends, back = lat.max(0), int(np.argmin(nv[:len(loops[0]), 1]))
    return {
        "face": dict(mat="skin", mesh=lambda sub: (head, quads, along, lat), field=face.field, detail=face.field,
                     normals=smooth(face, loops, along), paint=paint, hidden=under(tunic, CLOTH_DEPTH),
                     seam=middle(ends, lambda c: c[:, 1] == 0, lambda c: (c[:, 2] == ends[2]) & (c[:, 1] <= ends[1] // 2)),
                     favour=lambda v: smoothstep(-0.01, 0.03, HEAD.l(v)[:, 1]), boost=1.0, mirror=False),
        "neck": dict(mat="skin", mesh=lambda sub: (round_neck, nq, round_along, nlat), field=throat.field,
                     detail=throat.field, normals=smooth(throat, throat_loops, round_along), paint=bare,
                     hidden=under(tunic, CLOTH_DEPTH), seam=lambda a, b, sub: (a[:, 0] == back) & (b[:, 0] == back),
                     boost=1.0, mirror=False),
        "tunic": dict(mat="cloth", mesh=tunic_mesh, field=tunic, detail=tunic, paint=cloth,
                      hidden=under(throat.field, CLOTH_DEPTH),
                      seam=middle(TUNIC_DIMS, lambda c: c[:, 1] == TUNIC_DIMS[1], lambda c: c[:, 2] == 0,
                                  lambda c: (c[:, 2] == TUNIC_DIMS[2]) & (c[:, 1] >= TUNIC_DIMS[1] // 2)),
                      boost=1.0, mirror=False, grain=0.20, pitch=0.0018, grain_tint=0.08),
    }


def turnaround(path, views, zoom):
    target, scale, res = ZOOMS[zoom]
    bl.turnaround(path, views, target, scale, res, bl.studio(*B.LAMPS), 40)


def main():
    t0 = time.time()
    model = B.current()
    sex = Sex(model, opt("--sex")) if opt("--sex") else None
    bl.reset_scene()
    faces, lopsided = B.drawn(model, sex, int(opt("--seed", "1")))
    specs = figure(model, faces[0], lopsided[0])
    pieces = [P.sculpt(name, spec) for name, spec in specs.items()]
    for pc in pieces:
        pc["q"] = P.outward(pc["v"], pc["q"], pc["n"])
    print("SCULPTED tris=%d  t=%.1fs" % (P.triangles(pieces), time.time() - t0))
    views = [float(a) for a in opt("--views", "0,-40,-90,180").split(",")]
    zooms = opt("--zoom", ",".join(ZOOMS)).split(",")
    if not (opt("--out") or opt("--shots")):
        if opt("--clay"):
            build.clay_objects(pieces, wire=True)
            for zoom in zooms:
                turnaround(opt("--clay").replace(".png", "_%s.png" % zoom), views, zoom)
        return
    folder = opt("--textures") or tempfile.mkdtemp(prefix=NAME + "_")
    painted, clay = build.textures(pieces, BAKED, int(opt("--size", "2048")), folder, NAME)
    bust = build.assemble(NAME.capitalize(), pieces, list(BAKED), painted)
    print("MESH %s: %d triangles  t=%.1fs" % (bust.name, len(bust.data.polygons), time.time() - t0))
    if opt("--shots"):
        for zoom in zooms:
            for kind, mats in (("clay", clay), ("painted", painted)):
                for k, m in enumerate(mats):
                    bust.data.materials[k] = m
                turnaround(os.path.join(opt("--shots"), "%s_%s.png" % (kind, zoom)), views, zoom)
        for k, m in enumerate(painted):
            bust.data.materials[k] = m
    if opt("--out"):
        bl.export_glb(opt("--out"), [bust], export_animations=False, export_skins=False, export_tangents=True,
                      export_vertex_color="NONE")
    print("DONE t=%.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
