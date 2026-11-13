<script lang="ts">
	/*
	 * The player's sound panel: guide vocals, key, this device's delay and the lyrics style. It
	 * sits beside (or under) the lyrics without covering the line being sung.
	 */
	import { resolve } from '$app/paths';
	import { i18n } from '#lib/i18n';
	import { THEMES } from '#lib/lyrics';
	import Button from '#lib/ui/Button.svelte';
	import Slider from '#lib/ui/Slider.svelte';
	import PlayerPanel from './PlayerPanel.svelte';
	import type { PlayerSession } from './session.svelte';

	interface Props {
		session: PlayerSession;
		themeId: string;
		latencyMs: number;
		ontheme: (id: string) => void;
		onlatency: (ms: number) => void;
		onclose: () => void;
	}

	let { session, themeId, latencyMs, ontheme, onlatency, onclose }: Props = $props();

	const t = $derived(i18n.t.player);
	const signed = (n: number) => (n > 0 ? `+${n}` : n < 0 ? `−${-n}` : '0');
</script>

<PlayerPanel title={t.sound} {onclose}>
	<section>
		<Slider
			label={t.vocals}
			value={session.vocals}
			step={0.05}
			oninput={(v) => session.setVocals(v)}
		/>
		<p class="hint">{t.vocalsHint}</p>
	</section>

	<section>
		<h3 id="key-label">{t.key}</h3>
		<div class="stepper" role="group" aria-labelledby="key-label">
			<Button
				iconOnly
				icon="minus"
				disabled={!session.pitchAvailable || session.pitch <= -12}
				onclick={() => session.setPitch(session.pitch - 1)}>{t.keyDown}</Button
			>
			<output aria-live="polite">{signed(session.pitch)}</output>
			<Button
				iconOnly
				icon="plus"
				disabled={!session.pitchAvailable || session.pitch >= 12}
				onclick={() => session.setPitch(session.pitch + 1)}>{t.keyUp}</Button
			>
		</div>
		{#if !session.pitchAvailable}<p class="hint">{t.keyUnavailable}</p>{/if}
	</section>

	<section>
		<h3 id="delay-label">{t.delay}</h3>
		<div class="stepper" role="group" aria-labelledby="delay-label">
			<Button iconOnly icon="minus" onclick={() => onlatency(latencyMs - 10)}
				>{t.delayEarlier}</Button
			>
			<output aria-live="polite">{i18n.t.settings.ms(latencyMs)}</output>
			<Button iconOnly icon="plus" onclick={() => onlatency(latencyMs + 10)}>{t.delayLater}</Button>
			<a class="link" href={resolve('/axustes#retardo')}>{t.calibrate}</a>
		</div>
		<p class="hint">{t.delayHint}</p>
	</section>

	<section>
		<h3 id="theme-label">{t.theme}</h3>
		<div class="themes" role="radiogroup" aria-labelledby="theme-label">
			{#each Object.entries(THEMES) as [id, theme] (id)}
				<button
					type="button"
					role="radio"
					aria-checked={id === themeId}
					onclick={() => ontheme(id)}
					style:--theme-font={`"${theme.font.family}"`}
					style:--theme-sung={theme.colors.sung}
				>
					<span class="sample" aria-hidden="true">Aa</span><span class="name">{theme.name}</span>
				</button>
			{/each}
		</div>
	</section>
</PlayerPanel>

<style>
	h3 {
		margin-bottom: var(--s-2);
		font-size: var(--t--1);
		font-weight: 700;
		color: var(--texto-2);
	}

	section {
		display: grid;
	}

	.hint {
		margin-top: var(--s-1);
		font-size: var(--t--1);
		color: var(--texto-2);
	}

	.stepper {
		display: flex;
		align-items: center;
		gap: var(--s-3);
	}

	.stepper output {
		min-width: 4.5ch;
		text-align: center;
		font-family: var(--font-data);
		font-size: var(--t-2);
		font-weight: 650;
		font-variant-numeric: tabular-nums;
		line-height: 1;
	}

	.link {
		display: inline-flex;
		align-items: center;
		min-height: var(--target);
		margin-left: auto;
		font-weight: 700;
		color: var(--texto);
		text-decoration-color: var(--raia-forte);
		transition:
			color var(--dur-1) ease,
			text-decoration-color var(--dur-1) ease;
	}

	.link:hover {
		color: var(--ceo);
		text-decoration-color: currentColor;
	}

	/* The lyrics styles, one a line: each one's sample in its own font and sung colour; the
	   chosen one in the selection blue. */
	.themes {
		display: grid;
		gap: 2px;
	}

	.themes button {
		position: relative;
		display: flex;
		align-items: center;
		gap: var(--s-4);
		min-height: var(--target);
		padding: var(--s-2) var(--s-3);
		border: 0;
		border-radius: var(--radius-control);
		background: transparent;
		font-weight: 600;
		text-align: start;
		transition:
			background-color var(--dur-1) ease,
			transform var(--dur-1) var(--ease);
	}

	.themes button:focus-visible {
		outline-offset: -3px;
	}

	.themes button:active {
		transform: scale(0.98);
	}

	@media (hover: hover) {
		.themes button:hover {
			background: var(--panel-claro);
		}
	}

	.themes button[aria-checked='true'] {
		background: var(--ceo-fondo);
	}

	.themes button[aria-checked='true'] .name {
		color: var(--ceo);
	}

	.sample {
		flex: none;
		width: 2.2em;
		font-family: var(--theme-font), var(--font-text);
		font-size: var(--t-2);
		line-height: 1;
		color: var(--theme-sung);
	}
</style>
