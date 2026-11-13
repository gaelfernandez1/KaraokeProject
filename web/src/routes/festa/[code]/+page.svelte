<script lang="ts">
	import { splitTitle } from '#lib/poster/fit.js';
	import SongTitle from '#lib/poster/SongTitle.svelte';
	/*
	 * A guest's phone at a party: join with a name (no account), request songs, follow the queue
	 * and, if the host allows it, act as the remote. Rejoining with the same name on the same
	 * phone keeps the same colour and songs.
	 */
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { ApiError, listSongs, type SongSummary } from '#lib/api';
	import { i18n } from '#lib/i18n';
	import { filterSongs } from '#lib/library/filter.js';
	import {
		enqueue,
		getParty,
		joinParty,
		rememberedGuest,
		rememberGuest,
		removeItem,
		sendCommand
	} from '#lib/party/client.js';
	import { PartyConnection } from '#lib/party/connection.svelte.js';
	import { singerColor } from '#lib/party/colors.js';
	import QueueList from '#lib/party/QueueList.svelte';
	import { guestOf, nowPlaying, upcoming, waitEstimate } from '#lib/party/rotation.js';
	import {
		SINGER_COLORS,
		type Joined,
		type PartyCommand,
		type PartyState
	} from '#lib/party/types.js';
	import Cover from '#lib/poster/Cover.svelte';
	import Button from '#lib/ui/Button.svelte';
	import Icon from '#lib/ui/Icon.svelte';
	import Slider from '#lib/ui/Slider.svelte';

	const code = $derived((page.params.code ?? '').toUpperCase());
	let joined = $state.raw<Joined | null>(null);
	let connection = $state.raw<PartyConnection | null>(null);
	let exists = $state<boolean | null>(null);
	let name = $state('');
	let otherCode = $state('');
	let joining = $state(false);
	let failure = $state<string | null>(null);
	let tab = $state<'request' | 'queue' | 'remote'>('request');
	let songs = $state.raw<SongSummary[]>([]);
	let query = $state('');
	let pending = $state<string[]>([]);
	let now = $state(Date.now());
	/** The party as seen before joining: who is singing, and the colour a newcomer gets. */
	let preview = $state.raw<PartyState | null>(null);

	const t = $derived(i18n.t.party);
	const party = $derived(connection?.state ?? null);
	const me = $derived(joined?.guest.id ?? null);
	const myColor = $derived(
		singerColor(
			party?.guests.find((g) => g.id === me)?.color ?? joined?.guest.color,
			'var(--texto)'
		)
	);
	const queue = $derived(party ? upcoming(party) : []);
	const waits = $derived(party ? waitEstimate(party, now) : new Map<string, number>());
	const playing = $derived(party ? nowPlaying(party) : null);
	/** Guests control the TV if the host allows it; whoever is singing always controls their song. */
	const canControl = $derived(
		(party?.settings.guests_control ?? false) || (playing !== null && playing.guest_id === me)
	);
	const results = $derived(filterSongs(songs, { query, language: 'all', saved: null }));
	const newColor = $derived(
		singerColor(SINGER_COLORS[(preview?.guests.length ?? 0) % SINGER_COLORS.length])
	);
	const previewPlaying = $derived(preview ? nowPlaying(preview) : null);

	$effect(() => {
		const current = code;
		untrack(() => {
			exists = null;
			joined = rememberedGuest(current);
			name = joined?.guest.name ?? '';
		});
		getParty(current)
			.then((state) => {
				exists = true;
				preview = state;
			})
			.catch((error: unknown) => {
				exists = error instanceof ApiError && error.status === 404 ? false : true;
				if (error instanceof ApiError && error.status === 0) failure = i18n.t.errors.network;
			});
	});

	// Once joined: follow the party live, and fetch the songs to request.
	$effect(() => {
		if (!joined || exists !== true) return;
		const live = new PartyConnection(code, joined.token);
		// Starting reads the connection's own state: that must not restart this effect.
		untrack(() => {
			live.start();
			connection = live;
		});
		listSongs()
			.then((list) => (songs = list))
			.catch(() => {});
		const clock = setInterval(() => (now = Date.now()), 15_000);
		return () => {
			clearInterval(clock);
			live.close();
		};
	});

	async function join(event: SubmitEvent) {
		event.preventDefault();
		if (!name.trim()) return;
		joining = true;
		failure = null;
		try {
			const result = await joinParty(code, name);
			rememberGuest(code, result);
			joined = result;
		} catch (error) {
			failure =
				error instanceof ApiError && error.status === 0
					? i18n.t.errors.network
					: i18n.t.errors.generic;
		} finally {
			joining = false;
		}
	}

	async function request(song: SongSummary) {
		if (!joined) return;
		pending = [...pending, song.id];
		try {
			await enqueue(code, joined.token, song.id);
		} catch {
			failure = i18n.t.errors.generic;
		} finally {
			pending = pending.filter((id) => id !== song.id);
		}
	}

	function positionOf(songId: string): number {
		return queue.findIndex((item) => item.song_id === songId && item.guest_id === me) + 1;
	}

	function command(cmd: PartyCommand) {
		if (joined) void sendCommand(code, joined.token, cmd).catch(() => {});
	}

	let vocalsTimer: ReturnType<typeof setTimeout> | undefined;
	function vocals(value: number) {
		clearTimeout(vocalsTimer);
		vocalsTimer = setTimeout(() => command({ type: 'vocals', value }), 120);
	}
