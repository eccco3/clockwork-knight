// Leaded diamond-pane window on a foggy day. Opaque: each hand-blown pane passes a slightly
// different share of the flat white fog outside, under a glossy surface that mirrors the firelight.
// The light the windows throw into the hall comes from the FogLight spots of builders/hall_scene.gd.
shader_type spatial;
render_mode cull_disabled;

uniform vec2 size = vec2(1.6, 2.5);
uniform vec2 pane = vec2(0.105, 0.15);
uniform vec3 fog_high : source_color = vec3(0.86, 0.9, 0.96);
uniform vec3 fog_low : source_color = vec3(0.6, 0.65, 0.71);
uniform float energy = 3.0;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void fragment() {
	vec2 p = (UV - 0.5) * size;
	vec2 q = vec2(p.x / pane.x + p.y / pane.y, p.x / pane.x - p.y / pane.y);
	vec2 cell = floor(q);
	vec2 f = fract(q);
	float edge = min(min(f.x, 1.0 - f.x), min(f.y, 1.0 - f.y));
	float aa = fwidth(q.x) + fwidth(q.y);
	float lead = 1.0 - smoothstep(0.045, 0.045 + aa, edge);
	float h1 = hash(cell);
	float h2 = hash(cell + 17.3);
	float up = 1.0 - UV.y + (h1 - 0.5) * 0.3;
	vec3 fog = mix(fog_low, fog_high, smoothstep(0.0, 0.85, up));
	fog *= mix(0.72, 1.1, h2);
	fog *= 1.0 - 0.2 * length(f - 0.5);
	ALBEDO = mix(vec3(0.015), vec3(0.05, 0.05, 0.055), lead);
	EMISSION = fog * energy * (1.0 - lead);
	ROUGHNESS = mix(0.14 + 0.14 * h1, 0.55, lead);
	METALLIC = lead * 0.7;
	SPECULAR = 0.6;
	NORMAL_MAP = normalize(vec3((h1 - 0.5) * 0.09 + (f.x - 0.5) * 0.06, (h2 - 0.5) * 0.09 + (f.y - 0.5) * 0.06, 1.0)) * 0.5 + 0.5;
}
