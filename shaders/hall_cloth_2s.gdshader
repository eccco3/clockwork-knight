// Two-sided hanging cloth (banners, tapestries): a pattern image over a tiling weave normal, with a soft grazing-angle sheen.
shader_type spatial;
render_mode cull_disabled;

uniform sampler2D pattern_tex : source_color, filter_linear_mipmap_anisotropic;
uniform sampler2D weave_normal : hint_normal, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D weave_orm : repeat_enable, filter_linear_mipmap_anisotropic;
uniform vec2 weave_scale = vec2(10.0, 10.0);
uniform float normal_strength = 0.8;
uniform float fuzz = 0.25;
uniform float saturation = 1.0;
uniform float brightness = 1.0;

void fragment() {
	vec3 a = texture(pattern_tex, UV).rgb * COLOR.rgb;
	a = mix(vec3(dot(a, vec3(0.3, 0.55, 0.15))), a, saturation) * brightness;
	vec2 wuv = UV * weave_scale;
	vec3 orm = texture(weave_orm, wuv).rgb;
	float fres = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	ALBEDO = a * mix(0.72, 1.0, orm.r) * (1.0 + fres * fuzz * 2.0);
	ROUGHNESS = 1.0;
	SPECULAR = 0.2;
	BACKLIGHT = a * 0.25;
	NORMAL_MAP = texture(weave_normal, wuv).rgb;
	NORMAL_MAP_DEPTH = normal_strength;
}
