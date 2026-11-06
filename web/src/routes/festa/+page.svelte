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
	import Poster from '#lib/poster/Poster.svelte';
	import { summaryOf } from '#lib/poster/summary.js';
	import { settings } from '#lib/settings/settings.svelte.js';
	import { arrowNavigation } from '#lib/tv/focus.js';
	import Button from '#lib/ui/Button.svelte';
	import Slider from '#lib/ui/Slider.svelte';
	import Switch from '#lib/ui/Switch.svelte';
	import Wordmark from '#lib/ui/Wordmark.svelte';
	import { chrome } from '#lib/ui/chrome.svelte.js';

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

	const t = $derived(i18n.t.party);
	const theme = $derived(THEMES[settings.theme] ?? THEMES[DEFAULT_THEME]);
	const party = $derived(host?.state ?? null);
	const queue = $derived(party ? upcoming(party) : []);
	const waits = $derived(party ? waitEstimate(party, now) : new Map<string, number>());
	const joinUrl = $derived(host ? `${baseUrl}/festa/${host.code}` : '');
	const singer = $derived(party && host?.current ? guestOf(party, host.current) : undefined);
	const nextUp = $derived(host?.phase === 'singing' ? queue[0] : undefined);
	/** Before the first line, the TV also says what song it is. */
	const intro = $derived(
		host?.doc ? host.session.time < (host.doc.lines[0]?.start ?? 0) - 1 : false
	);
	const progress = $derived(
		host && host.session.duration > 0 ? host.session.time / host.session.duration : 0
	);
	/** Three rows of posters drift across the empty lobby until the first request. */
	const attractRows = $derived(
		songs.length === 0
			? []
			: [0, 1, 2].map((row) => {
					const shift = (row * 3) % songs.length;
					const rotated = [...songs.slice(shift), ...songs.slice(0, shift)].slice(0, 8);
					return [...rotated, ...rotated];
				})
	);

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
		if (root) await toggleFullscreen(root);
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

<svelte:head><title>{t.title} · Proxecto Karaoke en Galego</title></svelte:head>
<svelte:window onkeydown={onKey} onpointermove={wake} />
<svelte:document onfullscreenchange={() => (fullscreen = isFullscreen())} />

