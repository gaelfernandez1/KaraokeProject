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
					<span class="sample" aria-hidden="true">Aa</span>{theme.name}
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
		color: var(--papel-suave);
	}

	section {
		display: grid;
	}

	.hint {
		margin-top: var(--s-1);
		font-size: var(--t--1);
		color: var(--papel-suave);
	}

	.stepper {
		display: flex;
		align-items: center;
		gap: var(--s-3);
	}

	.stepper output {
		min-width: 4.5ch;
		text-align: center;
		font-family: var(--font-display);
		font-size: var(--t-2);
		font-weight: 800;
		font-variant-numeric: tabular-nums;
	}

	.link {
		margin-left: auto;
		font-weight: 700;
		color: var(--farol);
	}

	.themes {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: var(--s-2);
	}

	.themes button {
		display: grid;
		justify-items: start;
		gap: var(--s-1);
		padding: var(--s-3);
		border: 2px solid var(--linha);
		border-radius: var(--radius-control);
		background: transparent;
		font-size: var(--t--1);
		font-weight: 600;
		text-align: left;
	}

	.themes button[aria-checked='true'] {
		border-color: var(--farol);
		background: color-mix(in oklch, var(--farol) 10%, transparent);
	}

	.sample {
		font-family: var(--theme-font), var(--font-text);
		font-size: var(--t-2);
		line-height: 1;
		color: var(--theme-sung);
	}
</style>
