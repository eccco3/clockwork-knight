// Scanned PBR surface with world-space macro variation, so big walls and masonry never read as tiled.
shader_type spatial;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D orm_tex : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D macro_tex : filter_linear_mipmap, repeat_enable;
uniform vec3 tint = vec3(1.0);
uniform float normal_strength = 1.0;
uniform float macro_strength = 0.2;
uniform float macro_scale = 0.15;
uniform float roughness_scale = 1.0;
uniform float grime_height = 0.0;
uniform float grime_strength = 0.0;
uniform float saturation = 1.0;
varying vec3 wpos;
varying vec3 wnrm;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnrm = normalize(mat3(MODEL_MATRIX) * NORMAL);
}

void fragment() {
	vec3 a = texture(albedo_tex, UV).rgb;
	a = mix(vec3(dot(a, vec3(0.3, 0.55, 0.15))), a, saturation);
	vec3 an = abs(wnrm);
	vec2 muv = an.y > 0.6 ? wpos.xz : (an.x > an.z ? wpos.zy : wpos.xy);
	float m = texture(macro_tex, muv * macro_scale).r;
	float m2 = texture(macro_tex, muv * macro_scale * 3.3 + vec2(0.37, 0.71)).r;
	float mv = (m * 0.65 + m2 * 0.35 - 0.5) * 2.0;
	a *= tint * COLOR.rgb * (1.0 + mv * macro_strength);
	if (grime_height > 0.0) {
		float g = grime_strength * (1.0 - smoothstep(0.0, grime_height, wpos.y)) * (0.5 + m2);
		a *= 1.0 - g;
	}
	ALBEDO = a;
	vec3 orm = texture(orm_tex, UV).rgb;
	ROUGHNESS = clamp(orm.g * roughness_scale, 0.0, 1.0);
	AO = orm.r;
	AO_LIGHT_AFFECT = 0.3;
	NORMAL_MAP = texture(normal_tex, UV).rgb;
	NORMAL_MAP_DEPTH = normal_strength;
}
