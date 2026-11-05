<script lang="ts">
	/*
	 * A karaoke (or video) being made: its title fills with the sung colour as the job goes on,
	 * the stage in words underneath. Done, it offers to sing; failed, it says why.
	 */
	import { resolve } from '$app/paths';
	import { mediaUrl, type Job } from '#lib/api';
	import { i18n } from '#lib/i18n';
	import Button from '#lib/ui/Button.svelte';
	import SungText from '#lib/ui/SungText.svelte';
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
</script>

<article
	class="job"
	class:failed={job.stage === 'error'}
	aria-busy={running}
	style:--p={progress ?? last}
>
	<SungText text={job.title} progress={progress ?? last} as="h3" class="job-title" />
	<p class="stage" aria-live="polite">
		{job.kind === 'export' && job.stage === 'video' ? i18n.t.player.makeVideo : t.stages[job.stage]}
		{#if running}<span class="elapsed num">{formatDuration(elapsed)}</span>{/if}
	</p>
	{#if job.stage === 'error'}
		<p class="error">{job.error ?? t.failed}</p>
	{/if}
	<div class="actions">
		{#if running}
			<Button variant="ghost" icon="close" onclick={() => jobs.cancel(job.id)}>{t.cancelJob}</Button
			>
		{:else if job.stage === 'done' && job.kind === 'make' && job.song_id}
			<Button variant="primary" icon="play" href={resolve('/cantar/[id]', { id: job.song_id })}
				>{t.singNow}</Button
			>
		{:else if job.stage === 'done' && job.kind === 'export' && job.song_id && job.file}
			<Button variant="primary" icon="download" href={mediaUrl(job.song_id, job.file)} download
				>{i18n.t.player.downloads}</Button
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
	/* A strip of paper whose bottom edge fills with the sung colour as the karaoke is made. */
	.job {
		position: relative;
		display: grid;
		gap: var(--s-1);
		padding: var(--s-4) var(--s-4) var(--s-4) var(--s-5);
		background: var(--noite-alta);
	}

	.job::after {
		content: '';
		position: absolute;
		inset: auto 0 0 0;
		height: 5px;
		background: var(--farol);
		transform-origin: left;
		transform: scaleX(var(--p));
		transition: transform var(--dur-2) linear;
	}

	.failed::after {
		background: var(--erro);
	}

	.job :global(.job-title) {
		font-family: var(--font-display);
		font-size: var(--t-3);
		font-weight: 900;
		line-height: 1.05;
	}

	.stage {
		display: flex;
		gap: var(--s-3);
		align-items: baseline;
		color: var(--papel-suave);
		font-weight: 600;
	}

	.elapsed {
		font-variant-numeric: tabular-nums;
		font-weight: 400;
	}

	.error {
		color: var(--erro);
	}

	.actions {
		display: flex;
		align-items: center;
		gap: var(--s-2);
		margin-top: var(--s-2);
	}

	.actions > :global(:last-child) {
		margin-left: auto;
	}
</style>
