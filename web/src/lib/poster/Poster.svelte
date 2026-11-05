<script lang="ts">
	/*
	 * A song as a festival poster: the cover printed in one ink on coloured paper, the title in
	 * the condensed poster face as big as it fits, the artist and length at the foot. Sizes are
	 * in container units, so the same poster works on a phone grid and as a TV hero.
	 */
	import { mediaUrl, type SongSummary } from '#lib/api';
	import { languageName } from '#lib/create/languages.js';
	import { i18n } from '#lib/i18n';
	import { formatDuration } from '#lib/ui/format.js';
	import { fitTitle, splitTitle } from './fit';
	import { posterStyle } from './style';

	interface Props {
		song: SongSummary;
		href?: string;
		/** Saved for offline use on this device. */
		saved?: boolean;
		/** Set on the poster that is opening, so it can grow into the player. */
		transition?: string | null;
		onopen?: (event: MouseEvent) => void;
		/** A song still being made: no length yet. */
		preview?: boolean;
		/** A thumbnail: only the title on its colour. */
		compact?: boolean;
	}

	let {
		song,
		href,
		saved = false,
		transition = null,
		onopen,
		preview = false,
		compact = false
	}: Props = $props();

	let broken = $state(false);
	/** Line height of titles: tight like a poster, with room for Galician accented capitals. */
	const LEADING = 0.94;
	const style = $derived(posterStyle(song.id));
	const cover = $derived(song.cover && !broken && !compact ? mediaUrl(song.id, song.cover) : null);
	const hook = $derived(compact ? null : song.hook);
	/** The chorus fills what the missing picture leaves, bigger the shorter it is. */
	const hookSize = $derived(hook ? Math.max(6.5, Math.min(11, 11 - (hook.length - 18) * 0.09)) : 0);
	// Title box in % of the poster's width; a poster is 125 wide-units tall.
	const parts = $derived(splitTitle(song.title));
	const tag = $derived(compact ? null : parts.tag);
	const fit = $derived(
		fitTitle(parts.main, {
			maxWidth: 84,
			// What is left once the picture or the chorus and the foot have their room.
			maxHeight: (cover ? 44 : hook ? 46 : compact ? 100 : 76) - (tag ? 8 : 0),
			lineHeight: LEADING,
			maxSize: cover ? 30 : compact ? 34 : 44,
			maxLines: cover ? 3 : 4
		})
	);
	const language = $derived(song.language === 'gl' ? null : languageName(song.language));
	const label = $derived(
		[song.title, song.artist, formatDuration(song.duration)].filter(Boolean).join(', ')
	);
</script>

<svelte:element
	this={href ? 'a' : 'div'}
	{href}
	class="poster {style.layout}"
	class:dark={style.dark}
	class:has-cover={cover !== null}
	class:has-hook={!cover && !!hook}
	class:compact
	aria-label={label}
	style:--paper={style.paper}
	style:--ink={style.ink}
	style:--size={fit.size}
	style:view-transition-name={transition}
	onclick={onopen}
	role={href ? undefined : 'img'}
