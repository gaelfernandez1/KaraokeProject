<script lang="ts">
	/*
	 * Create a karaoke: a file or a link, the language (Galician first), the lyrics if the singer
	 * has them. The new song's plate takes shape as the form is filled in, and the jobs on the
	 * server show above it, live, as lines of a departures board.
	 */
	import { tick } from 'svelte';
	import { ApiError, type SongSummary } from '#lib/api';
	import { explain, needsPairing } from '#lib/devices/explain.js';
	import PairingNotice from '#lib/devices/PairingNotice.svelte';
	import JobCard from '#lib/create/JobCard.svelte';
	import { jobs } from '#lib/create/jobs.svelte.js';
	import GlobeAnchor from '#lib/globe/GlobeAnchor.svelte';
	import { LIGHTS, PEOPLE } from '#lib/globe/galicia.js';
	import { stage } from '#lib/globe/stage.svelte.js';
	import { formatCount } from '#lib/ui/format.js';
	import { onDestroy } from 'svelte';
	import { LANGUAGES } from '#lib/create/languages.js';
	import { guessTitle, validateCreate, type CreateError } from '#lib/create/validate.js';
	import { i18n } from '#lib/i18n';
	import Cover from '#lib/poster/Cover.svelte';
	import Button from '#lib/ui/Button.svelte';
	import Icon from '#lib/ui/Icon.svelte';
	import Switch from '#lib/ui/Switch.svelte';

	let file = $state<File | null>(null);
	let url = $state('');
	let language = $state('gl');
	let lyrics = $state('');
	let lrclib = $state(true);
	let title = $state('');
	let artist = $state('');
	let error = $state<CreateError | null>(null);
	let failure = $state<string | null>(null);
	let unpaired = $state(false);
	let sending = $state(false);
	let dragging = $state(false);
	let fileInput = $state<HTMLInputElement | null>(null);
	let top = $state<HTMLElement | null>(null);

	const t = $derived(i18n.t.create);
	void jobs.refresh();

	// The globe follows the karaoke being made: the lights of Galicia come on from the west as
	// far as the job has got. With nothing on the way, a line just keeps crossing it.
	$effect(() => {
		stage.mood = 'scan';
		stage.progress = jobs.working;
	});
	onDestroy(() => {
		stage.mood = 'calm';
		stage.progress = null;
	});

	const preview = $derived<SongSummary | null>(
		file || url.trim()
			? {
					// Its sky of lights comes from the song itself, not from each key typed in the title.
					id: file ? file.name : url.trim(),
					title: title.trim() || (file ? guessTitle(file.name).title : hostOf(url)),
					artist: artist.trim() || null,
					language,
					duration: 0,
					cover: null,
					has_video: false,
					created_at: '',
					edited: false,
					lyrics_source: 'user',
					hook:
						lyrics
							.trim()
							.split('\n')
							.find((l) => l.trim() && !/^\[.*\]$/.test(l.trim()))
							?.trim() ?? null
				}
			: null
	);

	function hostOf(link: string): string {
		try {
			return new URL(link.trim()).hostname.replace(/^www\./, '');
		} catch {
			return link.trim();
		}
	}

	function choose(chosen: File | null | undefined) {
		if (!chosen) return;
		file = chosen;
		error = null;
		if (!title.trim()) {
			const guess = guessTitle(chosen.name);
			title = guess.title;
			if (!artist.trim() && guess.artist) artist = guess.artist;
		}
	}

	function onDrop(event: DragEvent) {
		event.preventDefault();
		dragging = false;
		choose(event.dataTransfer?.files[0]);
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		failure = null;
		unpaired = false;
		const result = validateCreate({ file, url, language, lyrics, lrclib, title, artist });
		if (!result.ok) {
			error = result.error;
			// On a phone the problem is far above the button: take the singer there.
			await tick();
			const field = document.getElementById(result.error === 'errorUrl' ? 'link' : 'source');
			field?.scrollIntoView({ behavior: 'smooth', block: 'start' });
			field?.focus({ preventScroll: true });
			return;
		}
		error = null;
		sending = true;
		try {
			await jobs.start(result.value);
			file = null;
			url = '';
			lyrics = '';
			title = '';
			artist = '';
			if (fileInput) fileInput.value = '';
			top?.scrollIntoView({ behavior: 'smooth', block: 'start' });
		} catch (caught) {
			unpaired = needsPairing(caught);
			failure = explain(
				caught,
				caught instanceof ApiError ? `${t.failed} ${caught.message}` : t.failed,
				i18n.t
			);
		} finally {
			sending = false;
		}
	}
</script>

