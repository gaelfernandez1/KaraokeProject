<script lang="ts">
	/*
	 * Where a screen wants the night globe: a square in the page's own layout. The globe itself
	 * is drawn behind everything by `Stage.svelte`, fitted to this square; until it is running
	 * (or where there is no WebGL) a still drawing of Galicia's outline stands in. A visitor can
	 * take the globe and turn it; let go, it comes back.
	 */
	import { onMount } from 'svelte';
	import { OUTLINE } from './galicia';
	import { stage, type Anchor } from './stage.svelte';

	interface Props {
		/** What the picture shows, for whoever cannot see it. */
		label: string;
		yaw?: number;
		tilt?: number;
		fit?: number;
		names?: boolean;
		/** The visitor can turn it with the pointer or a finger. */
		turnable?: boolean;
	}

	let {
		label,
		yaw = -0.06,
		tilt = 0.18,
		fit = 0.84,
		names = false,
		turnable = false
	}: Props = $props();

	let element = $state<HTMLDivElement | null>(null);
	let holding = $state(false);
	const anchor: Anchor = {
		element: null as unknown as HTMLElement,
		yaw: 0,
		tilt: 0,
		fit: 1,
		names: false
	};
	$effect(() => {
		anchor.yaw = yaw;
		anchor.tilt = tilt;
		anchor.fit = fit;
		anchor.names = names;
	});

	onMount(() => {
		if (!element) return;
		anchor.element = element;
		return stage.place(anchor);
	});

	let last = { x: 0, y: 0, at: 0 };

	function radius(): number {
		const box = element?.getBoundingClientRect();
		return box ? (Math.min(box.width, box.height) / 2) * fit : 1;
	}

	function take(event: PointerEvent) {
		if (event.button !== 0) return;
		// A mouse would start selecting the page's text while it drags.
		if (event.pointerType === 'mouse') event.preventDefault();
		holding = true;
		stage.drag.held = true;
		stage.drag.speedYaw = 0;
		stage.drag.speedTilt = 0;
		last = { x: event.clientX, y: event.clientY, at: event.timeStamp };
		(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
	}

	function turn(event: PointerEvent) {
		if (!holding) return;
		const r = radius();
		const seconds = Math.max(0.001, (event.timeStamp - last.at) / 1000);
		const byYaw = (event.clientX - last.x) / r;
		const byTilt = -(event.clientY - last.y) / r;
		stage.drag.yaw += byYaw;
		// Never upside down: the north may tip a little towards the eye or well away from it.
		stage.drag.tilt = Math.min(0.75, Math.max(-0.7, stage.drag.tilt + byTilt));
		stage.drag.speedYaw = 0.6 * stage.drag.speedYaw + 0.4 * (byYaw / seconds);
		stage.drag.speedTilt = 0.6 * stage.drag.speedTilt + 0.4 * (byTilt / seconds);
		last = { x: event.clientX, y: event.clientY, at: event.timeStamp };
	}

	function release() {
		if (!holding) return;
		holding = false;
		stage.drag.held = false;
		// Come back the short way round.
		const turns = Math.round(stage.drag.yaw / (2 * Math.PI));
		stage.drag.yaw -= turns * 2 * Math.PI;
	}
</script>

<div class="anchor" bind:this={element} role="img" aria-label={label}>
	{#if !stage.live}
		<svg
			class="still"
			viewBox="{-1000 / fit} {-1000 / fit} {2000 / fit} {2000 / fit}"
			aria-hidden="true"
		>
			<circle class="sea" r="1000" />
			<path class="land" d={OUTLINE} />
		</svg>
	{/if}
	{#if turnable}
		<div
			class="grip"
			role="presentation"
			class:holding
			style:inset="{(1 - fit) * 50}%"
			onpointerdown={take}
			onpointermove={turn}
			onpointerup={release}
			onpointercancel={release}
		></div>
	{/if}
</div>

<style>
	.anchor {
		position: relative;
		aspect-ratio: 1;
		width: 100%;
	}

	.still {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		overflow: visible;
	}

	.sea {
		fill: var(--mar);
		stroke: color-mix(in oklab, var(--ceo) 45%, transparent);
		stroke-width: 2;
		vector-effect: non-scaling-stroke;
	}

	.land {
		fill: var(--terra);
		stroke: var(--ceo);
		stroke-width: 1.5;
		stroke-linejoin: round;
		vector-effect: non-scaling-stroke;
	}

	/* The globe is taken by its face, not by the square around it. Up and down still scroll the
	   page under a finger; sideways turns the globe. */
	.grip {
		position: absolute;
		border-radius: 50%;
		cursor: grab;
		touch-action: pan-y;
		user-select: none;
		-webkit-user-select: none;
	}

	.grip.holding {
		cursor: grabbing;
	}
</style>
