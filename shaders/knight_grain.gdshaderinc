// Grain space for the knight's wood and surface shaders: the rest-pose coordinates (metres, z along
// the fibres) and the per-piece seed that her build stores in UV and UV2, value noise over them, and
// the relief of a height field too fine to model.

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

// two value-noise lattices at an angle to each other, so thresholded spots are not square
float rnoise(vec3 p) {
	vec3 r = vec3(0.80 * p.x - 0.60 * p.y, 0.60 * p.x + 0.80 * p.y, p.z) * 1.37 + 17.3;
	return 0.5 * (vnoise(p) + vnoise(r));
}

void vertex() {
	gpos = vec3(UV, UV2.x);
	gseed = UV2.y;
}

// The normal of the surface at `position` once it is raised by `height` metres.
vec3 relief(float height, vec3 position, vec3 normal) {
	vec3 dpx = dFdx(position);
	vec3 dpy = dFdy(position);
	vec3 r1 = cross(dpy, normal);
	vec3 r2 = cross(normal, dpx);
	float det = dot(dpx, r1);
	vec3 grad = sign(det) * (dFdx(height) * r1 + dFdy(height) * r2);
	vec3 raised = abs(det) * normal - grad;
	float l2 = dot(raised, raised);
	// degenerate derivatives (sub-pixel triangles) would give NaN, which bloom turns into a white flare
	return l2 > 1e-24 && l2 < 1e24 ? raised * inversesqrt(l2) : normal;
}
