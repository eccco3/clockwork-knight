// Candle flame with a soft halo: Y-billboarded quad (0.3 m), per-instance flicker from world position.
shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, shadows_disabled, fog_disabled;

uniform float intensity = 6.0;
uniform float halo = 0.1;
uniform float quad_size = 0.3;
varying float flick;
varying float sway;

void vertex() {
	vec3 wp = MODEL_MATRIX[3].xyz;
	float ph = fract(sin(dot(wp.xz + wp.y, vec2(12.9898, 78.233))) * 43758.5453);
	float t = TIME * 6.0 + ph * 40.0;
	sway = sin(t) * 0.6 + sin(t * 2.7 + 1.3) * 0.4;
	flick = 0.88 + 0.12 * sin(t * 2.1) * sin(t * 0.63 + ph * 6.0);
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(
		vec4(normalize(cross(vec3(0.0, 1.0, 0.0), INV_VIEW_MATRIX[2].xyz)), 0.0),
		vec4(0.0, 1.0, 0.0, 0.0),
		vec4(normalize(cross(INV_VIEW_MATRIX[0].xyz, vec3(0.0, 1.0, 0.0))), 0.0),
		MODEL_MATRIX[3]);
	MODELVIEW_NORMAL_MATRIX = mat3(MODELVIEW_MATRIX);
}

void fragment() {
	vec2 q = vec2(UV.x - 0.5, 0.5 - UV.y) * quad_size;      // metres from the flame centre
	float lift = clamp((q.y + 0.045) / 0.095, 0.0, 1.0);
	q.x -= sway * lift * lift * 0.006;
	vec2 p = vec2(q.x / 0.021, q.y / (0.0475 * (0.96 + 0.08 * flick)));
	float a = 0.0;
	vec3 col = vec3(0.0);
	if (abs(p.x) < 1.0 && abs(p.y) < 1.0) {
		float r = 0.62 * sqrt(clamp(1.0 - (p.y + 0.35) / 1.35, 0.0, 1.0));
		r *= smoothstep(-1.0, -0.45, p.y);
		float d = abs(p.x) / max(r, 0.001);
		a = (1.0 - smoothstep(0.35, 1.0, d)) * step(0.001, r);
		col = mix(vec3(1.0, 0.5, 0.12), vec3(1.0, 0.92, 0.66), 1.0 - smoothstep(0.0, 0.75, d));
		col = mix(vec3(0.15, 0.25, 0.9), col, smoothstep(-0.95, -0.5, p.y));
	}
	float rr = dot(q, q);
	float edge = 1.0 - smoothstep(0.1, 0.15, length(q));
	float g = (exp(-rr / 0.0016) * 0.9 + exp(-rr / 0.009) * 0.25) * halo * edge;
	ALBEDO = (col * intensity * a + vec3(1.0, 0.62, 0.28) * g) * flick;
	ALPHA = clamp(a + g, 0.0, 1.0);
}
