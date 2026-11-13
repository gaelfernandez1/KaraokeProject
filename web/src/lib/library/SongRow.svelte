<script lang="ts">
	/*
	 * A song in the list: cover, title, artist, language and length. Pointed at or focused, the
	 * row lifts out of the night and its cover takes its full colour; the one whose details show
	 * beside the list is marked in the blue of what is selected.
	 */
	import type { SongSummary } from '#lib/api';
	import { languageName } from '#lib/create/languages.js';
	import { i18n } from '#lib/i18n';
	import Cover from '#lib/poster/Cover.svelte';
	import Icon from '#lib/ui/Icon.svelte';
	import { formatDuration } from '#lib/ui/format.js';

	interface Props {
		song: SongSummary;
		href: string;
		/** Saved for offline use on this device. */
		saved?: boolean;
		/** The song whose details show beside the list. */
		selected?: boolean;
		onopen?: (event: MouseEvent) => void;
	}

	let { song, href, saved = false, selected = false, onopen }: Props = $props();

	const language = $derived(song.language === 'gl' ? null : languageName(song.language));
	const label = $derived(
		[song.title, song.artist, language, formatDuration(song.duration)].filter(Boolean).join(', ')
	);
</script>

<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- the caller builds it with resolve() -->
<a class="row wake" class:selected {href} aria-label={label} onclick={onopen}>
	<span class="thumb"><Cover {song} awake={selected} /></span>
	<span class="name" aria-hidden="true">
		<span class="title">{song.title}</span>
		<span class="artist">{song.artist ?? i18n.t.common.unknownArtist}</span>
	</span>
	{#if song.hook}<span class="hook" aria-hidden="true">«{song.hook}»</span>{/if}
	<span class="facts" aria-hidden="true">
		{#if saved}<span class="saved" title={i18n.t.library.savedOffline}
				><Icon name="offline" size={1} /></span
			>{/if}
		{#if language}<span class="language">{language}</span>{/if}
		<span class="duration data">{formatDuration(song.duration)}</span>
	</span>
</a>

<style>
	.row {
		display: grid;
		grid-template-areas: 'cover name facts';
		grid-template-columns: auto minmax(0, 1fr) auto;
		align-items: center;
		gap: var(--s-4);
		min-height: 4.5rem;
		padding: var(--s-2) var(--s-4) var(--s-2) var(--s-2);
		border-radius: var(--radius-row);
		color: var(--texto);
		text-decoration: none;
		transition:
			background-color var(--dur-1) ease,
			transform var(--dur-1) var(--ease);
	}

	.row:focus-visible {
		outline-offset: -2px;
	}

	.row:active {
		transform: scale(0.985);
	}

	.thumb {
		grid-area: cover;
		width: 3.5rem;
	}

	.name {
		grid-area: name;
		display: grid;
		/* A track that may shrink: the title is cut with an ellipsis, it never widens the row. */
		grid-template-columns: minmax(0, 1fr);
		min-width: 0;
	}

	.title {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: var(--t-1);
		font-weight: 650;
		line-height: 1.2;
	}

	.artist {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		color: var(--texto-2);
		font-size: var(--t--1);
	}

	.hook {
		grid-area: hook;
		display: none;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		color: var(--texto-3);
	}

	.facts {
		grid-area: facts;
		justify-content: end;
		display: flex;
		align-items: center;
		gap: var(--s-3);
		color: var(--texto-2);
		font-size: var(--t--1);
	}

	.duration {
		min-width: 3.4em;
		text-align: end;
	}

	.saved {
		color: var(--ceo);
	}

	.row:focus-visible,
	.row:hover {
		background: var(--panel-claro);
	}

	@media (hover: none) {
		.row:hover {
			background: none;
		}
	}

	/* The song in the spotlight beside the list (where there is room for that). */
	@media (min-width: 64em) {
		.row.selected {
			background: var(--ceo-fondo);
		}

		.row.selected .title {
			color: var(--ceo);
		}
	}

	@container (min-width: 46rem) {
		.row {
			grid-template-areas: 'cover name hook facts';
			grid-template-columns: auto minmax(10rem, 0.9fr) minmax(0, 1fr) auto;
		}

		.hook {
			display: block;
		}
	}
</style>
