<script lang="ts">
	/*
	 * Create a karaoke: a file or a link, the language (Galician first), the lyrics if the singer
	 * has them. The new song's poster takes shape as the form is filled in, and the jobs on the
	 * server show above it, live.
	 */
	import { tick } from 'svelte';
	import { ApiError, type SongSummary } from '#lib/api';
	import { explain, needsPairing } from '#lib/devices/explain.js';
	import PairingNotice from '#lib/devices/PairingNotice.svelte';
	import JobCard from '#lib/create/JobCard.svelte';
	import { jobs } from '#lib/create/jobs.svelte.js';
	import { LANGUAGES } from '#lib/create/languages.js';
	import { guessTitle, validateCreate, type CreateError } from '#lib/create/validate.js';
	import { i18n } from '#lib/i18n';
	import Poster from '#lib/poster/Poster.svelte';
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
	jobs.refresh();

	const preview = $derived<SongSummary | null>(
		file || url.trim()
			? {
					id: title || file?.name || url,
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

<svelte:head><title>{t.title} · Foliada</title></svelte:head>

<main class="create" bind:this={top}>
	<header>
		<h1>{t.title}</h1>
		<p class="intro">{t.intro}</p>
	</header>

	{#if jobs.shown.length > 0}
		<section class="jobs" aria-labelledby="jobs-title">
			<h2 id="jobs-title">{t.jobs}</h2>
			{#each jobs.shown as job (job.id)}<JobCard {job} />{/each}
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
					<Poster song={preview} preview />
				{:else}
					<span class="blank">
						<Icon name="upload" size={2.5} />
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
		gap: var(--s-6);
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

	.intro {
		max-width: 40rem;
		margin-top: var(--s-3);
		font-size: var(--t-1);
		color: var(--papel-suave);
	}

	h2 {
		font-size: var(--t-1);
		font-weight: 800;
	}

	.jobs {
		display: grid;
		gap: var(--s-3);
		max-width: 72rem;
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
		outline-offset: 5px;
	}

	.drop:has(input:focus-visible) {
		outline: 3px solid var(--farol);
	}

	/* An empty poster waiting for its song. */
	.blank {
		display: grid;
		place-items: center;
		align-content: center;
		gap: var(--s-4);
		aspect-ratio: 4 / 5;
		padding: var(--s-5);
		border: 2px solid var(--linha);
		background:
			repeating-linear-gradient(
				-45deg,
				transparent 0 14px,
				color-mix(in oklch, var(--linha) 35%, transparent) 14px 15px
			),
			var(--noite-alta);
		text-align: center;
		color: var(--papel-suave);
		transition:
			border-color var(--dur-1) var(--ease),
			background-color var(--dur-1) var(--ease);
	}

	.invalid .blank,
	.invalid :global(.poster) {
		border-color: var(--erro);
		outline: 2px solid var(--erro);
	}

	.drop:hover .blank,
	.dragging .blank {
		border-color: var(--farol);
		color: var(--papel);
	}

	.dragging :global(.poster) {
		outline: 3px solid var(--farol);
	}

	.drop-text {
		font-family: var(--font-display);
		font-size: var(--t-3);
		font-weight: 800;
		line-height: 1;
		color: var(--papel);
	}

	/* Secondary to Create karaoke: an outline, not a second filled button. */
	.pill {
		padding: var(--s-2) var(--s-4);
		border: 2px solid var(--papel);
		border-radius: var(--radius-control);
		color: var(--papel);
		font-weight: 800;
	}

	/* On phones the blank poster is a low band, not a whole screen. */
	@media (max-width: 51.99em) {
		.blank {
			aspect-ratio: auto;
			min-height: 10rem;
		}

		.drop.filled {
			max-width: 14rem;
		}
	}

	.file {
		display: flex;
		flex-wrap: wrap;
		gap: var(--s-1) var(--s-3);
		align-items: baseline;
		font-size: var(--t--1);
		color: var(--papel-suave);
		overflow-wrap: anywhere;
	}

	.change {
		padding: 0;
		border: 0;
		background: none;
		font-weight: 700;
		color: var(--farol);
		text-decoration: underline;
		text-underline-offset: 0.2em;
	}

	.or {
		display: flex;
		align-items: center;
		gap: var(--s-3);
		color: var(--papel-suave);
		font-weight: 700;
	}

	.or::before,
	.or::after {
		content: '';
		flex: 1;
		height: 1px;
		background: var(--linha);
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
		font-weight: 700;
	}

	.optional {
		font-weight: 400;
		color: var(--papel-suave);
	}

	.hint {
		display: block;
		font-size: var(--t--1);
		font-weight: 400;
		color: var(--papel-suave);
	}

	input[type='url'],
	input[type='text'],
	select,
	textarea {
		width: 100%;
		min-height: var(--target);
		padding: var(--s-2) var(--s-4);
		border: 2px solid var(--linha);
		border-radius: var(--radius-control);
		background: var(--noite-alta);
		color: var(--papel);
	}

	input:focus,
	select:focus,
	textarea:focus {
		outline: none;
		border-color: var(--farol);
	}

	textarea {
		resize: vertical;
		line-height: 1.5;
	}

	select {
		appearance: none;
		background-image:
			linear-gradient(45deg, transparent 50%, var(--papel) 50%),
			linear-gradient(135deg, var(--papel) 50%, transparent 50%);
		background-position:
			calc(100% - 1.25rem) 50%,
			calc(100% - 0.9rem) 50%;
		background-size: 0.35rem 0.35rem;
		background-repeat: no-repeat;
		background-color: var(--noite-alta);
	}

	.with-icon {
		position: relative;
		display: flex;
		align-items: center;
		color: var(--papel-suave);
	}

	.with-icon :global(svg) {
		position: absolute;
		left: var(--s-4);
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
		font-weight: 700;
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
