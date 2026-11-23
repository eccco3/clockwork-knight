// Bare earth with mossy patches, both Poly Haven scans. moss_map (1 px per metre) says where the
// moss grows, the same map that places the grass; the scans' height maps decide which one shows
// through along the border. Each scan is read at two scales mixed by slow noise to hide its repeat.
shader_type spatial;

uniform sampler2D mud_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D mud_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D mud_arm : hint_default_white, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D mud_height : hint_default_black, filter_linear_mipmap, repeat_enable;
uniform sampler2D moss_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D moss_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D moss_arm : hint_default_white, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D moss_height : hint_default_black, filter_linear_mipmap, repeat_enable;
uniform sampler2D moss_map : hint_default_black, filter_linear, repeat_disable;
uniform sampler2D noise : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform float map_size = 320.0;
uniform vec2 moss_edge = vec2(0.42, 0.72);
uniform float mud_tile = 2.6;
uniform float moss_tile = 2.2;
uniform vec3 mud_tint : source_color = vec3(1.08, 1.0, 0.9);
uniform vec3 moss_tint : source_color = vec3(1.0);
uniform float normal_depth = 1.3;

varying vec3 wp;

void vertex() {
	wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

#define scan(tex, uv, k) mix(texture(tex, uv), texture(tex, (uv) * 0.37 + vec2(0.43, 0.17)), k)

void fragment() {
	vec2 xz = wp.xz;
	float k = smoothstep(0.3, 0.7, texture(noise, xz / 19.0).r);
	float ragged = texture(noise, xz / 6.1).r + texture(noise, xz / 1.7 + 0.3).r * 0.6 - 0.8;
	float moss = smoothstep(moss_edge.x, moss_edge.y, texture(moss_map, xz / map_size + 0.5).r + ragged * 0.16);
	vec2 mu = xz / mud_tile;
	vec2 su = xz / moss_tile + vec2(0.61, 0.29);
	float mh = scan(mud_height, mu, k).r;
	float sh = scan(moss_height, su, k).r;
	float t = smoothstep(-0.3, 0.3, (moss + sh * 0.5) - (1.0 - moss + mh * 0.5));
	vec3 alb = mix(scan(mud_albedo, mu, k).rgb * mud_tint, scan(moss_albedo, su, k).rgb * moss_tint, t);
	vec3 arm = mix(scan(mud_arm, mu, k).rgb, scan(moss_arm, su, k).rgb, t);
	vec3 nrm = mix(scan(mud_normal, mu, k).rgb, scan(moss_normal, su, k).rgb, t);
	float macro = texture(noise, xz / 83.0 + 0.5).r;
	ALBEDO = alb * mix(0.78, 1.12, macro);
	AO = arm.r;
	AO_LIGHT_AFFECT = 0.35;
	ROUGHNESS = mix(arm.g, 1.0, 0.15);
	SPECULAR = 0.4;
	NORMAL_MAP = nrm;
	NORMAL_MAP_DEPTH = normal_depth;
}
