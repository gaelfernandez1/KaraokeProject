/*
 * The shaders of the night globe (GLSL ES 3.00). Everything is drawn in the globe's own frame,
 * where Galicia's centre is at the front (+z) and the north is up, then turned by `uGlobe` and
 * seen through `uViewProj`. The moon stays where it is while the globe turns under it.
 */

const HEAD = `#version 300 es
precision highp float;
`;

/** Shared by the shaders that place things on the sphere. */
const COMMON = `
uniform mat4 uViewProj;
uniform mat3 uGlobe;
uniform vec3 uEye;
uniform float uPx;
uniform float uTime;

vec3 dir(vec2 a) {
	float c = cos(a.y);
	return vec3(c * sin(a.x), sin(a.y), c * cos(a.x));
}

/* 1 facing the eye, 0 at the edge of the globe, negative behind it. */
float facing(vec3 world) {
	return dot(normalize(world), normalize(uEye - world));
}
`;

/** The atlas: relief, lights, distance to the coast and borders, by angle from the centre. */
const ATLAS = `
uniform sampler2D uAtlas;
uniform float uExtent;
uniform float uCoastStep;

/* Where a point of the land's frame falls on the atlas; outside it, a negative x. */
vec2 atlasUv(vec3 p) {
	if (p.z <= 0.0) return vec2(-1.0);
	vec2 uv = vec2(atan(p.x, p.z) + uExtent, uExtent - asin(clamp(p.y, -1.0, 1.0))) / (2.0 * uExtent);
	if (uv.x <= 0.0 || uv.x >= 1.0 || uv.y <= 0.0 || uv.y >= 1.0) return vec2(-1.0);
	return uv;
}

/* Height from 0 to 1 of the tallest. */
float heightAt(vec2 uv) {
	float stored = textureLod(uAtlas, uv, 0.0).r * 255.0;
	float root = max(stored - 1.0, 0.0) / 254.0;
	return root * root;
}

/* Cells to the coast: positive inland, negative out at sea. */
float coastAt(vec2 uv) {
	return (textureLod(uAtlas, uv, 0.0).b * 255.0 - 128.0) / uCoastStep;
}
`;

const ROUND = `
float disc(float soft) {
	float r = length(gl_PointCoord - 0.5) * 2.0;
	return smoothstep(1.0, soft, r);
}
`;

export const STARS_VS = `${HEAD}
in vec4 aStar;
in float aSeed;
uniform mat3 uSky;
uniform vec2 uLens;
uniform float uTime;
uniform float uDpr;
out float vAlpha;
void main() {
	vec3 p = uSky * aStar.xyz;
	gl_Position = vec4(p.x * uLens.x, p.y * uLens.y, -p.z * 0.999, -p.z);
	float twinkle = 0.78 + 0.22 * sin(uTime * (0.4 + aSeed * 1.5) + aSeed * 50.0);
	// Fewer and fainter away from the planet: the canvas ends without an edge.
	vec2 at = gl_Position.xy / max(gl_Position.w, 0.001);
	vAlpha = aStar.w * twinkle * smoothstep(1.0, 0.55, length(at));
	gl_PointSize = (1.0 + aStar.w * 1.4) * uDpr;
}`;

export const STARS_FS = `${HEAD}
in float vAlpha;
out vec4 color;
${ROUND}
void main() {
	color = vec4(vec3(0.78, 0.88, 1.0) * vAlpha * disc(0.1), 0.0);
}`;

export const HALO_VS = `${HEAD}
in vec2 aCorner;
uniform mat4 uViewProj;
uniform float uSize;
out vec2 vAt;
void main() {
	vAt = aCorner;
	gl_Position = uViewProj * vec4(aCorner * uSize, 0.0, 1.0);
}`;

export const HALO_FS = `${HEAD}
in vec2 vAt;
uniform float uEdge;
uniform float uTech;
out vec4 color;
void main() {
	float d = length(vAt);
	// Brightest right at the planet's edge, gone at the square's.
	float glow = pow(smoothstep(1.0, uEdge, d), 2.6);
	color = vec4(mix(vec3(0.14, 0.40, 0.80), vec3(0.2, 0.7, 0.9), uTech) * glow * 0.22, 0.0);
}`;

export const BALL_VS = `${HEAD}
in vec3 aPos;
${COMMON}
uniform float uRadius;
out vec3 vWorld;
out vec3 vLand;
void main() {
	vLand = aPos;
	vWorld = uGlobe * (aPos * uRadius);
	gl_Position = uViewProj * vec4(vWorld, 1.0);
}`;

