<script lang="ts" module>
	/** A small fixed hash of a song id, for its own colours. */
	function hash(text: string): number {
		let h = 2166136261;
		for (let i = 0; i < text.length; i++) h = Math.imul(h ^ text.charCodeAt(i), 16777619);
		return h >>> 0;
	}
</script>

<script lang="ts">
	/*
	 * A song's cover: its picture or, without one, a night sky of its own (two soft lights whose
	 * colours come from the song's id, the same everywhere) with the title's first letter. As a
	 * plate it also carries the title, set as big as it fits, with the artist and length.
	 */
	import { mediaUrl, type SongSummary } from '#lib/api';
	import { formatDuration } from '#lib/ui/format.js';
	import { fitTitle, splitTitle } from './fit';

	interface Props {
		song: SongSummary;
		/** `plate`: 4:5 with the title; `square`: just the picture or the sky. */
		shape?: 'plate' | 'square';
		/** At full strength instead of a little dimmed (what is playing, what is pointed at). */
		awake?: boolean;
		/** A song still being made: no length yet. */
		preview?: boolean;
	}

	let { song, shape = 'square', awake = false, preview = false }: Props = $props();

	let broken = $state(false);
	const picture = $derived(song.cover && !broken ? mediaUrl(song.id, song.cover) : null);
	const plate = $derived(shape === 'plate');
	const parts = $derived(splitTitle(song.title));
	// From the blue of the sea round to the pink of a late sunset, never the gold of what is lit.
	const hue = $derived(195 + (hash(song.id) % 150));
	const second = $derived(hue + 35 + ((hash(song.id) >>> 9) % 70));
	const initial = $derived((parts.main.match(/[\p{L}\p{N}]/u)?.[0] ?? '♪').toLocaleUpperCase());
	const fit = $derived(
		fitTitle(parts.main, {
			maxWidth: 84,
			maxHeight: 46,
			lineHeight: 1.06,
			maxSize: 17,
			maxLines: 4
		})
	);
</script>

<span
	class="cover"
	class:plate
	class:awake
	style:--hue={hue}
	style:--second={second}
	aria-hidden="true"
>
	{#if picture}
		<img src={picture} alt="" loading="lazy" decoding="async" onerror={() => (broken = true)} />
	{:else if !plate}
		<span class="initial">{initial}</span>
	{/if}
	{#if plate}
		<span class="sheet" style:--size={fit.size}>
			<span class="title">
				{#each fit.lines as line, i (i)}<span>{line}</span>{/each}
			</span>
			{#if parts.tag}<span class="tag">{parts.tag}</span>{/if}
			<span class="foot">
				<span class="artist">{song.artist ?? ''}</span>
				{#if !preview}<span class="data">{formatDuration(song.duration)}</span>{/if}
			</span>
		</span>
	{/if}
</span>

<style>
	.cover {
		position: relative;
		display: grid;
		place-items: center;
		container-type: inline-size;
		aspect-ratio: 1;
		overflow: hidden;
		border-radius: clamp(0.5rem, 12cqi, var(--radius-row));
		background:
			radial-gradient(
				110% 110% at 18% 12%,
				oklch(0.66 0.15 calc(var(--hue) * 1deg)),
				transparent 62%
			),
			radial-gradient(
				120% 120% at 88% 92%,
				oklch(0.5 0.17 calc(var(--second) * 1deg)),
				transparent 64%
			),
			oklch(0.2 0.05 calc(var(--hue) * 1deg));
		isolation: isolate;
		filter: saturate(0.82) brightness(0.86);
		transition: filter var(--dur-2) ease;
	}

	.plate {
		aspect-ratio: 4 / 5;
		border-radius: var(--radius-panel);
	}

	/* At full strength: playing, in the spotlight, or pointed at (a parent with `wake`). */
	.awake,
	:global(.wake:is(:hover, :focus-visible)) .cover {
		filter: none;
	}

	@media (hover: none) {
		:global(.wake:hover:not(:focus-visible)) .cover:not(.awake) {
			filter: saturate(0.82) brightness(0.86);
		}
	}

	img {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.initial {
		font-family: var(--font-display);
		font-size: 46cqi;
		font-weight: 700;
		line-height: 1;
		color: rgb(255 255 255 / 0.92);
	}

	/* The title over the picture: a shade rises from the foot so it always reads. */
	.sheet {
		position: absolute;
		inset: 0;
		z-index: 1;
		display: flex;
		flex-direction: column;
		justify-content: flex-end;
		gap: 2.5cqi;
		padding: 8cqi;
		background: linear-gradient(transparent 30%, rgb(2 4 6 / 0.82));
		color: var(--texto);
	}

	.title {
		display: grid;
		font-family: var(--font-display);
		font-size: calc(var(--size) * 1cqi);
		font-weight: 700;
		line-height: 1.06;
		letter-spacing: -0.02em;
	}

	.tag {
		font-size: 4.6cqi;
		color: var(--texto-2);
	}

	.foot {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 4cqi;
		padding-top: 3cqi;
		border-top: 1px solid var(--raia-forte);
		font-size: 4.6cqi;
		font-weight: 600;
	}

	.artist {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
</style>