{#if !host}
	<main class="start" class:touch>
		<h1>{t.title}</h1>
		{#if touch}
			<form class="join" onsubmit={join}>
				<label for="code">{t.joinWithCode}</label>
				<input
					id="code"
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
						onclick={() => begin(resumable ?? undefined)}>{t.continueParty(resumable.code)}</Button
					>
					<Button size="l" onclick={() => begin()}>{t.newParty}</Button>
				{:else}
					<Button variant="primary" size="l" icon="party" onclick={() => begin()}>{t.start}</Button>
				{/if}
			</div>
		{/if}
		{#if failure}<p class="error" role="alert">{failure}</p>{/if}
	</main>
{:else}
	<div class="tv" class:idle bind:this={root} data-phase={host.phase}>
		{#if host.phase === 'singing' && host.doc && host.current}
			<div class="stage" style:--who={singer?.color ?? 'var(--papel)'}>
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
				{#if !controls}<p class="corner-code num" aria-label={t.code}>{host.code}</p>{/if}
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
			<main class="screen">
				<UpNext
					song={posterOf(host.current)}
					guest={guestOf(party, host.current)}
					countdown={host.countdown}
					onstart={() => host?.startNow()}
					onskip={() => host?.skip()}
				/>
			</main>
		{:else}
			<main class="screen lobby" class:empty={queue.length === 0}>
				<header class="bar">
					<Wordmark size="3rem" />
					<div class="tools">
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
								<Button variant="ghost" size="l" onclick={() => (confirmingEnd = true)}
									>{t.endParty}</Button
								>
							{/if}
						</div>
					{/if}
				</header>
				<section class="queue" aria-labelledby="queue-title">
					{#if party && queue.length > 0}
						<h2 id="queue-title">{t.queue}</h2>
						<QueueList state={party} items={queue} {waits} size="tv" limit={5} />
					{:else}
						<h2 id="queue-title" class="visually-hidden">{t.queue}</h2>
						<div class="attract" aria-hidden="true">
							{#each attractRows as row, r (r)}
								<div class="row" class:reverse={r % 2 === 1}>
									{#each row as song, i (`${song.id}-${i}`)}
										<div class="mini"><Poster {song} compact /></div>
									{/each}
								</div>
							{/each}
						</div>
						<p class="call">{t.attract}</p>
					{/if}
				</section>
				<aside class="join-card">
					<div class="qr" class:short={!reachable}><Qr text={joinUrl} label={t.scan} /></div>
					<p class="scan">{t.scan}</p>
					<p class="code num" aria-label={t.code}>{host.code}</p>
					{#if reachable}
						<p class="url num">{t.orOpen(joinUrl.replace(/^https?:\/\//, ''))}</p>
					{:else}
						<!-- The address would not open on a phone: say why instead. -->
						<p class="unreachable" role="status">{t.unreachable}</p>
					{/if}
					{#if party}<p class="guests num">{t.guests(party.guests.length)}</p>{/if}
				</aside>
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
		background: var(--noite);
		font-size: var(--t-0);
	}

	.tv :global(:focus-visible) {
		outline: 6px solid var(--papel);
		outline-offset: 6px;
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
		justify-items: start;
		gap: var(--s-6);
		max-width: var(--page-max);
		margin: 0 auto;
		padding: var(--s-8) var(--page-x);
	}

	.start h1 {
		font-family: var(--font-display);
		font-size: var(--t-6);
		font-weight: 900;
		line-height: 0.9;
	}

	.start.touch {
		gap: var(--s-5);
		padding-top: var(--s-6);
	}

	.intro {
		max-width: 40rem;
		font-size: var(--t-1);
		color: var(--papel-suave);
	}

	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: var(--s-3);
	}

	.join {
		display: grid;
		gap: var(--s-3);
		width: 100%;
	}

	.join label {
		font-weight: 800;
		font-size: var(--t-1);
	}

	.join input {
		width: 100%;
		padding: var(--s-2) var(--s-4);
		border: 2px solid var(--linha);
		border-radius: var(--radius-control);
		background: var(--noite-alta);
		font-family: var(--font-display);
		font-size: 4rem;
		font-weight: 900;
		letter-spacing: 0.3em;
		text-transform: uppercase;
		color: var(--farol);
	}

	.join input::placeholder {
		color: color-mix(in oklch, var(--papel-suave) 45%, transparent);
	}

	.join input:focus {
		outline: none;
		border-color: var(--farol);
	}

	.lobby {
		display: grid;
		grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);
		grid-template-rows: auto 1fr;
		gap: var(--s-6) var(--s-9);
	}

	.bar {
		position: relative;
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

	/* Opens over the queue side, never over the QR the guests are scanning. */
	.settings :global(.switch) {
		font-size: 1.75rem;
	}

	.settings {
		position: absolute;
		top: calc(100% + var(--s-2));
		left: 0;
		z-index: 2;
		display: grid;
		justify-items: start;
		gap: var(--s-4);
		padding: var(--s-5);
		background: var(--noite-alta);
		border: 1px solid var(--linha);
	}

	.confirm {
		font-weight: 700;
	}

	.confirm-actions {
		display: flex;
		gap: var(--s-3);
	}

	.queue {
		position: relative;
		min-height: 0;
	}

	.queue h2 {
		margin-bottom: var(--s-4);
		font-family: var(--font-display);
		font-size: 4rem;
		font-weight: 900;
		line-height: 1;
	}

	/* The empty lobby: posters from the library drift by, and one line says what to do. */
	/* The posters run in from the screen's edge and stop at a rule before the QR. */
	.attract {
		position: absolute;
		inset: 0 0 7rem calc(-1 * var(--safe-x));
		border-right: 3px solid var(--linha);
		display: grid;
		gap: var(--s-4);
		align-content: center;
		overflow: hidden;
		opacity: 0.9;
	}

	.row {
		display: flex;
		gap: var(--s-4);
		width: max-content;
		animation: drift 90s linear infinite;
	}

	.row.reverse {
		animation-direction: reverse;
	}

	.mini {
		width: 9rem;
		flex: none;
	}

	@keyframes drift {
		to {
			transform: translateX(-50%);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.row {
			animation: none;
		}
	}

	.call {
		position: absolute;
		inset: auto 0 0;
		font-family: var(--font-display);
		font-size: 5rem;
		font-weight: 900;
		line-height: 1;
	}

	.join-card {
		display: grid;
		align-content: start;
		justify-items: center;
		gap: var(--s-3);
		text-align: center;
	}

	.qr {
		width: min(100%, 40vh);
	}

	/* Room for the warning that replaces the address, without pushing the lobby down. */
	.qr.short {
		width: min(100%, 34vh);
	}

	.scan {
		font-size: 2rem;
		font-weight: 700;
	}

	/* The room code, set like a festival bill: the biggest thing in the room. */
	.code {
		font-size: clamp(6rem, 13vw, 16rem);
		font-weight: 900;
		line-height: 0.85;
		letter-spacing: 0.06em;
		color: var(--papel);
	}

	.url,
	.guests {
		font-size: 1.75rem;
		color: var(--papel-suave);
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
	}

	/* After the intro, the singer stays on screen as a pill of their colour. */
	.singer {
		justify-self: start;
		width: fit-content;
		padding: 0.05em 0.45em;
		border-radius: 999px;
		background: var(--who);
		color: var(--noite);
		font-family: var(--font-display);
		font-size: 2.75rem;
		font-weight: 900;
		line-height: 1.1;
	}

	/* Covers the stage until the first line, exactly like the countdown before it. */
	.song-intro {
		position: absolute;
		z-index: 1;
		inset: 0;
		padding: var(--safe-y) var(--safe-x);
		background: var(--noite);
	}

	.next {
		margin-top: var(--s-2);
		font-size: 1.75rem;
		font-weight: 700;
		color: var(--papel-suave);
		text-shadow: 0 2px 0 var(--noite);
	}

	.corner-code {
		position: absolute;
		top: var(--safe-y);
		right: var(--safe-x);
		padding: 0.15em 0.45em;
		border-radius: var(--radius-control);
		background: var(--noite-alta);
		font-size: 2.25rem;
		font-weight: 900;
		letter-spacing: 0.06em;
		color: var(--papel);
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
		background: var(--noite-alta);
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
		font-size: 1.25rem;
		font-weight: 700;
		color: var(--farol);
	}

	.reconnecting {
		position: absolute;
		left: 50%;
		bottom: 0;
		transform: translateX(-50%);
		padding: var(--s-2) var(--s-5);
		background: var(--papel);
		color: var(--noite);
		font-weight: 800;
	}

	.error {
		color: var(--erro);
		font-weight: 700;
	}
</style>
