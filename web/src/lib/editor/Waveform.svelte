<script lang="ts">
	/*
	 * A line of the song under the magnifying glass: the guide vocals' waveform drawn in thin
	 * bars, a block for each word over it, and the playhead. While it plays, the bars behind the
	 * playhead light up in amber, like a sung line. A click seeks; dragging a block's edge moves
	 * where the word starts or ends.
	 */
	import { peaks } from './peaks';

	export interface WaveWord {
		text: string;
		start: number;
		end: number;
		doubtful: boolean;
	}

	interface Props {
		buffer: AudioBuffer | null;
		from: number;
		to: number;
		words: WaveWord[];
		selected: number;
		time: number;
		/** The sound is playing: what has been heard is lit. */
		playing?: boolean;
		onseek: (seconds: number) => void;
		onselect: (index: number) => void;
		/** A drag of a word's edge: seconds moved since it began (null if cancelled); `done` when it ends. */
		ondrag: (index: number, edge: 'start' | 'end', delta: number | null, done: boolean) => void;
	}

	let {
		buffer,
		from,
		to,
		words,
		selected,
		time,
		playing = false,
		onseek,
		onselect,
		ondrag
	}: Props = $props();

	/** Distance between the bars of the waveform, in CSS pixels. */
	const PITCH = 3;

	let width = $state(0);
	let height = $state(0);
	let canvas = $state<HTMLCanvasElement | null>(null);
	let lit = $state<HTMLCanvasElement | null>(null);
	const span = $derived(Math.max(0.1, to - from));
	const x = (seconds: number) => ((seconds - from) / span) * 100;
	const heard = $derived(playing && time > from ? Math.min(100, x(time)) : 0);

	/** Each column of the waveform as a rounded bar round the middle line; silence is a thin
	    line. */
	function draw(target: HTMLCanvasElement, values: ArrayLike<number>, max: number) {
		const ratio = devicePixelRatio || 1;
		target.width = Math.round(width * ratio);
		target.height = Math.round(height * ratio);
		const context = target.getContext('2d');
		if (!context) return;
		context.clearRect(0, 0, target.width, target.height);
		context.fillStyle = getComputedStyle(target).color;
		const pitch = PITCH * ratio;
		const thick = Math.max(1, 1.6 * ratio);
		const mid = target.height / 2;
		const reach = mid * 0.9;
		context.beginPath();
		for (let i = 0; i < values.length; i++) {
			const tall = Math.max(thick / 2, ((values[i] ?? 0) / max) * reach);
			context.roundRect((i + 0.5) * pitch - thick / 2, mid - tall, thick, tall * 2, thick / 2);
		}
		context.fill();
	}

	$effect(() => {
		if (!canvas || !lit || width === 0 || height === 0) return;
		const columns = Math.floor(width / PITCH);
		const values: ArrayLike<number> = buffer
			? peaks(buffer.getChannelData(0), buffer.sampleRate, from, to, columns)
			: new Float32Array(columns);
		const max = Math.max(0.05, ...Array.from(values));
		draw(canvas, values, max);
		draw(lit, values, max);
	});

	let box = $state<HTMLElement | null>(null);

	function seek(event: PointerEvent) {
		if (!box || event.target !== event.currentTarget) return;
		const rect = box.getBoundingClientRect();
		onseek(from + ((event.clientX - rect.left) / rect.width) * span);
	}

	function drag(index: number, edge: 'start' | 'end') {
		return (event: PointerEvent) => {
			event.stopPropagation();
			const handle = event.currentTarget as HTMLElement;
			handle.setPointerCapture(event.pointerId);
			const startX = event.clientX;
			const perPixel = span / (box?.getBoundingClientRect().width || 1);
			onselect(index);
			const move = (e: PointerEvent) => ondrag(index, edge, (e.clientX - startX) * perPixel, false);
			const stop = () => {
				handle.removeEventListener('pointermove', move);
				handle.removeEventListener('pointerup', up);
				handle.removeEventListener('pointercancel', cancel);
			};
			const up = (e: PointerEvent) => {
				stop();
				ondrag(index, edge, (e.clientX - startX) * perPixel, true);
			};
			// A system gesture can take the pointer away: the drag is dropped, nothing changes.
			const cancel = () => {
				stop();
				ondrag(index, edge, null, true);
			};
			handle.addEventListener('pointermove', move);
			handle.addEventListener('pointerup', up);
			handle.addEventListener('pointercancel', cancel);
		};
	}
