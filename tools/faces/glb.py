"""Binary glTF meshes written and read with numpy alone: what Godot imports a head with a blend shape per
number from, which Blender's exporter cannot make (its blend shapes carry the normals it works out itself).

A mesh is a dict: "name"; "positions" and "normals" (N, 3); "indices" (T, 3), wound counterclockwise seen
from outside; "uvs", a list of (N, 2) arrays, TEXCOORD_0 on, which Godot reads as UV, UV2 and then, two at
a time, as CUSTOM0 to CUSTOM2; "targets", a list of (positions, normals), each (N, 3) moved per unit, and
their "target_names"; and "extras", which Godot keeps as the node's metadata.
"""
import json, struct
import numpy as np

FLOAT, UINT = 5126, 5125
KINDS = {1: "SCALAR", 2: "VEC2", 3: "VEC3", 4: "VEC4"}


def triangles(quads):
    """Quads (Q, 4) as triangles (2Q, 3), wound the same way."""
    return np.concatenate([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]])


class _Bin:
    def __init__(self):
        self.chunks, self.views, self.accessors, self.size = [], [], [], 0

    def add(self, array, component, bounds=False, target=None):
        """The accessor of `array` (count, width), a buffer view of its own."""
        array = np.ascontiguousarray(array, np.uint32 if component == UINT else np.float32)
        data = array.tobytes()
        view = dict(buffer=0, byteOffset=self.size, byteLength=len(data))
        if target:
            view["target"] = target
        self.views.append(view)
        self.chunks.append(data + b"\0" * (-len(data) % 4))
        self.size += len(self.chunks[-1])
        flat = array.reshape(len(array), -1)
        accessor = dict(bufferView=len(self.views) - 1, componentType=component, count=len(array),
                        type=KINDS[flat.shape[1]])
        if bounds:
            accessor.update(min=flat.min(0).tolist(), max=flat.max(0).tolist())
        self.accessors.append(accessor)
        return len(self.accessors) - 1


def write(path, meshes, extras=None):
    """Writes the meshes, each on a node of its own name, into one GLB; `extras` goes on the scene."""
    out, nodes, gltf_meshes = _Bin(), [], []
    for mesh in meshes:
        vertices = 34962
        attributes = dict(POSITION=out.add(mesh["positions"], FLOAT, True, vertices),
                          NORMAL=out.add(mesh["normals"], FLOAT, target=vertices))
        for k, uv in enumerate(mesh.get("uvs", ())):
            attributes["TEXCOORD_%d" % k] = out.add(uv, FLOAT, target=vertices)
        primitive = dict(attributes=attributes, indices=out.add(np.asarray(mesh["indices"]).reshape(-1, 1), UINT,
                                                                 target=34963), mode=4)
        targets = mesh.get("targets", ())
        if targets:
            primitive["targets"] = [dict(POSITION=out.add(p, FLOAT, True), NORMAL=out.add(n, FLOAT)) for p, n in targets]
        gltf_mesh = dict(name=mesh["name"], primitives=[primitive])
        if targets:
            gltf_mesh.update(weights=[0.0] * len(targets), extras=dict(targetNames=list(mesh["target_names"])))
        gltf_meshes.append(gltf_mesh)
        node = dict(name=mesh["name"], mesh=len(gltf_meshes) - 1)
        if mesh.get("extras"):
            node["extras"] = mesh["extras"]
        nodes.append(node)
    scene = dict(nodes=list(range(len(nodes))))
    if extras:
        scene["extras"] = extras
    gltf = dict(asset=dict(version="2.0", generator="clockwork-knight tools/faces/glb.py"), scene=0, scenes=[scene],
                nodes=nodes, meshes=gltf_meshes, buffers=[dict(byteLength=out.size)], bufferViews=out.views,
                accessors=out.accessors)
    text = json.dumps(gltf, separators=(",", ":")).encode()
    text += b" " * (-len(text) % 4)
    blob = b"".join(out.chunks)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(text) + 8 + len(blob)))
        f.write(struct.pack("<II", len(text), 0x4E4F534A) + text)
        f.write(struct.pack("<II", len(blob), 0x004E4942) + blob)


def read(path):
    """The glTF JSON of a GLB this module wrote, and a function giving an accessor's array."""
    with open(path, "rb") as f:
        data = f.read()
    length = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20:20 + length])
    blob = memoryview(data)[20 + length + 8:]

    def accessor(k):
        a = gltf["accessors"][k]
        view = gltf["bufferViews"][a["bufferView"]]
        width = {v: k for k, v in KINDS.items()}[a["type"]]
        kind = np.uint32 if a["componentType"] == UINT else np.float32
        return np.frombuffer(blob, kind, a["count"] * width, view["byteOffset"]).reshape(a["count"], width)
    return gltf, accessor
