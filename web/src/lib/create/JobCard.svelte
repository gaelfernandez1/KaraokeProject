<script lang="ts">
	/*
	 * A karaoke (or video) being made, as a line of a departures board: the title, the stage as
	 * its status word, and a road of lights that switch on in amber as the job goes on. Done, it
	 * offers to sing; failed, it says why and the lights stop, red, where it fell.
	 *
	 * Laid out on its own; inside a `.job-board` grid (crear) its columns join the board's, so
	 * the meters and the figures of every row fall in line.
	 */
	import { resolve } from '$app/paths';
	import { downloadUrl, type Job } from '#lib/api';
	import { jobError } from '#lib/devices/explain.js';
	import { videoName } from '#lib/player/downloads.js';
	import { i18n } from '#lib/i18n';
	import Button from '#lib/ui/Button.svelte';
	import { formatDuration } from '#lib/ui/format.js';
	import { jobs } from './jobs.svelte';
	import { isRunning, overallProgress } from './stages';

	interface Props {
		job: Job;
	}

	let { job }: Props = $props();

	const t = $derived(i18n.t.create);
	let last = $state(0);
	const progress = $derived(overallProgress(job));
	$effect(() => {
		if (progress !== null) last = progress;
	});

	let now = $state(Date.now());
	$effect(() => {
		if (!isRunning(job)) return;
		const timer = setInterval(() => (now = Date.now()), 1000);
		return () => clearInterval(timer);
	});
	const elapsed = $derived(Math.max(0, (now - Date.parse(job.created_at)) / 1000));
	const running = $derived(isRunning(job));
	const word = $derived(
		job.kind === 'export' && job.stage === 'video' ? i18n.t.player.makeVideo : t.stages[job.stage]
	);
	/** What the status word says about the job: on its way, waiting, done or stopped. */
	const tone = $derived(
		job.stage === 'queued'
			? 'waiting'
			: running
				? 'now'
				: job.stage === 'done'
					? 'done'
					: job.stage === 'error'
						? 'failed'
						: 'stopped'
	);
</script>

<article class="job {tone}" aria-busy={running} style:--p={progress ?? last}>
	<div class="name">
		<h3 class="title">{job.title}</h3>
		<p class="stage" aria-live="polite">
			<span class="word">{word}</span>
			{#if running}
				<span class="elapsed num">{formatDuration(elapsed)}</span>
				{#if job.eta}<span class="eta">{i18n.t.party.wait(Math.ceil(job.eta / 60))}</span>{/if}
			{/if}
		</p>
		{#if job.stage === 'error'}
			<p class="error">{jobError(job, t.failed, i18n.t)}</p>
		{/if}
	</div>
	<span class="meter" aria-hidden="true"></span>
	<span class="figure data">
		{#if running}{Math.round((progress ?? 0) * 100)}<small> %</small>{/if}
	</span>
	<div class="actions">
		{#if running}
			<Button variant="ghost" icon="close" onclick={() => jobs.cancel(job.id)}>{t.cancelJob}</Button
			>
		{:else if job.stage === 'done' && job.kind === 'make' && job.song_id}
			<Button variant="primary" icon="play" href={resolve('/cantar/[id]', { id: job.song_id })}
				>{t.singNow}</Button
			>
		{:else if job.stage === 'done' && job.kind === 'export' && job.song_id && job.file}
			{@const p = i18n.t.player}
			{@const name = videoName({ title: job.title, artist: null }, job.file, {
				wide: p.fileKaraoke,
				tall: p.fileKaraokeTall,
				vocals: p.fileVocalsLevel
			})}
			<Button
				variant="primary"
				icon="download"
				href={downloadUrl(job.song_id, job.file, name)}
				download={name}>{p.videoDownload}</Button
			>
		{:else if (job.stage === 'error' || job.stage === 'cancelled') && jobs.canRetry(job)}
			<Button icon="loop" onclick={() => jobs.retry(job)}>{i18n.t.common.retry}</Button>
		{/if}
		{#if !running}
			<Button variant="ghost" iconOnly icon="close" onclick={() => jobs.dismiss(job.id)}
				>{t.dismiss}</Button
			>
		{/if}
	</div>
</article>

<style>
	/* Phones: the name and the figure, the road of lights across, the actions under it. */
	.job {
		--light: var(--ouro);
		display: grid;
		grid-template-areas:
			'name figure'
			'meter meter'
			'actions actions';
		grid-template-columns: minmax(0, 1fr) auto;
		align-items: center;
		gap: var(--s-2) var(--s-4);
		padding: var(--s-4) var(--s-5);
		border: 1px solid var(--raia);
		border-radius: var(--radius-row);
		background: var(--panel-claro);
	}

	.name {
		grid-area: name;
		display: grid;
		min-width: 0;
	}

	.title {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-family: var(--font-text);
		font-size: var(--t-2);
		font-weight: 650;
		line-height: 1.1;
	}

	.stage {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0 var(--s-3);
		font-size: var(--t--1);
		color: var(--texto-2);
	}

	.word {
		font-weight: 650;
		color: var(--texto);
	}

	.now .word {
		color: var(--ouro);
	}

	.waiting .word,
	.stopped .word {
		color: var(--texto-2);
	}

	.failed .word,
	.error {
		color: var(--erro);
	}

	.error {
		font-size: var(--t--1);
		font-weight: 600;
	}

	/* The road: a track that fills with light from the left as far as the job has gone. A
	   failed job keeps it, red, where it stopped. */
	.meter {
		grid-area: meter;
		position: relative;
		height: 6px;
		overflow: hidden;
		border-radius: var(--radius-pill);
		background: var(--raia);
	}

	.meter::after {
		content: '';
		position: absolute;
		inset: 0;
		border-radius: inherit;
		background: var(--light);
		transform: scaleX(var(--p));
		transform-origin: left;
		transition: transform var(--dur-2) linear;
	}

	.failed {
		--light: var(--erro);
	}

	.stopped {
		--light: var(--raia-forte);
	}

	.figure {
		grid-area: figure;
		min-width: 3.5ch;
		text-align: end;
		font-size: var(--t-1);
		line-height: 1;
		color: var(--ouro);
	}

	.figure small {
		font-size: 0.7em;
	}

	.actions {
		grid-area: actions;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--s-2);
	}

	.actions > :global(:only-child) {
		margin-left: auto;
	}

	/* Wider: one line of the board, name, road, figure and actions side by side. */
	@media (min-width: 45em) {
		.job {
			grid-template-areas: 'name meter figure actions';
			grid-template-columns: minmax(0, 1fr) minmax(6rem, 14rem) 4.5rem auto;
			gap: var(--s-5);
			min-height: 4.5rem;
			padding-block: var(--s-2);
		}

		/* In the board: its columns, so every row's road starts at the same place. */
		:global(.job-board) > .job {
			grid-column: 1 / -1;
			grid-template-columns: subgrid;
		}

		.actions {
			justify-content: end;
		}
	}
</style>
