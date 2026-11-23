// Grass tufts, one MultiMesh instance each. Tufts thin out with distance from the camera: one
// stays while its INSTANCE_CUSTOM.r is below the share left at that distance, and shrinks away
// as it crosses. INSTANCE_CUSTOM.g shifts its green toward olive, .b toward dry straw.
// The mesh's UV.x is a per-blade random, UV.y the height along the blade.
shader_type spatial;
render_mode cull_disabled, world_vertex_coords;

uniform vec3 root_color : source_color = vec3(0.1, 0.1, 0.05);
uniform vec3 green : source_color = vec3(0.36, 0.43, 0.18);
uniform vec3 olive : source_color = vec3(0.47, 0.46, 0.24);
uniform vec3 straw : source_color = vec3(0.64, 0.57, 0.4);
uniform float full_range = 9.0;
uniform float range = 46.0;
uniform vec2 wind = vec2(0.8, 0.45);
uniform float sway = 0.07;

varying float along;
varying vec3 tint;

void vertex() {
	vec3 o = MODEL_MATRIX[3].xyz;
	float left = 1.0 - smoothstep(full_range, range, distance(o, CAMERA_POSITION_WORLD));
	float s = smoothstep(INSTANCE_CUSTOM.r, INSTANCE_CUSTOM.r + 0.12, left * 1.12);
	along = UV.y;
	float phase = TIME * 1.6 + dot(o.xz, wind) * 0.35 + UV.x * 5.0;
	float gust = 0.55 + 0.45 * sin(TIME * 0.45 + dot(o.xz, wind) * 0.06);
	vec2 bend = wind * gust * (0.6 + 0.4 * sin(phase)) + vec2(-wind.y, wind.x) * 0.25 * sin(phase * 1.7);
	VERTEX = o + (VERTEX - o) * s + vec3(bend.x, -0.25 * gust, bend.y) * sway * along * along * s;
	tint = mix(mix(green, olive, INSTANCE_CUSTOM.g), straw, INSTANCE_CUSTOM.b);
}

void fragment() {
	vec3 c = mix(root_color, tint, smoothstep(0.0, 0.55, along));
	c *= mix(0.82, 1.14, fract(UV.x * 7.31));
	ALBEDO = c;
	ROUGHNESS = 0.65;
	SPECULAR = 0.3;
	BACKLIGHT = c * 0.7;
	AO = mix(0.5, 1.0, along);
	AO_LIGHT_AFFECT = 0.6;
	if (!FRONT_FACING) {
		NORMAL = -NORMAL;
	}
}
