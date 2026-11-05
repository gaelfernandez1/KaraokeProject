<script lang="ts">
	/*
	 * Text that fills with the "sung" colour from left to right, like a lyric line being sung.
	 * The app's way of showing progress and state. A clipped copy over the text, so changing
	 * the progress never moves layout. Single line: longer text is cut with an ellipsis.
	 */
	interface Props {
		text: string;
		/** 0 to 1. */
		progress: number;
		/** Tag for the text, for headings. */
		as?: 'span' | 'h1' | 'h2' | 'h3' | 'p';
		class?: string;
	}

	let { text, progress, as = 'span', class: className = '' }: Props = $props();
	const clamped = $derived(Math.min(1, Math.max(0, progress)));
</script>

<svelte:element this={as} class="sung-text {className}" style:--p={clamped}>
	<span class="base">{text}</span>
	<span class="fill" aria-hidden="true">{text}</span>
</svelte:element>

<style>
	.sung-text {
		position: relative;
		display: block;
		min-width: 0;
	}

	.base,
	.fill {
		display: block;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.base {
		color: var(--sung-unsung, var(--papel));
	}

	.fill {
		position: absolute;
		inset: 0;
		color: var(--sung-color, var(--farol));
		clip-path: inset(-20% calc((1 - var(--p)) * 100%) -20% 0);
		transition: clip-path var(--dur-2) linear;
	}
</style>
