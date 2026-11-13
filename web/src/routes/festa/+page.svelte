<script lang="ts">
	/*
	 * The party on the TV. The laptop shows this full screen over HDMI: the room code and QR
	 * for the phones, the queue in turn order, the "now singing" card and then the song, with
	 * who is singing in their colour. Everything works from a keyboard or a presentation
	 * clicker; the phones are the remote. On a phone, this page offers to join a party instead.
	 */
	import { splitTitle } from '#lib/poster/fit.js';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { listSongs, serverInfo, type SongSummary } from '#lib/api';
	import { i18n } from '#lib/i18n';
	import { DEFAULT_THEME, THEMES } from '#lib/lyrics';
	import { createParty, getParty, rememberedHost, rememberHost } from '#lib/party/client.js';
	import { HostParty } from '#lib/party/host.svelte.js';
	import { singerColor } from '#lib/party/colors.js';
	import Qr from '#lib/party/Qr.svelte';
	import QueueList from '#lib/party/QueueList.svelte';
	import { guestOf, upcoming, waitEstimate } from '#lib/party/rotation.js';
	import type { PartyCreated, QueueItem } from '#lib/party/types.js';
	import UpNext from '#lib/party/UpNext.svelte';
	import { playerAction } from '#lib/player/keys.js';
	import {
		canFullscreen,
		isFullscreen,
		keepAwake,
		toggleFullscreen
	} from '#lib/player/platform.js';
	import Stage from '#lib/player/Stage.svelte';
	import { summaryOf } from '#lib/poster/summary.js';
	import { settings } from '#lib/settings/settings.svelte.js';
	import { arrowNavigation } from '#lib/tv/focus.js';
	import Button from '#lib/ui/Button.svelte';
	import Slider from '#lib/ui/Slider.svelte';
	import Switch from '#lib/ui/Switch.svelte';
	import Wordmark from '#lib/ui/Wordmark.svelte';
	import { chrome } from '#lib/ui/chrome.svelte.js';
	import { formatCount } from '#lib/ui/format.js';
	import GlobeAnchor from '#lib/globe/GlobeAnchor.svelte';
	import { LIGHTS, PEOPLE } from '#lib/globe/galicia.js';
	import { stage } from '#lib/globe/stage.svelte.js';
	import { onDestroy } from 'svelte';

	const LAST_KEY = 'foliada.party-last';
	/** A phone that opens /festa wants to join a party, not to host one. */
	const touch = matchMedia('(hover: none) and (pointer: coarse)').matches;

	let host = $state.raw<HostParty | null>(null);
	let resumable = $state<PartyCreated | null>(null);
	let baseUrl = $state(location.origin);
	/** Whether phones can open that address (not while WSL keeps the laptop off the Wi-Fi). */
	let reachable = $state(true);
	let failure = $state<string | null>(null);
	let fullscreen = $state(false);
	let idle = $state(false);
	let now = $state(Date.now());
	let root = $state<HTMLElement | null>(null);
	let songs = $state.raw<SongSummary[]>([]);
	let code = $state('');
	let showSettings = $state(false);
	const globeLabel = $derived(i18n.t.home.globe(formatCount(PEOPLE), formatCount(LIGHTS)));

	const t = $derived(i18n.t.party);
	const theme = $derived(THEMES[settings.theme] ?? THEMES[DEFAULT_THEME]);
	const party = $derived(host?.state ?? null);
	const queue = $derived(party ? upcoming(party) : []);
	const waits = $derived(party ? waitEstimate(party, now) : new Map<string, number>());
	const joinUrl = $derived(host ? `${baseUrl}/festa/${host.code}` : '');
	const singer = $derived(party && host?.current ? guestOf(party, host.current) : undefined);
	/** Songs already sung or skipped: they stay on the board, struck through. */
	const past = $derived(
		party ? party.queue.filter((item) => item.state === 'done' || item.state === 'skipped') : []
	);
	const nextUp = $derived(host?.phase === 'singing' ? queue[0] : undefined);
	/** Before the first line, the TV also says what song it is. */
	const intro = $derived(
		host?.doc ? host.session.time < (host.doc.lines[0]?.start ?? 0) - 1 : false
	);
	const progress = $derived(
		host && host.session.duration > 0 ? host.session.time / host.session.duration : 0
	);

	// A party on the globe: the lights dance and rockets go up, one for every guest who joins.
	$effect(() => {
		stage.mood = 'party';
	});
	onDestroy(() => {
		stage.mood = 'calm';
	});

	serverInfo()
		.then((info) => {
			baseUrl = info.url;
			reachable = info.home_reachable !== false;
		})
		.catch(() => {});

	// A party this TV was running (the page was reloaded) can be picked up again.
	void (async () => {
		let last: string | null;
		try {
			last = localStorage.getItem(LAST_KEY);
		} catch {
			return;
		}
		const remembered = last ? rememberedHost(last) : null;
		if (!remembered) return;
		try {
			await getParty(remembered.code);
			resumable = remembered;
		} catch {
			// The server forgot it (restarted): start a new one.
		}
	})();

	async function begin(created?: PartyCreated) {
		failure = null;
		try {
			const started = created ?? (await createParty());
			rememberHost(started);
			try {
				localStorage.setItem(LAST_KEY, started.code);
			} catch {
				// Without storage a reload starts a new party.
			}
			const running = new HostParty(started, {
				device: { vocals: settings.vocals, latencyMs: settings.latencyMs }
			});
			running.start();
			host = running;
			listSongs()
				.then((list) => (songs = list))
				.catch(() => {});
		} catch {
			failure = i18n.t.errors.network;
		}
	}

	/** The poster of a queued song: the library's (cover, chorus), else what the queue knows. */
	function posterOf(item: QueueItem): SongSummary {
		if (host?.doc && host.current?.id === item.id) return summaryOf(item.song_id, host.doc);
		return (
			songs.find((song) => song.id === item.song_id) ?? {
				id: item.song_id,
				title: item.title,
				artist: item.artist,
				language: 'gl',
				duration: item.duration,
				cover: null,
				has_video: false,
				created_at: '',
				edited: false,
				lyrics_source: 'user',
				hook: null
			}
		);
	}

	function join(event: SubmitEvent) {
		event.preventDefault();
		const clean = code.trim().toUpperCase();
		if (clean) void goto(resolve('/festa/[code]', { code: clean }));
	}

	$effect(() => {
		const current = host;
		if (!current) return;
		let frame = requestAnimationFrame(function loop() {
			current.frame();
			frame = requestAnimationFrame(loop);
		});
		const clock = setInterval(() => (now = Date.now()), 15_000);
		const release = keepAwake();
		return () => {
			cancelAnimationFrame(frame);
			clearInterval(clock);
			release();
			current.stop();
		};
	});

	$effect(() => {
		if (root && host?.phase !== 'singing') return arrowNavigation(root);
	});

	// The TV takes the whole screen once the party is on; before, the app's navigation stays.
	$effect(() => {
		chrome.immersive = host !== null;
		return () => (chrome.immersive = false);
	});

	// The cursor goes after a moment without moving: nobody wants an arrow on the TV.
	let idleTimer: ReturnType<typeof setTimeout> | undefined;
	let controls = $state(false);
	let controlsTimer: ReturnType<typeof setTimeout> | undefined;
	/** Any movement or key shows the cursor and, while a song plays, its controls for a while. */
	function wake() {
		idle = false;
		clearTimeout(idleTimer);
		idleTimer = setTimeout(() => (idle = true), 2500);
		if (host?.phase === 'singing') {
			controls = true;
			clearTimeout(controlsTimer);
			controlsTimer = setTimeout(() => (controls = false), 4000);
		}
	}

	let confirmingEnd = $state(false);

	/** Stops the party on this TV (the phones see it as finished when the server forgets it). */
	function endParty() {
		confirmingEnd = false;
		void host?.end();
		host = null;
		resumable = null;
		showSettings = false;
		try {
			localStorage.removeItem(LAST_KEY);
		} catch {
			// Nothing to forget.
		}
	}

	async function toggleScreen() {
		// The whole page goes full screen, not just this screen: the globe is drawn behind it.
		if (root) await toggleFullscreen(document.documentElement);
		fullscreen = isFullscreen();
	}

	function onKey(event: KeyboardEvent) {
		wake();
		if (!host) return;
		if (
			host.phase === 'countdown' &&
			event.key === 'Enter' &&
			document.activeElement === document.body
		) {
			host.startNow();
			return;
		}
		if (host.phase !== 'singing') return;
		const action = playerAction(event);
		if (!action) return;
		event.preventDefault();
		const session = host.session;
		if (action === 'toggle') void session.toggle();
		else if (action === 'back5') session.skip(-5);
		else if (action === 'forward5') session.skip(5);
		else if (action === 'nextLine') host.skip();
		else if (action === 'vocalsDown') session.setVocals(session.vocals - 0.1);
		else if (action === 'vocalsUp') session.setVocals(session.vocals + 0.1);
		else if (action === 'pitchDown') void session.setPitch(session.pitch - 1);
		else if (action === 'pitchUp') void session.setPitch(session.pitch + 1);
		else if (action === 'fullscreen') void toggleScreen();
	}
