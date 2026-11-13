<script lang="ts">
	// The main menu: Galicia at night on its own small planet, the four ways in, and below, the
	// songs with the one in the spotlight beside them.
	import { onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { ApiError, listSongs, type SongSummary } from '#lib/api';
	import { needsPairing } from '#lib/devices/explain.js';
	import PairingNotice from '#lib/devices/PairingNotice.svelte';
	import { i18n } from '#lib/i18n';
	import { languageName } from '#lib/create/languages.js';
	import { jobs } from '#lib/create/jobs.svelte.js';
	import GlobeAnchor from '#lib/globe/GlobeAnchor.svelte';
	import { LIGHTS, PEOPLE } from '#lib/globe/galicia.js';
	import { stage, type Mood } from '#lib/globe/stage.svelte.js';
	import { filterSongs, languagesOf } from '#lib/library/filter.js';
	import SongRow from '#lib/library/SongRow.svelte';
	import Cover from '#lib/poster/Cover.svelte';
	import Button from '#lib/ui/Button.svelte';
	import Icon from '#lib/ui/Icon.svelte';
	import Wordmark from '#lib/ui/Wordmark.svelte';
	import { formatCount, formatDuration } from '#lib/ui/format.js';
	import { arrowNavigation } from '#lib/tv/focus.js';
	import { saved } from '#lib/offline/saved.svelte.js';

	let songs = $state.raw<SongSummary[] | null>(null);
	let failed = $state<string | null>(null);
	let unpaired = $state(false);
	let query = $state('');
	let language = $state('all');
	let savedOnly = $state(false);
	let online = $state(navigator.onLine);
	let search = $state<HTMLInputElement | null>(null);
	let board = $state<HTMLElement | null>(null);
	let first = $state<HTMLAnchorElement | null>(null);
	/** The item of the menu the pointer or the focus was on last. */
	let chosen = $state(0);
	/** The song whose details show beside the list. */
	let pointed = $state<string | null>(null);

	// On a TV driven by a keyboard or a clicker the arrows move around the whole page: the menu,
	// then the search, the filters and the songs below. The menu's first item starts with focus.
	$effect(() => arrowNavigation(document.body, () => first ?? board?.querySelector('a') ?? null));

	const t = $derived(i18n.t.library);
	const h = $derived(i18n.t.home);
	const languages = $derived(songs ? languagesOf(songs) : []);
	const shown = $derived(
		songs ? filterSongs(songs, { query, language, saved: savedOnly ? saved.ids : null }) : []
	);
	const filtering = $derived(query.trim() !== '' || language !== 'all' || savedOnly);
	const spotlight = $derived(shown.find((song) => song.id === pointed) ?? shown[0] ?? null);

	const items = $derived<{ href: string; word: string; hint: string; mood: Mood }[]>([
		{
			href: '#cancions',
			word: h.sing,
			hint: songs ? h.singHint(songs.length) : i18n.t.common.loading,
			mood: 'calm'
		},
		{ href: resolve('/festa'), word: i18n.t.nav.party, hint: h.partyHint, mood: 'party' },
		{ href: resolve('/crear'), word: i18n.t.nav.create, hint: h.createHint, mood: 'scan' },
		{ href: resolve('/axustes'), word: i18n.t.nav.settings, hint: h.settingsHint, mood: 'tech' }
	]);

	/** The globe shows what the chosen item is about: a party, a karaoke being made, the settings. */
	function choose(index: number) {
		chosen = index;
		stage.mood = items[index]?.mood ?? 'calm';
	}

	/** Hours and minutes of music, as "1 h 34 min". */
	function long(seconds: number): string {
		const minutes = Math.round(seconds / 60);
		return minutes >= 60 ? `${Math.floor(minutes / 60)} h ${minutes % 60} min` : `${minutes} min`;
	}
	const total = $derived.by(() => {
		if (!songs) return '';
		const list = filtering ? shown : songs;
		return h.total(t.count(list.length), long(list.reduce((sum, song) => sum + song.duration, 0)));
	});

	onDestroy(() => {
		stage.mood = 'calm';
	});

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
		void goto(resolve('/cantar/[id]', { id: song.id }));
	}

	/** "Sing" goes down to the songs and puts the cursor in the search. */
	function sing(event: MouseEvent) {
		event.preventDefault();
		const target = document.getElementById('cancions');
		target?.scrollIntoView({ block: 'start' });
		(search ?? board?.querySelector<HTMLElement>('a'))?.focus({ preventScroll: true });
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

<svelte:head><title>Karaoke en Galego</title></svelte:head>
<svelte:window
	onkeydown={onKey}
	ononline={() => {
		online = true;
		void load();
	}}
	onoffline={() => (online = false)}
/>

<main class="home">
	<section class="hero" aria-labelledby="menu-title">
		<header class="top">
			<a class="brand" href={resolve('/')}><Wordmark animate size="var(--t-0)" /></a>
			<button
				type="button"
				class="still"
				aria-pressed={stage.still}
				aria-label={stage.still ? h.play : h.stop}
				title={stage.still ? h.play : h.stop}
				onclick={() => stage.toggleStill()}
			>
				<Icon name={stage.still ? 'play' : 'pause'} size={1} />
			</button>
		</header>

		<h1 id="menu-title" class="visually-hidden">{h.menu}</h1>
		<nav class="menu" aria-label={h.menu}>
			<ul>
				{#each items as item, i (item.href)}
					<li class:chosen={chosen === i} style:--i={i}>
						{#if i === 0}
							<!-- eslint-disable svelte/no-navigation-without-resolve -- a place in this page -->
							<a
								href={item.href}
								bind:this={first}
								onclick={sing}
								onpointerenter={() => choose(i)}
								onfocus={() => choose(i)}
							>
								<span class="word">{item.word}</span>
								<span class="hint">{item.hint}</span>
							</a>
							<!-- eslint-enable svelte/no-navigation-without-resolve -->
						{:else}
							<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- built with resolve() -->
							<a href={item.href} onpointerenter={() => choose(i)} onfocus={() => choose(i)}>
								<span class="word">{item.word}</span>
								<span class="hint">
									{#if i === 2 && jobs.working !== null}
										<span class="working data">{Math.round(jobs.working * 100)} %</span>
									{/if}
									{item.hint}
								</span>
							</a>
						{/if}
					</li>
				{/each}
			</ul>
		</nav>

		<div class="sphere">
			<GlobeAnchor
				label={h.globe(formatCount(PEOPLE), formatCount(LIGHTS))}
				names
				turnable
				fit={0.82}
			/>
		</div>
	</section>

	<section id="cancions" class="songs" aria-labelledby="songs-title">
		<header class="head">
			<div class="heading">
				<h2 id="songs-title">{t.title}</h2>
				{#if songs && songs.length > 0}<p class="count">{total}</p>{/if}
			</div>
			{#if songs && songs.length > 0}
				<div class="tools">
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
					{#if languages.length > 1 || saved.list.length > 0}
						<div class="chips" role="group" aria-label={i18n.t.create.language}>
							<!-- "All" drops the language and the saved filter; the search stays as typed. -->
							<button
								type="button"
								aria-pressed={language === 'all' && !savedOnly}
								onclick={() => {
									language = 'all';
									savedOnly = false;
								}}>{t.all}</button
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
				</div>
			{/if}
		</header>

		{#if !online}<p class="offline" role="status">{t.offline}</p>{/if}

		{#if unpaired}
			<div class="notice panel">
				<PairingNotice text={i18n.t.errors.server.not_paired} />
			</div>
		{:else if failed}
			<div class="notice panel" role="alert">
				<p>{failed}</p>
				<Button onclick={load} icon="loop">{i18n.t.common.retry}</Button>
			</div>
		{:else if songs === null}
			<ul class="board loading" aria-busy="true" aria-label={i18n.t.common.loading}>
				{#each Array.from({ length: 6 }, (_, i) => i) as i (i)}
					<li><div class="placeholder"></div></li>
				{/each}
			</ul>
		{:else if songs.length === 0}
			<div class="empty panel">
				<h3>{t.emptyTitle}</h3>
				<p>{t.emptyBody}</p>
				<Button variant="primary" size="l" icon="create" href={resolve('/crear')}
					>{t.emptyAction}</Button
				>
			</div>
		{:else if shown.length === 0}
			<div class="notice panel">
				<p>{query.trim() ? t.noResults(query.trim()) : t.noResultsFiltered}</p>
				<Button onclick={clearFilters}>{t.clearFilters}</Button>
			</div>
		{:else}
			<div class="library">
				<ul class="board" bind:this={board}>
					{#each shown as song (song.id)}
						<li onpointerenter={() => (pointed = song.id)} onfocusin={() => (pointed = song.id)}>
							<SongRow
								{song}
								saved={saved.has(song.id)}
								selected={spotlight?.id === song.id}
								href={resolve('/cantar/[id]', { id: song.id })}
								onopen={(event) => open(song, event)}
							/>
						</li>
					{/each}
				</ul>
				{#if spotlight}
					<aside class="detail panel" aria-label={spotlight.title}>
						{#key spotlight.id}
							<div class="card">
								<div class="art"><Cover song={spotlight} awake /></div>
								<h3>{spotlight.title}</h3>
								<p class="artist">{spotlight.artist ?? i18n.t.common.unknownArtist}</p>
								{#if spotlight.hook}<p class="hook">«{spotlight.hook}»</p>{/if}
								<ul class="facts">
									<li class="data">{formatDuration(spotlight.duration)}</li>
									<li>{languageName(spotlight.language)}</li>
									{#if spotlight.has_video}<li>{h.withVideo}</li>{/if}
									<li>{spotlight.edited ? t.edited : h.lyricsBy[spotlight.lyrics_source]}</li>
									{#if saved.has(spotlight.id)}<li class="kept">{t.savedOffline}</li>{/if}
								</ul>
								<div class="actions">
									<Button
										variant="primary"
										size="l"
										icon="play"
										href={resolve('/cantar/[id]', { id: spotlight.id })}>{h.sing}</Button
									>
									<Button icon="edit" href={resolve('/editar/[id]', { id: spotlight.id })}
										>{h.edit}</Button
									>
								</div>
							</div>
						{/key}
					</aside>
				{/if}
			</div>
		{/if}
	</section>

	<footer class="credits">
		<p>{h.credits}</p>
	</footer>
</main>

<style>
	.home {
		--edge: max(var(--page-x), var(--safe-x));
		overflow-x: clip;
	}

	/* The first screen: the night. On phones the globe leads and the songs follow at once. */
	.hero {
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: var(--s-4);
		padding: var(--s-4) var(--page-x) var(--s-6);
	}

	.top {
		display: flex;
		align-items: center;
		gap: var(--s-4);
		min-height: var(--target);
	}

	.brand {
		margin-right: auto;
		text-decoration: none;
	}

	.still {
		display: grid;
		place-items: center;
		flex: none;
		width: 2.75rem;
		height: 2.75rem;
		border: 1px solid var(--raia-forte);
		border-radius: 50%;
		background: var(--panel-claro);
		color: var(--texto-2);
		transition:
			border-color var(--dur-1) ease,
			color var(--dur-1) ease,
			transform var(--dur-1) var(--ease);
	}

	.still:active {
		transform: scale(0.94);
	}

	.menu {
		display: none;
	}

	.sphere {
		width: min(100%, 54dvh);
		margin: 0 auto;
	}

	@keyframes appear {
		from {
			opacity: 0;
			transform: translateY(0.35em);
		}
	}

	@keyframes rise {
		from {
			opacity: 0;
			transform: translateY(0.9rem);
		}
	}

	@media (hover: hover) {
		.still:hover {
			border-color: var(--ceo);
			color: var(--texto);
		}
	}

	@media (min-width: 45em) {
		.top {
			display: none;
		}
	}

	/* Laptop and TV: the menu on the left, the planet on the right. */
	@media (min-width: 64em) {
		.hero {
			grid-template-columns: minmax(24rem, 0.86fr) minmax(0, 1.14fr);
			grid-template-rows: auto minmax(0, 1fr);
			column-gap: var(--s-6);
			min-height: 100dvh;
			padding: max(var(--s-5), var(--safe-y)) var(--edge);
		}

		.top {
			display: flex;
			grid-column: 1 / -1;
			grid-row: 1;
			z-index: 1;
		}

		.menu {
			display: block;
			grid-column: 1;
			grid-row: 2;
			align-self: center;
			z-index: 1;
		}

		.menu ul {
			display: grid;
			gap: var(--s-3);
			margin: 0;
			padding: 0;
			list-style: none;
		}

		.menu li {
			animation: rise var(--dur-3) var(--ease) calc(var(--i) * 70ms + 120ms) both;
		}

		.menu a {
			position: relative;
			display: grid;
			justify-items: start;
			gap: 0.1rem;
			width: fit-content;
			padding: 0.15rem 0;
			border-radius: var(--radius-control);
			text-decoration: none;
			outline-offset: 0.5rem;
		}

		/* The chosen item steps forward behind a short line of sky blue; the rest wait dimmed. */
		.menu a::before {
			content: '';
			position: absolute;
			left: 0;
			top: calc(clamp(2.6rem, 5.2vw, 6.25rem) * 0.56);
			width: 2.4rem;
			height: 3px;
			border-radius: 2px;
			background: var(--ceo);
			transform: scaleX(0);
			transform-origin: left;
			transition: transform var(--dur-2) var(--ease);
		}

		.word,
		.hint {
			transition:
				transform var(--dur-3) var(--ease),
				color var(--dur-2) ease;
		}

		.word {
			font-family: var(--font-display);
			font-size: clamp(2.6rem, 5.2vw, 6.25rem);
			font-weight: 600;
			line-height: 1.06;
			letter-spacing: -0.035em;
			color: color-mix(in oklab, var(--texto) 36%, transparent);
		}

		.hint {
			display: flex;
			align-items: baseline;
			gap: var(--s-2);
			font-size: var(--t-0);
			color: var(--texto-3);
		}

		.working {
			color: var(--ouro);
		}

		.chosen .word {
			color: var(--texto);
		}

		.chosen .hint {
			color: var(--texto-2);
		}

		.chosen .word,
		.chosen .hint {
			transform: translateX(3.4rem);
		}

		.chosen a::before {
			transform: scaleX(1);
		}

		.sphere {
			grid-column: 2;
			grid-row: 1 / -1;
			align-self: center;
			justify-self: center;
			width: min(100%, 96dvh);
			margin: 0 calc(var(--edge) * -0.5) 0 0;
		}
	}

	/* The songs. */
	.songs {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: var(--s-5);
		max-width: var(--page-max);
		margin: 0 auto;
		padding: var(--s-7) var(--page-x) var(--s-8);
	}

	.head {
		display: grid;
		gap: var(--s-4);
	}

	.heading {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--s-2) var(--s-5);
	}

	h2 {
		font-family: var(--font-display);
		font-size: var(--t-4);
		font-weight: 600;
		letter-spacing: -0.03em;
		line-height: 1.05;
	}

	.count {
		color: var(--texto-2);
	}

	.tools {
		display: grid;
		gap: var(--s-3);
		min-width: 0;
	}

	.search {
		position: relative;
		display: flex;
		align-items: center;
		gap: var(--s-2);
		min-height: var(--target);
		padding: 0 var(--s-4) 0 var(--s-5);
		border: 1px solid var(--raia-forte);
		border-radius: var(--radius-pill);
		background: var(--panel-claro);
		color: var(--texto-2);
		transition:
			border-color var(--dur-1) ease,
			background-color var(--dur-1) ease;
	}

	.search:focus-within {
		border-color: var(--ceo);
		background: var(--ceo-fondo);
		color: var(--texto);
	}

	.search input {
		flex: 1;
		min-width: 0;
		height: 2.75rem;
		border: 0;
		background: transparent;
		outline: none;
		color: var(--texto);
	}

	.search input::placeholder {
		color: var(--texto-2);
	}

	kbd {
		display: none;
		padding: 0 0.5em;
		border: 1px solid var(--raia-forte);
		border-radius: 0.4rem;
		font-family: var(--font-data);
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
		margin: -4px;
		padding: 4px;
	}

	.chips button {
		flex: none;
		min-height: 2.75rem;
		padding: 0 var(--s-4);
		border: 1px solid var(--raia-forte);
		border-radius: var(--radius-pill);
		background: transparent;
		font-weight: 600;
		color: var(--texto-2);
		transition:
			background-color var(--dur-1) ease,
			border-color var(--dur-1) ease,
			color var(--dur-1) ease,
			transform var(--dur-1) var(--ease);
	}

	.chips button:active {
		transform: scale(0.96);
	}

	.chips button[aria-pressed='true'] {
		border-color: var(--ceo);
		background: var(--ceo-fondo);
		color: var(--ceo);
	}

	@media (hover: hover) {
		.chips button:hover {
			color: var(--texto);
		}
	}

	@media (min-width: 45em) {
		.tools {
			grid-template-columns: minmax(16rem, 26rem) minmax(0, 1fr);
			align-items: center;
			gap: var(--s-4);
		}
	}

	.offline {
		padding: var(--s-3) var(--s-5);
		border: 1px solid var(--raia-forte);
		border-radius: var(--radius-row);
		background: var(--panel-claro);
		font-weight: 600;
	}

	.library {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: var(--s-6);
		align-items: start;
	}

	.board {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 2px;
		margin: 0 calc(var(--s-2) * -1);
		padding: 0;
		list-style: none;
		container-type: inline-size;
	}

	/* A long library only lays out the rows near the screen. */
	.board li {
		content-visibility: auto;
		contain-intrinsic-size: auto 4.5rem;
	}

	.placeholder {
		height: 4.5rem;
		border-radius: var(--radius-row);
		background: var(--panel-claro);
		animation: wait 1.6s ease-in-out infinite alternate;
	}

	@keyframes wait {
		to {
			opacity: 0.45;
		}
	}

	/* The song the pointer or the focus is on, big, with what to do with it. */
	.detail {
		display: none;
	}

	@media (min-width: 64em) {
		.library {
			grid-template-columns: minmax(0, 1.25fr) minmax(20rem, 0.75fr);
			gap: var(--s-7);
		}

		.detail {
			position: sticky;
			top: var(--s-6);
			display: block;
			padding: var(--s-5);
		}

		.card {
			display: grid;
			gap: var(--s-3);
			animation: appear var(--dur-2) var(--ease) both;
		}

		.art {
			width: min(100%, 15rem);
			margin-bottom: var(--s-2);
			border-radius: var(--radius-row);
			box-shadow: var(--sombra);
		}

		h3 {
			font-family: var(--font-display);
			font-size: var(--t-2);
			font-weight: 600;
			letter-spacing: -0.025em;
			line-height: 1.12;
			overflow-wrap: anywhere;
		}

		.artist {
			margin-top: calc(var(--s-2) * -1);
			color: var(--texto-2);
		}

		.hook {
			font-size: var(--t-1);
			font-style: italic;
			line-height: 1.3;
			color: var(--ouro);
		}

		.facts {
			display: flex;
			flex-wrap: wrap;
			gap: var(--s-2);
			margin: 0;
			padding: 0;
			list-style: none;
		}

		.facts li {
			padding: 0.2rem 0.75rem;
			border: 1px solid var(--raia);
			border-radius: var(--radius-pill);
			font-size: var(--t--1);
			color: var(--texto-2);
		}

		.facts .kept {
			border-color: color-mix(in oklab, var(--ceo) 50%, transparent);
			color: var(--ceo);
		}

		.actions {
			display: flex;
			flex-wrap: wrap;
			gap: var(--s-3);
			margin-top: var(--s-2);
		}
	}

	.notice,
	.empty {
		display: grid;
		justify-items: start;
		gap: var(--s-4);
		max-width: 44rem;
		padding: var(--s-6);
	}

	.empty h3 {
		font-family: var(--font-display);
		font-size: var(--t-3);
		font-weight: 600;
		letter-spacing: -0.03em;
	}

	.empty p {
		color: var(--texto-2);
	}

	.credits {
		max-width: var(--page-max);
		margin: 0 auto;
		padding: 0 var(--page-x) var(--s-7);
		font-size: var(--t--1);
		color: var(--texto-3);
	}

	.credits p {
		max-width: 60ch;
		padding-top: var(--s-5);
		border-top: 1px solid var(--raia);
	}
</style>
