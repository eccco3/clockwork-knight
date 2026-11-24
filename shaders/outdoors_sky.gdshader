// The flat white fog of the hall's windows (hall_glass.gdshader), seen from inside it: a little
// brighter overhead, and the dull earth below the horizon for the ambient light's bounce.
// The fog spreads the sun into a soft glow. Lacquer and brass reflect that glow rather than a
// point, so the sun light itself has no specular.
shader_type sky;

uniform vec3 fog_high : source_color = vec3(0.86, 0.9, 0.96);
uniform vec3 fog_low : source_color = vec3(0.6, 0.65, 0.71);
uniform vec3 ground : source_color = vec3(0.13, 0.12, 0.1);
uniform float energy = 1.0;
uniform float sun_glow = 50.0;
uniform float sun_spread = 0.175;  // radians from the sun to where the glow falls to 60%

void sky() {
	float y = EYEDIR.y;
	vec3 c = mix(fog_low, fog_high, smoothstep(0.0, 0.75, y)) * energy;
	if (LIGHT0_ENABLED) {
		float glow = exp((dot(EYEDIR, LIGHT0_DIRECTION) - 1.0) / (sun_spread * sun_spread));
		c += LIGHT0_COLOR * LIGHT0_ENERGY * sun_glow * glow;
	}
	COLOR = mix(c, ground * energy, smoothstep(0.0, -0.35, y));
}