export const SEA_FS = `${HEAD}
in vec3 vWorld;
in vec3 vLand;
uniform mat3 uGlobe;
uniform vec3 uEye;
uniform vec3 uMoon;
uniform float uTime;
uniform float uShown;
uniform float uTech;
${ATLAS}
out vec4 color;
void main() {
	vec3 n = normalize(vLand);
	vec3 normal = normalize(vWorld);
	vec3 view = normalize(uEye - vWorld);
	float ndv = max(dot(normal, view), 0.0);

	// The deep, a little lighter towards the edge where the air thickens.
	vec3 c = mix(vec3(0.020, 0.052, 0.100), vec3(0.006, 0.015, 0.034), pow(ndv, 0.85));

	// Meridians and parallels every fifteen degrees, as a chart has them.
	vec2 g = vec2(atan(n.x, n.z), asin(clamp(n.y, -1.0, 1.0))) / radians(15.0);
	vec2 w = max(fwidth(g), vec2(1e-5));
	vec2 gl = abs(fract(g - 0.5) - 0.5) / w;
	float meridian = (1.0 - min(gl.x, 1.0)) * smoothstep(1.0, 0.9, abs(n.y)) * step(w.x, 0.4);
	float parallel = 1.0 - min(gl.y, 1.0);
	c += vec3(0.16, 0.44, 0.78) * max(meridian, parallel) * (0.075 + 0.2 * uTech) * uShown;

	// The moon on the water: a soft sheen and a glint that the swell breaks up.
	vec3 ripple = vec3(
		sin(n.x * 83.0 + n.y * 31.0 + uTime * 0.50),
		sin(n.y * 97.0 - n.z * 41.0 - uTime * 0.43),
		sin(n.z * 71.0 + n.x * 53.0 + uTime * 0.37)
	);
	vec3 wave = normalize(normal + uGlobe * ripple * 0.03);
	vec3 halfway = normalize(uMoon + view);
	c += vec3(0.040, 0.085, 0.150) * pow(max(dot(normal, halfway), 0.0), 9.0);
	c += vec3(0.50, 0.66, 0.90) * pow(max(dot(wave, halfway), 0.0), 150.0) * 0.5;

	// Near Galicia: the shallows glow, and water lines follow the coast as on an old chart,
	// breathing slowly out to sea.
	vec2 uv = atlasUv(n);
	if (uv.x >= 0.0) {
		float out_ = max(-coastAt(uv), 0.0);
		float near = exp(-out_ * 0.24);
		c += vec3(0.05, 0.36, 0.62) * near * 0.5 * uShown;
		float band = fract(out_ * 0.2 - uTime * 0.045);
		float line = smoothstep(0.0, 0.1, band) * smoothstep(0.3, 0.1, band);
		c += vec3(0.20, 0.60, 0.95) * line * exp(-out_ * 0.13) * 0.2 * uShown;
	}
	color = vec4(c, 1.0);
}`;

export const AIR_FS = `${HEAD}
in vec3 vWorld;
in vec3 vLand;
uniform vec3 uEye;
uniform vec3 uMoon;
out vec4 color;
void main() {
	vec3 normal = normalize(vWorld);
	float ndv = max(dot(normal, normalize(uEye - vWorld)), 0.0);
	float haze = pow(1.0 - ndv, 5.0);
	// A little brighter on the side the moon lights.
	float lit = 0.7 + 0.6 * max(dot(normal, uMoon), 0.0);
	color = vec4(vec3(0.30, 0.60, 0.95) * haze * 0.36 * lit, 0.0);
}`;

export const LAND_VS = `${HEAD}
in vec2 aUv;
${COMMON}
${ATLAS}
uniform float uRelief;
out vec2 vUv;
out vec3 vWorld;
out vec3 vUp;
void main() {
	vUv = aUv;
	vec2 angle = vec2(-uExtent + aUv.x * 2.0 * uExtent, uExtent - aUv.y * 2.0 * uExtent);
	vUp = dir(angle);
	vWorld = uGlobe * (vUp * (1.0 + heightAt(aUv) * uRelief));
	gl_Position = uViewProj * vec4(vWorld, 1.0);
}`;