</script>

<svelte:head><title>{t.title} {code} · Karaoke en Galego</title></svelte:head>

<div class="remote" style:--me={myColor}>
	<header class="bar">
		<p class="party-code"><span>{t.title}</span> {code}</p>
		{#if joined}<p class="me">{joined.guest.name}</p>{/if}
	</header>

	{#if exists === false || connection?.ended}
		<main class="panel">
			<p class="message">{connection?.ended ? t.ended : t.unknownCode}</p>
			<form
				class="other"
				onsubmit={(e) => {
					e.preventDefault();
					if (otherCode.trim())
						void goto(resolve('/festa/[code]', { code: otherCode.trim().toUpperCase() }));
				}}
			>
				<label for="other-code">{t.otherCode}</label>
				<div class="row">
					<input
						id="other-code"
						bind:value={otherCode}
						autocomplete="off"
						autocapitalize="characters"
						maxlength="8"
					/>
					<Button variant="primary" type="submit">{t.go}</Button>
				</div>
			</form>
		</main>
	{:else if !joined}
		<main class="panel join" style:--new={newColor}>
			<form onsubmit={join}>
				<label for="name"><h1>{t.whatsYourName}</h1></label>
				<!-- svelte-ignore a11y_autofocus -->
				<input
					id="name"
					bind:value={name}
					autocomplete="nickname"
					maxlength="24"
					enterkeyhint="go"
					autofocus
					required
				/>
				<p class="you" aria-hidden="true">
					<span class="you-name" class:empty={!name.trim()}>{name.trim() || t.yourName}</span>
					<span class="you-note">{t.yourColor}</span>
				</p>
				<Button variant="primary" size="l" type="submit" disabled={joining || !name.trim()}
					>{t.join}</Button
				>
			</form>
			{#if previewPlaying}<p class="playing-note">{t.nowPlaying(previewPlaying.title)}</p>{/if}
			{#if failure}<p class="error" role="alert">{failure}</p>{/if}
		</main>
	{:else}
		<main class="content">
			{#if party && !connection?.connected}<p class="reconnecting" role="status">
					{t.reconnecting}
				</p>{/if}

			{#if tab === 'request'}
				<label class="search">
					<span class="visually-hidden">{t.searchSongs}</span>
					<Icon name="search" size={1.25} />
					<input type="search" bind:value={query} placeholder={t.searchSongs} autocomplete="off" />
				</label>
				<ul class="songs">
					{#each results as song (song.id)}
						{@const position = positionOf(song.id)}
						<li>
							<button
								type="button"
								class="song-row wake"
								class:queued={position > 0}
								disabled={position > 0 || pending.includes(song.id) || playing?.song_id === song.id}
								onclick={() => request(song)}
							>
								<span class="thumb"><Cover {song} /></span>
								<span class="info">
									<span class="title"><SongTitle title={song.title} /></span>
									{#if song.artist}<span class="artist">{song.artist}</span>{/if}
								</span>
								{#if playing?.song_id === song.id}
									<span
										class="in-queue"
										style:--me={party && playing
											? singerColor(guestOf(party, playing)?.color)
											: undefined}>{t.playingNow}</span
									>
								{:else if position > 0}
									<span class="in-queue">{t.inQueue(position)}</span>
								{:else}
									<span class="add" aria-hidden="true"><Icon name="plus" size={1.4} /></span>
									<span class="visually-hidden">{t.request}</span>
								{/if}
							</button>
						</li>
					{/each}
				</ul>
			{:else if tab === 'queue'}
				{#if playing && party}
					<section class="playing" style:--who={singerColor(guestOf(party, playing)?.color)}>
						<p class="label">{t.nowSingingLabel}</p>
						<p class="who-pill">{guestOf(party, playing)?.name}</p>
						<p class="song"><SongTitle title={playing.title} /></p>
					</section>
				{/if}
				{#if party && queue.length > 0}
					<QueueList
						state={party}
						items={queue}
						{waits}
						{me}
						onremove={(item) => joined && removeItem(code, joined.token, item.id).catch(() => {})}
					/>
				{:else}
					<p class="message">{t.queueEmpty}</p>
				{/if}
			{:else}
				<section class="controls">
					{#if playing && party}
						{@const singer = guestOf(party, playing)}
						<div class="playing" style:--who={singerColor(singer?.color)}>
							<p class="label">{t.nowSingingLabel}</p>
							<p class="who-pill">{singer?.name}</p>
							<p class="song big"><SongTitle title={playing.title} /></p>
							{#if playing.artist}<p class="artist">{playing.artist}</p>{/if}
						</div>
					{:else}
						<p class="message">{t.nothingPlaying}</p>
					{/if}
					{#if !canControl}
						{@const next = queue.find((item) => item.guest_id === me)}
						<p class="mine-next">
							{next
								? t.myNext(
										splitTitle(next.title).main,
										t.wait(Math.max(1, Math.round((waits.get(next.id) ?? 0) / 60)))
									)
								: t.noRequests}
						</p>
						{#if !next}
							<Button variant="primary" icon="search" onclick={() => (tab = 'request')}
								>{t.tabRequest}</Button
							>
						{/if}
						<p class="note">{t.noControl}</p>
					{:else}
						<div class="transport">
							<Button
								variant="primary"
								size="l"
								iconOnly
								icon={party?.playback.playing ? 'pause' : 'play'}
								onclick={() => command({ type: party?.playback.playing ? 'pause' : 'play' })}
								class="big-play"
								>{party?.playback.playing ? i18n.t.player.pause : i18n.t.player.play}</Button
							>
							<Button size="l" icon="skip" onclick={() => command({ type: 'skip' })}
								>{t.skip}</Button
							>
						</div>
						<Slider
							label={t.vocals}
							value={party?.playback.vocals ?? 0}
							step={0.05}
							oninput={vocals}
						/>
						<div class="key">
							<span class="key-label">{t.key}</span>
							<Button
								iconOnly
								icon="minus"
								onclick={() => command({ type: 'pitch', value: (party?.playback.pitch ?? 0) - 1 })}
								>{i18n.t.player.keyDown}</Button
							>
							<output class="num">{party?.playback.pitch ?? 0}</output>
							<Button
								iconOnly
								icon="plus"
								onclick={() => command({ type: 'pitch', value: (party?.playback.pitch ?? 0) + 1 })}
								>{i18n.t.player.keyUp}</Button
							>
						</div>
					{/if}
				</section>
			{/if}
		</main>

		<nav class="tabs" aria-label={t.title}>
			{#each [['request', t.tabRequest, 'search'], ['queue', t.tabQueue, 'queue'], ['remote', t.tabRemote, 'remote']] as const as [id, label, icon] (id)}
				<button type="button" aria-pressed={tab === id} onclick={() => (tab = id)}>
					<Icon name={icon} size={1.5} />
					<span>{label}</span>
				</button>
			{/each}
		</nav>
	{/if}
</div>

<style>
	.remote {
		display: grid;
		grid-template-rows: auto 1fr auto;
		grid-template-columns: minmax(0, 1fr);
		min-height: 100dvh;
	}

	.bar {
		position: sticky;
		top: 0;
		z-index: 2;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--s-3);
		padding: max(var(--s-3), env(safe-area-inset-top)) var(--page-x) var(--s-3);
		background: var(--fondo);
		border-bottom: 1px solid var(--raia);
	}

	.party-code {
		font-family: var(--font-display);
		font-size: var(--t-2);
		font-weight: 700;
		letter-spacing: 0.04em;
		color: var(--texto);
	}

	.party-code span {
		color: var(--texto-2);
		letter-spacing: 0;
	}

	/* People are the one place pills live: a name on its own colour. */
	.me,
	.who-pill {
		padding: var(--s-1) var(--s-3);
		border-radius: 999px;
		background: var(--me);
		color: var(--fondo-3);
		font-weight: 700;
		line-height: 1.3;
	}

	.who-pill {
		background: var(--who, var(--texto));
	}

	.panel {
		display: grid;
		align-content: start;
		gap: var(--s-4);
		padding: var(--s-6) var(--page-x);
	}

	.join h1 {
		font-family: var(--font-display);
		font-size: var(--t-4);
		font-weight: 700;
		line-height: 0.95;
	}

	.join form,
	.other {
		display: grid;
		gap: var(--s-4);
	}

	label {
		font-weight: 650;
	}

	input:not([type='range']) {
		width: 100%;
		min-height: 3.25rem;
		padding: 0 var(--s-4);
		border: 1px solid var(--raia-forte);
		border-radius: var(--radius-control);
		background: var(--fondo-2);
		font-size: var(--t-1);
		transition: border-color var(--dur-1) ease;
	}

	input:not([type='range'])::placeholder {
		color: var(--texto-2);
	}

	input:not([type='range']):focus {
		outline: none;
		border-color: var(--ceo);
		box-shadow: 0 0 0 1px var(--ceo);
	}

	.row {
		display: flex;
		gap: var(--s-2);
	}

	/* The name as the TV will announce it: big, in the colour this guest gets. */
	.you {
		display: grid;
		gap: var(--s-2);
		padding: var(--s-4) 0;
		border-block: 1px solid var(--raia);
	}

	.you-name {
		font-family: var(--font-display);
		font-size: var(--t-6);
		font-weight: 700;
		line-height: 0.88;
		color: var(--new);
		overflow-wrap: anywhere;
		transition: opacity var(--dur-1) ease;
	}

	.you-name.empty {
		opacity: 0.35;
	}

	.you-note {
		color: var(--texto-2);
	}

	.playing-note {
		color: var(--texto-2);
	}

	.content {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		align-content: start;
		gap: var(--s-4);
		padding: var(--s-4) var(--page-x) calc(5rem + env(safe-area-inset-bottom));
	}

	.search {
		position: relative;
		display: flex;
		align-items: center;
		color: var(--texto-2);
	}

	.search:focus-within {
		color: var(--texto);
	}

	.search :global(svg) {
		position: absolute;
		left: var(--s-4);
		pointer-events: none;
	}

	.search input {
		padding-left: 2.9rem;
	}

	/* The songs to ask for, as lines of the board. */
	.songs {
		display: grid;
		margin: 0;
		padding: 0;
		list-style: none;
		border-top: 1px solid var(--raia);
	}

	.song-row {
		display: grid;
		grid-template-columns: 3.5rem minmax(0, 1fr) auto;
		align-items: center;
		gap: var(--s-3);
		width: 100%;
		min-height: 4.5rem;
		padding: var(--s-2) 0;
		border: 0;
		border-bottom: 1px solid var(--raia);
		background: none;
		text-align: left;
		transition: background-color var(--dur-1) ease;
	}

	.song-row:focus-visible {
		outline-offset: -3px;
	}

	.song-row:disabled {
		cursor: default;
	}

	.thumb {
		width: 3.5rem;
	}

	.info {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		min-width: 0;
	}

	.title {
		font-family: var(--font-text);
		font-size: var(--t-2);
		font-weight: 650;
		line-height: 1.05;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.artist {
		font-size: var(--t--1);
		color: var(--texto-2);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.add {
		display: grid;
		place-items: center;
		width: var(--target);
		height: var(--target);
		border: 1px solid var(--raia-forte);
		border-radius: var(--radius-control);
		transition:
			border-color var(--dur-1) ease,
			color var(--dur-1) ease,
			transform var(--dur-1) var(--ease);
	}

	.song-row:not(:disabled):active .add {
		border-color: var(--ouro);
		color: var(--ouro);
		transform: scale(0.94);
	}

	@media (hover: hover) {
		.song-row:not(:disabled):hover .add {
			border-color: var(--ouro);
			color: var(--ouro);
		}
	}

	/* Asked for: its place in the queue, in this guest's colour. */
	.in-queue {
		font-size: var(--t--1);
		font-weight: 700;
		color: var(--me);
	}

	.playing {
		display: grid;
		justify-items: start;
		gap: var(--s-2);
		padding: var(--s-4);
		background: var(--fondo-2);
	}

	.label {
		font-weight: 650;
		color: var(--ouro);
	}

	.song {
		font-family: var(--font-display);
		font-size: var(--t-3);
		font-weight: 700;
		line-height: 1;
	}

	.song.big {
		font-size: var(--t-4);
	}

	.controls {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: var(--s-5);
	}

	.mine-next {
		font-family: var(--font-text);
		font-size: var(--t-2);
		font-weight: 650;
		line-height: 1.1;
	}

	.note,
	.message {
		color: var(--texto-2);
	}

	.transport {
		display: flex;
		align-items: center;
		gap: var(--s-4);
	}

	.transport :global(.big-play) {
		width: 5rem;
		min-height: 5rem;
	}

	.key {
		display: flex;
		align-items: center;
		gap: var(--s-3);
	}

	.key-label {
		flex: 1;
		font-weight: 650;
	}

	.key output {
		min-width: 3ch;
		text-align: center;
		font-family: var(--font-data);
		font-size: var(--t-3);
		font-weight: 700;
	}

	.tabs {
		position: fixed;
		inset: auto 0 0;
		z-index: 2;
		display: flex;
		padding-bottom: env(safe-area-inset-bottom);
		background: var(--fondo-3);
		border-top: 1px solid var(--raia);
	}

	.tabs button {
		flex: 1;
		display: grid;
		justify-items: center;
		gap: 2px;
		min-height: 4rem;
		padding: var(--s-2);
		border: 0;
		background: none;
		font-size: var(--t--1);
		font-weight: 600;
		color: var(--texto-2);
		transition:
			color var(--dur-1) ease,
			transform var(--dur-1) var(--ease);
	}

	.tabs button:active {
		transform: scale(0.97);
	}

	.tabs button:focus-visible {
		outline-offset: -3px;
	}

	/* The tab in view: the blue of what is selected, as everywhere else. */
	.tabs button[aria-pressed='true'] {
		color: var(--ceo);
		--icon-accent: var(--texto);
	}

	.reconnecting {
		padding: var(--s-2) var(--s-3);
		border: 1px solid var(--raia-forte);
		background: var(--fondo-2);
		font-weight: 650;
	}

	.error {
		font-weight: 650;
		color: var(--erro);
	}
</style>
