<script lang="ts">
	/*
	 * A line of the song under the magnifying glass: the guide vocals' waveform, a block for
	 * each word over it, and the playhead. A click seeks; dragging a block's edge moves where the
	 * word starts or ends.
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
		onseek: (seconds: number) => void;
		onselect: (index: number) => void;
		/** A drag of a word's edge: seconds moved since it began (null if cancelled); `done` when it ends. */
		ondrag: (index: number, edge: 'start' | 'end', delta: number | null, done: boolean) => void;
	}

	let { buffer, from, to, words, selected, time, onseek, onselect, ondrag }: Props = $props();

	let width = $state(0);
	let height = $state(0);
	let canvas = $state<HTMLCanvasElement | null>(null);
	const span = $derived(Math.max(0.1, to - from));
	const x = (seconds: number) => ((seconds - from) / span) * 100;

	$effect(() => {
		if (!canvas || width === 0 || height === 0) return;
		const ratio = devicePixelRatio || 1;
		canvas.width = Math.round(width * ratio);
		canvas.height = Math.round(height * ratio);
		const context = canvas.getContext('2d');
		if (!context) return;
		context.clearRect(0, 0, canvas.width, canvas.height);
		if (!buffer) return;
		const columns = Math.round(width / 3);
		const values = peaks(buffer.getChannelData(0), buffer.sampleRate, from, to, columns);
		const max = Math.max(0.05, ...values);
		const mid = canvas.height / 2;
		context.fillStyle = getComputedStyle(canvas).color;
		const step = canvas.width / columns;
		for (let i = 0; i < columns; i++) {
			const h = Math.max(1, (values[i] / max) * mid * 0.92);
			context.fillRect(i * step, mid - h, Math.max(1, step - ratio), 2 * h);
		}
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
		border-radius: var(--radius-control);
		background: var(--noite-funda);
		overflow: hidden;
		cursor: text;
		touch-action: none;
	}

	canvas {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		color: color-mix(in oklch, var(--papel) 30%, transparent);
		pointer-events: none;
	}

	.word {
		position: absolute;
		top: 0.5rem;
		bottom: 0.5rem;
		min-width: 4px;
		border: 2px solid color-mix(in oklch, var(--papel) 45%, transparent);
		border-radius: 6px;
		background: color-mix(in oklch, var(--papel) 8%, transparent);
	}

	.word.doubtful {
		border-style: dashed;
	}

	.word.selected {
		border-color: var(--farol);
		background: color-mix(in oklch, var(--farol) 18%, transparent);
		z-index: 1;
	}

	.label {
		position: absolute;
		left: 0;
		top: 0;
		max-width: 100%;
		padding: 0.1rem 0.35rem;
		border: 0;
		background: none;
		font-size: var(--t--1);
		font-weight: 700;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		cursor: pointer;
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
		background: var(--farol);
	}

	.playhead {
		position: absolute;
		top: 0;
		bottom: 0;
		width: 2px;
		margin-left: -1px;
		background: var(--papel);
		pointer-events: none;
		z-index: 2;
	}
</style>
