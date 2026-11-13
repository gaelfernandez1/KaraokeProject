<script lang="ts">
	/*
	 * A native range input in the app's style: the filled part is "sung" (lyric amber), the rest
	 * a quiet track; a 48 px tall hit area around a thin track.
	 */
	interface Props {
		label: string;
		value: number;
		min?: number;
		max?: number;
		step?: number;
		/** How the value is read out (and shown, unless hideValue). */
		format?: (value: number) => string;
		hideValue?: boolean;
		hideLabel?: boolean;
		disabled?: boolean;
		oninput?: (value: number) => void;
		onchange?: (value: number) => void;
	}

	let {
		label,
		value,
		min = 0,
		max = 1,
		step = 0.01,
		format = (v) => `${Math.round(v * 100)} %`,
		hideValue = false,
		hideLabel = false,
		disabled = false,
		oninput,
		onchange
	}: Props = $props();

	const id = $props.id();
	const fraction = $derived(max > min ? (value - min) / (max - min) : 0);
</script>

<div class="slider" class:disabled>
	<div class="head" class:visually-hidden={hideLabel && hideValue}>
		<label for={id} class:visually-hidden={hideLabel}>{label}</label>
		{#if !hideValue}<output for={id} class="num">{format(value)}</output>{/if}
	</div>
	<input
		{id}
		type="range"
		{min}
		{max}
		{step}
		{value}
		{disabled}
		aria-valuetext={format(value)}
		style:--fraction={fraction}
		oninput={(e) => oninput?.(Number(e.currentTarget.value))}
		onchange={(e) => onchange?.(Number(e.currentTarget.value))}
	/>
</div>

<style>
	.slider {
		display: grid;
		gap: var(--s-1);
		min-width: 0;
	}

	/* Disabled is grey, never a faded amber. */
	.disabled {
		--ouro: var(--raia);
		color: var(--texto-2);
	}

	.disabled input::-webkit-slider-thumb {
		background: var(--texto-2);
	}

	.head {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: var(--s-3);
		font-size: var(--t--1);
		color: var(--texto-2);
	}

	output {
		font-variant-numeric: tabular-nums;
		color: var(--texto);
		font-weight: 600;
	}

	input {
		--track: 6px;
		--thumb: 1.375rem;
		appearance: none;
		width: 100%;
		height: var(--target);
		margin: 0;
		background: transparent;
		cursor: pointer;
	}

	input:disabled {
		cursor: not-allowed;
	}

	input::-webkit-slider-runnable-track {
		height: var(--track);
		border-radius: 999px;
		background: linear-gradient(
			to right,
			var(--ouro) calc(var(--fraction) * 100%),
			var(--raia) calc(var(--fraction) * 100%)
		);
	}

	input::-moz-range-track {
		height: var(--track);
		border-radius: 999px;
		background: var(--raia);
	}

	input::-moz-range-progress {
		height: var(--track);
		border-radius: 999px;
		background: var(--ouro);
	}

	input::-webkit-slider-thumb {
		appearance: none;
		width: var(--thumb);
		height: var(--thumb);
		margin-top: calc((var(--track) - var(--thumb)) / 2);
		border: 3px solid var(--fondo);
		border-radius: 50%;
		background: var(--texto);
		transition: transform var(--dur-1) var(--ease);
	}

	input::-moz-range-thumb {
		width: var(--thumb);
		height: var(--thumb);
		border: 3px solid var(--fondo);
		border-radius: 50%;
		background: var(--texto);
	}

	input:active::-webkit-slider-thumb {
		transform: scale(1.15);
	}

	input:focus-visible {
		outline: none;
	}

	input:focus-visible::-webkit-slider-thumb {
		outline: 3px solid var(--ceo);
		outline-offset: 2px;
	}

	input:focus-visible::-moz-range-thumb {
		outline: 3px solid var(--ceo);
		outline-offset: 2px;
	}
</style>