export const LAND_FS = `${HEAD}
in vec2 vUv;
in vec3 vWorld;
in vec3 vUp;
uniform mat3 uGlobe;
uniform vec3 uEye;
uniform vec3 uMoon;
uniform float uTime;
uniform float uTexel;
uniform float uSlope;
uniform float uTallest;
uniform float uLights;
uniform float uParty;
uniform float uTech;
uniform float uScan;
uniform float uScanAt;
uniform float uFill;
${ATLAS}
out vec4 color;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void main() {
	float inland = coastAt(vUv);
	float alpha = smoothstep(-0.7, 0.25, inland);
	if (alpha < 0.004) discard;

	// The slope of the ground, from the heights around.
	float h = heightAt(vUv);
	float east = heightAt(vUv + vec2(uTexel, 0.0)) - heightAt(vUv - vec2(uTexel, 0.0));
	float north = heightAt(vUv - vec2(0.0, uTexel)) - heightAt(vUv + vec2(0.0, uTexel));
	vec3 up = normalize(vUp);
	vec3 toEast = normalize(cross(vec3(0.0, 1.0, 0.0), up));
	vec3 toNorth = cross(up, toEast);
	vec3 normal = uGlobe * normalize(up - uSlope * 0.5 * (east * toEast + north * toNorth));
	vec3 view = normalize(uEye - vWorld);

	// Moonlit relief: slate in the valleys, paler on the heights.
	vec3 ground = mix(vec3(0.026, 0.050, 0.078), vec3(0.165, 0.225, 0.290), pow(h, 0.62));
	float lit = max(dot(normal, uMoon), 0.0);
	vec3 c = ground * (0.34 + 1.25 * lit);
	c += vec3(0.03, 0.06, 0.10) * pow(1.0 - max(dot(normal, view), 0.0), 3.0);

	// Contour lines every 200 metres.
	float level = h * uTallest / 200.0;
	float contour = 1.0 - smoothstep(0.0, 1.3, abs(fract(level - 0.5) - 0.5) / max(fwidth(level), 1e-5));
	c += vec3(0.20, 0.42, 0.66) * contour * (0.055 + 0.2 * uTech) * step(0.012, h);

	vec4 here = texture(uAtlas, vUv);
	// Where two provinces meet.
	c = mix(c, vec3(0.50, 0.68, 0.88), smoothstep(0.2, 0.75, here.a) * 0.15);
	// The coast, a clean bright line.
	c = mix(c, vec3(0.62, 0.86, 1.0), smoothstep(1.7, 0.35, inland) * 0.8);

	// The lights of the towns: a sharp core and the glow it throws around.
	// (The atlas keeps the square root of the brightness.)
	float core = textureLod(uAtlas, vUv, 0.0).g;
	float near = textureLod(uAtlas, vUv, 2.2).g;
	float far = textureLod(uAtlas, vUv, 4.4).g;
	// Cities first, villages last.
	float order = (1.0 - clamp(max(core, near * 1.6), 0.0, 1.0)) * 0.84
		+ hash(floor(vUv / uTexel)) * 0.16;
	core *= core;
	near *= near;
	far *= far;
	float on = smoothstep(0.0, 0.09, uLights * 1.15 - order);
	float twinkle = 0.9 + 0.1 * sin(uTime * 1.7 + hash(floor(vUv / uTexel) + 7.0) * 60.0);
	float glow = (core * 2.8 * twinkle + near * 2.2 + far * 2.4) * on;
	vec3 lamp = mix(vec3(1.0, 0.55, 0.16), vec3(1.0, 0.90, 0.66), clamp(core * 2.0, 0.0, 1.0));

	// A party: rings of light run out from the centre in the singers' colours.
	vec2 fromCentre = (vUv - 0.5) * 2.0;
	float ring = pow(0.5 + 0.5 * sin(uTime * 6.0 - length(fromCentre) * 22.0), 6.0);
	float pick = fract(length(fromCentre) * 1.6 - uTime * 0.12);
	vec3 singer = pick < 0.25 ? vec3(1.0, 0.45, 0.66) : pick < 0.5 ? vec3(0.37, 0.89, 0.61)
		: pick < 0.75 ? vec3(1.0, 0.60, 0.30) : vec3(0.78, 0.91, 0.35);
	lamp = mix(lamp, singer, uParty * 0.7);
	glow *= 1.0 + uParty * 1.5 * ring;

	// A karaoke being made: a line crosses from the west; behind it the lights are on.
	float x = vUv.x * 2.0 - 1.0;
	float done = step(x, uScanAt);
	glow *= mix(1.0, mix(0.16, 1.25, done), uFill);
	glow *= 1.0 - 0.5 * uTech;
	c += lamp * glow;
	c += vec3(0.45, 0.80, 1.0) * smoothstep(0.035, 0.0, abs(x - uScanAt)) * uScan * 0.9;

	color = vec4(c * alpha, alpha);
}`;

