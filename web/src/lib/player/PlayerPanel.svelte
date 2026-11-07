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
		gap: var(--s-5);
		width: 100%;
		max-height: 100%;
		overflow-y: auto;
		padding: var(--s-4) var(--s-5) var(--s-6);
		background: var(--noite);
		border-left: 1px solid var(--linha);
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
	}

	h2 {
		font-family: var(--font-display);
		font-size: var(--t-3);
		font-weight: 900;
	}
</style>
