<script lang="ts">
	/*
	 * The player's side panel: guide vocals, key, this device's delay, the lyrics style and the
	 * downloads. It sits beside (or under) the lyrics without covering the line being sung.
	 */
	import { resolve } from '$app/paths';
	import { mediaUrl } from '#lib/api';
	import type { KaraokeDoc } from '#lib/contracts';
	import { i18n } from '#lib/i18n';
	import { THEMES } from '#lib/lyrics';
	import Button from '#lib/ui/Button.svelte';
	import Icon from '#lib/ui/Icon.svelte';
	import Slider from '#lib/ui/Slider.svelte';
	import { saved } from '#lib/offline/saved.svelte.js';
	import { summaryOf } from '#lib/poster/summary.js';
	import type { PlayerSession } from './session.svelte';

	interface Props {
		session: PlayerSession;
		doc: KaraokeDoc;
		songId: string;
		themeId: string;
		latencyMs: number;
		ontheme: (id: string) => void;
		onlatency: (ms: number) => void;
		onexport: (aspect: '16:9' | '9:16') => void;
		onclose: () => void;
	}

	let { session, doc, songId, themeId, latencyMs, ontheme, onlatency, onexport, onclose }: Props =
		$props();

	const t = $derived(i18n.t.player);
	const lib = $derived(i18n.t.library);
	let saveError = $state<string | null>(null);
	const saving = $derived(saved.progress[songId]);

	async function saveOffline() {
		saveError = null;
		const reason = await saved.save(summaryOf(songId, doc));
		if (reason === 'quota') saveError = lib.saveQuota;
		else if (reason === 'network') saveError = lib.saveNetwork;
		else if (reason === 'insecure') saveError = i18n.t.settings.storageInsecure;
	}
	const signed = (n: number) => (n > 0 ? `+${n}` : n < 0 ? `−${-n}` : '0');
	const downloads = $derived(
		[
			{ label: t.downloadInstrumental, file: doc.audio.instrumental },
			{ label: t.downloadVocals, file: doc.audio.vocals },
			{ label: t.downloadLyrics, file: 'karaoke.json' }
		].filter((d): d is { label: string; file: string } => Boolean(d.file))
	);
</script>

<aside class="panel" aria-label={t.sound}>
	<header>
		<h2>{t.sound}</h2>
		<Button variant="ghost" iconOnly icon="close" onclick={onclose}>{i18n.t.common.close}</Button>
	</header>

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

	<section>
		<h3>{t.downloads}</h3>
		<ul class="downloads">
			{#each downloads as d (d.file)}
				<li>
					<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- a file to download, not a page -->
					<a href={mediaUrl(songId, d.file)} download>
						<Icon name="download" size={1.2} />{d.label}
					</a>
				</li>
			{/each}
		</ul>
		{#if saved.available}
			<div class="offline">
				{#if saved.has(songId)}
					<p class="saved-note">{lib.savedOffline}</p>
					<Button variant="ghost" icon="trash" onclick={() => saved.remove(songId)}
						>{lib.removeOffline}</Button
					>
				{:else if saving !== undefined}
					<Button icon="offline" disabled>{lib.saving(Math.round(saving * 100))}</Button>
				{:else}
					<Button icon="offline" onclick={saveOffline}>{lib.saveOffline}</Button>
				{/if}
				{#if saveError}<p class="hint error">{saveError}</p>{/if}
			</div>
		{/if}
		<h3 class="sub">{t.makeVideo}</h3>
		<div class="videos">
			<Button icon="tv" onclick={() => onexport('16:9')}>{t.videoWide}</Button>
			<Button icon="remote" onclick={() => onexport('9:16')}>{t.videoTall}</Button>
		</div>
	</section>
</aside>

<style>
	.panel {
		display: grid;
		align-content: start;
		gap: var(--s-5);
		width: min(24rem, 100%);
		max-height: 100%;
		overflow-y: auto;
		padding: var(--s-4) var(--s-5) var(--s-6);
		background: var(--noite);
		border-left: 1px solid var(--linha);
	}

	header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		position: sticky;
		top: calc(-1 * var(--s-4));
		margin: calc(-1 * var(--s-4)) calc(-1 * var(--s-5)) 0;
		padding: var(--s-3) var(--s-3) var(--s-3) var(--s-5);
		background: inherit;
	}

	h2 {
		font-family: var(--font-display);
		font-size: var(--t-3);
		font-weight: 900;
	}

	h3 {
		margin-bottom: var(--s-2);
		font-size: var(--t--1);
		font-weight: 700;
		color: var(--papel-suave);
	}

	.sub {
		margin-top: var(--s-4);
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

	.downloads {
		display: grid;
		gap: var(--s-1);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.downloads a {
		display: flex;
		align-items: center;
		gap: var(--s-3);
		min-height: var(--target);
		font-weight: 600;
		text-decoration: none;
	}

	.downloads a:hover {
		color: var(--farol);
	}

	.offline {
		display: grid;
		justify-items: start;
		gap: var(--s-2);
		margin-top: var(--s-3);
	}

	.saved-note {
		font-weight: 700;
		color: var(--farol);
	}

	.error {
		color: var(--erro);
	}

	.videos {
		display: flex;
		flex-wrap: wrap;
		gap: var(--s-2);
	}
</style>
