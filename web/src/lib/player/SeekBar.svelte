<script lang="ts">
	/*
	 * The song's position, drawn as the song's shape: raised marks where someone sings, a thin
	 * line through the instrumental parts, and everything up to now in the sung colour. A native
	 * range input on top does the dragging, the keys and the accessibility.
	 */
	import { formatDuration } from '#lib/ui/format.js';

	interface Props {
		time: number;
		duration: number;
		segments: { from: number; to: number }[];
		label: string;
		onseek: (seconds: number) => void;
	}

	let { time, duration, segments, label, onseek }: Props = $props();
	const fraction = $derived(duration > 0 ? Math.min(1, Math.max(0, time / duration)) : 0);
</script>

<div class="seek" style:--p={fraction}>
	<div class="track" aria-hidden="true">
		{#each [false, true] as sung (sung)}
			<div class="layer" class:sung>
				<span class="line"></span>
				{#each segments as segment, i (i)}
					<span
						class="mark"
						style:left="{segment.from * 100}%"
						style:width="{(segment.to - segment.from) * 100}%"
					></span>
				{/each}
			</div>
		{/each}
		<span class="head"></span>
	</div>
	<input
		type="range"
		min="0"
		max={duration || 1}
		step="0.1"
		value={time}
		aria-label={label}
		aria-valuetext="{formatDuration(time)} / {formatDuration(duration)}"
		oninput={(e) => onseek(Number(e.currentTarget.value))}
	/>
</div>

<style>
	.seek {
		position: relative;
		height: 2.75rem;
	}

	.track {
		position: absolute;
		inset: 0;
	}

	.layer {
		position: absolute;
		inset: 0;
		color: color-mix(in oklch, var(--papel) 38%, transparent);
	}

	.layer.sung {
		color: var(--farol);
		clip-path: inset(0 calc((1 - var(--p)) * 100%) 0 0);
	}

	.line {
		position: absolute;
		left: 0;
		right: 0;
		top: 50%;
		height: 2px;
		margin-top: -1px;
		background: currentColor;
	}

	.mark {
		position: absolute;
		top: 50%;
		height: 10px;
		min-width: 2px;
		margin-top: -5px;
		border-radius: 2px;
		background: currentColor;
	}

	.head {
		position: absolute;
		top: 50%;
		left: calc(var(--p) * 100%);
		width: 4px;
		height: 22px;
		margin: -11px 0 0 -2px;
		border-radius: 2px;
		background: var(--papel);
		box-shadow: 0 0 0 3px var(--noite-funda);
	}

	input {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		margin: 0;
		opacity: 0;
		cursor: pointer;
	}

	.seek:has(input:focus-visible) .head {
		outline: 3px solid var(--farol);
		outline-offset: 3px;
	}
</style>
