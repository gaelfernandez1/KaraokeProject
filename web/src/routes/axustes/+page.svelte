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
	import { formatBytes, formatCount } from '#lib/ui/format.js';
	import GlobeAnchor from '#lib/globe/GlobeAnchor.svelte';
	import { LIGHTS, PEOPLE } from '#lib/globe/galicia.js';
	import { stage } from '#lib/globe/stage.svelte.js';
	import { onDestroy } from 'svelte';

	const t = $derived(i18n.t.settings);
	const clock = { now: () => SAMPLE_TIME };
	/** The delay as words, its figure apart: the figure in dots of light, the unit in text. */
	const latency = $derived.by(() => {
		const text = t.ms(settings.latencyMs);
		const figure = String(settings.latencyMs);
		const at = text.indexOf(figure);
		return at < 0
			? { before: '', figure: text, after: '' }
			: { before: text.slice(0, at), figure, after: text.slice(at + figure.length) };
	});
	let used = $state<number | null>(null);
	$effect(() => {
		void saved.list;
		storageEstimate()
			.then((estimate) => (used = estimate?.usage ?? null))
			.catch(() => {});
	});

	// The globe, as a chart: its meridians and contour lines come forward.
	$effect(() => {
		stage.mood = 'tech';
	});
	onDestroy(() => {
		stage.mood = 'calm';
	});
</script>

<svelte:head><title>{t.title} · Karaoke en Galego</title></svelte:head>

<main class="settings">
	<header class="head">
		<h1>{t.title}</h1>
		<div class="globe">
			<GlobeAnchor label={i18n.t.home.globe(formatCount(PEOPLE), formatCount(LIGHTS))} fit={0.86} />
		</div>
	</header>

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
			<output aria-live="polite"
				>{latency.before}<span class="data">{latency.figure}</span>{latency.after}</output
			>
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
		/* Tracks that may shrink: the previews and sliders fit the phone, they never widen it. */
		grid-template-columns: minmax(0, 1fr);
		gap: var(--s-6);
		max-width: var(--page-max);
		margin: 0 auto;
		padding: var(--s-6) var(--page-x) var(--s-9);
	}

	.head {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		align-items: center;
	}

	.globe {
		display: none;
	}

	@media (min-width: 64em) {
		.head {
			grid-template-columns: minmax(0, 1fr) auto;
		}

		.globe {
			display: block;
			width: clamp(12rem, 18vw, 17rem);
			margin: calc(var(--s-5) * -1) 0 calc(var(--s-6) * -1);
		}
	}

	h1 {
		font-family: var(--font-display);
		font-size: var(--t-4);
		font-weight: 600;
		letter-spacing: -0.03em;
		line-height: 1.05;
	}

	/* Each setting a section of the board, a hairline above it. */
	.settings > :global(section) {
		/* Also the sections other components bring (calibration, this device). */
		grid-template-columns: minmax(0, 1fr);
		/* A link to a section (#aparello) lands below the sticky bar, not under it. */
		scroll-margin-top: 5.5rem;
		padding-top: var(--s-5);
		border-top: 1px solid var(--raia);
	}

	.settings :global(h2) {
		margin-bottom: var(--s-2);
		font-family: var(--font-display);
		font-size: var(--t-1);
		font-weight: 600;
		letter-spacing: -0.02em;
		line-height: 1.2;
	}

	section {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: var(--s-2);
	}

	/* Laptop and TV: the board's two columns, what each setting is on the left, its controls on
	   the right. */
	@media (min-width: 64em) {
		.settings > :global(section) {
			grid-template-columns: minmax(14rem, 22rem) minmax(0, 1fr);
			gap: 0 var(--s-7);
			align-items: start;
		}

		/* No row gap (the heading spans rows that may stay empty): the controls keep their
		   distance with a margin. */
		.settings > :global(section) > :global(*) {
			grid-column: 2;
			margin-bottom: var(--s-2);
		}

		.settings > :global(section) > :global(:last-child) {
			margin-bottom: 0;
		}

		.settings > :global(section) > :global(h2) {
			grid-column: 1;
			grid-row: 1 / span 12;
		}
	}

	.hint {
		max-width: 40rem;
		color: var(--texto-2);
	}

	/* One choice of three: a segmented control, a single control with square inner joins. */
	.choices {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		max-width: 30rem;
		padding: 4px;
		gap: 2px;
		border: 1px solid var(--raia);
		border-radius: var(--radius-pill);
		background: var(--panel-claro);
	}

	.choices button {
		min-height: var(--target);
		padding: 0 var(--s-3);
		border: 0;
		border-radius: var(--radius-pill);
		background: transparent;
		font-weight: 650;
		color: var(--texto-2);
		outline-offset: -2px;
		transition:
			background-color var(--dur-1) ease,
			box-shadow var(--dur-1) ease;
	}

	@media (hover: hover) {
		.choices button:hover {
			color: var(--texto);
		}
	}

	.choices button[aria-checked='true'] {
		background: var(--ceo);
		color: var(--fondo);
	}

	/* Side by side where there is room, never narrower than a phone's: wide enough to read the
	   lyrics at the size they will have. */
	.themes {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 22rem), 1fr));
		gap: var(--s-5);
		max-width: 80rem;
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
		border: 2px solid var(--raia);
		border-radius: var(--radius-row);
		transition: border-color var(--dur-1) ease;
		/* A stage as songs without a picture look: the night. */
		background: radial-gradient(120% 90% at 30% 20%, #0f2136, var(--fondo-3) 70%);
	}

	@media (hover: hover) {
		.themes button:hover .preview {
			border-color: var(--raia-forte);
		}
	}

	.themes button[aria-checked='true'] .preview {
		border-color: var(--ceo);
	}

	.name {
		font-weight: 650;
	}

	.themes button[aria-checked='true'] .name {
		color: var(--ceo);
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
		border-bottom: 1px solid var(--raia);
	}

	.saved-title {
		font-family: var(--font-text);
		font-size: var(--t-1);
		font-weight: 650;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.saved-size {
		color: var(--texto-2);
	}

	/* The delay, a big figure in dots of light. */
	output {
		display: flex;
		align-items: baseline;
		justify-content: center;
		gap: 0.15em;
		min-width: 7.5rem;
		color: var(--texto-2);
		font-weight: 600;
	}

	output .data {
		font-size: var(--t-4);
		line-height: 1;
		color: var(--texto);
	}
</style>
