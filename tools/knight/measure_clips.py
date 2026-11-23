"""Root-motion distances and key timings of the source clips (for matching controller speeds)."""
import bpy, sys
import numpy as np

paths = sys.argv[sys.argv.index("--") + 1:]
want = ["Walk_Loop", "Jog_Fwd_Loop", "Sprint_Loop", "Roll", "Jump_Start", "Jump_Loop", "Jump_Land", "Sword_Attack",
        "Sword_Regular_A", "Sword_Regular_A_Rec", "Sword_Regular_B", "Sword_Regular_B_Rec", "Sword_Regular_C",
        "Sword_Regular_Combo", "Sword_Dash", "Idle_Loop", "Sword_Idle"]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30
for path in paths:
    bpy.ops.import_scene.gltf(filepath=path)
    arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
    arm.animation_data_create()
    for name in want:
        act = bpy.data.actions.get(name)
        if act is None:
            continue
        arm.animation_data.action = act
        if hasattr(arm.animation_data, "action_slot") and act.slots:
            arm.animation_data.action_slot = act.slots[0]
        f0, f1 = int(act.frame_range[0]), int(round(act.frame_range[1]))
        rows = []
        for f in range(f0, f1 + 1):
            bpy.context.scene.frame_set(f)
            M = arm.matrix_world
            root = M @ arm.pose.bones["root"].head
            pel = M @ arm.pose.bones["pelvis"].head
            fl = M @ arm.pose.bones["foot_l"].head
            fr = M @ arm.pose.bones["foot_r"].head
            hr = M @ arm.pose.bones["hand_r"].head
            rows.append((f, root.x, root.y, root.z, pel.y, pel.z, fl.y, fl.z, fr.y, fr.z, hr.x, hr.y, hr.z))
        R = np.array(rows)
        dur = (f1 - f0) / 30.0
        dist = -(R[-1, 2] - R[0, 2])
        print("CLIP %-20s frames=%3d dur=%.3fs rootFwd=%.3fm speed=%.2fm/s  pelvisZ[min %.2f max %.2f]" % (
            name, f1 - f0, dur, dist, dist / max(dur, 1e-6), R[:, 5].min(), R[:, 5].max()))
        if name in ("Roll", "Jump_Start", "Jump_Land", "Sword_Regular_A", "Sword_Regular_B", "Sword_Regular_C", "Sword_Dash", "Sword_Attack"):
            step = max(1, (f1 - f0) // 14)
            print("    f:rootFwd/pelvisZ/handR.z  " + "  ".join("%d:%.2f/%.2f/%.2f" % (r[0], -r[2], r[5], r[12]) for r in R[::step]))
        if name in ("Walk_Loop", "Jog_Fwd_Loop", "Sprint_Loop"):
            # which foot is planted (lowest) per frame, to align gait phases
            print("    f:footL.y,z (rel root)  " + "  ".join("%d:%.2f,%.2f" % (r[0], r[6] - r[2], r[7]) for r in R))
    for ob in list(bpy.context.scene.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
