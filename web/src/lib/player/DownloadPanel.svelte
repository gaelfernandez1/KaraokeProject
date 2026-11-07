<script lang="ts">
	/*
	 * What the singer can take away from a song: its karaoke video (made here and followed live,
	 * then kept to download any time), its sound and lyrics, and a copy on this device for
	 * singing offline. Every file is named after the song.
	 */
	import { deleteExport, downloadUrl, listExports, mediaUrl, type Export } from '#lib/api';
	import type { KaraokeDoc } from '#lib/contracts';
	import { jobs } from '#lib/create/jobs.svelte.js';
	import { isRunning, overallProgress } from '#lib/create/stages.js';
	import { explain } from '#lib/devices/explain.js';
	import { owner } from '#lib/devices/owner.svelte.js';
	import PairingNotice from '#lib/devices/PairingNotice.svelte';
	import { i18n } from '#lib/i18n';
	import { THEMES } from '#lib/lyrics';
	import { saved } from '#lib/offline/saved.svelte.js';
	import { summaryOf } from '#lib/poster/summary.js';
	import Button from '#lib/ui/Button.svelte';
	import Icon from '#lib/ui/Icon.svelte';
	import { formatBytes } from '#lib/ui/format.js';
	import Slider from '#lib/ui/Slider.svelte';
	import { downloadName, videoName } from './downloads';
	import PlayerPanel from './PlayerPanel.svelte';

	interface Props {
		doc: KaraokeDoc;
		songId: string;
		themeId: string;
		onclose: () => void;
	}

	let { doc, songId, themeId, onclose }: Props = $props();

	const t = $derived(i18n.t.player);
	const lib = $derived(i18n.t.library);

	let videos = $state<Export[] | null>(null);
	let failure = $state<string | null>(null);
	/** The video whose deletion is being confirmed. */
	let confirming = $state<string | null>(null);
	let saveError = $state<string | null>(null);
	const saving = $derived(saved.progress[songId]);
	/** The guide vocals in the next video: none (a karaoke) unless the singer wants them. */
	let videoVocals = $state(0);
	/** A video asked for and not yet answered: the buttons wait, so one press is one video. */
	let starting = $state(false);

	const exportsOfSong = $derived(
		jobs.list.filter((job) => job.kind === 'export' && job.song_id === songId)
	);
	const making = $derived(exportsOfSong.filter(isRunning));
	const finished = $derived(exportsOfSong.filter((job) => job.stage === 'done').length);

	async function load() {
		try {
			videos = await listExports(songId);
		} catch (error) {
			failure = explain(error, i18n.t.errors.generic, i18n.t);
		}
	}

	// On opening, and again each time one of this song's videos is finished.
	$effect(() => {
		void finished;
		void load();
	});

	$effect(() => {
		void jobs.refresh();
		void owner.refresh();
	});

	async function make(aspect: Export['aspect']) {
		failure = null;
		starting = true;
		try {
			await jobs.startExport(songId, { aspect, theme: themeId, vocals: videoVocals });
		} catch (error) {
			failure = explain(error, i18n.t.errors.generic, i18n.t);
		} finally {
			starting = false;
		}
	}

	async function remove(video: Export) {
		failure = null;
		try {
			await deleteExport(songId, video.file);
		} catch (error) {
			failure = explain(error, i18n.t.errors.generic, i18n.t);
		}
		confirming = null;
		await load();
	}

	async function saveOffline() {
		saveError = null;
		const reason = await saved.save(summaryOf(songId, doc));
		if (reason === 'quota') saveError = lib.saveQuota;
		else if (reason === 'network') saveError = lib.saveNetwork;
		else if (reason === 'insecure') saveError = i18n.t.settings.storageInsecure;
	}

	const themeName = (id: string) => THEMES[id]?.name ?? id;
	const percent = (level: number) => Math.round(level * 100);
	const vocalsText = (level: number) =>
		level > 0 ? t.videoVocalsLevel(percent(level)) : t.videoVocalsNone;
	const words = $derived({
		wide: t.fileKaraoke,
		tall: t.fileKaraokeTall,
		vocals: t.fileVocalsLevel
	});
	const day = (iso: string) =>
		new Intl.DateTimeFormat(i18n.locale, { day: 'numeric', month: 'long' }).format(new Date(iso));

	const files = $derived(
		[
			{ label: t.downloadInstrumental, file: doc.audio.instrumental, what: t.fileInstrumental },
			{ label: t.downloadVocals, file: doc.audio.vocals, what: t.fileVocals },
			{ label: t.downloadLyrics, file: 'karaoke.json', what: undefined }
		].flatMap(({ label, file, what }) =>
			file ? [{ label, file, name: downloadName(doc, file, what) }] : []
		)
	);
