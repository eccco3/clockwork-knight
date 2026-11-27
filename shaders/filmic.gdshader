shader_type spatial;
// Blender's Filmic view transform, which the face sheets are rendered in, on all a camera sees: a quad over its
// view, under a linear tonemapper at exposure 1. `table` holds what Filmic shows of each light, `cells` a side
// over log2 of the light from stops.x to stops.y in each of red, green and blue (tools/faces/build_head.py).
render_mode unshaded, cull_disabled, depth_test_disabled, depth_draw_never, fog_disabled, shadows_disabled;

uniform sampler2D screen : hint_screen_texture, filter_nearest;
uniform sampler3D table : filter_linear, repeat_disable;
uniform vec2 stops = vec2(-14.0, 4.0);
uniform float cells = 65.0;

void vertex() {
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

void fragment() {
	vec3 light = textureLod(screen, SCREEN_UV, 0.0).rgb;
	vec3 at = clamp((log2(max(light, vec3(1e-9))) - stops.x) / (stops.y - stops.x), 0.0, 1.0);
	vec3 shown = textureLod(table, (at * (cells - 1.0) + 0.5) / cells, 0.0).rgb;
	ALBEDO = mix(shown / 12.92, pow((shown + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), shown));
	ALPHA = 1.0;
}
