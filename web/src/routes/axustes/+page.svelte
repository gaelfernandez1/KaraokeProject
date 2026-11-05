<script lang="ts">
	// This device's settings: interface language, lyrics style, guide vocals, sound delay, pairing.
	import { i18n, LOCALE_NAMES, LOCALES, setLocale } from '#lib/i18n';
	import { Lyrics, THEMES } from '#lib/lyrics';
	import Calibration from '#lib/settings/Calibration.svelte';
	import { SAMPLE_DOC, SAMPLE_TIME } from '#lib/settings/sample.js';
	import { settings, updateSettings } from '#lib/settings/settings.svelte.js';
	import DevicePanel from '#lib/devices/DevicePanel.svelte';
	import Button from '#lib/ui/Button.svelte';
	import Slider from '#lib/ui/Slider.svelte';
	import { saved } from '#lib/offline/saved.svelte.js';
	import { storageEstimate } from '#lib/offline/store.js';
	import { formatBytes } from '#lib/ui/format.js';

	const t = $derived(i18n.t.settings);
	const clock = { now: () => SAMPLE_TIME };
	let used = $state<number | null>(null);
	$effect(() => {
		void saved.list;
		storageEstimate()
			.then((estimate) => (used = estimate?.usage ?? null))
			.catch(() => {});
	});
</script>

<svelte:head><title>{t.title} · Foliada</title></svelte:head>

<main class="settings">
	<h1>{t.title}</h1>

	<section aria-labelledby="language">
		<h2 id="language">{t.language}</h2>
		<div class="choices" role="radiogroup" aria-labelledby="language">
			{#each LOCALES as locale (locale)}
				<button
					type="button"
					role="radio"
					lang={locale}
					aria-checked={i18n.locale === locale}
					onclick={() => setLocale(locale)}>{LOCALE_NAMES[locale]}</button
				>
			{/each}
		</div>
	</section>

	<section aria-labelledby="theme">
		<h2 id="theme">{t.theme}</h2>
		<div class="themes" role="radiogroup" aria-labelledby="theme">
			{#each Object.entries(THEMES) as [id, theme] (id)}
				<button
					type="button"
					role="radio"
					aria-checked={settings.theme === id}
					onclick={() => updateSettings({ theme: id })}
				>
					<!-- A small stage, whole: where the lyrics sit and how big they are on it. -->
					<span class="preview" aria-hidden="true">
						<Lyrics doc={SAMPLE_DOC} {theme} {clock} />
					</span>
					<span class="name">{theme.name}</span>
				</button>
			{/each}
		</div>
	</section>

	<section aria-labelledby="vocals">
		<h2 id="vocals">{t.vocals}</h2>
		<div class="narrow">
			<Slider
				label={t.vocals}
				hideLabel
				value={settings.vocals}
				step={0.05}
				onchange={(v) => updateSettings({ vocals: v })}
				oninput={(v) => (settings.vocals = v)}
			/>
		</div>
	</section>

	<section aria-labelledby="retardo" id="retardo">
		<h2>{t.latency}</h2>
		<p class="hint">{t.latencyHint}</p>
		<div class="stepper">
			<Button
				iconOnly
				icon="minus"
				onclick={() => updateSettings({ latencyMs: settings.latencyMs - 10 })}
				>{i18n.t.player.delayEarlier}</Button
			>
			<output aria-live="polite">{t.ms(settings.latencyMs)}</output>
			<Button
				iconOnly
				icon="plus"
				onclick={() => updateSettings({ latencyMs: settings.latencyMs + 10 })}
				>{i18n.t.player.delayLater}</Button
			>
		</div>
		<Calibration onresult={(ms) => updateSettings({ latencyMs: ms })} />
	</section>

	<section aria-labelledby="storage">
		<h2 id="storage">{t.storage}</h2>
		{#if !saved.available}
			<p class="hint">{t.storageInsecure}</p>
		{:else if saved.list.length === 0}
			<p class="hint">{t.storageEmpty}</p>
		{:else}
			{#if used !== null}<p class="hint">{t.storageUsed(formatBytes(used, i18n.locale))}</p>{/if}
			<ul class="saved">
				{#each saved.list as song (song.id)}
					<li>
						<span class="saved-title">{song.title}</span>
						<span class="saved-size num">{formatBytes(song.bytes, i18n.locale)}</span>
						<Button variant="ghost" iconOnly icon="trash" onclick={() => saved.remove(song.id)}
							>{i18n.t.library.removeOffline}</Button
						>
					</li>
				{/each}
			</ul>
		{/if}
	</section>

	<DevicePanel />
</main>

<style>
	.settings {
		display: grid;
		gap: var(--s-7);
		max-width: var(--page-max);
		margin: 0 auto;
		padding: var(--s-6) var(--page-x) var(--s-9);
	}

	h1 {
		font-family: var(--font-display);
		font-size: var(--t-5);
		font-weight: 900;
		line-height: 0.9;
	}

	h2 {
		margin-bottom: var(--s-3);
		font-size: var(--t-1);
		font-weight: 800;
	}

	section {
		display: grid;
		gap: var(--s-2);
	}

	.hint {
		max-width: 40rem;
		color: var(--papel-suave);
	}

	/* One choice of three: a segmented control, a single control with square inner joins. */
	.choices {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		max-width: 30rem;
		border: 2px solid var(--linha);
		border-radius: var(--radius-control);
		overflow: hidden;
	}

	.choices button {
		min-height: var(--target);
		padding: 0 var(--s-3);
		border: 0;
		background: transparent;
		font-weight: 700;
	}

	.choices button + button {
		border-left: 2px solid var(--linha);
	}

	.choices button[aria-checked='true'] {
		background: var(--farol);
		color: var(--noite);
	}

	.themes {
		display: grid;
		gap: var(--s-5);
	}

	/* One per row, wide enough to read the lyrics at the size they will have. */
	.themes {
		max-width: 36rem;
	}

	.themes button {
		display: grid;
		gap: var(--s-2);
		padding: 0;
		border: 0;
		background: none;
		text-align: left;
	}

	.preview {
		position: relative;
		display: block;
		aspect-ratio: 16 / 9;
		overflow: hidden;
		border: 3px solid var(--linha);
		/* A stage as songs without a picture look: a poster's paper under the night. */
		background:
			linear-gradient(to top, rgb(22 18 46 / 0.88), rgb(22 18 46 / 0.2) 55%, transparent),
			linear-gradient(rgb(22 18 46 / 0.45), rgb(22 18 46 / 0.45)), #ff6a4d;
	}

	.themes button[aria-checked='true'] .preview {
		border-color: var(--farol);
	}

	.name {
		font-weight: 700;
	}

	.themes button[aria-checked='true'] .name {
		color: var(--farol);
	}

	.narrow {
		max-width: 26rem;
	}

	.stepper {
		display: flex;
		align-items: center;
		gap: var(--s-3);
		margin-bottom: var(--s-4);
	}

	.saved {
		display: grid;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.saved li {
		display: grid;
		grid-template-columns: 1fr auto auto;
		align-items: center;
		gap: var(--s-4);
		border-bottom: 1px solid var(--linha);
	}

	.saved-title {
		font-family: var(--font-display);
		font-size: var(--t-1);
		font-weight: 800;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.saved-size {
		color: var(--papel-suave);
	}

	output {
		min-width: 6ch;
		text-align: center;
		font-family: var(--font-display);
		font-size: var(--t-3);
		font-weight: 900;
		font-variant-numeric: tabular-nums;
	}
</style>
