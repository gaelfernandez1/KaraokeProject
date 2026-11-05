<script lang="ts">
	/*
	 * A song's poster cut down to a square: its paper with the cover printed on it, or without a
	 * cover the title's first word in the poster face.
	 */
	import { mediaUrl, type SongSummary } from '#lib/api';
	import { keyWord } from './fit';
	import { posterStyle } from './style';

	interface Props {
		song: SongSummary;
	}

	let { song }: Props = $props();
	let broken = $state(false);
	const style = $derived(posterStyle(song.id));
	const word = $derived(keyWord(song.title).toLocaleUpperCase('gl'));
</script>

<span
	class="swatch"
	class:dark={style.dark}
	style:--paper={style.paper}
	style:--ink={style.ink}
	aria-hidden="true"
>
	{#if song.cover && !broken}
		<img
			src={mediaUrl(song.id, song.cover)}
			alt=""
			loading="lazy"
			onerror={() => (broken = true)}
		/>
	{:else}
		<span class="word">{word}</span>
	{/if}
</span>

<style>
	/* A fragment of the poster: the word big, cut by the square's edges. */
	.swatch {
		display: grid;
		align-items: end;
		justify-items: start;
		aspect-ratio: 1;
		overflow: hidden;
		container-type: inline-size;
		background: var(--paper);
	}

	.word {
		margin: 0 0 -4cqi 8cqi;
		font-family: var(--font-display);
		font-weight: 900;
		font-size: 58cqi;
		line-height: 0.85;
		color: var(--ink);
		white-space: nowrap;
	}

	img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		filter: grayscale(1) contrast(1.25);
		mix-blend-mode: multiply;
	}

	.dark img {
		mix-blend-mode: screen;
		opacity: 0.8;
	}
</style>