<svelte:head><title>{t.title} · Karaoke en Galego</title></svelte:head>

<main class="create" bind:this={top}>
	<header class="head">
		<div>
			<h1>{t.title}</h1>
			<p class="intro">{t.intro}</p>
		</div>
		<div class="globe">
			<GlobeAnchor label={i18n.t.home.globe(formatCount(PEOPLE), formatCount(LIGHTS))} fit={0.86} />
		</div>
	</header>

	{#if jobs.shown.length > 0}
		<section class="jobs" aria-labelledby="jobs-title">
			<h2 id="jobs-title">{t.jobs}</h2>
			<div class="job-board">
				{#each jobs.shown as job (job.id)}<JobCard {job} />{/each}
			</div>
		</section>
	{/if}

	<form class="form" onsubmit={submit} novalidate>
		<fieldset class="source" aria-describedby={error ? 'source-error' : undefined}>
			<legend class="visually-hidden">{t.source}</legend>
			<label
				id="source"
				tabindex="-1"
				class:invalid={error !== null && error !== 'errorUrl'}
				class="drop"
				class:dragging
				class:filled={preview !== null}
				ondragover={(e) => {
					e.preventDefault();
					dragging = true;
				}}
				ondragleave={() => (dragging = false)}
				ondrop={onDrop}
			>
				<input
					bind:this={fileInput}
					class="visually-hidden"
					type="file"
					accept="audio/*,video/*,.mkv,.opus,.flac"
					onchange={(e) => choose(e.currentTarget.files?.[0])}
				/>
				{#if preview}
					<Cover song={preview} shape="plate" preview />
				{:else}
					<span class="blank">
						<span class="arrow"><Icon name="upload" size={2.25} /></span>
						<span class="drop-text pointer">{t.drop}</span>
						<span class="drop-text touch">{t.dropTouch}</span>
						<span class="pill">{t.chooseFile}</span>
					</span>
				{/if}
			</label>
			{#if file}
				<p class="file">
					<span>{file.name}</span>
					<button type="button" class="change" onclick={() => fileInput?.click()}
						>{t.changeFile}</button
					>
					<button
						type="button"
						class="change"
						onclick={() => {
							file = null;
							if (fileInput) fileInput.value = '';
						}}>{i18n.t.common.remove}</button
					>
				</p>
			{/if}

			<p class="or" aria-hidden="true"><span>{t.or}</span></p>

			<div class="field">
				<label for="link">{t.link}</label>
				<div class="with-icon">
					<Icon name="link" size={1.25} />
					<input
						id="link"
						type="url"
						inputmode="url"
						autocomplete="off"
						placeholder="https://"
						bind:value={url}
						oninput={() => (error = null)}
						aria-invalid={error === 'errorUrl'}
						aria-describedby="link-hint"
					/>
				</div>
				<p class="hint" id="link-hint">{t.linkHint}</p>
			</div>
			{#if error}<p class="error" id="source-error" role="alert">{t[error]}</p>{/if}
		</fieldset>

		<div class="details">
			<div class="field">
				<label for="language">{t.language}</label>
				<select id="language" bind:value={language}>
					{#each LANGUAGES as l (l.code)}<option value={l.code}>{l.name}</option>{/each}
				</select>
			</div>

			<div class="field">
				<label for="lyrics"
					>{t.lyrics} <span class="optional">({i18n.t.common.optional})</span></label
				>
				<textarea
					id="lyrics"
					rows="9"
					bind:value={lyrics}
					aria-describedby="lyrics-hint"
					spellcheck="false"></textarea>
				<p class="hint" id="lyrics-hint">{t.lyricsHint}</p>
			</div>

			{#if !lyrics.trim()}
				<Switch bind:checked={lrclib} label={t.lrclib} hint={t.lrclibHint} />
			{/if}

			<div class="pair">
				<div class="field">
					<label for="title"
						>{t.songTitle} <span class="optional">({i18n.t.common.optional})</span></label
					>
					<input id="title" type="text" autocomplete="off" bind:value={title} />
				</div>
				<div class="field">
					<label for="artist"
						>{t.artist} <span class="optional">({i18n.t.common.optional})</span></label
					>
					<input id="artist" type="text" autocomplete="off" bind:value={artist} />
				</div>
			</div>

			{#if error}<p class="error">{t[error]}</p>{/if}
			{#if unpaired}<PairingNotice text={failure ?? ''} />
			{:else if failure}<p class="error" role="alert">{failure}</p>{/if}
			<Button variant="primary" size="l" icon="create" type="submit" disabled={sending}>
				{sending ? `${t.sending} ${Math.round((jobs.uploading ?? 0) * 100)} %` : t.submit}
			</Button>
		</div>
	</form>
</main>

<style>
	.create {
		display: grid;
		gap: var(--s-7);
		max-width: var(--page-max);
		margin: 0 auto;
		padding: var(--s-6) var(--page-x) var(--s-9);
	}

	.head {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		align-items: center;
		gap: var(--s-5);
	}

	.globe {
		display: none;
	}

	@media (min-width: 64em) {
		.head {
			grid-template-columns: minmax(0, 1fr) auto;
		}

		/* The globe sits beside the title, a little off the page's edge. */
		.globe {
			display: block;
			width: clamp(13rem, 20vw, 19rem);
			margin: calc(var(--s-6) * -1) 0 calc(var(--s-7) * -1);
		}
	}

	h1 {
		font-family: var(--font-display);
		font-size: var(--t-4);
		font-weight: 600;
		letter-spacing: -0.03em;
		line-height: 1.05;
	}

	.intro {
		max-width: 40rem;
		margin-top: var(--s-3);
		font-size: var(--t-1);
		color: var(--texto-2);
	}

	/* The jobs: one line per karaoke on its way. */
	.jobs {
		display: grid;
		gap: var(--s-4);
		max-width: 72rem;
	}

	h2 {
		font-family: var(--font-display);
		font-size: var(--t-3);
		font-weight: 650;
		line-height: 1;
	}

	.job-board {
		display: grid;
		border-top: 1px solid var(--raia);
	}

	@media (min-width: 45em) {
		.job-board {
			grid-template-columns: minmax(0, 1fr) minmax(6rem, 14rem) 4.5rem auto;
			column-gap: var(--s-5);
		}
	}

	.drop-text.touch {
		display: none;
	}

	@media (hover: none) and (pointer: coarse) {
		.drop-text.pointer {
			display: none;
		}

		.drop-text.touch {
			display: block;
		}
	}

	.form {
		display: grid;
		gap: var(--s-7);
		align-items: start;
		max-width: 72rem;
	}

	@media (min-width: 52em) {
		.form {
			grid-template-columns: minmax(15rem, 20rem) 1fr;
		}
	}

	/* Scrolled to on a failed submit: below any top margin, the message above the tab bar. */
	#source,
	#link {
		scroll-margin-top: var(--s-6);
	}

	fieldset {
		min-width: 0;
		margin: 0;
		padding: 0;
		border: 0;
		display: grid;
		gap: var(--s-3);
	}

	.drop {
		display: block;
		cursor: pointer;
		outline-offset: 4px;
	}

	.drop:has(input:focus-visible) {
		outline: 2px solid var(--ceo);
		border-radius: var(--radius-panel);
	}

	/* An empty plate waiting for its song. */
	.blank {
		display: grid;
		place-items: center;
		align-content: center;
		gap: var(--s-4);
		aspect-ratio: 4 / 5;
		padding: var(--s-5);
		border: 1.5px dashed var(--raia-forte);
		border-radius: var(--radius-panel);
		background: var(--panel-claro);
		text-align: center;
		color: var(--texto-2);
		transition:
			border-color var(--dur-1) ease,
			background-color var(--dur-1) ease,
			color var(--dur-1) ease;
	}

	.arrow {
		display: grid;
		place-items: center;
		width: 3.5rem;
		height: 3.5rem;
		border: 1px solid var(--raia-forte);
		border-radius: 50%;
		background: var(--panel-claro);
		transition:
			border-color var(--dur-1) ease,
			color var(--dur-1) ease;
	}

	.invalid .blank,
	.invalid :global(.cover) {
		border-color: var(--erro);
		outline: 2px solid var(--erro);
	}

	/* A file held over it: the plate is picked, in the blue of whatever is selected. */
	.dragging .blank {
		border-color: var(--ceo);
		background-color: var(--ceo-fondo);
		color: var(--texto);
	}

	.dragging .arrow {
		border-color: var(--ceo);
		color: var(--ceo);
	}

	.dragging :global(.cover) {
		outline: 3px solid var(--ceo);
	}

	@media (hover: hover) {
		.drop:hover .blank {
			border-color: var(--ceo);
			color: var(--texto);
		}

		.drop:hover .arrow {
			border-color: var(--ceo);
			color: var(--ceo);
		}

		.drop:hover .pill {
			border-color: var(--ceo);
			background: var(--ceo-fondo);
		}
	}

	.drop-text {
		max-width: 16ch;
		font-family: var(--font-display);
		font-size: var(--t-1);
		font-weight: 600;
		letter-spacing: -0.02em;
		line-height: 1.2;
		color: var(--texto);
	}

	/* Secondary to Create karaoke: drawn as a quiet button, not a second filled one. */
	.pill {
		display: inline-flex;
		align-items: center;
		min-height: var(--target);
		padding: 0 var(--s-5);
		border: 1px solid var(--raia-forte);
		border-radius: var(--radius-pill);
		background: var(--panel-claro);
		color: var(--texto);
		font-weight: 650;
		transition:
			border-color var(--dur-1) ease,
			background-color var(--dur-1) ease,
			transform var(--dur-1) var(--ease);
	}

	.drop:active .pill {
		transform: scale(0.97);
	}

	/* On phones the empty plate is a low band, not a whole screen. */
	@media (max-width: 51.99em) {
		.blank {
			aspect-ratio: auto;
			min-height: 11rem;
		}

		.drop.filled {
			max-width: 14rem;
		}
	}

	.file {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0 var(--s-1);
		font-size: var(--t--1);
		color: var(--texto-2);
		overflow-wrap: anywhere;
	}

	.file span {
		flex: 1 1 100%;
		color: var(--texto);
		font-weight: 600;
	}

	.change {
		min-height: var(--target);
		padding: 0 var(--s-2);
		margin-left: calc(-1 * var(--s-2));
		margin-right: var(--s-2);
		border: 0;
		background: none;
		font-weight: 650;
		color: var(--texto);
		text-decoration: underline;
		text-decoration-color: var(--raia-forte);
		text-underline-offset: 0.25em;
		transition:
			color var(--dur-1) ease,
			text-decoration-color var(--dur-1) ease;
	}

	@media (hover: hover) {
		.change:hover {
			color: var(--ceo);
			text-decoration-color: currentColor;
		}
	}

	.or {
		display: flex;
		align-items: center;
		gap: var(--s-3);
		color: var(--texto-2);
		font-weight: 600;
	}

	.or::before,
	.or::after {
		content: '';
		flex: 1;
		height: 1px;
		background: var(--raia);
	}

	.details {
		display: grid;
		gap: var(--s-5);
		max-width: 44rem;
	}

	.field {
		display: grid;
		gap: var(--s-2);
		min-width: 0;
	}

	label {
		font-weight: 650;
	}

	.optional {
		font-weight: 400;
		color: var(--texto-2);
	}

	.hint {
		display: block;
		font-size: var(--t--1);
		font-weight: 400;
		color: var(--texto-2);
	}

	/* Fields: the night raised a step, a hairline round it; the blue line when focused. */
	input[type='url'],
	input[type='text'],
	select,
	textarea {
		width: 100%;
		min-height: var(--target);
		padding: var(--s-2) var(--s-4);
		border: 1px solid var(--raia-forte);
		border-radius: var(--radius-control);
		background-color: var(--fondo-2);
		color: var(--texto);
		transition:
			border-color var(--dur-1) ease,
			box-shadow var(--dur-1) ease;
	}

	input::placeholder,
	textarea::placeholder {
		color: var(--texto-2);
	}

	input:focus,
	select:focus,
	textarea:focus {
		outline: none;
		border-color: var(--ceo);
		box-shadow: 0 0 0 1px var(--ceo);
	}

	input[aria-invalid='true'] {
		border-color: var(--erro);
	}

	textarea {
		resize: vertical;
		line-height: 1.5;
	}

	select {
		appearance: none;
		padding-right: 2.75rem;
		background-image:
			linear-gradient(45deg, transparent 50%, var(--texto-2) 50%),
			linear-gradient(135deg, var(--texto-2) 50%, transparent 50%);
		background-position:
			calc(100% - 1.25rem) 50%,
			calc(100% - 0.9rem) 50%;
		background-size: 0.35rem 0.35rem;
		background-repeat: no-repeat;
		cursor: pointer;
	}

	option {
		background: var(--fondo-2);
		color: var(--texto);
	}

	.with-icon {
		position: relative;
		display: flex;
		align-items: center;
		color: var(--texto-2);
	}

	.with-icon :global(svg) {
		position: absolute;
		left: var(--s-4);
		pointer-events: none;
	}

	.with-icon:focus-within {
		color: var(--ceo);
	}

	.with-icon input {
		padding-left: 2.75rem;
	}

	.pair {
		display: grid;
		gap: var(--s-4);
	}

	@media (min-width: 36em) {
		.pair {
			grid-template-columns: 1fr 1fr;
		}
	}

	.error {
		font-weight: 650;
		color: var(--erro);
	}

	.details > :global(.button) {
		justify-self: start;
	}

	/* On phones the main action spans the column. */
	@media (max-width: 44.99em) {
		.details > :global(.button) {
			justify-self: stretch;
		}
	}
</style>