>
	<div class="sheet">
		<div class="title" aria-hidden="true">
			{#each fit.lines as line, i (i)}<span>{line}</span>{/each}
		</div>
		{#if tag}<p class="tag" aria-hidden="true">{tag}</p>{/if}
		{#if !cover && hook}
			<p class="hook" aria-hidden="true" style:--hook-size={hookSize}>«{hook}»</p>
		{/if}
		{#if cover}
			<div class="picture">
				<img src={cover} alt="" loading="lazy" decoding="async" onerror={() => (broken = true)} />
			</div>
		{/if}
		<div class="foot" aria-hidden="true">
			<span class="artist">{song.artist ?? ''}</span>
			<span class="end">
				{#if language}<span class="language">{language}</span>{/if}
				{#if !preview}<span class="duration num">{formatDuration(song.duration)}</span>{/if}
			</span>
		</div>
	</div>
	{#if saved}<span class="saved" title={i18n.t.library.savedOffline}></span>{/if}
</svelte:element>

<style>
	/* The poster is the size container; the sheet inside lays out in its units. */
	.poster {
		position: relative;
		display: block;
		container-type: inline-size;
		aspect-ratio: 4 / 5;
		overflow: hidden;
		background: var(--paper);
		color: var(--ink);
		text-decoration: none;
		isolation: isolate;
		transition:
			transform var(--dur-2) var(--ease),
			outline-offset var(--dur-1) var(--ease);
	}

	.sheet {
		display: flex;
		flex-direction: column;
		height: 100%;
		padding: 7cqi;
	}

	/* Paper grain, so the colour reads as printed paper rather than a flat panel. */
	.poster::after {
		content: '';
		position: absolute;
		inset: 0;
		z-index: 2;
		pointer-events: none;
		background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 .55 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
		mix-blend-mode: multiply;
		opacity: 0.22;
	}

	.dark::after {
		mix-blend-mode: screen;
		opacity: 0.1;
		filter: invert(1);
	}

	@media (hover: hover) {
		a.poster:hover {
			transform: translateY(-4px);
		}
	}

	a.poster:focus-visible {
		outline: 4px solid var(--farol);
		outline-offset: 5px;
	}

	.title {
		display: flex;
		flex-direction: column;
		font-family: var(--font-display);
		font-weight: 900;
		font-size: calc(var(--size) * 1cqi);
		line-height: 0.94;
		letter-spacing: 0;
		/* Room above for accents on capitals (Á, É…), which the tight leading would clip. */
		padding-top: 0.06em;
		white-space: nowrap;
	}

	.picture {
		position: relative;
		flex: 1;
		min-height: 0;
		margin: 5cqi 0 4cqi;
		background: var(--paper);
		overflow: hidden;
	}

	/* Brackets, descenders and accents hang outside the tight leading. */
	.bottom .title {
		padding-bottom: 0.14em;
		margin-bottom: 3cqi;
	}

	/* The version of the song, small under its title, as on a gig poster. */
	.tag {
		margin-top: 1.5cqi;
		font-size: clamp(0.75rem, 6.6cqi, 1.4rem);
		font-weight: 800;
		line-height: 1.15;
	}

	.bottom .title + .tag {
		margin-top: -1.5cqi;
		margin-bottom: 3cqi;
	}

	.compact .sheet {
		padding: 10cqi;
	}

	.bottom .picture {
		order: -1;
		margin: 0 0 5cqi;
	}

	.picture img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		filter: grayscale(1) contrast(1.25) brightness(1.08);
		mix-blend-mode: multiply;
	}

	.dark .picture img {
		filter: grayscale(1) contrast(1.15) brightness(0.95);
		mix-blend-mode: screen;
		opacity: 0.8;
	}

	.poster:not(.has-cover):not(.has-hook) .title {
		flex: 1;
	}

	.poster:not(.has-cover):not(.has-hook).bottom .title {
		justify-content: flex-end;
		padding-bottom: 4cqi;
	}

	/* A poster without a picture quotes the chorus instead. */
	.hook {
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 4;
		line-clamp: 4;
		overflow: hidden;
		max-width: 96%;
		margin: auto 0;
		padding-block: 4cqi;
		font-size: max(0.8125rem, calc(var(--hook-size) * 1cqi));
		font-weight: 800;
		line-height: 1.08;
		text-wrap: balance;
	}

	.bottom .hook {
		order: -1;
	}

	/* The tight leading lets brackets and descenders hang below the last line: keep the foot
	   clear of them. */
	.has-hook .foot {
		margin-top: 0;
		padding-top: 5cqi;
	}

	.compact .foot {
		display: none;
	}

	.compact .title {
		justify-content: center;
	}

	.foot {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 4cqi;
		margin-top: auto;
		padding-top: 3cqi;
		font-size: clamp(0.8125rem, 6.4cqi, 1.25rem);
		font-weight: 700;
		line-height: 1.2;
	}

	.artist {
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.end {
		flex: none;
		display: flex;
		gap: 3cqi;
		align-items: baseline;
	}

	.duration {
		font-variant-numeric: tabular-nums;
		font-weight: 600;
	}

	/* On a small poster the artist matters more than the language. */
	@container (max-width: 13rem) {
		.language {
			display: none;
		}
	}

	.language {
		padding: 0 1.5cqi;
		background: var(--ink);
		color: var(--paper);
		font-weight: 700;
	}

	.saved {
		position: absolute;
		left: 0;
		top: 0;
		z-index: 1;
		width: 0;
		height: 0;
		border-style: solid;
		border-width: 9cqi 9cqi 0 0;
		border-color: var(--ink) transparent transparent transparent;
	}
</style>
