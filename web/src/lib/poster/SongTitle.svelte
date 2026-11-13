<script lang="ts">
	/*
	 * A song's title with its version tag ("demo sintética", "en directo"…) set small and quiet
	 * after it, as on the posters; when space runs out the tag goes first.
	 */
	import { splitTitle } from './fit';

	interface Props {
		title: string;
		/** Leave the tag out altogether (where the poster beside it already shows it). */
		bare?: boolean;
	}

	let { title, bare = false }: Props = $props();
	const parts = $derived(splitTitle(title));
</script>

<span class="song-title"
	><span class="main">{parts.main}</span>{#if parts.tag && !bare}<span class="tag">
			{parts.tag}</span
		>{/if}</span
>

<style>
	.song-title {
		display: inline-flex;
		align-items: baseline;
		gap: 0.4em;
		max-width: 100%;
		min-width: 0;
	}

	.main {
		flex: 0 0 auto;
		max-width: 100%;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.tag {
		flex: 0 1 auto;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-family: var(--font-text);
		font-size: max(0.75rem, 0.42em);
		font-weight: 700;
		letter-spacing: 0;
		color: var(--texto-2);
	}
</style>
