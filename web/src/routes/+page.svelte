<script lang="ts">
	// The library: a wall of song posters with search and language filters.
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { ApiError, listSongs, type SongSummary } from '#lib/api';
	import { needsPairing } from '#lib/devices/explain.js';
	import PairingNotice from '#lib/devices/PairingNotice.svelte';
	import { i18n } from '#lib/i18n';
	import { languageName } from '#lib/create/languages.js';
	import { filterSongs, languagesOf } from '#lib/library/filter.js';
	import Poster from '#lib/poster/Poster.svelte';
	import Button from '#lib/ui/Button.svelte';
	import Icon from '#lib/ui/Icon.svelte';
	import Wordmark from '#lib/ui/Wordmark.svelte';
	import { transitionName } from '#lib/ui/format.js';
	import { arrowNavigation } from '#lib/tv/focus.js';
	import { saved } from '#lib/offline/saved.svelte.js';

	let songs = $state.raw<SongSummary[] | null>(null);
	let failed = $state<string | null>(null);
	let unpaired = $state(false);
	let query = $state('');
	let language = $state('all');
	let savedOnly = $state(false);
	let online = $state(navigator.onLine);
	let opening = $state<string | null>(null);
	let search = $state<HTMLInputElement | null>(null);
	let wall = $state<HTMLElement | null>(null);

	// On a TV driven by a keyboard or a clicker, the arrows move around the whole page: the
	// posters, and the search, the filters and the menu above them.
	$effect(() => arrowNavigation(document.body, () => wall?.querySelector<HTMLElement>('a')));

	const t = $derived(i18n.t.library);
	const languages = $derived(songs ? languagesOf(songs) : []);
	const shown = $derived(
		songs ? filterSongs(songs, { query, language, saved: savedOnly ? saved.ids : null }) : []
	);
	const filtering = $derived(query.trim() !== '' || language !== 'all' || savedOnly);

	async function load() {
		failed = null;
		unpaired = false;
		try {
			songs = await listSongs();
		} catch (error) {
			// Away from home, an unpaired device sees nothing until it is paired.
			unpaired = needsPairing(error);
			failed =
				error instanceof ApiError && error.status === 0 ? i18n.t.errors.network : t.loadError;
		}
	}
	void load();

	function open(song: SongSummary, event: MouseEvent) {
		if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
		event.preventDefault();
		opening = transitionName(song.id);
		void goto(resolve('/cantar/[id]', { id: song.id }));
	}

	function clearFilters() {
		query = '';
		language = 'all';
		savedOnly = false;
	}

	function onKey(event: KeyboardEvent) {
		const target = event.target instanceof Element ? event.target : document.body;
		if (event.key === '/' && !['INPUT', 'TEXTAREA'].includes(target.tagName)) {
			event.preventDefault();
			search?.focus();
		}
	}
</script>

<svelte:head><title>{t.title} · Proxecto Karaoke en Galego</title></svelte:head>
<svelte:window
	onkeydown={onKey}
	ononline={() => {
		online = true;
		void load();
	}}
	onoffline={() => (online = false)}
/>

