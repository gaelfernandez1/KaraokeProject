<script lang="ts" module>
	const LIT_KEY = 'noite.acesa';
	/** Seconds the globe takes to glide from one screen's place to the next. */
	const GLIDE = 0.9;
</script>

<script lang="ts">
	/*
	 * The night globe behind every screen: one canvas that fills the viewport, under the page.
	 * Each frame it finds the anchor on screen and draws the globe fitted to it; when the anchor
	 * changes (another screen), the globe glides there. Its engine and its map load only once a
	 * screen asks for the globe, after the first paint. The first time in a visit the planet
	 * turns in from the open sea and the lights of Galicia come on, cities first; under reduced
	 * motion it is simply there, lit and still.
	 */
	import { onMount } from 'svelte';
	import { prefersReducedMotion } from 'svelte/motion';
	import { afterNavigate, beforeNavigate } from '$app/navigation';
	import { i18n } from '#lib/i18n';
	import { direction, project, rotation, viewProjection, type Frame } from './camera';
	import type { Scene } from './engine';
	import { CITIES, EXTENT, HEIGHT_MAX, KM_PER_RADIAN, LIGHTHOUSES } from './galicia';
	import mapUrl from './galicia-map.bin?url';
	import { loadGlobe } from './load';
	import { SINGER_LIGHTS, stage, type Anchor } from './stage.svelte';

	interface Place {
		name: string;
		theta: number;
		phi: number;
		kind: 'city' | 'sea';
	}

	// The ocean goes where a chart would write it: off the west coast.
	const places = $derived<Place[]>([
		...CITIES.map((city) => ({ ...city, kind: 'city' as const })),
		{ name: i18n.t.globe.atlantic, theta: -0.86, phi: -0.12, kind: 'sea' }
	]);

	let canvas = $state<HTMLCanvasElement | null>(null);
	let shown = $state(false);
	let named = $state(false);
	const tags: HTMLElement[] = $state([]);
	/** While the page changes, the globe waits: the new screen comes first. */
	let navigating = false;
	beforeNavigate(() => {
		navigating = true;
	});
	afterNavigate(() => {
		navigating = false;
	});

	onMount(() => {
		if (!canvas) return;
		const surface = canvas;
		let scene: Scene | null = null;
		let loading = false;
		let failed = false;
		let frameId = 0;
		let previous = performance.now();
		let clock = 0;
		let current: Anchor | null = null;
		let from: { cx: number; cy: number; radius: number; yaw: number; tilt: number } | null = null;
		let glideStart = 0;
		const pose = { cx: 0, cy: 0, radius: 0, yaw: 0, tilt: 0 };
		// The first time in a visit the planet arrives; afterwards it is just there.
		let arrival: number | null = null;
		let arrived = false;
		try {
			arrived = sessionStorage.getItem(LIT_KEY) === '1';
		} catch {
			// Without storage it arrives on every visit, which is fine.
		}
		const weight = { party: 0, tech: 0, scan: 0, fill: 0, mark: 0, scanAt: -1.2 };
		let lastMark: { theta: number; phi: number } | null = null;
		let nextRocket = 0;
		let signature = '';
		let slow = 0;
		/** How far the picture has been simplified for a machine that cannot keep up (0 to 3). */
		let thrift = 0;
		let frames = 0;
		/** The side of the canvas, in CSS pixels: it covers the globe and its glow, no more. */
		let side = 0;
		const sharpness = Math.min(2, window.devicePixelRatio || 1);
		const viewProj = new Float32Array(16);
		const globe = new Float32Array(9);

		async function load() {
			loading = true;
			try {
				const { createScene, buildAtlas, loadMap } = await loadGlobe();
				const map = await loadMap(mapUrl);
				if (!map) throw new Error('map');
				scene = createScene(surface, {
					atlas: buildAtlas(map),
					lighthouses: LIGHTHOUSES,
					extent: EXTENT,
					kmPerRadian: KM_PER_RADIAN,
					tallest: HEIGHT_MAX
				});
				if (!scene) failed = true;
			} catch {
				failed = true;
			}
			loading = false;
		}

		const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
		const approach = (value: number, target: number, rate: number, seconds: number) =>
			target + (value - target) * Math.exp(-rate * seconds);

		function hide() {
			if (shown) shown = false;
			if (stage.live) stage.live = false;
			current = null;
		}

		function tick(now: number) {
			frameId = requestAnimationFrame(tick);
			const anchor = stage.anchor;
			if (!anchor || failed || document.hidden) return hide();
			if (navigating) return;
			if (!scene) {
				if (!loading) void load();
				return;
			}
			const box = anchor.element.getBoundingClientRect();
			const width = window.innerWidth;
			const height = window.innerHeight;
			const target = {
				cx: box.left + box.width / 2,
				cy: box.top + box.height / 2,
				radius: (Math.min(box.width, box.height) / 2) * anchor.fit
			};
			if (target.radius < 12 || width === 0) return hide();

			// A machine that cannot keep up gets fewer pixels, then fewer frames.
			frames += 1;
			if (thrift >= 2 && frames % (thrift === 2 ? 2 : 4) !== 0) return;
			const elapsed = now - previous;
			const seconds = Math.min(0.05 * (thrift >= 2 ? 4 : 1), elapsed / 1000);
			previous = now;
			const moving = !stage.still && !prefersReducedMotion.current;
			if (moving) clock += seconds;

			// The hand on the globe; let go, it swings back to rest.
			const drag = stage.drag;
			if (!drag.held) {
				drag.speedYaw += (-3.2 * drag.yaw - 3.4 * drag.speedYaw) * seconds;
				drag.speedTilt += (-3.2 * drag.tilt - 3.4 * drag.speedTilt) * seconds;
				drag.yaw += drag.speedYaw * seconds;
				drag.tilt += drag.speedTilt * seconds;
			}

			if (arrival === null) arrival = now;
			const since = (now - arrival) / 1000;
			const arriving = !arrived && !prefersReducedMotion.current;
			const turnIn = arriving ? 1 - (1 - Math.min(1, since / 2.4)) ** 3 : 1;
			const appeared = arriving ? Math.min(1, since / 0.9) : 1;
			const lights = arriving ? Math.min(1, Math.max(0, (since - 1.1) / 2.3)) : 1;
			if (arriving && since > 3.6) {
				arrived = true;
				try {
					sessionStorage.setItem(LIT_KEY, '1');
				} catch {
					// See above.
				}
			}

			// A slow sway, the whole planet as one, so the relief and the lights never sit flat.
			const sway = 0.2 * Math.sin((clock * 2 * Math.PI) / 44);
			const nod = 0.04 * Math.sin((clock * 2 * Math.PI) / 31 + 1);
			const rest = {
				...target,
				yaw: anchor.yaw + sway + drag.yaw - (1 - turnIn) * 2.1,
				tilt: anchor.tilt + nod + drag.tilt
			};
			if (anchor !== current) {
				from = current && shown && !prefersReducedMotion.current ? { ...pose } : null;
				glideStart = now;
				current = anchor;
			}
			let k = 1;
			if (from) {
				k = ease(Math.min(1, (now - glideStart) / 1000 / GLIDE));
				if (k >= 1) from = null;
			}
			const start = from ?? rest;
			pose.cx = start.cx + (rest.cx - start.cx) * k;
			pose.cy = start.cy + (rest.cy - start.cy) * k;
			pose.radius = start.radius + (rest.radius - start.radius) * k;
			pose.yaw = start.yaw + (rest.yaw - start.yaw) * k;
			pose.tilt = start.tilt + (rest.tilt - start.tilt) * k;

			// Out of sight (scrolled away): nothing to draw.
			const reach = pose.radius * 1.7;
			if (
				pose.cx + reach < 0 ||
				pose.cx - reach > width ||
				pose.cy + reach < 0 ||
				pose.cy - reach > height
			) {
				if (shown) shown = false;
				return;
			}

			// What the globe is doing eases in and out.
			weight.party = approach(weight.party, stage.mood === 'party' ? 1 : 0, 4, seconds);
			weight.tech = approach(weight.tech, stage.mood === 'tech' ? 1 : 0, 4, seconds);
			const making = stage.progress !== null;
			weight.fill = approach(weight.fill, making ? 1 : 0, 3, seconds);
			weight.scan = approach(weight.scan, making || stage.mood === 'scan' ? 1 : 0, 4, seconds);
			if (making) {
				weight.scanAt = approach(weight.scanAt, -0.95 + 1.9 * (stage.progress ?? 0), 3, seconds);
			} else if (stage.mood === 'scan') {
				weight.scanAt = -1.15 + 2.3 * ((clock * 0.28) % 1);
			}
			if (stage.mark) lastMark = stage.mark;
			weight.mark = approach(weight.mark, stage.mark ? 1 : 0, 6, seconds);

			// Rockets: the ones a page asked for, and a few more while a party is on.
			if (moving && weight.party > 0.6 && clock > nextRocket) {
				nextRocket = clock + 0.55 + Math.random() * 0.7;
				stage.rockets.push(SINGER_LIGHTS[Math.floor(Math.random() * 4)]);
			}
			while (stage.rockets.length > 0) {
				const city = CITIES[Math.floor(Math.random() * CITIES.length)];
				const color = stage.rockets.shift()!;
				if (moving) {
					scene.firework(
						city.theta + (Math.random() - 0.5) * 0.3,
						city.phi + (Math.random() - 0.5) * 0.3,
						color
					);
				}
			}

			// The canvas covers the globe and its glow, no more, and follows it; its size changes in
			// steps, so gliding between two places does not rebuild it on every frame.
			const wanted = Math.ceil((pose.radius * 3.3) / 96) * 96;
			if (wanted > side || wanted < side * 0.6) {
				side = wanted;
				surface.style.width = `${side}px`;
				surface.style.height = `${side}px`;
			}
			surface.style.transform = `translate3d(${(pose.cx - side / 2).toFixed(1)}px, ${(pose.cy - side / 2).toFixed(1)}px, 0)`;
			const scale = thrift === 0 ? sharpness : thrift === 1 ? 1 : thrift === 2 ? 0.7 : 0.5;

			// Standing still, the same picture is not drawn twice.
			const sign = [
				side,
				scale,
				pose.cx.toFixed(1),
				pose.cy.toFixed(1),
				pose.radius.toFixed(1),
				pose.yaw.toFixed(4),
				pose.tilt.toFixed(4),
				clock.toFixed(3),
				lights.toFixed(3),
				appeared.toFixed(3),
				weight.party.toFixed(3),
				weight.tech.toFixed(3),
				weight.fill.toFixed(3),
				weight.scan.toFixed(3),
				weight.scanAt.toFixed(3),
				weight.mark.toFixed(3)
			].join();
			if (sign !== signature) {
				signature = sign;
				const pixels = Math.round(side * scale);
				scene.resize(pixels, pixels);
				scene.draw({
					time: clock,
					delta: moving ? seconds : 0,
					frame: {
						width: pixels,
						height: pixels,
						cx: pixels / 2,
						cy: pixels / 2,
						radius: pose.radius * scale
					},
					yaw: pose.yaw,
					tilt: pose.tilt,
					shown: appeared,
					lights,
					party: weight.party,
					tech: weight.tech,
					scan: weight.scan,
					scanAt: weight.scanAt,
					fill: weight.fill,
					mark: lastMark,
					markAlpha: weight.mark
				});
				// Frames that take too long to come round: the machine cannot keep up, so the picture
				// gets simpler, a step at a time, and stays so.
				const late = elapsed > (thrift >= 2 ? 160 : 40);
				slow = late ? slow + 1 : Math.max(0, slow - 1);
				if (slow > 24 && thrift < 3) {
					thrift += 1;
					slow = 0;
				}
			}
			if (!shown) shown = true;
			if (!stage.live) stage.live = true;

			// The names follow their places.
			const withNames = anchor.names && pose.radius > 170 && lights > 0.85 && !from;
			if (withNames !== named) named = withNames;
			if (withNames) {
				const frame: Frame = { width, height, cx: pose.cx, cy: pose.cy, radius: pose.radius };
				viewProjection(frame, viewProj);
				rotation(pose.yaw, pose.tilt, globe);
				places.forEach((place, i) => {
					const tag = tags[i];
					if (!tag) return;
					const [x, y, z] = direction(place.theta, place.phi);
					const wx = globe[0] * x + globe[3] * y + globe[6] * z;
					const wy = globe[1] * x + globe[4] * y + globe[7] * z;
					const wz = globe[2] * x + globe[5] * y + globe[8] * z;
					const at = project(viewProj, wx * 1.02, wy * 1.02, wz * 1.02, frame);
					// Facing the eye enough to be read; behind the edge, gone.
					const facing = Math.min(1, Math.max(0, (wz - 0.38) / 0.2));
					tag.style.transform = `translate3d(${at.x.toFixed(1)}px, ${at.y.toFixed(1)}px, 0)`;
					tag.style.opacity = facing.toFixed(2);
				});
			}
		}

		frameId = requestAnimationFrame(tick);
		const lost = (event: Event) => {
			event.preventDefault();
			failed = true;
		};
		surface.addEventListener('webglcontextlost', lost);
		return () => {
			cancelAnimationFrame(frameId);
			surface.removeEventListener('webglcontextlost', lost);
			scene?.destroy();
			stage.live = false;
		};
	});
