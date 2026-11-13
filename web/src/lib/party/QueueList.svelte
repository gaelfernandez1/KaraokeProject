<script lang="ts">
	/*
	 * The party queue as a departures board: one line per song with its turn, who sings it (a
	 * pill of their colour), the song and a status word ("Xa mesmo", "En 6 min"). Songs already
	 * sung stay at the top, struck through, so nothing silently disappears; the line on now (or,
	 * with nothing on, the next one) is lit in amber, the way a sung line of lyrics fills. The
	 * same board on the TV (big) and on the phones (where your own songs can be taken out).
	 */
	import SongTitle from '#lib/poster/SongTitle.svelte';
	import { flip } from 'svelte/animate';
	import { i18n } from '#lib/i18n';
	import Button from '#lib/ui/Button.svelte';
	import Icon from '#lib/ui/Icon.svelte';
	import { singerColor } from './colors';
	import { guestOf } from './rotation';
	import type { PartyState, QueueItem } from './types';

	interface Props {
		state: PartyState;
		/** The songs still to sing, in turn order. */
		items: QueueItem[];
		waits: Map<string, number>;
		size?: 'tv' | 'phone';
		/** The guest using this phone: their songs stand out and can be removed. */
		me?: string | null;
		onremove?: (item: QueueItem) => void;
		limit?: number;
		/** Songs already sung or skipped, struck through above the rest. */
		past?: QueueItem[];
		/** The song on now (or being announced), lit above the songs to come. */
		current?: QueueItem | null;
	}

	let {
		state,
		items,
		waits,
		size = 'phone',
		me = null,
		onremove,
		limit = 50,
		past = [],
		current = null
	}: Props = $props();
	const t = $derived(i18n.t.party);

	type Line = { item: QueueItem; kind: 'past' | 'now' | 'next'; turn: number };
	const lines = $derived<Line[]>([
		...past.map((item) => ({ item, kind: 'past' as const, turn: 0 })),
		...(current ? [{ item: current, kind: 'now' as const, turn: 0 }] : []),
		...items
			.filter((item) => item.id !== current?.id)
			.slice(0, limit)
			.map((item, i) => ({ item, kind: 'next' as const, turn: i + 1 }))
	]);
	/** Lit: the song on now, else the next one. */
	const litId = $derived(current?.id ?? lines.find((line) => line.kind === 'next')?.item.id);

	function status(line: Line): string {
		if (line.kind === 'past') return line.item.state === 'skipped' ? t.skippedStatus : t.sung;
		if (line.kind === 'now') return t.now;
		return t.wait(Math.max(1, Math.round((waits.get(line.item.id) ?? 0) / 60)));
	}
</script>

