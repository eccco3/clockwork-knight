// Leaded diamond-pane window at dusk. Opaque: each hand-blown pane shows a slightly different
// patch of evening sky (procedural gradient), with a glossy surface that mirrors the firelight.
shader_type spatial;
render_mode cull_disabled;

uniform vec2 size = vec2(1.6, 2.5);
uniform vec2 pane = vec2(0.105, 0.15);
uniform vec3 sky_top : source_color = vec3(0.035, 0.07, 0.2);
uniform vec3 sky_mid : source_color = vec3(0.16, 0.2, 0.42);
uniform vec3 sky_horizon : source_color = vec3(0.62, 0.36, 0.3);
uniform vec3 ground : source_color = vec3(0.02, 0.025, 0.04);
uniform float energy = 1.0;

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
	vec3 dir = normalize((INV_VIEW_MATRIX * vec4(-VIEW, 0.0)).xyz);
	float up = dir.y * 0.8 + (0.5 - UV.y) * 0.35 + (h1 - 0.5) * 0.22 + 0.12;
	vec3 sky = mix(sky_horizon, sky_mid, smoothstep(-0.05, 0.28, up));
	sky = mix(sky, sky_top, smoothstep(0.25, 0.8, up));
	sky = mix(ground, sky, smoothstep(-0.28, -0.04, up));
	sky *= mix(0.7, 1.15, h2);
	// bullseye-ish thickness variation inside a pane
	float bump = length(f - 0.5);
	sky *= 1.0 - 0.18 * bump;
	ALBEDO = mix(vec3(0.015), vec3(0.05, 0.05, 0.055), lead);
	EMISSION = sky * energy * (1.0 - lead);
	ROUGHNESS = mix(0.14 + 0.14 * h1, 0.55, lead);
	METALLIC = lead * 0.7;
	SPECULAR = 0.6;
	NORMAL_MAP = normalize(vec3((h1 - 0.5) * 0.09 + (f.x - 0.5) * 0.06, (h2 - 0.5) * 0.09 + (f.y - 0.5) * 0.06, 1.0)) * 0.5 + 0.5;
}
