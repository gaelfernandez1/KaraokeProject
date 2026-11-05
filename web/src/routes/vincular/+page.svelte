<script lang="ts">
	// Opened from the pairing QR code: pairs this device with the laptop, then off to the songs.
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { ApiError, pairDevice } from '#lib/api';
	import { owner } from '#lib/devices/owner.svelte.js';
	import { i18n } from '#lib/i18n';
	import Button from '#lib/ui/Button.svelte';

	const t = $derived(i18n.t.device);
	let result = $state<'pairing' | 'paired' | 'failed'>('pairing');
	let reason = $state('');

	$effect(() => {
		const code = page.url.searchParams.get('code') ?? '';
		pairDevice(code)
			.then(() => {
				result = 'paired';
				owner.refresh();
			})
			.catch((error: unknown) => {
				result = 'failed';
				reason =
					error instanceof ApiError && error.code === 'locked'
						? t.locked
						: error instanceof ApiError && error.status === 0
							? i18n.t.errors.network
							: t.badCode;
			});
	});
</script>

<svelte:head><title>{t.pair} · Foliada</title></svelte:head>

<main class="pair">
	<h1>{t.title}</h1>
	<p role="status">
		{result === 'pairing' ? t.pairing : result === 'paired' ? t.paired : reason}
	</p>
	{#if result === 'paired'}
		<Button variant="primary" size="l" icon="songs" href={resolve('/')}>{t.toLibrary}</Button>
	{:else if result === 'failed'}
		<Button size="l" href={resolve('/axustes#aparello')}>{t.goPair}</Button>
	{/if}
</main>

<style>
	.pair {
		display: grid;
		align-content: start;
		justify-items: start;
		gap: var(--s-5);
		max-width: var(--page-max);
		margin: 0 auto;
		padding: var(--s-6) var(--page-x) var(--s-9);
	}

	h1 {
		font-family: var(--font-display);
		font-size: var(--t-5);
		font-weight: 900;
		line-height: 0.9;
	}

	p {
		max-width: 40rem;
		font-size: var(--t-1);
		font-weight: 700;
	}
</style>
