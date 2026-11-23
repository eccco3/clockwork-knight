// Bed of coals / charred logs: dark char with slowly breathing orange patches.
shader_type spatial;

uniform sampler2D noise_tex : repeat_enable, filter_linear_mipmap;
uniform float glow = 4.0;
uniform float coverage = 0.5;
uniform float scale = 2.0;
uniform float ash_amount = 1.0;
uniform vec3 char_color : source_color = vec3(0.025, 0.02, 0.018);
uniform vec3 hot : source_color = vec3(1.0, 0.3, 0.03);

void fragment() {
	vec2 uv = UV * scale;
	float n = texture(noise_tex, uv).r;
	float n2 = texture(noise_tex, uv * 3.3 + vec2(0.37, 0.11)).r;
	float n3 = texture(noise_tex, uv * 9.0 + vec2(0.71, 0.53)).r;
	float breathe = texture(noise_tex, uv * 0.3 + vec2(TIME * 0.035, TIME * 0.022)).r;
	float f = n * 0.5 + n2 * 0.33 + n3 * 0.17 + (breathe - 0.5) * 0.4;
	float th = 1.0 - coverage;
	float heat = smoothstep(th - 0.18, th + 0.22, f);
	// ash crust: fine dark flecks over the glow
	float ash = smoothstep(0.42, 0.62, n3) * ash_amount;
	heat *= mix(1.0, 0.35, ash * (1.0 - heat * 0.6));
	ALBEDO = char_color * COLOR.rgb * (0.5 + n2) + vec3(0.12, 0.11, 0.1) * ash * 0.4;
	ROUGHNESS = 0.95;
	vec3 e = mix(vec3(0.45, 0.03, 0.0), hot, heat) * heat;
	e += vec3(1.0, 0.62, 0.2) * pow(heat, 4.0) * 0.5;
	EMISSION = e * glow;
}
