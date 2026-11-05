<script lang="ts">
	/*
	 * The party queue in turn order: position, who sings it (in their colour), the song and
	 * roughly when. The same list on the TV (big) and on the phones (where your own songs can be
	 * taken out).
	 */
	import SongTitle from '#lib/poster/SongTitle.svelte';
	import { flip } from 'svelte/animate';
	import { i18n } from '#lib/i18n';
	import Button from '#lib/ui/Button.svelte';
	import { guestOf } from './rotation';
	import type { PartyState, QueueItem } from './types';

	interface Props {
		state: PartyState;
		items: QueueItem[];
		waits: Map<string, number>;
		size?: 'tv' | 'phone';
		/** The guest using this phone: their songs stand out and can be removed. */
		me?: string | null;
		onremove?: (item: QueueItem) => void;
		limit?: number;
	}

	let { state, items, waits, size = 'phone', me = null, onremove, limit = 50 }: Props = $props();
	const t = $derived(i18n.t.party);
</script>

<ol class="queue {size}">
	{#each items.slice(0, limit) as item, i (item.id)}
		{@const guest = guestOf(state, item)}
		<li
			class:mine={item.guest_id === me}
			style:--who={guest?.color ?? 'var(--papel-suave)'}
			animate:flip={{ duration: 240 }}
		>
			<span class="position num" aria-hidden="true">{i + 1}</span>
			<span class="body">
				<span class="who">{guest?.name ?? '—'}</span>
				<span class="song"><SongTitle title={item.title} /></span>
				{#if item.artist}<span class="artist">{item.artist}</span>{/if}
				<span class="wait num"
					>{t.wait(Math.max(1, Math.round((waits.get(item.id) ?? 0) / 60)))}</span
				>
			</span>
			{#if onremove && item.guest_id === me}
				<Button variant="ghost" iconOnly icon="trash" onclick={() => onremove(item)}
					>{i18n.t.common.remove}</Button
				>
			{/if}
		</li>
	{/each}
</ol>

<style>
	.queue {
		display: grid;
		gap: var(--s-2);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	li {
		display: grid;
		grid-template-columns: auto 1fr auto;
		align-items: center;
		gap: var(--s-4);
		padding: var(--s-3) var(--s-3) var(--s-3) var(--s-4);
		background: var(--noite-alta);
	}

	li.mine {
		box-shadow: inset 0 0 0 2px var(--who);
	}

	.position {
		min-width: 1.6ch;
		font-family: var(--font-display);
		font-size: var(--t-3);
		font-weight: 900;
		line-height: 1;
		text-align: right;
		color: var(--who);
	}

	.body {
		display: grid;
		min-width: 0;
	}

	/* A person is a pill of their colour. */
	.who {
		justify-self: start;
		padding: 0 0.6em;
		border-radius: 999px;
		background: var(--who);
		color: var(--noite);
		font-weight: 800;
	}

	.song {
		font-family: var(--font-display);
		font-size: var(--t-2);
		font-weight: 800;
		line-height: 1.05;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.artist {
		font-size: var(--t--1);
		color: var(--papel-suave);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.wait {
		font-size: var(--t--1);
		color: var(--papel-suave);
		white-space: nowrap;
	}

	/* Ten feet away: everything bigger, nothing under 28 px at 1080p. */
	.tv li {
		gap: var(--s-5);
		padding: var(--s-4) var(--s-5);
	}

	.tv .position {
		font-size: 3.2rem;
	}

	.tv .who {
		font-size: 1.9rem;
	}

	.tv .song {
		font-size: 3rem;
	}

	.tv .artist,
	.tv .wait {
		font-size: 1.75rem;
	}

	/* On the TV the wait stands apart, at the right. */
	.tv .body {
		grid-template-columns: 1fr auto;
		column-gap: var(--s-5);
	}

	.tv .body > :not(.wait) {
		grid-column: 1;
	}

	.tv .wait {
		grid-column: 2;
		grid-row: 1 / span 3;
		align-self: center;
	}
</style>
