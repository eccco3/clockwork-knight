// Streaks of light across the air gaps at a figure's joints. scripts/joint_light.gd lays each as a card from
// one part to the next: NORMAL runs along it, UV is (along, side) and UV2 is (joint, the streak's own number).
// A streak lights nothing: it only adds its own glow to the picture.
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, world_vertex_coords;

const int JOINTS = 64;
// For each joint, how hard it glows, from 0 at rest to 1 turning fast, and how many cycles its streaks have run.
uniform vec2 joints[JOINTS];
uniform vec3 color : source_color = vec3(1.0);
uniform float width = 0.0022;
// A streak thinner than this many pixels is drawn that wide and as much dimmer, so it never breaks into dots.
uniform float min_pixels = 1.25;
uniform float rest_energy = 0.3;
uniform float moving_energy = 3.5;
// The share of a joint's streaks alight at once.
uniform float rest_share = 0.3;
uniform float moving_share = 0.9;

varying float energy;
varying float cycle;
varying float along;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void vertex() {
	vec2 joint = joints[int(UV2.x + 0.5)];
	float beat = joint.y + UV2.y * 64.0;
	cycle = fract(beat);
	float alight = step(hash(vec2(UV2.y, floor(beat))), mix(rest_share, moving_share, joint.x));
	along = mix(UV.x, 1.0 - UV.x, step(0.5, fract(UV2.y * 8.0)));
	vec3 to_eye = CAMERA_POSITION_WORLD - VERTEX;
	float pixel = 2.0 * dot(-to_eye, CAMERA_DIRECTION_WORLD) / (abs(PROJECTION_MATRIX[1][1]) * VIEWPORT_SIZE.y);
	float drawn = max(width, pixel * min_pixels);
	energy = alight * mix(rest_energy, moving_energy, joint.x) * width / drawn;
	VERTEX += normalize(cross(NORMAL, to_eye)) * UV.y * 0.5 * drawn * alight;
}

void fragment() {
	float core = 1.0 - abs(UV.y);
	// the light runs across the gap and off its far side, sharp ahead and trailing behind, over a steady thread
	float behind = cycle * 1.6 - along;
	float runner = behind > 0.0 ? exp(-behind * 3.5) : exp(behind * 30.0);
	float thread = 0.3 * sin(cycle * PI);
	float ends = smoothstep(0.0, 0.12, along) * smoothstep(1.0, 0.88, along);
	ALBEDO = color * energy * core * core * (thread + runner) * ends;
}