<ol class="queue {size}">
	{#each lines as line (line.item.id)}
		{@const guest = guestOf(state, line.item)}
		<li
			class={line.kind}
			class:lit={line.item.id === litId}
			class:mine={line.kind === 'next' && line.item.guest_id === me}
			style:--who={singerColor(guest?.color)}
			animate:flip={{ duration: 240 }}
		>
			<span class="turn" aria-hidden="true">
				{#if line.kind === 'next'}<span class="data">{line.turn}</span>
				{:else if line.kind === 'now'}<Icon name="play" size={0.9} />
				{:else if line.item.state === 'done'}<Icon name="check" size={0.9} />{/if}
			</span>
			<span class="who">{guest?.name ?? '—'}</span>
			<span class="song">
				<span class="titles">
					<span class="title"><SongTitle title={line.item.title} /></span>
					{#if line.item.id === litId}<span class="title glow" aria-hidden="true"
							><SongTitle title={line.item.title} /></span
						>{/if}
				</span>
				{#if line.item.artist}<span class="artist">{line.item.artist}</span>{/if}
			</span>
			<span class="status num">{status(line)}</span>
			{#if onremove && line.kind === 'next' && line.item.guest_id === me}
				<span class="remove">
					<Button variant="ghost" iconOnly icon="trash" onclick={() => onremove(line.item)}
						>{i18n.t.common.remove}</Button
					>
				</span>
			{/if}
		</li>
	{/each}
</ol>

<style>
	.queue {
		display: grid;
		margin: 0;
		padding: 0;
		list-style: none;
		gap: 2px;
	}

	/* Phone: the turn, then the song over who sings it, then the status. */
	li {
		position: relative;
		display: grid;
		grid-template-areas:
			'turn song status remove'
			'turn who status remove';
		grid-template-columns: 2rem minmax(0, 1fr) auto auto;
		align-items: center;
		column-gap: var(--s-3);
		row-gap: var(--s-1);
		min-height: 4.5rem;
		padding: var(--s-3) var(--s-3) var(--s-3) var(--s-4);
		border-radius: var(--radius-row);
		transition: background-color var(--dur-2) ease;
	}

	/* The line that is on: lit in gold, like a window at night. */
	li.lit {
		background: color-mix(in oklab, var(--ouro) 11%, transparent);
	}

	li.mine:not(.lit) {
		background: var(--panel-claro);
	}

	.turn {
		grid-area: turn;
		align-self: center;
		display: flex;
		justify-content: center;
		color: var(--texto-2);
		font-size: var(--t-1);
		line-height: 1;
	}

	.lit .turn {
		color: var(--ouro);
	}

	/* A person is a pill of their colour; once their song is sung, just its outline. */
	.who {
		grid-area: who;
		justify-self: start;
		max-width: 100%;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		padding: 0 0.6em;
		border: 2px solid var(--who);
		border-radius: 999px;
		background: var(--who);
		color: var(--fondo);
		font-weight: 750;
		font-size: var(--t--1);
		line-height: 1.5;
	}

	.past .who {
		background: transparent;
		color: var(--who);
	}

	.song {
		grid-area: song;
		display: flex;
		align-items: baseline;
		gap: var(--s-3);
		min-width: 0;
	}

	/* The title and its lit copy share one cell, so they always cut at the same letter. */
	.titles {
		display: grid;
		min-width: 0;
	}

	.title {
		grid-area: 1 / 1;
		display: block;
		min-width: 0;
		font-family: var(--font-text);
		font-size: var(--t-2);
		font-weight: 650;
		line-height: 1.05;
	}

	/* The amber copy of the title, swept in from the left when the line lights up. */
	.glow {
		color: var(--ouro);
		clip-path: inset(-10% 0 -10% 0);
		animation: sweep 300ms var(--ease) both;
	}

	.glow :global(.tag) {
		color: inherit;
	}

	@keyframes sweep {
		from {
			clip-path: inset(-10% 100% -10% 0);
		}
	}

	.artist {
		display: none;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		color: var(--texto-2);
		font-size: var(--t--1);
	}

	.status {
		grid-area: status;
		justify-self: end;
		white-space: nowrap;
		color: var(--texto);
		font-size: var(--t--1);
	}

	.lit .status {
		color: var(--ouro);
	}

	.remove {
		grid-area: remove;
	}

	/* Sung: struck through and quiet, but still on the board. */
	.past .title {
		color: var(--texto-2);
		text-decoration: line-through;
		text-decoration-thickness: 0.08em;
	}

	.past .status {
		color: var(--texto-2);
		font-weight: 500;
	}

	/* Ten feet away: one line per song in columns, nothing under 28 px at 1080p. */
	.tv li {
		grid-template-areas: 'turn who song status';
		grid-template-columns: 3.5rem minmax(0, 13rem) minmax(0, 1fr) 9.5rem;
		column-gap: var(--s-5);
		min-height: min(5.25rem, 8vh);
		padding: var(--s-2) var(--s-4) var(--s-2) var(--s-5);
	}

	.tv .turn {
		font-size: 2.4rem;
	}

	.tv .who {
		font-size: 1.75rem;
		line-height: 1.35;
	}

	.tv .title {
		font-size: 2.75rem;
	}

	.tv .artist {
		display: block;
		font-size: 1.75rem;
	}

	.tv .status {
		font-size: 1.75rem;
	}
</style>
