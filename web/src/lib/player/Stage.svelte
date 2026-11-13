<script lang="ts">
	/*
	 * Where a song is sung, at night: its video dimmed behind the animated lyrics, or its cover
	 * asleep in the night blue and out of focus, or, for a song without a picture, its own sky of
	 * lights (the same one its cover shows on the board). Whatever the picture, the night is
	 * deepest where the lyrics are, so the sung amber and the white always read. Fills whatever
	 * box it is given. Used by the player and the party TV.
	 */
	import { mediaUrl } from '#lib/api';
	import type { KaraokeDoc, PlaybackClock, Theme } from '#lib/contracts';
	import { Lyrics } from '#lib/lyrics';
	import Cover from '#lib/poster/Cover.svelte';
	import { summaryOf } from '#lib/poster/summary.js';

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
		/** False before the song starts: its cover is on screen instead. */
		showLyrics?: boolean;
		/** The poster world's paper strip along the bottom. The night has none; still accepted
		 * until the party TV stops passing it. */
		strip?: boolean;
	}

	// eslint-disable-next-line svelte/no-unused-props -- `strip` is accepted only so callers compile
	let {
		doc,
		songId,
		theme,
		clock,
		onvideo,
		transition = null,
		lyricsInset = 0,
		showLyrics = true
	}: Props = $props();

	let video = $state<HTMLVideoElement | null>(null);
	let coverFailed = $state(false);
	const cover = $derived(doc.cover && !coverFailed ? mediaUrl(songId, doc.cover) : null);
	const backgroundVideo = $derived(
		doc.video?.background ? mediaUrl(songId, doc.video.background) : null
	);
	const song = $derived(summaryOf(songId, doc));
	const centred = $derived(theme.layout.mode === 'scroll');

	$effect(() => {
		onvideo?.(video);
		return () => onvideo?.(null);
	});
</script>

<div class="stage" style:view-transition-name={transition} data-testid="stage">
	{#if backgroundVideo}
		<div class="backdrop film">
			<video
				src={backgroundVideo}
				muted
				loop
				playsinline
				preload="auto"
				disablepictureinpicture
				bind:this={video}
			></video>
		</div>
	{:else if cover}
		<!-- The cover, dark and out of focus: a place, not a picture. -->
		<div class="backdrop asleep" aria-hidden="true">
			<img src={cover} alt="" onerror={() => (coverFailed = true)} />
		</div>
	{:else}
		<!-- No picture: the song's own sky, as on its cover. -->
		<div class="backdrop sky" aria-hidden="true"><Cover {song} /></div>
	{/if}
	<div class="scrim" class:centred></div>
	<div class="lyrics-box" class:hidden={!showLyrics} style:bottom="{lyricsInset}px">
		<Lyrics {doc} {theme} {clock} />
	</div>
</div>

<style>
	.stage {
		position: absolute;
		inset: 0;
		overflow: hidden;
		background: var(--fondo);
	}

	.backdrop,
	.scrim,
	.lyrics-box {
		position: absolute;
		inset: 0;
	}

	.lyrics-box.hidden {
		visibility: hidden;
	}

	.backdrop video,
	.backdrop img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	/* Behind the lyrics the picture steps back: darker, its colours calmer. A video stays a
	   little lighter, as it moves. */
	.film video {
		filter: brightness(0.62) saturate(0.85);
	}

	/* A still is also out of focus: a place, not a picture. Its own layer, so the lyrics moving
	   above it never repaint the blur. */
	.asleep img {
		filter: blur(1.4vmin) brightness(0.5) saturate(0.8);
		transform: scale(1.08);
		will-change: transform;
	}

	/* No picture: the song's own sky, at the size of the screen, without its letter. */
	.sky :global(.cover) {
		position: absolute;
		inset: 0;
		aspect-ratio: auto;
		border-radius: 0;
		filter: brightness(0.6);
	}

	.sky :global(.initial) {
		display: none;
	}

	/* The night over the picture: darkest at the foot, where the lyrics are. */
	.scrim {
		background:
			linear-gradient(
				to top,
				color-mix(in srgb, var(--fondo) 90%, transparent),
				color-mix(in srgb, var(--fondo) 30%, transparent) 55%,
				transparent
			),
			color-mix(in srgb, var(--fondo) 30%, transparent);
	}

	/* Centred lyrics (scroll mode) get the night most where they are. */
	.scrim.centred {
		background:
			radial-gradient(
				ellipse 85% 50% at 50% 50%,
				color-mix(in srgb, var(--fondo) 70%, transparent),
				transparent 80%
			),
			color-mix(in srgb, var(--fondo) 35%, transparent);
	}
</style>
