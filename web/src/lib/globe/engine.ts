/*
 * The night globe, drawn with WebGL 2 and nothing else: a small planet whose only land is
 * Galicia. From back to front: stars, the planet's glow, its sea (with the moon on it, the
 * meridians and the glowing shallows), the relief of Galicia as real geometry lit by the moon,
 * with its coast, contour lines and the lights of its towns, the beams of its lighthouses and
 * the air at its edge. The whole planet turns as one.
 */
import {
	DISTANCE,
	direction,
	pixelsPerUnit,
	rotation,
	turn,
	viewProjection,
	type Frame
} from './camera';
import type { Lighthouse } from './galicia';
import { COAST_STEP, beamOffsets, jitter, type Atlas } from './map';
import * as glsl from './shaders';

export interface SceneData {
	atlas: Atlas;
	lighthouses: readonly Lighthouse[];
	/** Radians the atlas reaches each way from Galicia's centre. */
	extent: number;
	kmPerRadian: number;
	/** Metres of the tallest height the atlas can hold. */
	tallest: number;
}

/** What one frame shows. Times in seconds; weights from 0 to 1. */
export interface View {
	time: number;
	/** Seconds since the frame before (0 when nothing moves). */
	delta: number;
	/** Where the globe goes, in the canvas's own pixels. */
	frame: Frame;
	yaw: number;
	tilt: number;
	/** The planet appearing, then its lights switching on. */
	shown: number;
	lights: number;
	party: number;
	tech: number;
	/** A line sweeping from west (-1) to east (1), and how much of the land behind it is done. */
	scan: number;
	scanAt: number;
	fill: number;
	/** A lighthouse or a place to point at, and how visible the ring is. */
	mark: { theta: number; phi: number } | null;
	markAlpha: number;
}

export interface Scene {
	draw(view: View): void;
	resize(width: number, height: number): void;
	/** A rocket goes up from a place and bursts in a colour (0..1 each). */
	firework(theta: number, phi: number, color: [number, number, number]): void;
	destroy(): void;
}

/** How much the tallest mountain stands out, in radii (several times the real thing). */
const RELIEF = 0.07;
/** Squares along each side of the land's mesh. */
const MESH = 288;
const STARS = 520;
const SPARKS = 1_800;
const NAUTICAL_MILE_KM = 1.852;
/** The moon, up and to the left of the eye: it stays there while the globe turns. */
const MOON = normalise([-0.52, 0.5, 0.69]);

function normalise(v: [number, number, number]): [number, number, number] {
	const length = Math.hypot(v[0], v[1], v[2]);
	return [v[0] / length, v[1] / length, v[2] / length];
}