</script>

<canvas bind:this={canvas} class:shown aria-hidden="true"></canvas>
<div class="names" class:named aria-hidden="true">
	{#each places as place, i (place.kind + i)}
		<span bind:this={tags[i]} class={place.kind}><span>{place.name}</span></span>
	{/each}
</div>

<style>
	/* Under the page: whatever a screen draws is on top of the globe. */
	canvas,
	.names {
		position: fixed;
		z-index: -1;
		pointer-events: none;
		opacity: 0;
		transition: opacity 500ms ease;
	}

	/* The canvas is only as big as the globe and its glow, and is moved to where the globe is. */
	canvas {
		top: 0;
		left: 0;
		max-width: none;
		will-change: transform;
	}

	.names {
		inset: 0;
		width: 100%;
		height: 100%;
	}

	canvas.shown,
	.names.named {
		opacity: 1;
	}

	.names {
		overflow: hidden;
		transition-duration: 300ms;
	}

	.names > span {
		position: absolute;
		top: 0;
		left: 0;
		will-change: transform;
	}

	.city span {
		position: absolute;
		left: 0.6rem;
		top: -0.62em;
		font-size: var(--t--1);
		font-weight: 600;
		white-space: nowrap;
		color: var(--texto);
		text-shadow:
			0 0 0.4em var(--fondo),
			0 0 0.8em var(--fondo);
	}

	.city::before {
		content: '';
		position: absolute;
		left: -2px;
		top: -2px;
		width: 4px;
		height: 4px;
		border-radius: 50%;
		background: var(--texto);
	}

	/* The seas, as charts letter them: slanted and widely spaced. */
	.sea span {
		position: absolute;
		transform: translate(-50%, -50%);
		font-size: var(--t--1);
		font-style: italic;
		letter-spacing: 0.22em;
		white-space: nowrap;
		color: color-mix(in oklab, var(--ceo) 62%, transparent);
	}
</style>
