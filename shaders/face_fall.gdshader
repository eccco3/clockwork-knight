shader_type spatial;
// The long hair's fall as the sheets streak it (tools/faces/build_faces.py, fall): the hair's colour, its
// strands running down it, UV.x where a point lies across them (tools/faces/hair.py, sheet).
render_mode diffuse_lambert, specular_schlick_ggx, cull_disabled;

#include "res://shaders/face_hair.gdshaderinc"

void vertex() {
	TANGENT = vec3(0.0, 1.0, 0.0);
	BINORMAL = cross(NORMAL, TANGENT);
}

void fragment() {
	vec3 streak = streaks(UV.x);
	vec3 n = relief(NORMAL, dFdx(VERTEX), dFdy(VERTEX), streak.xy);
	vec2 shine = gloss(streak.z);
	ALBEDO = hair_colour * clump(UV.x) * beneath(n, VIEW, shine.x);
	ROUGHNESS = shine.x;
	ANISOTROPY = shine.y;
	TANGENT = along(TANGENT, n);
	BINORMAL = cross(n, TANGENT);
	NORMAL = n;
}