</script>

<div
	class="wave"
	bind:this={box}
	bind:clientWidth={width}
	bind:clientHeight={height}
	onpointerdown={seek}
	role="presentation"
>
	<canvas bind:this={canvas} aria-hidden="true"></canvas>
	<canvas
		bind:this={lit}
		class="lit"
		aria-hidden="true"
		style:clip-path="inset(0 {100 - heard}% 0 0)"
	></canvas>
	{#each words as word, i (i)}
		<div
			class="word"
			class:selected={i === selected}
			class:doubtful={word.doubtful}
			style:left="{x(word.start)}%"
			style:width="{x(word.end) - x(word.start)}%"
		>
			{#if ((word.end - word.start) / span) * width > word.text.length * 8 + 10}
				<button
					type="button"
					class="label"
					tabindex="-1"
					aria-hidden="true"
					onpointerdown={(e) => {
						e.stopPropagation();
						onselect(i);
					}}>{word.text}</button
				>
			{/if}
			<span class="edge start" onpointerdown={drag(i, 'start')} aria-hidden="true"></span>
			<span class="edge end" onpointerdown={drag(i, 'end')} aria-hidden="true"></span>
		</div>
	{/each}
	{#if time >= from && time <= to}
		<span class="playhead" style:left="{x(time)}%"></span>
	{/if}
</div>

<style>
	.wave {
		position: relative;
		height: 9rem;
		border: 1px solid var(--raia);
		background: var(--fondo-3);
		overflow: hidden;
		cursor: text;
		touch-action: none;
	}

	canvas {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		color: color-mix(in oklch, var(--texto-2) 55%, transparent);
		pointer-events: none;
	}

	canvas.lit {
		color: var(--ouro);
	}

	.word {
		position: absolute;
		top: 0.5rem;
		bottom: 0.5rem;
		min-width: 4px;
		border: 1px solid color-mix(in oklch, var(--texto-2) 45%, transparent);
		border-radius: 4px;
		background: color-mix(in oklch, var(--texto) 4%, transparent);
	}

	.word.doubtful {
		border-style: dashed;
	}

	/* The word picked: blue, as everything selected. */
	.word.selected {
		border: 2px solid var(--ceo);
		background: color-mix(in oklch, var(--ceo) 12%, transparent);
		z-index: 1;
	}

	.label {
		position: absolute;
		left: 0;
		top: 0;
		max-width: 100%;
		padding: 0.1rem 0.35rem;
		border: 0;
		border-radius: 0 0 4px 0;
		background: color-mix(in oklch, var(--fondo-3) 75%, transparent);
		color: var(--texto);
		font-size: var(--t--1);
		font-weight: 650;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		cursor: pointer;
	}

	.selected .label {
		color: var(--ceo);
	}

	.edge {
		position: absolute;
		top: 0;
		bottom: 0;
		width: 12px;
		cursor: ew-resize;
	}

	.edge.start {
		left: -7px;
	}

	.edge.end {
		right: -7px;
	}

	.selected .edge::after {
		content: '';
		position: absolute;
		top: 30%;
		bottom: 30%;
		left: 4px;
		width: 4px;
		border-radius: 2px;
		background: var(--ceo);
	}

	/* Now: the amber line of the playhead. */
	.playhead {
		position: absolute;
		top: 0;
		bottom: 0;
		width: 2px;
		margin-left: -1px;
		background: var(--ouro);
		pointer-events: none;
		z-index: 2;
	}
</style>
