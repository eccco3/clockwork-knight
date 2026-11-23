// Layered hearth flame card: Y-billboarded quad, scrolling noise, additive.
shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, shadows_disabled, fog_disabled;

uniform sampler2D noise_tex : repeat_enable, filter_linear_mipmap;
uniform float speed = 1.0;
uniform float intensity = 1.0;
uniform float seed = 0.0;
uniform float lean = 0.0;
uniform vec3 color_core : source_color = vec3(1.0, 0.72, 0.26);
uniform vec3 color_mid : source_color = vec3(1.0, 0.3, 0.03);
uniform vec3 color_tip : source_color = vec3(0.6, 0.07, 0.01);

void vertex() {
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(
		vec4(normalize(cross(vec3(0.0, 1.0, 0.0), INV_VIEW_MATRIX[2].xyz)), 0.0),
		vec4(0.0, 1.0, 0.0, 0.0),
		vec4(normalize(cross(INV_VIEW_MATRIX[0].xyz, vec3(0.0, 1.0, 0.0))), 0.0),
		MODEL_MATRIX[3]);
	MODELVIEW_NORMAL_MATRIX = mat3(MODELVIEW_MATRIX);
}

void fragment() {
	float h = 1.0 - UV.y;
	float t = TIME * speed + seed * 7.31;
	float n1 = texture(noise_tex, vec2(UV.x * 0.38 + seed * 0.37, h * 0.32 - t * 0.34)).r;
	float n2 = texture(noise_tex, vec2(UV.x * 0.8 - seed * 0.61, h * 0.65 - t * 0.6)).r;
	float n3 = texture(noise_tex, vec2(UV.x * 2.4 + seed * 0.13, h * 2.0 - t * 1.25)).r;
	float x = (UV.x - 0.5) * 2.0;
	x += (n1 - 0.5) * 0.9 * h + lean * h;
	// density: wide and hot at the base, torn into tongues toward the top
	float v = 1.0 - x * x * (1.25 + 3.2 * h) - h * 0.95;
	v += (n1 - 0.5) * 2.2 * (0.2 + h) + (n2 - 0.5) * 1.5 * (0.25 + h) + (n3 - 0.5) * 0.45 * h;
	float body = smoothstep(0.02, 0.5, v) * smoothstep(0.0, 0.07, h) * (1.0 - smoothstep(0.85, 1.0, h));
	float edge = 1.0 - smoothstep(0.75, 1.0, abs(UV.x - 0.5) * 2.0);
	body *= edge;
	vec3 col = mix(color_tip, color_mid, smoothstep(0.05, 0.45, v));
	col = mix(col, color_core, smoothstep(0.5, 1.05, v));
	ALBEDO = col * intensity * body;
	ALPHA = body;
}
