<script lang="ts">
	/*
	 * Between songs on the TV: the next song's cover, who sings it (big, in their colour) and a
	 * countdown in dots of light big enough to read across the room. The song's intro shows the
	 * same bill, without the countdown, until the first line.
	 */
	import SongTitle from '#lib/poster/SongTitle.svelte';
	import type { SongSummary } from '#lib/api';
	import { i18n } from '#lib/i18n';
	import Cover from '#lib/poster/Cover.svelte';
	import Button from '#lib/ui/Button.svelte';
	import { singerColor } from './colors';
	import type { Guest } from './types';

	interface Props {
		song: SongSummary;
		guest: Guest | undefined;
		/** Seconds left; null once the song has started (its intro shows the same bill). */
		countdown: number | null;
		onstart?: () => void;
		onskip?: () => void;
	}

	let { song, guest, countdown, onstart, onskip }: Props = $props();
	const t = $derived(i18n.t.party);
</script>

<section class="up-next" style:--who={singerColor(guest?.color, 'var(--texto)')} aria-live="polite">
	<div class="cover"><Cover {song} awake /></div>
	<div class="bill">
		<p class="label">{t.nowSingingLabel}</p>
		<p class="name">{guest?.name ?? ''}</p>
		<p class="song"><SongTitle title={song.title} /></p>
		{#if song.artist}<p class="artist">{song.artist}</p>{/if}
		{#if countdown !== null}
			<div class="go">
				<Button variant="primary" size="l" icon="play" onclick={onstart}>{t.startNow}</Button>
				<Button size="l" icon="skip" onclick={onskip}>{t.skip}</Button>
			</div>
		{/if}
	</div>
	{#if countdown !== null}
		<span class="count data" role="timer" aria-label={t.startsIn(countdown)}>{countdown}</span>
	{/if}
</section>

<style>
	.up-next {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto;
		gap: var(--s-7);
		align-items: center;
	}

	.cover {
		width: min(38vh, 26vw);
	}

	.bill {
		display: grid;
		justify-items: start;
		gap: var(--s-2);
		min-width: 0;
	}

	/* "Now" is lit. */
	.label {
		font-size: 2rem;
		font-weight: 650;
		color: var(--ouro);
	}

	.name {
		max-width: 100%;
		font-family: var(--font-display);
		font-size: min(12vw, 21vh);
		font-weight: 700;
		line-height: 0.86;
		color: var(--who);
		overflow-wrap: anywhere;
	}

	.song {
		max-width: 100%;
		margin-top: var(--s-3);
		font-family: var(--font-display);
		font-size: 3.5rem;
		font-weight: 650;
		line-height: 1;
	}

	.artist {
		font-size: 1.9rem;
		color: var(--texto-2);
	}

	.go {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--s-4);
		margin-top: var(--s-5);
	}

	/* The countdown in dots of light, readable from the sofa. */
	.count {
		align-self: center;
		min-width: 2ch;
		font-size: min(30vh, 17vw);
		line-height: 0.8;
		text-align: right;
		color: var(--ouro);
	}
</style>
