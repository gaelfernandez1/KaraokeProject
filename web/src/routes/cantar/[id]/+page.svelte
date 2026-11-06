<script lang="ts">
	/*
	 * The player: the song's stage over the whole screen, with controls that step aside while
	 * singing. `?t=12.5` freezes the lyrics at that moment without sound (for screenshots and
	 * tests), and `&controis` keeps the controls showing.
	 */
	import SongTitle from '#lib/poster/SongTitle.svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { ApiError, getDoc, mediaUrl } from '#lib/api';
	import { explain } from '#lib/devices/explain.js';
	import { jobs } from '#lib/create/jobs.svelte.js';
	import type { KaraokeDoc, PlaybackClock } from '#lib/contracts';
	import { i18n } from '#lib/i18n';
	import { DEFAULT_THEME, THEMES } from '#lib/lyrics';
	import { playerAction } from '#lib/player/keys.js';
	import {
		canFullscreen,
		isFullscreen,
		keepAwake,
		setMediaSession,
		toggleFullscreen
	} from '#lib/player/platform.js';
	import { lineSeek, lineSegments } from '#lib/player/seek.js';
	import SeekBar from '#lib/player/SeekBar.svelte';
	import { PlayerSession } from '#lib/player/session.svelte.js';
	import SoundPanel from '#lib/player/SoundPanel.svelte';
	import Stage from '#lib/player/Stage.svelte';
	import Poster from '#lib/poster/Poster.svelte';
	import { summaryOf } from '#lib/poster/summary.js';
	import { settings, updateSettings } from '#lib/settings/settings.svelte.js';
	import Button from '#lib/ui/Button.svelte';
	import { formatDuration, transitionName } from '#lib/ui/format.js';

	const id = $derived(page.params.id ?? '');
	const frozenAt = page.url.searchParams.has('t') ? Number(page.url.searchParams.get('t')) : null;
	const pinnedControls = page.url.searchParams.has('controis');
	/** Phones: no full-screen button (iPhone cannot), more room for the title. */
	const touch = matchMedia('(hover: none) and (pointer: coarse)').matches;

	let doc = $state.raw<KaraokeDoc | null>(null);
	let missing = $state(false);
	let loadError = $state<string | null>(null);
	let panelOpen = $state(false);
	let idle = $state(false);
	let fullscreen = $state(false);
	let notice = $state<string | null>(null);
	let root = $state<HTMLElement | null>(null);
	let controlsHeight = $state(0);

	const session = new PlayerSession();
	const clock: PlaybackClock = frozenAt === null ? session.clock : { now: () => frozenAt };
	const t = $derived(i18n.t.player);
	const theme = $derived(THEMES[settings.theme] ?? THEMES[DEFAULT_THEME]);
	const segments = $derived(doc ? lineSegments(doc) : []);
	const playing = $derived(session.state === 'playing');
	const time = $derived(frozenAt ?? session.time);
	const duration = $derived(session.duration || doc?.duration || 0);
	const started = $derived(
		session.state === 'playing' || session.state === 'paused' || session.state === 'ended'
	);
	const controlsHidden = $derived(playing && idle && !panelOpen && !pinnedControls);

	// Load the lyrics, then the sound; the sound plays once the singer taps (browsers ask).
	$effect(() => {
		const songId = id;
		doc = null;
		missing = false;
		loadError = null;
		getDoc(songId)
			.then((loaded) => {
				if (songId !== id) return;
				doc = loaded;
				if (frozenAt !== null) return;
				void session.load(
					{
						instrumental: mediaUrl(songId, loaded.audio.instrumental),
						vocals: loaded.audio.vocals ? mediaUrl(songId, loaded.audio.vocals) : null
					},
					{ vocals: settings.vocals, latencyMs: settings.latencyMs }
				);
			})
			.catch((error: unknown) => {
				if (error instanceof ApiError && error.status === 404) missing = true;
				else
					loadError =
						error instanceof ApiError && error.status === 0
							? i18n.t.errors.network
							: i18n.t.errors.generic;
			});
	});

	$effect(() => () => session.destroy());

	// The frame loop: the clock, the video and the controls read from the session.
	$effect(() => {
		let frame = requestAnimationFrame(function loop() {
			session.tick();
			frame = requestAnimationFrame(loop);
		});
		return () => cancelAnimationFrame(frame);
	});

	// The screen stays on while singing.
	$effect(() => {
		if (playing) return keepAwake();
	});

	$effect(() => {
		if (!doc) return;
		return setMediaSession(
			{ title: doc.title, artist: doc.artist, artwork: doc.cover ? mediaUrl(id, doc.cover) : null },
			{
				play: () => void session.play(),
				pause: () => session.pause(),
				previous: () => jumpLine(-1),
				next: () => jumpLine(1),
				seek: (s) => session.seek(s)
			}
		);
	});

	// Controls hide after a few seconds without the pointer or the keys moving.
	let idleTimer: ReturnType<typeof setTimeout> | undefined;
	function wake() {
		idle = false;
		clearTimeout(idleTimer);
		idleTimer = setTimeout(() => (idle = true), 3000);
	}
	$effect(() => {
		wake();
		return () => clearTimeout(idleTimer);
	});

	function jumpLine(direction: 1 | -1) {
		if (!doc) return;
		const target = lineSeek(doc, session.time, direction);
		if (target !== null) session.seek(target);
	}

	async function toggleScreen() {
		if (root) await toggleFullscreen(root);
		fullscreen = isFullscreen();
	}

	function onKey(event: KeyboardEvent) {
		const target = event.target instanceof Element ? event.target : document.body;
		if (
			target.closest('input, textarea, select, button, a, [role="radio"]') &&
			event.key !== 'Escape'
		)
			return;
		const action = playerAction(event);
		if (!action) return;
		event.preventDefault();
		wake();
		switch (action) {
			case 'toggle':
				return session.toggle();
			case 'back5':
				return session.skip(-5);
			case 'forward5':
				return session.skip(5);
			case 'prevLine':
				return jumpLine(-1);
			case 'nextLine':
				return jumpLine(1);
			case 'vocalsDown':
				return session.setVocals(session.vocals - 0.1);
			case 'vocalsUp':
				return session.setVocals(session.vocals + 0.1);
			case 'pitchDown':
				return session.setPitch(session.pitch - 1);
			case 'pitchUp':
				return session.setPitch(session.pitch + 1);
			case 'fullscreen':
				return toggleScreen();
			case 'exit':
				if (panelOpen) panelOpen = false;
				else if (!isFullscreen()) void goto(resolve('/'));
		}
	}

	/** A tap on the stage shows the controls on touch screens; a click plays or pauses. */
	function onStage(event: PointerEvent) {
		if (event.pointerType === 'touch' && controlsHidden) {
			wake();
			return;
		}
		if (session.state === 'playing' || session.state === 'paused') void session.toggle();
		wake();
	}

	async function exportVideo(aspect: '16:9' | '9:16') {
		try {
			await jobs.startExport(id, { aspect, theme: settings.theme });
			notice = t.videoStarted;
		} catch (error) {
			notice = explain(error, i18n.t.errors.generic, i18n.t);
		}
		setTimeout(() => (notice = null), 5000);
	}

	function setLatency(ms: number) {
		updateSettings({ latencyMs: ms });
		session.setLatencyMs(ms);
	}
