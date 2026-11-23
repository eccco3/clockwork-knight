// Enamelled glass eye. Grain space here is the eyeball's own frame: z runs out along the gaze,
// x to the figure's left, y up. Everything is resolved analytically, so it stays crisp at any distance.
shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

uniform vec3 sclera : source_color = vec3(0.84, 0.81, 0.75);
uniform vec3 iris_outer : source_color = vec3(0.10, 0.22, 0.19);
uniform vec3 iris_inner : source_color = vec3(0.56, 0.44, 0.19);
uniform float iris_size : hint_range(0.2, 0.8) = 0.385;     // radians from the gaze axis (IRIS in head.py)
uniform float pupil_size : hint_range(0.05, 0.4) = 0.15;
uniform float lid_height : hint_range(0.0, 0.8) = 0.335;     // where the upper lid rests (AP_UP in head.py)
uniform float lid_shadow : hint_range(0.0, 1.0) = 0.55;

varying vec3 gpos;

float hash11(float n) {
	return fract(sin(n * 127.1) * 43758.5453);
}

// value noise that wraps after `period` cells, so it closes round the iris without a seam
float pnoise(float x, float period) {
	float i = floor(x);
	float f = fract(x);
	f = f * f * (3.0 - 2.0 * f);
	return mix(hash11(mod(i, period)), hash11(mod(i + 1.0, period)), f);
}

void vertex() {
	gpos = vec3(UV, UV2.x);
}

void fragment() {
	vec3 d = normalize(gpos);
	float rr = length(d.xy);
	float ang = atan(rr, d.z);                                  // well behaved at the pole, unlike acos
	float aa = clamp(fwidth(ang) * 1.2, 1e-4, 0.2);
	float turn = atan(d.y, d.x) / TAU + 0.5;
	float k = clamp((ang - pupil_size) / (iris_size - pupil_size), 0.0, 1.0);

	// radial fibres, each octave faded out before it gets finer than a pixel
	float px_turn = aa / max(rr, 0.04) / TAU;                   // turns of azimuth per pixel
	float f_lo = mix(0.5, pnoise(turn * 56.0, 56.0), clamp(1.0 - px_turn * 56.0 * 2.0, 0.0, 1.0));
	float f_hi = mix(0.5, pnoise(turn * 170.0 + 9.0, 170.0), clamp(1.0 - px_turn * 170.0 * 2.0, 0.0, 1.0));
	float fibres = f_lo * 0.6 + f_hi * 0.4;

	vec3 iris = mix(iris_inner, iris_outer, smoothstep(0.12, 0.70, k + (fibres - 0.5) * 0.30));
	iris *= 0.80 + 0.40 * fibres;
	iris *= mix(0.55, 1.0, smoothstep(0.0, 0.22, k));           // darker collar round the pupil
	iris *= 1.0 - 0.70 * smoothstep(0.72, 1.0, k);              // limbal ring

	vec3 white = sclera * (1.0 - 0.30 * smoothstep(0.55, 1.35, ang));
	float limbus = max(aa, 0.022);                              // the iris edge is soft in a real eye
	vec3 col = mix(white, iris, 1.0 - smoothstep(iris_size - limbus, iris_size + limbus, ang));
	col = mix(col, vec3(0.010, 0.008, 0.007), 1.0 - smoothstep(pupil_size - aa, pupil_size + aa, ang));

	// the upper lid and lashes shade the top of the eye
	float elev = asin(clamp(d.y, -1.0, 1.0));
	col *= 1.0 - lid_shadow * smoothstep(lid_height - 0.24, lid_height + 0.03, elev);

	ALBEDO = col;
	ROUGHNESS = 0.24;
	SPECULAR = 0.6;
	CLEARCOAT = 1.0;
	CLEARCOAT_ROUGHNESS = 0.10;
}
