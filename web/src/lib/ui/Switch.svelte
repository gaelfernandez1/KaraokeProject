<script lang="ts">
	// An on/off switch: a native checkbox (keyboard, screen readers) drawn as a sliding knob.
	interface Props {
		checked: boolean;
		label: string;
		hint?: string;
		onchange?: (checked: boolean) => void;
		size?: 'm' | 'l';
	}

	let { checked = $bindable(), label, hint, onchange, size = 'm' }: Props = $props();
</script>

<label class="switch {size}">
	<input
		type="checkbox"
		role="switch"
		bind:checked
		onchange={(e) => onchange?.(e.currentTarget.checked)}
	/>
	<span class="track" aria-hidden="true"></span>
	<span class="text">
		<span class="label">{label}</span>
		{#if hint}<span class="hint">{hint}</span>{/if}
	</span>
</label>

<style>
	.switch {
		display: flex;
		gap: var(--s-3);
		align-items: flex-start;
		cursor: pointer;
	}

	input {
		position: absolute;
		opacity: 0;
		width: 1px;
		height: 1px;
	}

	.track {
		position: relative;
		flex: none;
		width: 3rem;
		height: 1.75rem;
		margin-top: 0.1rem;
		border-radius: 999px;
		background: var(--linha);
		transition: background-color var(--dur-1) var(--ease);
	}

	.track::after {
		content: '';
		position: absolute;
		top: 0.25rem;
		left: 0.25rem;
		width: 1.25rem;
		height: 1.25rem;
		border-radius: 50%;
		background: var(--papel);
		transition: transform var(--dur-1) var(--ease);
	}

	input:checked + .track {
		background: var(--farol);
	}

	input:checked + .track::after {
		transform: translateX(1.25rem);
		background: var(--noite);
	}

	input:focus-visible + .track {
		outline: 3px solid var(--farol);
		outline-offset: 3px;
	}

	.text {
		display: grid;
	}

	.label {
		font-weight: 700;
	}

	.hint {
		font-size: var(--t--1);
		color: var(--papel-suave);
	}

	/* For the TV: bigger knob and text. */
	.l {
		align-items: center;
		font-size: 1.5rem;
	}

	.l .track {
		width: 4.5rem;
		height: 2.5rem;
		margin: 0;
	}

	.l .track::after {
		width: 1.9rem;
		height: 1.9rem;
		top: 0.3rem;
		left: 0.3rem;
	}

	.l input:checked + .track::after {
		transform: translateX(2rem);
	}
</style>
