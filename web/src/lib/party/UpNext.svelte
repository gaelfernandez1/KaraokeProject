<script lang="ts">
	/*
	 * Between songs on the TV: the next song's poster, who sings it (big, in their colour) and a
	 * countdown big enough to read across the room, like the bill outside a festival stage.
	 */
	import SongTitle from '#lib/poster/SongTitle.svelte';
	import type { SongSummary } from '#lib/api';
	import { i18n } from '#lib/i18n';
	import Poster from '#lib/poster/Poster.svelte';
	import Button from '#lib/ui/Button.svelte';
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

<section class="up-next" style:--who={guest?.color ?? 'var(--papel)'} aria-live="polite">
	<div class="poster"><Poster {song} /></div>
	<div class="bill">
		<p class="label">{t.nowSingingLabel}</p>
		<p class="name">{guest?.name ?? ''}</p>
		<p class="song"><SongTitle title={song.title} bare /></p>
		{#if song.artist}<p class="artist">{song.artist}</p>{/if}
		{#if countdown !== null}
			<div class="go">
				<Button variant="primary" size="l" icon="play" onclick={onstart}>{t.startNow}</Button>
				<Button variant="ghost" size="l" icon="skip" onclick={onskip}>{t.skip}</Button>
			</div>
		{/if}
	</div>
	<span class="count num" aria-label={countdown === null ? undefined : t.startsIn(countdown)}
		>{countdown ?? ''}</span
	>
</section>

<style>
	.up-next {
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 0.75fr) minmax(0, 1fr) auto;
		gap: var(--s-8);
		align-items: center;
		height: 100%;
	}

	/* The singer's colour as a hard band along the bottom of the screen, like a stage edge. */
	.up-next::after {
		content: '';
		position: absolute;
		inset: auto calc(-1 * var(--safe-x)) calc(-1 * var(--safe-y));
		height: 14px;
		background: var(--who);
	}

	.poster {
		width: min(100%, 62vh);
		justify-self: end;
	}

	.bill {
		display: grid;
		gap: var(--s-2);
		min-width: 0;
	}

	.label {
		font-size: 2rem;
		font-weight: 700;
		color: var(--papel-suave);
	}

	.name {
		font-family: var(--font-display);
		font-size: clamp(5rem, 11vw, 13rem);
		font-weight: 900;
		line-height: 0.85;
		color: var(--who);
		overflow-wrap: anywhere;
	}

	.song {
		margin-top: var(--s-4);
		font-family: var(--font-display);
		font-size: 3.5rem;
		font-weight: 800;
		line-height: 1;
	}

	.artist {
		font-size: 1.9rem;
		color: var(--papel-suave);
	}

	.go {
		display: flex;
		align-items: center;
		gap: var(--s-4);
		margin-top: var(--s-6);
	}

	/* The countdown, readable from the sofa. */
	.count {
		align-self: end;
		min-width: 1.2ch;
		font-size: 32vh;
		font-weight: 900;
		line-height: 0.8;
		text-align: right;
		color: var(--papel);
	}
</style>
