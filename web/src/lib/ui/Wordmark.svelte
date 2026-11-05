<script lang="ts" module>
	/** Provisional name; one place to change it. */
	export const APP_NAME = 'Foliada';
	const SEEN_KEY = 'foliada.sung';
</script>

<script lang="ts">
	/*
	 * The name, set in the poster face. The first time it shows in a visit it is "sung": it fills
	 * with the lyric colour from left to right, once, the way every line of a song does.
	 */
	import { untrack } from 'svelte';
	import { prefersReducedMotion } from 'svelte/motion';

	interface Props {
		animate?: boolean;
		size?: string;
	}

	let { animate = false, size = 'var(--t-3)' }: Props = $props();

	function alreadySung(): boolean {
		try {
			return sessionStorage.getItem(SEEN_KEY) === '1';
		} catch {
			return false;
		}
	}

	// Decided once, when it first shows.
	const sing = untrack(() => animate) && !prefersReducedMotion.current && !alreadySung();
	if (sing) {
		try {
			sessionStorage.setItem(SEEN_KEY, '1');
		} catch {
			// Without storage it sings on every visit, which is fine.
		}
	}
</script>

<span class="wordmark" class:sing style:font-size={size}>
	<span class="base">{APP_NAME}</span>
	<span class="fill" aria-hidden="true">{APP_NAME}</span>
</span>

<style>
	.wordmark {
		position: relative;
		display: inline-block;
		font-family: var(--font-display);
		font-weight: 900;
		line-height: 0.9;
		letter-spacing: 0.01em;
		white-space: nowrap;
	}

	.base {
		color: var(--papel);
	}

	.fill {
		position: absolute;
		inset: 0;
		color: var(--farol);
		clip-path: inset(-20% 0 -20% 0);
	}

	.sing .fill {
		animation: sing 1.4s 0.25s cubic-bezier(0.4, 0, 0.6, 1) both;
	}

	@keyframes sing {
		from {
			clip-path: inset(-20% 100% -20% 0);
		}
		to {
			clip-path: inset(-20% 0 -20% 0);
		}
	}
</style>
