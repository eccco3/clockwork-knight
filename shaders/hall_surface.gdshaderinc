// Scanned PBR surface with world-space macro variation, so big walls and masonry never read as tiled.
// Define WEAR before including it for a surface a craftsman wears: a map over the floor plan pales it
// where feet go (red) and darkens it with grime (green), low on walls.

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
#ifdef WEAR
uniform sampler2D wear_tex : filter_linear_mipmap, repeat_disable;
uniform vec4 wear_rect = vec4(0.0, 0.0, 1.0, 1.0);   // world x, z of the map's corner, and its size
#endif
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
	vec3 orm = texture(orm_tex, UV).rgb;
	float rough = orm.g * roughness_scale;
#ifdef WEAR
	vec2 w = texture(wear_tex, (wpos.xz - wear_rect.xy) / wear_rect.zw).rg;
	float low = an.y > 0.6 ? 1.0 : 1.0 - smoothstep(0.1, 1.1, wpos.y);
	float feet = clamp(w.r * (0.4 + 1.2 * m2) * low, 0.0, 1.0);
	float grime = clamp(w.g * (0.3 + 1.4 * m) * low, 0.0, 1.0);
	// feet wear the finish through to paler, duller wood; grime darkens and greases it
	a = mix(a, vec3(dot(a, vec3(0.3, 0.55, 0.15))) * 1.6, feet * 0.65);
	a *= 1.0 - 0.6 * grime;
	rough = mix(mix(rough, 0.95, feet), 0.45, grime * 0.6);
#endif
	ALBEDO = a;
	ROUGHNESS = clamp(rough, 0.0, 1.0);
	AO = orm.r;
	AO_LIGHT_AFFECT = 0.3;
	NORMAL_MAP = texture(normal_tex, UV).rgb;
	NORMAL_MAP_DEPTH = normal_strength;
}
