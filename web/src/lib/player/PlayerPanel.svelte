<script lang="ts">
	/*
	 * A side panel of the player (sound, downloads): beside the lyrics on wide screens and under
	 * them on phones, never over the line being sung.
	 */
	import type { Snippet } from 'svelte';
	import { i18n } from '#lib/i18n';
	import Button from '#lib/ui/Button.svelte';

	interface Props {
		title: string;
		onclose: () => void;
		children: Snippet;
	}

	let { title, onclose, children }: Props = $props();
</script>

<aside class="panel" aria-label={title}>
	<header>
		<h2>{title}</h2>
		<Button variant="ghost" iconOnly icon="close" onclick={onclose}>{i18n.t.common.close}</Button>
	</header>
	{@render children()}
</aside>

<style>
	.panel {
		display: grid;
		align-content: start;
		width: 100%;
		max-height: 100%;
		overflow-y: auto;
		overscroll-behavior: contain;
		padding: var(--s-4) var(--s-5) var(--s-6);
		/* The player's sizes (bigger on a TV), not the page's. */
		font-size: var(--t-0);
		background: var(--fondo);
		border-left: 1px solid var(--raia-forte);
	}

	header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		position: sticky;
		top: calc(-1 * var(--s-4));
		z-index: 1;
		margin: calc(-1 * var(--s-4)) calc(-1 * var(--s-5)) 0;
		padding: var(--s-3) var(--s-3) var(--s-3) var(--s-5);
		background: inherit;
		border-bottom: 1px solid var(--raia);
	}

	h2 {
		font-family: var(--font-display);
		font-size: var(--t-3);
		font-weight: 700;
		line-height: 1;
	}

	/* The panel's parts, one under another like the lines of a board. */
	.panel > :global(section) {
		padding-block: var(--s-5);
	}

	.panel > :global(section + section) {
		border-top: 1px solid var(--raia);
	}
</style>
