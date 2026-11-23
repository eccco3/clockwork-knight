// The flat white fog of the hall's windows (hall_glass.gdshader), seen from inside it: a little
// brighter overhead, and the dull earth below the horizon for the ambient light's bounce.
shader_type sky;

uniform vec3 fog_high : source_color = vec3(0.86, 0.9, 0.96);
uniform vec3 fog_low : source_color = vec3(0.6, 0.65, 0.71);
uniform vec3 ground : source_color = vec3(0.13, 0.12, 0.1);
uniform float energy = 1.0;

void sky() {
	float y = EYEDIR.y;
	vec3 c = mix(fog_low, fog_high, smoothstep(0.0, 0.75, y));
	c = mix(c, ground, smoothstep(0.0, -0.35, y));
	COLOR = c * energy;
}
