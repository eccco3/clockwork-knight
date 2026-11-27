shader_type spatial;
// A head of the face model as the sheets paint it (tools/faces/build_faces.py, portrait), worn by
// scripts/face_head.gd: its paint, the hair over it and the brows its brow numbers shape (tools/faces/brows.py),
// standing off the skin; skin, hair or eye wherever more than half of a point is.
render_mode diffuse_lambert, specular_schlick_ggx, cull_disabled;

#include "res://shaders/face_hair.gdshaderinc"

uniform float skin_roughness = 0.5;
uniform float eye_roughness = 0.15;
uniform float brows[6];                 // high, arched, slanted up, thick, long, apart
uniform vec3 brow_curve[3];             // (x, z, half height) of the inner end, the peak and the tail
uniform float brow_units[6];            // what one unit of each does
uniform float brow_fade = 0.003;
uniform float brow_density = 0.9;
uniform float brow_rise = 0.0006;       // the brows stand this far off the skin

varying vec3 paint;
varying float covered;                  // how much is hair or brow, as the sheets' vertices carry it
varying float eye;
varying float strand;

float ramp(float a, float b, float x) {
	float t = clamp((x - a) / (b - a), 0.0, 1.0);
	return t * t * (3.0 - 2.0 * t);
}

// How much of the point `at` of the mean face (x from the midline, z up) is brow, as brows.brow has it.
float brow(vec2 at) {
	float x = abs(at.x), z = at.y;
	float arched = brow_units[1] * brows[1], slanted = brow_units[2] * brows[2];
	vec3 xs = vec3(brow_curve[0].x + brow_units[5] * brows[5], brow_curve[1].x, brow_curve[2].x + brow_units[4] * brows[4]);
	vec3 zs = brow_units[0] * brows[0] + vec3(brow_curve[0].y - 0.5 * arched - slanted, brow_curve[1].y + arched,
			brow_curve[2].y - 0.5 * arched + slanted);
	float middle = zs.x * (x - xs.y) * (x - xs.z) / ((xs.x - xs.y) * (xs.x - xs.z))
			+ zs.y * (x - xs.x) * (x - xs.z) / ((xs.y - xs.x) * (xs.y - xs.z))
			+ zs.z * (x - xs.x) * (x - xs.y) / ((xs.z - xs.x) * (xs.z - xs.y));
	vec3 heights = vec3(brow_curve[0].z, brow_curve[1].z, brow_curve[2].z) * exp(brow_units[3] * brows[3]);
	float height = x < xs.y ? mix(heights.x, heights.y, clamp((x - xs.x) / (xs.y - xs.x), 0.0, 1.0))
			: mix(heights.y, heights.z, clamp((x - xs.y) / (xs.z - xs.y), 0.0, 1.0));
	float band = ramp(0.0, 1.0, (1.0 - abs(z - middle) / height) * 2.0);
	return brow_density * band * ramp(xs.x, xs.x + brow_fade, x) * ramp(xs.z, xs.z - brow_fade, x);
}

void vertex() {
	float b = brow(UV) * UV2.x;
	paint = CUSTOM0.rgb;
	covered = max(CUSTOM0.a, b);
	eye = UV2.y;
	strand = CUSTOM1.w;
	VERTEX += NORMAL * brow_rise * b;
	TANGENT = CUSTOM1.xyz;
	BINORMAL = cross(NORMAL, TANGENT);
}

void fragment() {
	float rise = brow_rise * brow(UV) * UV2.x;
	vec3 dpdx = dFdx(VERTEX), dpdy = dFdy(VERTEX);
	vec3 n = relief(NORMAL, dpdx, dpdy, vec2(dFdx(rise), dFdy(rise)));
	vec3 streak = streaks(strand);
	vec3 colour = paint + covered * (hair_colour - paint);
	float rough = skin_roughness;
	if (eye > 0.5) {
		rough = eye_roughness;
	} else if (covered > 0.5) {
		colour *= clump(strand);
		n = relief(n, dpdx, dpdy, streak.xy);
		vec2 shine = gloss(streak.z);
		rough = shine.x;
		ANISOTROPY = shine.y;
	}
	ALBEDO = colour * beneath(n, VIEW, rough);
	ROUGHNESS = rough;
	NORMAL = n;
	TANGENT = along(TANGENT, n);
	BINORMAL = cross(n, TANGENT);
}