</script>

<svelte:head
	><title>{doc ? `${doc.title} · Proxecto Karaoke en Galego` : 'Proxecto Karaoke en Galego'}</title
	></svelte:head
>
<svelte:window onkeydown={onKey} onpointermove={wake} />
<svelte:document onfullscreenchange={() => (fullscreen = isFullscreen())} />

<div
	class="player"
	class:hide-controls={controlsHidden}
	class:panel-open={panelOpen}
	class:singing={playing}
	style:--controls-h="{controlsHeight}px"
	bind:this={root}
	data-state={session.state}
	data-time={time.toFixed(2)}
>
	{#if doc}
		<div class="stage-box">
			<Stage
				{doc}
				songId={id}
				{theme}
				{clock}
				onvideo={(video) => session.attachVideo(video)}
				transition={transitionName(id)}
				lyricsInset={playing ? 0 : controlsHeight}
				showLyrics={frozenAt !== null ||
					session.state === 'playing' ||
					session.state === 'paused' ||
					session.state === 'ended'}
			/>
			<!-- It never takes the focus: a focused button would swallow the player's keys. -->
			<button
				class="hit"
				type="button"
				tabindex="-1"
				aria-hidden="true"
				onpointerdown={(event) => event.preventDefault()}
				onpointerup={onStage}
			></button>
		</div>

		<header class="top controls">
			<Button variant="ghost" iconOnly icon="back" href={resolve('/')}>{i18n.t.common.back}</Button>
			<div class="title">
				<h1><SongTitle title={doc.title} /></h1>
				{#if doc.artist}<p>{doc.artist}</p>{/if}
			</div>
			<Button variant="ghost" iconOnly icon="edit" href={resolve('/editar/[id]', { id })}
				>{t.edit}</Button
			>
			<Button
				variant="ghost"
				iconOnly
				icon="sound"
				aria-expanded={panelOpen}
				onclick={() => (panelOpen = !panelOpen)}>{t.sound}</Button
			>
			{#if canFullscreen() && !touch}
				<Button
					variant="ghost"
					iconOnly
					icon={fullscreen ? 'exitFullscreen' : 'fullscreen'}
					onclick={toggleScreen}>{fullscreen ? t.exitFullscreen : t.fullscreen}</Button
				>
			{/if}
		</header>

		{#if frozenAt === null && session.state !== 'playing' && session.state !== 'paused'}
			<div class="center">
				{#if session.state === 'error'}
					<p class="message" role="alert">{i18n.t.errors[session.error ?? 'audioLoad']}</p>
					<!-- A stuck audio output needs a new audio context: the page starts over. -->
					<Button
						variant="primary"
						size="l"
						icon="loop"
						onclick={() => (session.error === 'audioStalled' ? location.reload() : session.retry())}
						>{i18n.t.common.retry}</Button
					>
				{:else if session.state === 'ended'}
					<Button
						variant="primary"
						size="l"
						icon="play"
						onclick={() => {
							session.seek(0);
							void session.play();
						}}>{t.again}</Button
					>
					<Button href={resolve('/')}>{t.toLibrary}</Button>
				{:else}
					<!-- The song's poster, before the first note. -->
					<div class="start-poster"><Poster song={summaryOf(id, doc)} /></div>
					<Button
						variant="primary"
						size="l"
						icon="play"
						class="sing"
						disabled={session.state !== 'ready'}
						onclick={() => session.play()}
					>
						{session.state === 'ready' ? t.sing : i18n.t.common.loading}
					</Button>
				{/if}
			</div>
		{/if}

		<footer class="bottom controls" aria-label={t.controls} bind:clientHeight={controlsHeight}>
			<SeekBar {time} {duration} {segments} label={t.position} onseek={(s) => session.seek(s)} />
			<div class="transport">
				<span class="clock num">{formatDuration(time)}</span>
				<div class="buttons">
					<Button
						variant="ghost"
						iconOnly
						icon="back5"
						class={started ? '' : 'unstarted'}
						onclick={() => session.skip(-5)}>{t.back5}</Button
					>
					<Button
						variant="primary"
						iconOnly
						size="l"
						icon={playing ? 'pause' : 'play'}
						class="play {session.state === 'playing' || session.state === 'paused'
							? ''
							: 'unstarted'}"
						disabled={session.state === 'loading' || session.state === 'error'}
						onclick={() => session.toggle()}>{playing ? t.pause : t.play}</Button
					>
					<Button
						variant="ghost"
						iconOnly
						icon="forward5"
						class={started ? '' : 'unstarted'}
						onclick={() => session.skip(5)}>{t.forward5}</Button
					>
				</div>
				<span class="clock end num">{formatDuration(duration)}</span>
			</div>
		</footer>

		{#if panelOpen}
			<div class="panel-box">
				<SoundPanel
					{session}
					{doc}
					songId={id}
					themeId={settings.theme}
					latencyMs={settings.latencyMs}
					ontheme={(themeId) => updateSettings({ theme: themeId })}
					onlatency={setLatency}
					onexport={exportVideo}
					onclose={() => (panelOpen = false)}
				/>
			</div>
		{/if}

		{#if notice}<p class="notice" role="status">{notice}</p>{/if}
	{:else if missing}
		<div class="center static">
			<p class="message">{t.notFound}</p>
			<Button variant="primary" href={resolve('/')}>{t.toLibrary}</Button>
		</div>
	{:else if loadError}
		<div class="center static">
			<p class="message" role="alert">{loadError}</p>
			<Button variant="primary" onclick={() => location.reload()}>{i18n.t.common.retry}</Button>
		</div>
	{/if}
</div>

<style>
	.player {
		position: fixed;
		inset: 0;
		display: grid;
		grid-template-rows: auto 1fr auto;
		/* A long title must not widen the screen: it is cut instead. */
		grid-template-columns: minmax(0, 1fr);
		background: var(--noite);
		overflow: hidden;
	}

	.player.hide-controls {
		cursor: none;
	}

	.stage-box {
		position: absolute;
		inset: 0;
	}

	/* On wide screens the panel sits beside the lyrics instead of over them. */
	@media (min-width: 60em) {
		.panel-open .stage-box {
			right: min(24rem, 100%);
		}
	}

	.hit {
		position: absolute;
		inset: 0;
		border: 0;
		background: transparent;
		cursor: inherit;
	}

	.controls {
		position: relative;
		z-index: 2;
		transition:
			opacity var(--dur-2) var(--ease),
			transform var(--dur-2) var(--ease);
	}

	.hide-controls .controls {
		opacity: 0;
		pointer-events: none;
	}

	.hide-controls .top {
		transform: translateY(-0.5rem);
	}

	.hide-controls .bottom {
		transform: translateY(0.5rem);
	}

	.top {
		grid-row: 1;
		display: flex;
		align-items: center;
		gap: var(--s-2);
		padding: max(var(--s-3), env(safe-area-inset-top)) var(--s-3) var(--s-6);
		background: linear-gradient(to bottom, rgb(22 18 46 / 0.75), transparent);
	}

	.title {
		flex: 1;
		min-width: 0;
		padding-inline: var(--s-2);
	}

	.title h1 {
		font-family: var(--font-display);
		font-size: var(--t-2);
		font-weight: 900;
		line-height: 1;
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		overflow: hidden;
	}

	.title p {
		font-size: var(--t--1);
		color: var(--papel-suave);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.bottom {
		grid-row: 3;
		padding: var(--s-7) var(--page-x) max(var(--s-3), env(safe-area-inset-bottom));
		background: linear-gradient(to top, var(--noite) 35%, transparent);
	}

	/* A big screen (the TV, or a laptop in full screen) is seen from further away: bigger
	   controls, inside the TV's safe area. */
	@media (min-width: 1800px) {
		.player {
			--t--1: 1.5rem;
			--t-0: 1.75rem;
			--t-2: 2.6rem;
			--target: 4rem;
		}

		.top {
			padding: var(--safe-y) var(--safe-x) var(--s-6);
		}

		.bottom {
			padding: var(--s-7) var(--safe-x) var(--safe-y);
		}

		.buttons :global(.play) {
			width: 5rem;
			min-height: 5rem;
		}
	}

	.panel-open .bottom {
		padding-right: max(var(--page-x), min(24rem, 100%));
	}

	@media (max-width: 59.99em) {
		.panel-open .bottom {
			padding-right: var(--page-x);
		}
	}

	.transport {
		display: grid;
		grid-template-columns: 1fr auto 1fr;
		align-items: center;
	}

	.buttons {
		display: flex;
		align-items: center;
		gap: var(--s-4);
	}

	.clock {
		font-variant-numeric: tabular-nums;
		font-size: var(--t--1);
		font-weight: 600;
		color: var(--papel-suave);
	}

	.clock.end {
		justify-self: end;
	}

	.buttons :global(.play) {
		width: 4rem;
		min-height: 4rem;
	}

	/* Before the first play, the poster's own button starts the song: one main action. */
	.buttons :global(.unstarted) {
		visibility: hidden;
	}

	.center {
		position: absolute;
		inset: 0 0 var(--controls-h);
		z-index: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--s-4);
		pointer-events: none;
		padding: var(--page-x);
		text-align: center;
	}

	.center > :global(*) {
		pointer-events: auto;
	}

	.center :global(.sing) {
		min-width: 12rem;
		min-height: 4rem;
		font-size: var(--t-2);
	}

	.start-poster {
		width: min(78vw, 46vh, 26rem);
		margin-bottom: var(--s-3);
	}

	.message {
		max-width: 30rem;
		font-size: var(--t-1);
		font-weight: 600;
	}

	.panel-box {
		position: absolute;
		z-index: 3;
		inset: 0 0 0 auto;
		display: flex;
		max-width: 100%;
	}

	/* Phones: the panel is a sheet over the lower part of the screen. */
	@media (max-width: 59.99em) {
		.panel-box {
			inset: auto 0 0 0;
			max-height: 70dvh;
		}

		.panel-box :global(.panel) {
			width: 100%;
			border-left: 0;
			border-top: 1px solid var(--linha);
			border-radius: 16px 16px 0 0;
		}
	}

	.notice {
		position: absolute;
		z-index: 4;
		left: 50%;
		bottom: 9rem;
		transform: translateX(-50%);
		padding: var(--s-3) var(--s-5);
		border-radius: var(--radius-control);
		background: var(--papel);
		color: var(--noite);
		font-weight: 700;
	}
</style>