</script>

<svelte:head><title>{t.title} · Karaoke en Galego</title></svelte:head>
<svelte:window onkeydown={onKey} onpointermove={wake} />
<svelte:document onfullscreenchange={() => (fullscreen = isFullscreen())} />

{#snippet globeButton(variant: 'ghost' | 'quiet')}
	<Button
		{variant}
		iconOnly
		icon={stage.still ? 'play' : 'pause'}
		onclick={() => stage.toggleStill()}>{stage.still ? i18n.t.home.play : i18n.t.home.stop}</Button
	>
{/snippet}

{#if !host}
	<main class="start" class:touch>
		<div class="start-text">
			<h1>{t.title}</h1>
			{#if touch}
				<form class="join" onsubmit={join}>
					<label for="code">{t.joinWithCode}</label>
					<input
						id="code"
						class="data"
						bind:value={code}
						maxlength="4"
						autocomplete="off"
						autocapitalize="characters"
						spellcheck="false"
						placeholder="ABCD"
					/>
					<Button variant="primary" size="l" type="submit" disabled={code.trim().length < 4}
						>{t.join}</Button
					>
				</form>
				<Button variant="ghost" icon="party" onclick={() => begin()}>{t.hostHere}</Button>
			{:else}
				<p class="intro">{t.intro}</p>
				<div class="actions">
					{#if resumable}
						<Button
							variant="primary"
							size="l"
							icon="party"
							onclick={() => begin(resumable ?? undefined)}
							>{t.continueParty(resumable.code)}</Button
						>
						<Button size="l" onclick={() => begin()}>{t.newParty}</Button>
					{:else}
						<Button variant="primary" size="l" icon="party" onclick={() => begin()}
							>{t.start}</Button
						>
					{/if}
				</div>
			{/if}
			{#if failure}<p class="error" role="alert">{failure}</p>{/if}
		</div>
		{#if !touch}
			<div class="start-globe">
				<GlobeAnchor label={globeLabel} turnable />
				<div class="still">{@render globeButton('quiet')}</div>
			</div>
		{/if}
	</main>
{:else}
	<div class="tv" class:idle bind:this={root} data-phase={host.phase}>
		{#if host.phase === 'singing' && host.doc && host.current}
			<div class="stage" style:--who={singerColor(singer?.color, 'var(--texto)')}>
				<Stage
					doc={host.doc}
					songId={host.current.song_id}
					{theme}
					clock={host.session.clock}
					onvideo={(video) => host?.session.attachVideo(video)}
					strip={false}
				/>
				{#if intro}
					<!-- The song's intro: the same bill as the countdown, until the first line. -->
					<div class="song-intro">
						<UpNext song={posterOf(host.current)} guest={singer} countdown={null} />
					</div>
				{/if}
				<div class="now">
					{#if !intro}<p class="singer">{singer?.name ?? ''}</p>{/if}
					{#if nextUp && party}
						<p class="next">
							{t.nextChip(guestOf(party, nextUp)?.name ?? '', splitTitle(nextUp.title).main)}
						</p>
					{/if}
				</div>
				{#if !controls}<p class="corner-code data" aria-label={t.code}>{host.code}</p>{/if}
				{#if controls}
					<div class="tv-controls" role="toolbar" aria-label={i18n.t.player.controls}>
						<Button
							variant="primary"
							size="l"
							iconOnly
							icon={host.session.playing ? 'pause' : 'play'}
							onclick={() => host?.session.toggle()}
							>{host.session.playing ? i18n.t.player.pause : i18n.t.player.play}</Button
						>
						<Button size="l" icon="skip" onclick={() => host?.skip()}>{t.skip}</Button>
						<div class="tv-vocals">
							<Slider
								label={t.vocals}
								value={host.session.vocals}
								step={0.05}
								oninput={(v) => host?.session.setVocals(v)}
							/>
						</div>
					</div>
				{/if}
				<span class="hairline" style:--p={progress} aria-hidden="true"></span>
			</div>
		{:else if host.phase === 'countdown' && host.current && party}
			<main class="screen countdown">
				<UpNext
					song={posterOf(host.current)}
					guest={guestOf(party, host.current)}
					countdown={host.countdown}
					onstart={() => host?.startNow()}
					onskip={() => host?.skip()}
				/>
				<section class="board" aria-labelledby="queue-title">
					<h2 id="queue-title" class="visually-hidden">{t.queue}</h2>
					<QueueList
						state={party}
						items={queue}
						{waits}
						size="tv"
						limit={3}
						past={past.slice(-1)}
						current={host.current}
					/>
				</section>
				<p class="corner-code data" aria-label={t.code}>{host.code}</p>
			</main>
		{:else}
			{@const empty = queue.length === 0}
			{#if empty}
				<!-- The night: Galicia's lights, turning behind the lobby until the first request. -->
				<div class="lobby-globe">
					<GlobeAnchor label={globeLabel} turnable />
				</div>
			{/if}
			<main class="screen lobby" class:empty>
				<header class="bar">
					<Wordmark size="3rem" />
					<div class="tools">
						{#if empty}{@render globeButton('ghost')}{/if}
						<Button
							variant="ghost"
							icon="settings"
							aria-expanded={showSettings}
							onclick={() => (showSettings = !showSettings)}>{t.settingsTitle}</Button
						>
						{#if canFullscreen()}
							<Button
								variant="ghost"
								iconOnly
								icon={fullscreen ? 'exitFullscreen' : 'fullscreen'}
								onclick={toggleScreen}>{t.fullscreen}</Button
							>
						{/if}
					</div>
					{#if showSettings}
						<!-- Opens on the globe's side, never over the QR the guests are scanning. -->
						<div class="settings">
							<Switch
								size="l"
								checked={party?.settings.guests_control ?? false}
								label={t.guestsControl}
								onchange={(on) => host?.setGuestsControl(on)}
							/>
							{#if confirmingEnd}
								<!-- Asked here, at TV size: a browser dialog would also drop full screen. -->
								<p class="confirm">{t.endConfirm}</p>
								<div class="confirm-actions">
									<Button variant="primary" size="l" onclick={() => (confirmingEnd = false)}
										>{t.keepParty}</Button
									>
									<Button variant="danger" size="l" onclick={endParty}>{t.endParty}</Button>
								</div>
							{:else}
								<Button size="l" onclick={() => (confirmingEnd = true)}>{t.endParty}</Button>
							{/if}
						</div>
					{/if}
				</header>
				<aside class="join-card">
					{#if empty}<p class="call">{past.length > 0 ? t.attractNext : t.attract}</p>{/if}
					<div class="scan">
						<div class="qr" class:short={!reachable}><Qr text={joinUrl} label={t.scan} /></div>
						<div class="ways">
							<p class="scan-text">{t.scan}</p>
							{#if party}
								<div class="guests">
									<p class="guest-count num">{t.guests(party.guests.length)}</p>
									{#if party.guests.length > 0}
										<ul class="people">
											{#each party.guests as guest (guest.id)}
												<li style:--who={singerColor(guest.color)}>{guest.name}</li>
											{/each}
										</ul>
									{/if}
								</div>
							{/if}
						</div>
					</div>
					<div class="room">
						<p>
							<span class="visually-hidden">{t.code}</span>
							<span class="code data">{host.code}</span>
						</p>
						{#if reachable}
							<p class="url">{t.orOpen(joinUrl.replace(/^https?:\/\//, ''))}</p>
						{:else}
							<!-- The address would not open on a phone: say why instead. -->
							<p class="unreachable" role="status">{t.unreachable}</p>
						{/if}
					</div>
				</aside>
				{#if !empty && party}
					<section class="queue" aria-labelledby="queue-title">
						<h2 id="queue-title">{t.queue}</h2>
						<QueueList
							state={party}
							items={queue}
							{waits}
							size="tv"
							limit={5}
							past={past.slice(-2)}
						/>
					</section>
				{/if}
				{#if party && !host.connection.connected}
					<p class="reconnecting" role="status">{t.reconnecting}</p>
				{/if}
			</main>
		{/if}
	</div>
{/if}

<style>
	/* Ten feet away: nothing under 28 px, bigger targets, a focus you can see from the sofa. */
	.tv {
		--t--1: 1.75rem;
		--t-0: 1.75rem;
		--t-1: 2.1rem;
		--t-2: 2.6rem;
		--target: 4rem;
		position: fixed;
		inset: 0;
		overflow: hidden;
		font-size: var(--t-0);
	}

	.tv :global(:focus-visible) {
		outline: 5px solid var(--ceo);
		outline-offset: 5px;
	}

	.tv.idle,
	.tv.idle :global(*) {
		cursor: none;
	}

	/* Everything sits inside the TV's title-safe area. */
	.screen {
		position: absolute;
		inset: var(--safe-y) var(--safe-x);
	}

	/* Before the party: an ordinary page, with the app's navigation. */
	.start {
		display: grid;
		align-content: start;
		gap: var(--s-6);
		max-width: var(--page-max);
		margin: 0 auto;
		padding: var(--s-8) var(--page-x);
	}

	.start-text {
		display: grid;
		align-content: start;
		justify-items: start;
		gap: var(--s-6);
		min-width: 0;
	}

	.start h1 {
		font-family: var(--font-display);
		font-size: var(--t-7);
		font-weight: 700;
		line-height: 0.85;
	}

	.start.touch {
		padding-top: var(--s-6);
	}

	.start.touch .start-text {
		gap: var(--s-5);
	}

	.start.touch h1 {
		font-size: var(--t-6);
	}

	.intro {
		max-width: 34rem;
		font-size: var(--t-1);
		color: var(--texto-2);
	}

	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: var(--s-3);
	}

	.start-globe {
		position: relative;
		width: min(100%, 60vh);
		justify-self: center;
	}

	.start-globe .still {
		position: absolute;
		right: 0;
		bottom: 0;
	}

	/* Laptop and TV: the words on the left, the night on the right, as on the main menu. */
	@media (min-width: 64em) {
		.start:not(.touch) {
			grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr);
			align-items: center;
			gap: var(--s-8);
			min-height: calc(100dvh - 5rem);
			padding-block: var(--s-6);
		}

		.start-globe {
			width: min(100%, 76vh);
		}
	}

	.join {
		display: grid;
		gap: var(--s-3);
		width: 100%;
	}

	.join label {
		font-weight: 700;
		font-size: var(--t-1);
	}

	/* The code goes in as it shows on the TV: in dots of light. */
	.join input {
		width: 100%;
		min-height: 5.5rem;
		padding: var(--s-2) var(--s-4);
		border: 1px solid var(--raia-forte);
		border-radius: var(--radius-control);
		background: var(--fondo-2);
		font-size: 3.5rem;
		letter-spacing: 0.25em;
		text-transform: uppercase;
		color: var(--texto);
	}

	.join input::placeholder {
		color: color-mix(in oklch, var(--texto-2) 45%, transparent);
	}

	.join input:focus {
		outline: none;
		border-color: var(--ceo);
		box-shadow: inset 0 -3px 0 var(--ceo);
	}

	/* The lobby: the join card on the left, the night (or the board) on the right. */
	.lobby {
		display: grid;
		grid-template-columns: min(46rem, 44%) minmax(0, 1fr);
		grid-template-rows: auto minmax(0, 1fr);
		gap: var(--s-5) var(--s-9);
	}

	.lobby-globe {
		position: absolute;
		right: -10vh;
		bottom: -9vh;
		width: min(100vh, 58vw);
	}

	.bar {
		position: relative;
		z-index: 2;
		grid-column: 1 / -1;
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.tools {
		display: flex;
		align-items: center;
		gap: var(--s-3);
	}

	.settings :global(.switch) {
		font-size: 1.75rem;
	}

	.settings {
		position: absolute;
		top: calc(100% + var(--s-2));
		right: 0;
		display: grid;
		justify-items: start;
		gap: var(--s-4);
		max-width: 44rem;
		padding: var(--s-5);
		background: var(--fondo-2);
		border: 1px solid var(--raia-forte);
	}

	.confirm {
		font-weight: 700;
	}

	.confirm-actions {
		display: flex;
		gap: var(--s-3);
	}

	.join-card {
		grid-column: 1;
		grid-row: 2;
		display: grid;
		align-content: center;
		justify-items: start;
		gap: var(--s-5);
		min-height: 0;
	}

	.call {
		font-family: var(--font-display);
		font-size: min(5.5rem, 9vh);
		font-weight: 700;
		line-height: 0.92;
	}

	.scan {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		align-items: end;
		gap: var(--s-6);
	}

	.qr {
		width: min(34vh, 21vw);
	}

	/* Room for the warning that replaces the address, without pushing the lobby down. */
	.qr.short {
		width: min(28vh, 18vw);
	}

	.ways {
		display: grid;
		align-content: space-between;
		gap: var(--s-5);
		height: 100%;
		min-width: 0;
	}

	.scan-text {
		font-size: 2rem;
		font-weight: 650;
		line-height: 1.2;
	}

	.room {
		display: grid;
		gap: var(--s-3);
		min-width: 0;
	}

	.url {
		font-size: 1.75rem;
		color: var(--texto-2);
		white-space: nowrap;
	}

	/* The room code in dots of light: the biggest thing in the room. */
	.code {
		display: block;
		font-size: min(14rem, 19vh, 7.5vw);
		line-height: 0.9;
		color: var(--texto);
	}

	.guests {
		display: grid;
		gap: var(--s-3);
	}

	.guest-count {
		font-size: 1.75rem;
		font-weight: 600;
		color: var(--texto-2);
	}

	/* The guests, each a pill of their colour; three lines at most. */
	.people {
		display: flex;
		flex-wrap: wrap;
		gap: var(--s-2);
		max-height: 10rem;
		margin: 0;
		padding: 0;
		overflow: hidden;
		list-style: none;
	}

	.people li {
		padding: 0 0.6em;
		border-radius: 999px;
		background: var(--who);
		color: var(--fondo);
		font-size: 1.75rem;
		font-weight: 750;
		line-height: 1.6;
	}

	.queue {
		grid-column: 2;
		grid-row: 2;
		min-height: 0;
	}

	.queue h2 {
		margin-bottom: var(--s-4);
		font-family: var(--font-display);
		font-size: 4rem;
		font-weight: 700;
		line-height: 1;
	}

	/* Between songs: the bill fills the screen and the board runs along its foot. */
	.countdown {
		display: grid;
		grid-template-rows: minmax(0, 1fr) auto;
		gap: var(--s-6);
	}

	.countdown .board {
		min-height: 0;
	}

	.countdown .corner-code {
		top: 0;
		right: 0;
	}

	.stage {
		position: absolute;
		inset: 0;
	}

	/* Who is singing, in their colour, where everyone can see it. */
	.now {
		position: absolute;
		top: var(--safe-y);
		left: var(--safe-x);
		max-width: 40%;
		display: grid;
		justify-items: start;
		gap: var(--s-2);
	}

	/* After the intro, the singer stays on screen as a pill of their colour. */
	.singer {
		padding: 0.05em 0.45em;
		border-radius: 999px;
		background: var(--who);
		color: var(--fondo);
		font-family: var(--font-display);
		font-size: 2.75rem;
		font-weight: 700;
		line-height: 1.1;
	}

	/* Covers the stage until the first line, exactly like the countdown before it. */
	.song-intro {
		position: absolute;
		z-index: 1;
		inset: 0;
		display: grid;
		align-content: center;
		padding: var(--safe-y) var(--safe-x);
		background: var(--fondo);
	}

	.next {
		padding: 0.1em 0.4em;
		background: color-mix(in srgb, var(--fondo) 82%, transparent);
		font-size: 1.75rem;
		font-weight: 650;
		color: var(--texto);
	}

	.corner-code {
		position: absolute;
		top: var(--safe-y);
		right: var(--safe-x);
		padding: 0.1em 0.4em;
		background: var(--fondo-2);
		font-size: 2.5rem;
		line-height: 1.2;
		color: var(--texto);
	}

	/* Shown on any movement or key while singing: at the top, never over the lyrics. */
	.tv-controls {
		position: absolute;
		top: var(--safe-y);
		right: var(--safe-x);
		max-width: 55%;
		display: flex;
		align-items: center;
		gap: var(--s-5);
		padding: var(--s-4) var(--s-5);
		background: var(--fondo-2);
		border: 1px solid var(--raia);
	}

	.tv-vocals {
		flex: 1;
		max-width: 26rem;
	}

	/* The song's progress as a hairline in the singer's colour along the bottom. */
	.hairline {
		position: absolute;
		left: 0;
		bottom: 0;
		width: 100%;
		height: 5px;
		background: var(--who);
		transform-origin: left;
		transform: scaleX(var(--p));
	}

	.unreachable {
		max-width: 28rem;
		font-size: 1.75rem;
		font-weight: 650;
		line-height: 1.25;
		color: var(--ouro);
	}

	.reconnecting {
		position: absolute;
		left: 50%;
		bottom: 0;
		z-index: 2;
		transform: translateX(-50%);
		padding: var(--s-2) var(--s-5);
		background: var(--texto);
		color: var(--fondo);
		font-weight: 650;
	}

	.error {
		color: var(--erro);
		font-weight: 700;
	}
</style>
