# Backlog

## Cut GPU work enough to cool the laptop

### Task description

The RTX 3060's driver only lowers its clock when a frame needs under about 40% of the 16.7 ms budget. The hall needs 9 ms, so the GPU stays near 85 W and 87 °C. Get GPU time at 60 fps under 5 ms (72 W, 78 °C) or 3.5 ms (43 W, 70 °C). Candidate: bake the static lights and bounce light into lightmaps, keeping dynamic shadows only for the knight. Measure with the `perf:start` and `perf:stop` events of `dev/drive.tscn` and with `nvidia-smi dmon`.

### Open questions

- Is baked lighting acceptable, given it changes how the knight picks up light from the sconces and windows?
- Otherwise, which trade is acceptable: 67% render scale, half render scale, or a 30 fps cap?

### Status

Not started. Measured in real play: full quality 81 W; 67% render scale 72 W; half render scale 43 W; 30 fps cap 44 W.