<main class="library">
	<header class="head">
		<a class="phone-brand" href={resolve('/')}><Wordmark animate size="min(var(--t-3), 8vw)" /></a>
		<h1 class="visually-hidden">{t.title}</h1>
		{#if songs && songs.length > 0}
			<label class="search">
				<span class="visually-hidden">{t.search}</span>
				<Icon name="search" size={1.25} />
				<input
					type="search"
					bind:this={search}
					bind:value={query}
					placeholder={t.searchPlaceholder}
					autocomplete="off"
					spellcheck="false"
					enterkeyhint="search"
				/>
				<kbd aria-hidden="true">/</kbd>
			</label>
			<div class="filters">
				{#if languages.length > 1 || saved.list.length > 0}
					<div class="chips" role="group" aria-label={i18n.t.create.language}>
						<button
							type="button"
							aria-pressed={language === 'all'}
							onclick={() => (language = 'all')}>{t.all}</button
						>
						{#each languages as code (code)}
							<button
								type="button"
								aria-pressed={language === code}
								onclick={() => (language = language === code ? 'all' : code)}
								>{languageName(code)}</button
							>
						{/each}
						{#if saved.list.length > 0}
							<button
								type="button"
								aria-pressed={savedOnly}
								onclick={() => (savedOnly = !savedOnly)}>{t.saved}</button
							>
						{/if}
					</div>
				{/if}
				<p class="count">{t.count(filtering ? shown.length : songs.length)}</p>
			</div>
		{/if}
	</header>

	{#if !online}<p class="offline" role="status">{t.offline}</p>{/if}

	{#if unpaired}
		<section class="notice">
			<PairingNotice text={i18n.t.errors.server.not_paired} />
		</section>
	{:else if failed}
		<section class="notice" role="alert">
			<p>{failed}</p>
			<Button onclick={load} icon="loop">{i18n.t.common.retry}</Button>
		</section>
	{:else if songs === null}
		<ul class="wall loading" aria-busy="true" aria-label={i18n.t.common.loading}>
			{#each Array.from({ length: 8 }, (_, i) => i) as i (i)}
				<li class:feature={i === 0}><div class="placeholder"></div></li>
			{/each}
		</ul>
	{:else if songs.length === 0}
		<section class="empty">
			<h2>{t.emptyTitle}</h2>
			<p>{t.emptyBody}</p>
			<Button variant="primary" size="l" icon="create" href={resolve('/crear')}
				>{t.emptyAction}</Button
			>
		</section>
	{:else if shown.length === 0}
		<section class="notice">
			<p>{query.trim() ? t.noResults(query.trim()) : t.noResultsFiltered}</p>
			<Button onclick={clearFilters}>{t.clearFilters}</Button>
		</section>
	{:else}
		<ul class="wall" bind:this={wall}>
			{#each shown as song, i (song.id)}
				<!-- Every ninth poster is printed big, left then right, when enough follow it. -->
				<li
					class:feature={!filtering && i % 9 === 0 && i + 8 < shown.length}
					class:right={(i / 9) % 2 === 1}
				>
					<Poster
						{song}
						saved={saved.has(song.id)}
						href={resolve('/cantar/[id]', { id: song.id })}
						transition={opening === transitionName(song.id) ? opening : null}
						onopen={(event) => open(song, event)}
					/>
				</li>
			{/each}
		</ul>
	{/if}
</main>

<style>
	.library {
		max-width: var(--page-max);
		margin: 0 auto;
		padding: var(--s-4) var(--page-x) var(--s-8);
	}

	.head {
		display: grid;
		gap: var(--s-4);
		margin-bottom: var(--s-6);
	}

	.phone-brand {
		justify-self: start;
		text-decoration: none;
	}

	.filters {
		display: flex;
		align-items: center;
		gap: var(--s-4);
		min-width: 0;
	}

	.count {
		flex: none;
		margin-left: auto;
		color: var(--papel-suave);
		font-size: var(--t--1);
	}

	@media (min-width: 45em) {
		.phone-brand {
			display: none;
		}

		.head {
			grid-template-columns: minmax(16rem, 30rem) 1fr;
			align-items: center;
			padding-top: var(--s-4);
		}
	}

	.search {
		position: relative;
		display: flex;
		align-items: center;
		gap: var(--s-2);
		min-height: var(--target);
		padding: 0 var(--s-3) 0 var(--s-4);
		border: 2px solid var(--linha);
		border-radius: var(--radius-control);
		background: var(--noite-alta);
		color: var(--papel-suave);
	}

	.search:focus-within {
		border-color: var(--farol);
		color: var(--papel);
	}

	.search input {
		flex: 1;
		min-width: 0;
		height: 2.75rem;
		border: 0;
		background: transparent;
		outline: none;
		color: var(--papel);
	}

	.search input::placeholder {
		color: var(--papel-suave);
	}

	kbd {
		display: none;
		padding: 0 0.45em;
		border: 1px solid var(--linha);
		border-radius: 4px;
		font-family: inherit;
		font-size: var(--t--1);
	}

	@media (hover: hover) and (pointer: fine) {
		.search:not(:focus-within) kbd {
			display: inline-block;
		}
	}

	.chips {
		display: flex;
		gap: var(--s-2);
		overflow-x: auto;
		scrollbar-width: none;
		min-width: 0;
		/* Room for the focus ring, which the scroller would otherwise cut. */
		padding-block: 7px;
		margin-block: -7px;
	}

	.chips button {
		flex: none;
		min-height: 2.5rem;
		padding: 0 var(--s-4);
		border: 2px solid var(--linha);
		border-radius: 999px;
		background: transparent;
		font-weight: 600;
		color: var(--papel);
	}

	.chips button:hover {
		border-color: color-mix(in oklch, var(--linha), var(--papel) 30%);
	}

	.chips button:focus-visible {
		outline-color: var(--papel);
	}

	.chips button[aria-pressed='true'] {
		border-color: var(--farol);
		background: var(--farol);
		color: var(--noite);
	}

	.wall {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(11.5rem, 40vw), 1fr));
		grid-auto-flow: dense;
		gap: var(--s-5) var(--s-4);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.wall .feature {
		grid-column: span 2;
		grid-row: span 2;
	}

	.wall .feature.right {
		grid-column: -3 / -1;
	}

	.placeholder {
		aspect-ratio: 4 / 5;
		background: var(--noite-alta);
	}

	.feature .placeholder {
		height: 100%;
	}

	.offline {
		margin-bottom: var(--s-5);
		padding: var(--s-3) var(--s-4);
		background: var(--noite-alta);
		font-weight: 700;
	}

	.empty,
	.notice {
		display: grid;
		justify-items: start;
		gap: var(--s-4);
		max-width: 36rem;
		padding-block: var(--s-6);
	}

	.empty h2 {
		font-family: var(--font-display);
		font-weight: 900;
		font-size: var(--t-4);
		line-height: 0.95;
	}

	.empty p,
	.notice p {
		color: var(--papel-suave);
		font-size: var(--t-1);
	}

	@media (pointer: coarse) {
		.chips button {
			min-height: var(--target);
		}
	}

	/* Phones: every poster the same size so four to six show at once, and the filter chips
	   run to the screen's edge. These come last so they win over the rules above. */
	@media (max-width: 44.99em) {
		.wall .feature,
		.wall .feature.right {
			grid-column: auto;
			grid-row: auto;
		}

		.count {
			display: none;
		}

		.filters {
			margin-inline: calc(-1 * var(--page-x));
		}

		.chips {
			padding-inline: var(--page-x);
		}
	}
</style>
