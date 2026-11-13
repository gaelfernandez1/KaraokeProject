<script lang="ts">
	import '../lib/ui/styles/tokens.css';
	import '../lib/ui/styles/fonts.css';
	import '../lib/ui/styles/base.css';
	import displayFont from '../lib/ui/fonts/Unbounded.woff2?url';
	import textFont from '../lib/ui/fonts/Figtree.woff2?url';
	import favicon from '#lib/assets/favicon.svg';
	import { onNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { i18n, initLocale } from '#lib/i18n';
	import { jobs } from '#lib/create/jobs.svelte.js';
	import Stage from '#lib/globe/Stage.svelte';
	import Nav from '#lib/ui/Nav.svelte';
	import { chrome } from '#lib/ui/chrome.svelte.js';
	import { watchForUpdate } from '#lib/offline/register.js';
	import Button from '#lib/ui/Button.svelte';
	import { prefersReducedMotion } from 'svelte/motion';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	initLocale();
	// Karaoke jobs keep being followed from any screen (the Create tab shows their progress).
	void jobs.refresh();

	// A new version waits until the singer says so: an update must never cut a song.
	let applyUpdate = $state<(() => void) | null>(null);
	watchForUpdate((apply) => (applyUpdate = apply));

	/** Screens that take the whole viewport and bring their own controls. */
	const IMMERSIVE = ['/cantar/[id]', '/festa/[code]', '/editar/[id]', '/proba-letra'];
	const immersive = $derived(IMMERSIVE.includes(page.route.id ?? '') || chrome.immersive);

	// Page changes cross-fade (and shared elements morph) where the browser can.
	onNavigate((navigation) => {
		if (!document.startViewTransition || prefersReducedMotion.current || navigation.shallow) return;
		return new Promise((resolve) => {
			document.startViewTransition(async () => {
				resolve();
				await navigation.complete;
			});
		});
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<link rel="preload" href={displayFont} as="font" type="font/woff2" crossorigin="anonymous" />
	<link rel="preload" href={textFont} as="font" type="font/woff2" crossorigin="anonymous" />
</svelte:head>

<Stage />

{#if !immersive}<Nav working={jobs.working} home={page.route.id === '/'} />{/if}

<div class="app" class:immersive>
	{@render children()}
</div>

{#if applyUpdate && !immersive}
	<div class="update" role="status">
		<p>{i18n.t.common.updateReady}</p>
		<Button variant="primary" onclick={() => applyUpdate?.()}>{i18n.t.common.update}</Button>
	</div>
{/if}

<style>
	.app {
		/* Room for the phone tab bar. */
		padding-bottom: calc(4rem + env(safe-area-inset-bottom));
	}

	.update {
		position: fixed;
		z-index: 30;
		left: 50%;
		bottom: calc(5rem + env(safe-area-inset-bottom));
		transform: translateX(-50%);
		display: flex;
		align-items: center;
		gap: var(--s-4);
		width: max-content;
		max-width: calc(100% - 2 * var(--page-x));
		padding: var(--s-3) var(--s-3) var(--s-3) var(--s-5);
		border-radius: var(--radius-pill);
		background: var(--accion);
		color: var(--accion-texto);
		font-weight: 700;
		box-shadow: var(--sombra);
	}

	@media (min-width: 45em) {
		.update {
			bottom: var(--s-6);
		}
	}

	.app.immersive {
		padding-bottom: 0;
	}

	@media (min-width: 45em) {
		.app {
			padding-bottom: 0;
		}
	}
</style>
