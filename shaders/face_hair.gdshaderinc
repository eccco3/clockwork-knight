// The faces' hair as the sheets streak it (tools/faces/build_faces.py, streaked): across its strands, finely in
// relief and in clumps lighter and darker, by Blender's noise of where a point lies across them, and glossy
// along them. Shared by the head (face_head.gdshader) and the long hair's fall (face_fall.gdshader).

uniform vec3 hair_colour = vec3(0.045, 0.032, 0.025);   // linear
uniform float hair_roughness = 0.45;
uniform float hair_sheen = 0.8;                         // the anisotropy along the strands
uniform bool streaked = true;
uniform vec2 strands = vec2(0.0005, 0.0003);            // the streaks' noise scale (metres) and their relief
uniform vec2 clumps = vec2(0.004, 0.25);                // the clumps' noise scale and how much lighter or darker

// Blender's 1D Perlin noise (Cycles' noise.h): its hash, Bob Jenkins' lookup3 of one word...
uint lookup3(uint k) {
	uint a = 3735928576u + k;
	uint b = 3735928576u;
	uint c = 3735928576u;
	c ^= b; c -= (b << 14u) | (b >> 18u);
	a ^= c; a -= (c << 11u) | (c >> 21u);
	b ^= a; b -= (a << 25u) | (a >> 7u);
	c ^= b; c -= (b << 16u) | (b >> 16u);
	a ^= c; a -= (c << 4u) | (c >> 28u);
	b ^= a; b -= (a << 14u) | (a >> 18u);
	c ^= b; c -= (b << 24u) | (b >> 8u);
	return c;
}

// ...the slope it gives an integer point...
float slope(int i) {
	uint h = lookup3(uint(i)) & 15u;
	float g = float(1u + (h & 7u));
	return (h & 8u) != 0u ? -g : g;
}

// ...and the signed noise there, with its derivative.
vec2 perlin(float x) {
	float floor_x = floor(x);
	float f = x - floor_x;
	int i = int(floor_x);
	float g0 = slope(i), g1 = slope(i + 1);
	float a = g0 * f, b = g1 * (f - 1.0);
	float u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
	float du = 30.0 * f * f * (f - 1.0) * (f - 1.0);
	return 0.25 * vec2(mix(a, b, u), mix(g0, g1, u) + du * (b - a));
}

// The Noise Texture node's Fac in 1D, fBM of `detail` octaves at roughness 0.5 and lacunarity 2, normalized,
// at w / scale, and its derivative by w.
vec2 noise(float w, float scale, int detail) {
	float x = w / scale, fscale = 1.0, amp = 1.0, most = 0.0;
	vec2 sum = vec2(0.0);
	for (int i = 0; i <= detail; i++) {
		vec2 t = perlin(fscale * x);
		sum += amp * vec2(t.x, t.y * fscale);
		most += amp;
		amp *= 0.5;
		fscale *= 2.0;
	}
	return vec2(0.5 * sum.x / most + 0.5, 0.5 * sum.y / (most * scale));
}

// The normal n bent by a relief along it whose height changes by dh across the screen's x and y, where the
// view-space point changes by dpdx and dpdy: Blender's Bump node (Mikkelsen's surface gradient). The
// derivatives are taken outside branches.
vec3 relief(vec3 n, vec3 dpdx, vec3 dpdy, vec2 dh) {
	vec3 rx = cross(dpdy, n), ry = cross(n, dpdx);
	float det = dot(dpdx, rx);
	vec3 bent = abs(det) * n - sign(det) * (dh.x * rx + dh.y * ry);
	return dot(bent, bent) > 0.0 ? normalize(bent) : n;
}

// How much lighter or darker the hair is at `across` (metres across the strands): about 1.
float clump(float across) {
	return streaked ? mix(1.0 - clumps.y, 1.0 + clumps.y, clamp(noise(across, clumps.x, 2).x, 0.0, 1.0)) : 1.0;
}

// How the strands' relief changes across the screen at `across` (.xy), the Fac of the noise of 4 octaves
// relieving it strands.y high; and, in .z, the mean square of the slopes across the strands of the octaves
// too fine for the pixels to show, which are faded out over their last pixel and roughen the hair instead, as
// a render that averages many samples a pixel shows them (Toksvig). SLOPE is the mean square of the noise's
// slope per unit.
const float SLOPE = 1.2412;
vec3 streaks(float across) {
	vec2 step = vec2(dFdx(across), dFdy(across));
	if (!streaked) {
		return vec3(0.0);
	}
	float pixel = max(length(step), 1e-9);
	float x = across / strands.x, fscale = 1.0, amp = 1.0, most = 0.0, slope = 0.0, lost = 0.0;
	for (int i = 0; i <= 4; i++) {
		float shown = clamp(strands.x / fscale / pixel - 1.0, 0.0, 1.0);
		slope += perlin(fscale * x).y * shown;
		lost += 1.0 - shown * shown;
		most += amp;
		amp *= 0.5;
		fscale *= 2.0;
	}
	float rise = 0.5 * strands.y / (most * strands.x);
	return vec3(rise * slope * step, rise * rise * SLOPE * lost);
}

// The roughness and anisotropy (Godot's, which widen the highlight along the tangent as Blender's do) that give
// the hair's highlight hair_roughness and hair_sheen, widened across the strands by slopes of mean square `lost`.
vec2 gloss(float lost) {
	float alpha = hair_roughness * hair_roughness;
	float aspect = sqrt(1.0 - 0.9 * hair_sheen);
	float along_strands = alpha / aspect, across = sqrt(alpha * alpha * aspect * aspect + 2.0 * lost);
	return vec2(sqrt(sqrt(along_strands * across)), (1.0 - across / along_strands) / 0.9);
}

// How much light the gloss over the paint leaves it, seen along `view` on a surface of normal n and this
// roughness: Cycles' Principled BSDF dims its diffuse by one less its gloss's albedo toward the eye, as Godot does
// not; that albedo by the fit Godot's ambient gloss uses (Karis), for IOR 1.5.
float beneath(vec3 n, vec3 view, float roughness) {
	vec4 r = roughness * vec4(-1.0, -0.0275, -0.572, 0.022) + vec4(1.0, 0.0425, 1.04, -0.04);
	float a004 = min(r.x * r.x, exp2(-9.28 * clamp(dot(n, view), 0.0, 1.0))) * r.x + r.y;
	vec2 env = vec2(-1.04, 1.04) * a004 + r.zw;
	return 1.0 - (0.04 * env.x + env.y);
}

// The tangent t made square to the normal n: Godot's anisotropic highlight wants them so wherever it is used.
vec3 along(vec3 t, vec3 n) {
	vec3 square = t - n * dot(n, t);
	return dot(square, square) > 1e-12 ? normalize(square) : normalize(cross(n, abs(n.x) < 0.9 ? vec3(1.0, 0.0, 0.0) : vec3(0.0, 1.0, 0.0)));
}