</script>

<PlayerPanel title={t.download} {onclose}>
	<section aria-labelledby="video-title">
		<h3 id="video-title">{t.videoTitle}</h3>
		<p class="hint">{t.videoHint(themeName(themeId))}</p>

		{#each making as job (job.id)}
			{@const progress = overallProgress(job) ?? 0}
			{@const waiting = job.stage === 'queued'}
			<div class="making">
				<!-- Waiting is not «0 %»: the graphics card makes one thing at a time. -->
				<p>{waiting ? i18n.t.create.stages.queued : t.videoMaking}</p>
				<div
					class="bar"
					role="progressbar"
					aria-label={t.videoMaking}
					aria-valuemin={0}
					aria-valuemax={100}
					aria-valuenow={Math.round(progress * 100)}
					style:--p={progress}
				></div>
				<span class="num">{waiting ? '' : `${Math.round(progress * 100)} %`}</span>
				<Button variant="ghost" iconOnly icon="close" onclick={() => jobs.cancel(job.id)}
					>{i18n.t.create.cancelJob}</Button
				>
			</div>
		{/each}

		{#if videos?.length}
			<ul class="videos">
				{#each videos as video (video.file)}
					{@const tall = video.aspect === '9:16'}
					{@const name = videoName(doc, video.file, words)}
					<li class="video">
						<div class="thumb" class:tall aria-hidden="true">
							{#if video.thumbnail}
								<img src={mediaUrl(songId, video.thumbnail)} alt="" loading="lazy" />
							{:else}
								<Icon name={tall ? 'remote' : 'tv'} size={1.5} />
							{/if}
						</div>
						<div class="about">
							<p class="what">
								{tall ? t.videoTallShort : t.videoWideShort} · {themeName(video.theme)} · {vocalsText(
									video.vocals
								)}
							</p>
							<p class="meta">
								<span class="num">{formatBytes(video.size, i18n.locale)}</span> · {day(
									video.created_at
								)}
							</p>
							{#if video.outdated}<p class="outdated">{t.videoOutdated}</p>{/if}
						</div>
						<div class="actions">
							<Button
								variant="primary"
								icon="download"
								href={downloadUrl(songId, video.file, name)}
								download={name}>{t.videoDownload}</Button
							>
							{#if owner.isOwner}
								{#if confirming === video.file}
									<Button variant="danger" icon="trash" onclick={() => remove(video)}
										>{t.videoDeleteYes}</Button
									>
									<Button onclick={() => (confirming = null)}>{i18n.t.common.cancel}</Button>
								{:else}
									<Button
										variant="ghost"
										iconOnly
										icon="trash"
										onclick={() => (confirming = video.file)}>{t.videoDelete}</Button
									>
								{/if}
							{/if}
						</div>
					</li>
				{/each}
			</ul>
		{:else if videos && making.length === 0}
			<p class="empty">{t.videoNone}</p>
		{/if}

		{#if owner.isOwner}
			<h4>{t.makeVideo}</h4>
			<div class="vocals">
				<Slider
					label={t.videoVocals}
					value={videoVocals}
					step={0.05}
					format={(level) => (level > 0 ? `${percent(level)} %` : t.videoVocalsNone)}
					oninput={(level) => (videoVocals = level)}
				/>
				<p class="hint">{t.videoVocalsHint}</p>
			</div>
			<div class="make">
				<Button icon="tv" disabled={starting} onclick={() => make('16:9')}>{t.videoWide}</Button>
				<Button icon="remote" disabled={starting} onclick={() => make('9:16')}>{t.videoTall}</Button
				>
			</div>
		{:else if owner.me}
			<PairingNotice text={t.videoOwnerOnly} />
		{/if}
		{#if failure}<p class="hint error" role="alert">{failure}</p>{/if}
	</section>

	<section aria-labelledby="files-title">
		<h3 id="files-title">{t.soundAndLyrics}</h3>
		<ul class="files">
			{#each files as f (f.file)}
				<li>
					<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- a file to download, not a page -->
					<a href={downloadUrl(songId, f.file, f.name)} download={f.name}>
						<Icon name="download" size={1.2} />{f.label}
					</a>
				</li>
			{/each}
		</ul>
		{#if saved.available}
			<div class="offline">
				{#if saved.has(songId)}
					<p class="saved-note">{lib.savedOffline}</p>
					<Button variant="ghost" icon="trash" onclick={() => saved.remove(songId)}
						>{lib.removeOffline}</Button
					>
				{:else if saving !== undefined}
					<Button icon="offline" disabled>{lib.saving(Math.round(saving * 100))}</Button>
				{:else}
					<Button icon="offline" onclick={saveOffline}>{lib.saveOffline}</Button>
				{/if}
				{#if saveError}<p class="hint error">{saveError}</p>{/if}
			</div>
		{/if}
	</section>
</PlayerPanel>

<style>
	section {
		display: grid;
		gap: var(--s-2);
	}

	h3 {
		font-size: var(--t--1);
		font-weight: 700;
		color: var(--papel-suave);
	}

	h4 {
		margin-top: var(--s-3);
		font-size: var(--t--1);
		font-weight: 700;
		color: var(--papel-suave);
	}

	.hint,
	.empty {
		font-size: var(--t--1);
		color: var(--papel-suave);
	}

	.empty {
		padding: var(--s-3) 0;
		font-style: italic;
	}

	.error {
		color: var(--erro);
	}

	/* A video being made: its bar fills with the sung colour, as the jobs on the create page. */
	.making {
		display: grid;
		grid-template-columns: 1fr auto auto;
		align-items: center;
		gap: var(--s-1) var(--s-3);
		font-weight: 700;
	}

	.making p {
		grid-column: 1 / -1;
	}

	.bar {
		height: 0.5rem;
		border-radius: 999px;
		background: linear-gradient(
			to right,
			var(--farol) calc(var(--p) * 100%),
			var(--linha) calc(var(--p) * 100%)
		);
		transition: background 0.4s;
	}

	.videos,
	.files {
		display: grid;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.videos {
		gap: var(--s-4);
		margin-top: var(--s-2);
	}

	.video {
		display: grid;
		grid-template-columns: 5.5rem 1fr;
		gap: var(--s-2) var(--s-3);
		align-items: start;
	}

	.thumb {
		display: grid;
		place-items: center;
		aspect-ratio: 16 / 9;
		overflow: hidden;
		border-radius: var(--radius-control);
		background: var(--linha);
		color: var(--papel-suave);
	}

	.thumb.tall {
		width: 60%;
		aspect-ratio: 9 / 16;
	}

	.thumb img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.what {
		font-weight: 700;
	}

	.meta {
		font-size: var(--t--1);
		color: var(--papel-suave);
	}

	.outdated {
		margin-top: var(--s-1);
		font-size: var(--t--1);
		font-weight: 700;
		color: var(--farol);
	}

	.actions {
		grid-column: 1 / -1;
		display: flex;
		flex-wrap: wrap;
		gap: var(--s-2);
	}

	.vocals {
		display: grid;
		gap: var(--s-1);
		margin-bottom: var(--s-2);
	}

	.make {
		display: flex;
		flex-wrap: wrap;
		gap: var(--s-2);
	}

	.files {
		gap: var(--s-1);
	}

	.files a {
		display: flex;
		align-items: center;
		gap: var(--s-3);
		min-height: var(--target);
		font-weight: 600;
		text-decoration: none;
	}

	.files a:hover {
		color: var(--farol);
	}

	.offline {
		display: grid;
		justify-items: start;
		gap: var(--s-2);
		margin-top: var(--s-3);
	}

	.saved-note {
		font-weight: 700;
		color: var(--farol);
	}
</style>
