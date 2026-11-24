// Solid (3D) carved-wood material. The grain is a volume the carving cuts through, so growth
// rings show as contour bands on curved forms exactly as they do in real timber, with no UV
// seams. Rest-pose "grain space" coordinates (metres, z along the fibres) arrive in UV/UV2.
shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

uniform vec3 color_early : source_color = vec3(0.74, 0.50, 0.27);
uniform vec3 color_late : source_color = vec3(0.40, 0.22, 0.10);
uniform float ring_density = 130.0;
uniform float ring_contrast : hint_range(0.0, 1.0) = 0.55;
uniform float ring_wobble : hint_range(0.0, 2.0) = 0.6;
uniform float fiber_strength : hint_range(0.0, 1.0) = 0.22;
uniform float pore_strength : hint_range(0.0, 1.0) = 0.35;
uniform float figure_strength : hint_range(0.0, 1.0) = 0.25;
// The finish. The defaults are oiled, waxed wood: a broad sheen and no film. Lacquer is a coat over
// a smoother surface. Godot keeps a coat glossy at any coat_roughness, so it cannot stand in for wax.
uniform float roughness_min : hint_range(0.0, 1.0) = 0.36;
uniform float roughness_max : hint_range(0.0, 1.0) = 0.56;
uniform float coat : hint_range(0.0, 1.0) = 0.0;
uniform float coat_roughness : hint_range(0.0, 1.0) = 0.14;
uniform float bump : hint_range(0.0, 2.0) = 0.5;
uniform float paint : hint_range(0.0, 1.0) = 1.0;
uniform float paint_roughness : hint_range(0.0, 1.0) = 0.42;
// Paint on the face: a texture projected from the front. paint_origin is the grain-space
// position of the head frame's origin; paint_size is (half width, bottom, top) in metres. Zero = off.
uniform sampler2D paint_tex : source_color, hint_default_white, filter_linear_mipmap_anisotropic, repeat_disable;
uniform vec3 paint_origin = vec3(0.0);
uniform vec3 paint_size = vec3(0.0);

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

float fbm(vec3 p) {
	return vnoise(p) * 0.5 + vnoise(p * 2.03 + 7.1) * 0.3 + vnoise(p * 4.1 + 13.7) * 0.2;
}

void vertex() {
	gpos = vec3(UV, UV2.x);
	gseed = UV2.y;
}

void fragment() {
	vec3 p = gpos;
	float px = length(fwidth(p));                    // metres of grain space per pixel
	// the tree: rings about the pith (the z axis), wandering along the grain
	vec3 q = vec3(p.xy * 7.0, p.z * 1.3);
	vec2 warp = vec2(vnoise(q + 11.0), vnoise(q + 47.0)) - 0.5;
	float r = length(p.xy + warp * 0.035 * ring_wobble);
	float x = r * ring_density + (fbm(vec3(p.xy * 26.0, p.z * 3.2)) - 0.5) * 1.3 * ring_wobble;
	float t = fract(x);
	float ring_id = floor(x);
	float ring_var = 0.55 + 0.45 * hash13(vec3(ring_id, 3.0, gseed * 37.0));
	float ring_aa = clamp(1.0 - px * ring_density * 1.6, 0.0, 1.0);
	float late = smoothstep(0.30, 0.90, t) * (1.0 - smoothstep(0.93, 1.0, t));
	late = mix(0.42, late, ring_aa) * ring_var;
	// fibres: fine streaks along z; pores: short dark dashes, denser in early wood
	float fib_aa = clamp(1.0 - px * 900.0, 0.0, 1.0);
	float fib = vnoise(vec3(p.xy * 1300.0, p.z * 46.0)) * 0.6 + vnoise(vec3(p.xy * 420.0, p.z * 15.0)) * 0.4;
	float pore_aa = clamp(1.6 - px * 4500.0, 0.0, 1.0);       // gone before they shrink to a pixel and sparkle
	float pore = smoothstep(0.62, 0.80, rnoise(vec3(p.xy * 2300.0, p.z * 95.0))) * (1.0 - 0.6 * late) * pore_aa;
	// figure: slow shimmer bands across the grain (curl / ray fleck)
	float fig = vnoise(vec3(p.xy * 38.0, p.z * 5.0 + r * 60.0));

	vec3 col = mix(color_early, color_late, late * ring_contrast);
	col *= 1.0 + (fib - 0.5) * fiber_strength * fib_aa;
	col *= 1.0 - pore * pore_strength * 0.55;
	col *= 0.90 + 0.20 * vnoise(p * 11.0 + gseed * 9.0);
	col *= 1.0 + (fig - 0.5) * figure_strength;
	vec3 tint = pow(clamp(COLOR.rgb, vec3(0.0), vec3(1.0)), vec3(2.2));  // MSAA can extrapolate colours below zero
	if (paint_size.x > 0.0) {
		vec3 hp = p - paint_origin;                    // x across the face, y to the back, z up
		vec2 uv = vec2(0.5 + hp.x / (2.0 * paint_size.x), (paint_size.z - hp.z) / (paint_size.z - paint_size.y));
		tint *= mix(vec3(1.0), texture(paint_tex, uv).rgb, smoothstep(-0.012, -0.024, hp.y));
	}
	ALBEDO = col * mix(vec3(1.0), tint, paint);

	float painted = clamp((1.0 - min(tint.r, min(tint.g, tint.b))) * 2.0, 0.0, 1.0) * paint;
	float rough = mix(roughness_max, roughness_min, late) + pore * 0.18;
	ROUGHNESS = clamp(mix(rough, paint_roughness, painted), 0.03, 1.0);
	SPECULAR = 0.5;
	CLEARCOAT = coat;
	CLEARCOAT_ROUGHNESS = coat_roughness;

	// relief: late wood stands a hair proud, pores are pits
	float h = (late * 0.5 + (fib - 0.5) * 0.35 * fib_aa - pore * 1.2) * 0.00012 * bump;
	vec3 dpx = dFdx(VERTEX);
	vec3 dpy = dFdy(VERTEX);
	float dhx = dFdx(h);
	float dhy = dFdy(h);
	vec3 r1 = cross(dpy, NORMAL);
	vec3 r2 = cross(NORMAL, dpx);
	float det = dot(dpx, r1);
	vec3 grad = sign(det) * (dhx * r1 + dhy * r2);
	vec3 nn = abs(det) * NORMAL - grad;
	float l2 = dot(nn, nn);
	// degenerate derivatives (sub-pixel triangles) would give NaN, which bloom turns into a white flare
	if (l2 > 1e-24 && l2 < 1e24) {
		NORMAL = nn * inversesqrt(l2);
	}
}
