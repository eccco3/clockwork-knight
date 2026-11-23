// Brass, steel and leather for the knight: a base response with procedural micro-variation
// (brushing streaks, tarnish in broad patches, fine pitting) in rest-pose grain space.
shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

uniform vec3 albedo : source_color = vec3(0.90, 0.68, 0.30);
uniform vec3 tarnish_color : source_color = vec3(0.38, 0.26, 0.12);
uniform float metallic : hint_range(0.0, 1.0) = 1.0;
uniform float roughness : hint_range(0.0, 1.0) = 0.28;
uniform float roughness_var : hint_range(0.0, 1.0) = 0.18;
uniform float tarnish : hint_range(0.0, 1.0) = 0.25;
uniform float streak : hint_range(0.0, 1.0) = 0.5;
uniform float grain_scale = 900.0;
uniform float bump : hint_range(0.0, 2.0) = 0.3;
uniform float coat : hint_range(0.0, 1.0) = 0.0;

varying vec3 gpos;
varying float gseed;

float hash13(vec3 p) {
	p = fract(p * 0.1031);
	p += dot(p, p.zyx + 31.32);
	return fract((p.x + p.y) * p.z);
}

float vnoise(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = mix(mix(hash13(i), hash13(i + vec3(1, 0, 0)), f.x), mix(hash13(i + vec3(0, 1, 0)), hash13(i + vec3(1, 1, 0)), f.x), f.y);
	float b = mix(mix(hash13(i + vec3(0, 0, 1)), hash13(i + vec3(1, 0, 1)), f.x), mix(hash13(i + vec3(0, 1, 1)), hash13(i + vec3(1, 1, 1)), f.x), f.y);
	return mix(a, b, f.z);
}

float rnoise(vec3 p) {
	vec3 r = vec3(0.80 * p.x - 0.60 * p.y, 0.60 * p.x + 0.80 * p.y, p.z) * 1.37 + 17.3;
	return 0.5 * (vnoise(p) + vnoise(r));
}

void vertex() {
	gpos = vec3(UV, UV2.x);
	gseed = UV2.y;
}

void fragment() {
	vec3 p = gpos + gseed * 3.7;
	float px = length(fwidth(gpos));
	float aa = clamp(1.0 - px * grain_scale * 0.7, 0.0, 1.0);
	float patches = rnoise(p * 55.0) * 0.6 + rnoise(p * 140.0) * 0.4;
	float fine = rnoise(vec3(p.xy * grain_scale, p.z * grain_scale * mix(1.0, 0.06, streak)));
	float pits = smoothstep(0.70, 0.84, rnoise(p * grain_scale * 0.9 + 19.0)) * clamp(1.6 - px * grain_scale * 2.2, 0.0, 1.0);
	float tn = smoothstep(0.45, 0.80, patches) * tarnish;
	ALBEDO = mix(albedo, tarnish_color, tn) * (1.0 + (fine - 0.5) * 0.10 * aa) * (1.0 - pits * 0.15);
	METALLIC = metallic;
	ROUGHNESS = clamp(roughness + (fine - 0.5) * roughness_var * aa + tn * 0.22 + pits * 0.2, 0.14, 1.0);
	CLEARCOAT = coat;
	CLEARCOAT_ROUGHNESS = 0.2;
	float h = ((fine - 0.5) * 0.4 * aa - pits) * 0.00008 * bump;
	vec3 dpx = dFdx(VERTEX);
	vec3 dpy = dFdy(VERTEX);
	vec3 r1 = cross(dpy, NORMAL);
	vec3 r2 = cross(NORMAL, dpx);
	float det = dot(dpx, r1);
	vec3 grad = sign(det) * (dFdx(h) * r1 + dFdy(h) * r2);
	vec3 nn = abs(det) * NORMAL - grad;
	float l2 = dot(nn, nn);
	// degenerate derivatives (sub-pixel triangles) would give NaN, which bloom turns into a white flare
	if (l2 > 1e-24 && l2 < 1e24) {
		NORMAL = nn * inversesqrt(l2);
	}
}