export const GLOW_FS = `${HEAD}
in vec3 vColor;
out vec4 color;
${ROUND}
void main() {
	color = vec4(vColor * disc(0.25), 0.0);
}`;

export const BEAMS_VS = `${HEAD}
in vec2 aAngle;
in vec4 aBeam;
in vec2 aCorner;
${COMMON}
uniform float uOn;
out vec2 vAt;
out float vFacing;
void main() {
	vec3 n = dir(aAngle);
	vec3 east = normalize(cross(vec3(0.0, 1.0, 0.0), n));
	vec3 north = cross(n, east);
	// aBeam: period, where in the turn, length, half width.
	float a = uTime * 6.2831853 / aBeam.x + aBeam.y + aCorner.y * aBeam.w;
	vec3 along = cos(a) * east + sin(a) * north;
	vec3 world = uGlobe * (n * 1.012 + along * aBeam.z * aCorner.x);
	vAt = aCorner;
	vFacing = facing(uGlobe * n) * uOn;
	gl_Position = uViewProj * vec4(world, 1.0);
}`;

export const BEAMS_FS = `${HEAD}
in vec2 vAt;
in float vFacing;
out vec4 color;
void main() {
	float along = vAt.x;
	float side = vAt.y / max(along, 0.001);
	float a = pow(1.0 - along, 1.9) * pow(1.0 - side * side, 1.5) * smoothstep(0.0, 0.3, vFacing);
	color = vec4(vec3(1.0, 0.95, 0.80) * a * 0.3, 0.0);
}`;

export const BEACONS_VS = `${HEAD}
in vec2 aAngle;
in vec4 aBeacon;
${COMMON}
uniform vec3 uEyeLand;
uniform float uOn;
out vec3 vColor;
void main() {
	vec3 n = dir(aAngle);
	vec3 world = uGlobe * (n * 1.014);
	gl_Position = uViewProj * vec4(world, 1.0);
	// aBeacon: period (0 for a light with no known rhythm), flashes, gap between them, start.
	float flash = 0.0;
	if (aBeacon.x > 0.0) {
		vec3 east = normalize(cross(vec3(0.0, 1.0, 0.0), n));
		vec3 north = cross(n, east);
		vec3 toEye = normalize(uEyeLand - n);
		float bearing = atan(dot(toEye, north), dot(toEye, east));
		float a = uTime * 6.2831853 / aBeacon.x + aBeacon.w - bearing;
		for (int i = 0; i < 6; i++) {
			if (float(i) < aBeacon.y) flash += pow(max(cos(a + float(i) * aBeacon.z), 0.0), 240.0);
		}
	}
	// The flash is what a boat would see: the beam passing over the eye.
	float bright = (aBeacon.x > 0.0 ? 0.55 : 0.3) + 2.8 * flash;
	vColor = vec3(1.0, 0.96, 0.84) * bright * uOn * smoothstep(0.0, 0.25, facing(world));
	gl_PointSize = max(2.5, (0.012 + 0.024 * flash) * uPx);
}`;

export const SPARKS_VS = `${HEAD}
in vec3 aPos;
in vec4 aSpark;
${COMMON}
out vec3 vColor;
void main() {
	vec3 world = uGlobe * aPos;
	gl_Position = uViewProj * vec4(world, 1.0);
	vColor = aSpark.rgb;
	gl_PointSize = max(1.5, aSpark.a * uPx);
}`;

export const MARK_VS = `${HEAD}
${COMMON}
uniform vec2 uAt;
uniform float uSize;
out float vFacing;
void main() {
	vec3 world = uGlobe * (dir(uAt) * 1.02);
	gl_Position = uViewProj * vec4(world, 1.0);
	vFacing = facing(world);
	gl_PointSize = uSize;
}`;

export const MARK_FS = `${HEAD}
in float vFacing;
uniform float uAlpha;
uniform float uPulse;
out vec4 color;
void main() {
	float r = length(gl_PointCoord - 0.5) * 2.0;
	float ring = smoothstep(0.09, 0.0, abs(r - (0.42 + 0.38 * uPulse)));
	float a = ring * (1.0 - uPulse * 0.7) * uAlpha * smoothstep(0.0, 0.25, vFacing);
	color = vec4(vec3(0.62, 0.86, 1.0) * a, 0.0);
}`;
