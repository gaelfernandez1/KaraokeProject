<script lang="ts">
	/*
	 * Where a song is sung: its video darkened behind the animated lyrics, or its cover printed
	 * in one ink on the song's poster paper, or the bare night with a strip of that paper.
	 * Fills whatever box it is given. Used by the player and the party TV.
	 */
	import { mediaUrl } from '#lib/api';
	import type { KaraokeDoc, PlaybackClock, Theme } from '#lib/contracts';
	import { Lyrics } from '#lib/lyrics';
	import { fitTitle, splitTitle } from '#lib/poster/fit.js';
	import { posterStyle } from '#lib/poster/style.js';

	interface Props {
		doc: KaraokeDoc;
		/** The song's id in the library (where its media are served). */
		songId: string;
		theme: Theme;
		clock: PlaybackClock;
		/** Receives the background video element, so the session can keep it in step. */
		onvideo?: (video: HTMLVideoElement | null) => void;
		transition?: string | null;
		/** Room kept free under the lyrics (for controls), in px; the picture still fills it. */
		lyricsInset?: number;
		/** False before the song starts: its poster is on screen instead. */
		showLyrics?: boolean;
		/** The paper strip of songs without a picture (the party TV draws its own line there). */
		strip?: boolean;
	}

	let {
		doc,
		songId,
		theme,
		clock,
		onvideo,
		transition = null,
		lyricsInset = 0,
		showLyrics = true,
		strip = true
	}: Props = $props();

	let video = $state<HTMLVideoElement | null>(null);
	let coverFailed = $state(false);
	const cover = $derived(doc.cover && !coverFailed ? mediaUrl(songId, doc.cover) : null);
	const backgroundVideo = $derived(
		doc.video?.background ? mediaUrl(songId, doc.video.background) : null
	);
	const poster = $derived(posterStyle(songId));

	let width = $state(0);
	let height = $state(0);
	/** The faint title of the night print: the main title only, at most two lines, in the band
	 * between the header and the lyrics. */
	const ghost = $derived(
		width > 0 && height > 0
			? fitTitle(splitTitle(doc.title).main, {
					maxWidth: width * 0.9,
					maxHeight: height * 0.34,
					lineHeight: 0.94,
					maxSize: height * 0.26,
					maxLines: 2
				})
			: null
	);

	$effect(() => {
		onvideo?.(video);
		return () => onvideo?.(null);
	});
</script>

<div
	bind:clientWidth={width}
	bind:clientHeight={height}
	class="stage"
	class:dark={poster.dark}
	style:--paper={poster.paper}
	style:--ink={poster.ink}
	style:view-transition-name={transition}
	data-testid="stage"
>
	{#if backgroundVideo || cover}
		<!-- The video or the cover printed like the song's poster: one ink on its paper, dimmed
		     under the lyrics. -->
		<div class="print">
			{#if backgroundVideo}
				<video
					src={backgroundVideo}
					muted
					loop
					playsinline
					preload="auto"
					disablepictureinpicture
					bind:this={video}
				></video>
			{:else if cover}
				<img src={cover} alt="" onerror={() => (coverFailed = true)} />
			{/if}
		</div>
		<div class="scrim" class:band={theme.layout.mode === 'scroll'}></div>
	{:else}
		<!-- No picture: the night version of the song's poster, its title printed big and faint. -->
		<div class="night-print" aria-hidden="true">
			{#if ghost}
				<span class="ghost" style:font-size="{ghost.size}px">
					{#each ghost.lines as line, i (i)}<span>{line}</span>{/each}
				</span>
			{/if}
		</div>
		<div class="scrim lyrics-only" class:band={theme.layout.mode === 'scroll'}></div>
		{#if strip}<div class="strip"></div>{/if}
	{/if}
	<div class="lyrics-box" class:hidden={!showLyrics} style:bottom="{lyricsInset}px">
		<Lyrics {doc} {theme} {clock} />
	</div>
</div>

<style>
	.stage {
		position: absolute;
		inset: 0;
		overflow: hidden;
		background: var(--noite);
	}

	.print,
	.night-print,
	.scrim,
	.lyrics-box {
		position: absolute;
		inset: 0;
	}

	.lyrics-box.hidden {
		visibility: hidden;
	}

	.print {
		background: var(--paper);
	}

	.print video,
	.print img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		filter: grayscale(1) contrast(1.25) brightness(1.05);
		mix-blend-mode: multiply;
	}

	.dark .print video,
	.dark .print img {
		mix-blend-mode: screen;
		opacity: 0.8;
	}

	/* The night over the print: light enough to see the paper, darkest where the lyrics are. */
	.scrim {
		background:
			linear-gradient(to top, rgb(22 18 46 / 0.88), rgb(22 18 46 / 0.2) 55%, transparent),
			rgb(22 18 46 / 0.45);
	}

	/* Centred lyrics (scroll mode) get the night most where they are. */
	.scrim.band {
		background:
			radial-gradient(ellipse 85% 50% at 50% 50%, rgb(22 18 46 / 0.65), transparent 80%),
			rgb(22 18 46 / 0.45);
	}

	/* A strip of the song's paper along the bottom. */
	.strip {
		position: absolute;
		inset: auto 0 0;
		height: 6px;
		background: var(--paper);
	}

	.night-print {
		background: color-mix(in oklch, var(--paper) 30%, var(--noite));
	}

	/* The same paper grain as the posters. */
	.night-print::after {
		content: '';
		position: absolute;
		inset: 0;
		background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 .5 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
		mix-blend-mode: soft-light;
		opacity: 0.35;
	}

	.ghost {
		position: absolute;
		top: 14%;
		left: 5%;
		display: flex;
		flex-direction: column;
		font-family: var(--font-display);
		font-weight: 900;
		line-height: 0.94;
		color: var(--paper);
		opacity: 0.16;
		white-space: nowrap;
	}

	/* On the night print only the lyrics need the extra dark. */
	.scrim.lyrics-only {
		background: linear-gradient(to top, rgb(22 18 46 / 0.75), transparent 50%);
	}

	.scrim.lyrics-only.band {
		background: radial-gradient(ellipse 85% 50% at 50% 50%, rgb(22 18 46 / 0.55), transparent 80%);
	}
</style>