/** A fixed pseudo-random sequence, 0..1. */
function sequence(seed: number): () => number {
	let a = seed;
	return () => {
		a = (a + 0x6d2b79f5) >>> 0;
		let t = a;
		t = Math.imul(t ^ (t >>> 15), t | 1);
		t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}

/** A sphere of triangles. */
function ball(rings: number, segments: number): { points: Float32Array; indices: Uint16Array } {
	const points: number[] = [];
	const indices: number[] = [];
	for (let r = 0; r <= rings; r++) {
		const lat = Math.PI / 2 - (r / rings) * Math.PI;
		for (let s = 0; s <= segments; s++) {
			const lon = (s / segments) * 2 * Math.PI;
			points.push(Math.cos(lat) * Math.sin(lon), Math.sin(lat), Math.cos(lat) * Math.cos(lon));
		}
	}
	for (let r = 0; r < rings; r++) {
		for (let s = 0; s < segments; s++) {
			const a = r * (segments + 1) + s;
			const b = a + segments + 1;
			indices.push(a, b, a + 1, a + 1, b, b + 1);
		}
	}
	return { points: new Float32Array(points), indices: new Uint16Array(indices) };
}

/** A square sheet of triangles over the atlas, as texture coordinates. */
function sheet(squares: number): { points: Float32Array; indices: Uint32Array } {
	const side = squares + 1;
	const points = new Float32Array(side * side * 2);
	for (let row = 0; row < side; row++) {
		for (let column = 0; column < side; column++) {
			points[(row * side + column) * 2] = column / squares;
			points[(row * side + column) * 2 + 1] = row / squares;
		}
	}
	const indices = new Uint32Array(squares * squares * 6);
	let n = 0;
	for (let row = 0; row < squares; row++) {
		for (let column = 0; column < squares; column++) {
			const a = row * side + column;
			const b = a + side;
			indices.set([a, b, a + 1, a + 1, b, b + 1], n);
			n += 6;
		}
	}
	return { points, indices };
}

/** The beams (three corners each) and the lamps of the lighthouses. */
function beacons(lighthouses: readonly Lighthouse[], kmPerRadian: number) {
	const beams: number[] = [];
	const lamps: number[] = [];
	lighthouses.forEach((light, index) => {
		const start = (jitter(index * 97 + 13) + 0.5) * 2 * Math.PI;
		if (!light.period || !light.flashes) {
			lamps.push(light.theta, light.phi, 0, 0, 0, 0);
			return;
		}
		const offsets = beamOffsets(light.flashes, light.period);
		lamps.push(light.theta, light.phi, light.period, light.flashes, offsets[1] ?? 0, start);
		// As long as the light is seen at sea; an occulting light (more light than dark) is wide.
		const length = ((light.range ?? 14) * NAUTICAL_MILE_KM) / kmPerRadian;
		const width = light.kind === 'Oc' || light.kind === 'Iso' ? 0.55 : 0.13;
		for (const offset of offsets) {
			for (const [along, side] of [
				[0, 0],
				[1, -1],
				[1, 1]
			] as const) {
				beams.push(
					light.theta,
					light.phi,
					light.period,
					start + offset,
					length,
					width,
					along,
					side
				);
			}
		}
	});
	return { beams: new Float32Array(beams), lamps: new Float32Array(lamps) };
}

interface Spark {
	x: number;
	y: number;
	z: number;
	vx: number;
	vy: number;
	vz: number;
	age: number;
	life: number;
	color: [number, number, number];
	size: number;
	/** A rocket bursts when it dies. */
	rocket: boolean;
}

export function createScene(canvas: HTMLCanvasElement, data: SceneData): Scene | null {
	const context = canvas.getContext('webgl2', {
		alpha: true,
		antialias: true,
		depth: true,
		premultipliedAlpha: true,
		powerPreference: 'high-performance'
	});
	if (!context) return null;
	const gl = context;
	const random = sequence(0x51f15e);

	function compile(type: number, source: string): WebGLShader {
		const shader = gl.createShader(type)!;
		gl.shaderSource(shader, source);
		gl.compileShader(shader);
		if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
			throw new Error(gl.getShaderInfoLog(shader) ?? 'shader');
		}
		return shader;
	}

	/** A program, with a function that finds (and remembers) its uniforms by name. */
	function program(vertex: string, fragment: string) {
		const handle = gl.createProgram();
		gl.attachShader(handle, compile(gl.VERTEX_SHADER, vertex));
		gl.attachShader(handle, compile(gl.FRAGMENT_SHADER, fragment));
		gl.linkProgram(handle);
		if (!gl.getProgramParameter(handle, gl.LINK_STATUS)) {
			throw new Error(gl.getProgramInfoLog(handle) ?? 'program');
		}
		const found = new Map<string, WebGLUniformLocation | null>();
		const at = (name: string) => {
			if (!found.has(name)) found.set(name, gl.getUniformLocation(handle, name));
			return found.get(name) ?? null;
		};
		return { handle, at };
	}
	type Program = ReturnType<typeof program>;

	/** A vertex array over one buffer: [attribute, floats] in the order they are stored. */
	function array(
		target: Program,
		contents: Float32Array | number,
		layout: [string, number][],
		usage: number = gl.STATIC_DRAW
	) {
		const vao = gl.createVertexArray();
		const buffer = gl.createBuffer();
		gl.bindVertexArray(vao);
		gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
		if (typeof contents === 'number') gl.bufferData(gl.ARRAY_BUFFER, contents, usage);
		else gl.bufferData(gl.ARRAY_BUFFER, contents, usage);
		const stride = layout.reduce((sum, [, size]) => sum + size, 0) * 4;
		let offset = 0;
		for (const [name, size] of layout) {
			const location = gl.getAttribLocation(target.handle, name);
			if (location >= 0) {
				gl.enableVertexAttribArray(location);
				gl.vertexAttribPointer(location, size, gl.FLOAT, false, stride, offset);
			}
			offset += size * 4;
		}
		gl.bindVertexArray(null);
		return { vao, buffer };
	}

	let stars: Program, halo: Program, sea: Program, air: Program, land: Program;
	let beams: Program, lights: Program, sparks: Program, mark: Program;
	try {
		stars = program(glsl.STARS_VS, glsl.STARS_FS);
		halo = program(glsl.HALO_VS, glsl.HALO_FS);
		sea = program(glsl.BALL_VS, glsl.SEA_FS);
		air = program(glsl.BALL_VS, glsl.AIR_FS);
		land = program(glsl.LAND_VS, glsl.LAND_FS);
		beams = program(glsl.BEAMS_VS, glsl.BEAMS_FS);
		lights = program(glsl.BEACONS_VS, glsl.GLOW_FS);
		sparks = program(glsl.SPARKS_VS, glsl.GLOW_FS);
		mark = program(glsl.MARK_VS, glsl.MARK_FS);
	} catch (error) {
		console.error('The night globe could not start:', error);
		return null;
	}

	// Geometry.
	const starPoints = new Float32Array(STARS * 5);
	for (let i = 0; i < STARS; i++) {
		const y = random() * 2 - 1;
		const lon = random() * 2 * Math.PI;
		const r = Math.sqrt(1 - y * y);
		starPoints.set([Math.cos(lon) * r, y, Math.sin(lon) * r, random() ** 3.5, random()], i * 5);
	}
	const starArray = array(stars, starPoints, [
		['aStar', 4],
		['aSeed', 1]
	]);
	const haloArray = array(halo, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), [['aCorner', 2]]);
	const mesh = ball(64, 96);
	const seaArray = array(sea, mesh.points, [['aPos', 3]]);
	const airArray = array(air, mesh.points, [['aPos', 3]]);
	const ballIndices = gl.createBuffer();
	for (const { vao } of [seaArray, airArray]) {
		gl.bindVertexArray(vao);
		gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ballIndices);
		gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, mesh.indices, gl.STATIC_DRAW);
	}
	const ground = sheet(MESH);
	const landArray = array(land, ground.points, [['aUv', 2]]);
	gl.bindVertexArray(landArray.vao);
	gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, gl.createBuffer());
	gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, ground.indices, gl.STATIC_DRAW);
	gl.bindVertexArray(null);

	const beacon = beacons(data.lighthouses, data.kmPerRadian);
	const beamArray = array(beams, beacon.beams, [
		['aAngle', 2],
		['aBeam', 4],
		['aCorner', 2]
	]);
	const lightArray = array(lights, beacon.lamps, [
		['aAngle', 2],
		['aBeacon', 4]
	]);
	const sparkData = new Float32Array(SPARKS * 7);
	const sparkArray = array(
		sparks,
		sparkData.byteLength,
		[
			['aPos', 3],
			['aSpark', 4]
		],
		gl.DYNAMIC_DRAW
	);
	const markArray = gl.createVertexArray();

	const atlas = gl.createTexture();
	gl.bindTexture(gl.TEXTURE_2D, atlas);
	gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
	gl.texImage2D(
		gl.TEXTURE_2D,
		0,
		gl.RGBA8,
		data.atlas.size,
		data.atlas.size,
		0,
		gl.RGBA,
		gl.UNSIGNED_BYTE,
		data.atlas.data
	);
	gl.generateMipmap(gl.TEXTURE_2D);
	gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
	gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
	gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
	gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

	const viewProj = new Float32Array(16);
	const globe = new Float32Array(9);
	const sky = new Float32Array(9);
	const skyTurn = new Float32Array(9);
	const skyLean = new Float32Array(9);
	const live: Spark[] = [];
	// Metres per cell on the ground, for the slope of the relief.
	const cellMetres = ((2 * data.extent) / data.atlas.size) * data.kmPerRadian * 1000;

	/** a * b for 3 by 3 matrices, column-major. */
	function multiply(a: Float32Array, b: Float32Array, out: Float32Array): Float32Array {
		for (let column = 0; column < 3; column++) {
			for (let row = 0; row < 3; row++) {
				out[column * 3 + row] =
					a[row] * b[column * 3] + a[3 + row] * b[column * 3 + 1] + a[6 + row] * b[column * 3 + 2];
			}
		}
		return out;
	}

	/** The uniforms every shader on the sphere shares. */
	function common(target: Program, view: View, px: number) {
		gl.useProgram(target.handle);
		gl.uniformMatrix4fv(target.at('uViewProj'), false, viewProj);
		gl.uniformMatrix3fv(target.at('uGlobe'), false, globe);
		gl.uniform3f(target.at('uEye'), 0, 0, DISTANCE);
		gl.uniform3f(target.at('uMoon'), ...MOON);
		gl.uniform1f(target.at('uPx'), px);
		gl.uniform1f(target.at('uTime'), view.time);
		gl.uniform1i(target.at('uAtlas'), 0);
		gl.uniform1f(target.at('uExtent'), data.extent);
		gl.uniform1f(target.at('uCoastStep'), COAST_STEP);
	}

	function burst(rocket: Spark) {
		for (let i = 0; i < 64 && live.length < SPARKS; i++) {
			const y = random() * 2 - 1;
			const lon = random() * 2 * Math.PI;
			const r = Math.sqrt(1 - y * y);
			const speed = 0.1 + 0.11 * random();
			live.push({
				x: rocket.x,
				y: rocket.y,
				z: rocket.z,
				vx: Math.cos(lon) * r * speed,
				vy: y * speed,
				vz: Math.sin(lon) * r * speed,
				age: 0,
				life: 0.9 + 0.8 * random(),
				color: rocket.color,
				size: 0.008 + 0.006 * random(),
				rocket: false
			});
		}
	}

	function stepSparks(delta: number): number {
		for (let i = live.length - 1; i >= 0; i--) {
			const spark = live[i];
			spark.age += delta;
			if (spark.age >= spark.life) {
				live.splice(i, 1);
				if (spark.rocket) burst(spark);
				continue;
			}
			if (!spark.rocket) {
				const drag = Math.exp(-1.6 * delta);
				// Falling back towards the planet, slowly.
				const length = Math.hypot(spark.x, spark.y, spark.z);
				spark.vx = spark.vx * drag - (spark.x / length) * 0.05 * delta;
				spark.vy = spark.vy * drag - (spark.y / length) * 0.05 * delta;
				spark.vz = spark.vz * drag - (spark.z / length) * 0.05 * delta;
			}
			spark.x += spark.vx * delta;
			spark.y += spark.vy * delta;
			spark.z += spark.vz * delta;
		}
		let n = 0;
		for (const spark of live) {
			const fade = spark.rocket ? 0.9 : (1 - spark.age / spark.life) ** 1.5;
			sparkData.set(
				[
					spark.x,
					spark.y,
					spark.z,
					spark.color[0] * fade,
					spark.color[1] * fade,
					spark.color[2] * fade,
					spark.size
				],
				n * 7
			);
			n++;
		}
		return n;
	}

	function draw(view: View) {
		const { frame } = view;
		gl.viewport(0, 0, canvas.width, canvas.height);
		gl.clearColor(0, 0, 0, 0);
		gl.clearDepth(1);
		gl.depthMask(true);
		gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

		viewProjection(frame, viewProj);
		rotation(view.yaw, view.tilt, globe);
		const px = pixelsPerUnit(frame.radius);
		const dpr = canvas.width / Math.max(1, canvas.clientWidth);

		// Light adds up over the page; alpha is left alone.
		gl.enable(gl.BLEND);
		gl.blendFuncSeparate(gl.ONE, gl.ONE, gl.ZERO, gl.ONE);
		gl.disable(gl.DEPTH_TEST);
		gl.depthMask(false);

		// The sky turns very slowly, and a little with the globe.
		gl.useProgram(stars.handle);
		multiply(
			rotation(view.yaw * 0.3, view.tilt * 0.3, skyLean),
			turn(...normalise([0.2, 1, 0.1]), view.time * 0.003, skyTurn),
			sky
		);
		gl.uniformMatrix3fv(stars.at('uSky'), false, sky);
		const lens = 1.35;
		gl.uniform2f(stars.at('uLens'), lens / (frame.width / frame.height), lens);
		gl.uniform1f(stars.at('uTime'), view.time);
		gl.uniform1f(stars.at('uDpr'), dpr);
		gl.bindVertexArray(starArray.vao);
		gl.drawArrays(gl.POINTS, 0, STARS);

		gl.useProgram(halo.handle);
		gl.uniformMatrix4fv(halo.at('uViewProj'), false, viewProj);
		gl.uniform1f(halo.at('uSize'), 1.5);
		// Where the planet's edge falls inside the glow's square.
		gl.uniform1f(halo.at('uEdge'), 1 / Math.sqrt(1 - 1 / DISTANCE ** 2) / 1.5);
		gl.uniform1f(halo.at('uTech'), view.tech);
		gl.bindVertexArray(haloArray.vao);
		gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

		// The planet hides whatever is behind it.
		gl.enable(gl.DEPTH_TEST);
		gl.depthFunc(gl.LEQUAL);
		gl.depthMask(true);
		gl.disable(gl.BLEND);
		gl.enable(gl.CULL_FACE);
		gl.activeTexture(gl.TEXTURE0);
		gl.bindTexture(gl.TEXTURE_2D, atlas);
		common(sea, view, px);
		gl.uniform1f(sea.at('uRadius'), 0.9985);
		gl.uniform1f(sea.at('uShown'), view.shown);
		gl.uniform1f(sea.at('uTech'), view.tech);
		gl.bindVertexArray(seaArray.vao);
		gl.drawElements(gl.TRIANGLES, mesh.indices.length, gl.UNSIGNED_SHORT, 0);

		// The land, standing on it.
		gl.enable(gl.BLEND);
		gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
		common(land, view, px);
		gl.uniform1f(land.at('uRelief'), RELIEF);
		gl.uniform1f(land.at('uTexel'), 1 / data.atlas.size);
		// How steep a step of height between two cells is, as much exaggerated as the relief.
		gl.uniform1f(land.at('uSlope'), (data.tallest / cellMetres) * 3.2);
		gl.uniform1f(land.at('uTallest'), data.tallest);
		gl.uniform1f(land.at('uLights'), view.lights);
		gl.uniform1f(land.at('uParty'), view.party);
		gl.uniform1f(land.at('uTech'), view.tech);
		gl.uniform1f(land.at('uScan'), view.scan);
		gl.uniform1f(land.at('uScanAt'), view.scanAt);
		gl.uniform1f(land.at('uFill'), view.fill);
		gl.bindVertexArray(landArray.vao);
		gl.drawElements(gl.TRIANGLES, ground.indices.length, gl.UNSIGNED_INT, 0);
		gl.disable(gl.CULL_FACE);
		gl.depthMask(false);

		// From here on, light: the lighthouses come on with the last lights of the towns.
		gl.blendFuncSeparate(gl.ONE, gl.ONE, gl.ZERO, gl.ONE);
		const lit = Math.max(0, Math.min(1, view.lights * 3 - 2));
		common(beams, view, px);
		gl.uniform1f(beams.at('uOn'), lit);
		gl.bindVertexArray(beamArray.vao);
		gl.drawArrays(gl.TRIANGLES, 0, beacon.beams.length / 8);
		common(lights, view, px);
		gl.uniform1f(lights.at('uOn'), lit);
		// The eye, as the land sees it (the transpose of a rotation undoes it).
		gl.uniform3f(
			lights.at('uEyeLand'),
			globe[2] * DISTANCE,
			globe[5] * DISTANCE,
			globe[8] * DISTANCE
		);
		gl.bindVertexArray(lightArray.vao);
		gl.drawArrays(gl.POINTS, 0, beacon.lamps.length / 6);

		const flying = stepSparks(view.delta);
		if (flying > 0) {
			common(sparks, view, px);
			gl.bindVertexArray(sparkArray.vao);
			gl.bindBuffer(gl.ARRAY_BUFFER, sparkArray.buffer);
			gl.bufferSubData(gl.ARRAY_BUFFER, 0, sparkData, 0, flying * 7);
			gl.drawArrays(gl.POINTS, 0, flying);
		}

		if (view.mark && view.markAlpha > 0.01) {
			common(mark, view, px);
			gl.uniform2f(mark.at('uAt'), view.mark.theta, view.mark.phi);
			gl.uniform1f(mark.at('uSize'), Math.max(30 * dpr, 0.12 * px));
			gl.uniform1f(mark.at('uAlpha'), view.markAlpha);
			gl.uniform1f(mark.at('uPulse'), (view.time * 0.5) % 1);
			gl.bindVertexArray(markArray);
			gl.drawArrays(gl.POINTS, 0, 1);
		}

		// The air, brightest where it is seen edge on.
		gl.enable(gl.CULL_FACE);
		common(air, view, px);
		gl.uniform1f(air.at('uRadius'), 1.045);
		gl.bindVertexArray(airArray.vao);
		gl.drawElements(gl.TRIANGLES, mesh.indices.length, gl.UNSIGNED_SHORT, 0);
		gl.disable(gl.CULL_FACE);
		gl.bindVertexArray(null);
	}

	return {
		draw,
		resize(width, height) {
			if (canvas.width !== width || canvas.height !== height) {
				canvas.width = width;
				canvas.height = height;
			}
		},
		firework(theta, phi, color) {
			if (live.length >= SPARKS - 80) return;
			const [x, y, z] = direction(theta, phi);
			const speed = 0.2;
			live.push({
				x: x * 1.02,
				y: y * 1.02,
				z: z * 1.02,
				vx: x * speed,
				vy: y * speed,
				vz: z * speed,
				age: 0,
				life: 0.55 + 0.25 * random(),
				color,
				size: 0.007,
				rocket: true
			});
		},
		destroy() {
			gl.getExtension('WEBGL_lose_context')?.loseContext();
		}
	};
}
