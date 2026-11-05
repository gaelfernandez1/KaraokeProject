<script lang="ts">
	/*
	 * Main navigation: a tab bar at the bottom on phones (thumb reach), a top bar with the name
	 * and the main action on wider screens. Only one of the two shows at a time.
	 */
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { i18n } from '#lib/i18n';
	import Icon, { type IconName } from './Icon.svelte';
	import Wordmark from './Wordmark.svelte';

	interface Props {
		/** 0–1 while a karaoke is being made, shown on the Create item. */
		working?: number | null;
	}

	let { working = null }: Props = $props();

	const t = $derived(i18n.t.nav);
	const items = $derived<{ href: string; label: string; icon: IconName; match: string[] }[]>([
		{ href: resolve('/'), label: t.songs, icon: 'songs', match: ['/'] },
		{ href: resolve('/crear'), label: t.create, icon: 'create', match: ['/crear'] },
		{ href: resolve('/festa'), label: t.party, icon: 'party', match: ['/festa'] },
		{ href: resolve('/axustes'), label: t.settings, icon: 'settings', match: ['/axustes'] }
	]);
	const active = (match: string[]) => match.includes(page.route.id ?? '');
</script>

<header class="topbar">
	<a class="brand" href={resolve('/')}><Wordmark animate size="var(--t-3)" /></a>
	<nav aria-label={t.label}>
		<ul>
			{#each items.filter((i) => i.icon !== 'create') as item (item.href)}
				<li>
					<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- built with resolve() -->
					<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- built with resolve() -->
					<a href={item.href} aria-current={active(item.match) ? 'page' : undefined}>{item.label}</a
					>
				</li>
			{/each}
		</ul>
	</nav>
	{#if !active(['/crear'])}
		<a
			class="create"
			href={resolve('/crear')}
			aria-current={active(['/crear']) ? 'page' : undefined}
		>
			<Icon name="create" size={1.2} />
			<span>{i18n.t.create.submit}</span>
			{#if working !== null}<span class="ring" style:--p={working} aria-hidden="true"></span>{/if}
		</a>
	{/if}
</header>

<nav class="tabbar" aria-label={t.label}>
	<ul>
		{#each items as item (item.href)}
			<li>
				<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- built with resolve() -->
				<a href={item.href} aria-current={active(item.match) ? 'page' : undefined}>
					<span class="tab-icon">
						<Icon name={item.icon} size={1.5} />
						{#if item.icon === 'create' && working !== null}
							<span class="ring" style:--p={working} aria-hidden="true"></span>
						{/if}
					</span>
					<span>{item.label}</span>
				</a>
			</li>
		{/each}
	</ul>
</nav>

<style>
	ul {
		display: flex;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	a {
		text-decoration: none;
	}

	/* A progress ring around the Create icon while a karaoke is being made. */
	.ring {
		position: absolute;
		inset: -6px;
		border-radius: 50%;
		background: conic-gradient(var(--farol) calc(var(--p) * 360deg), var(--linha) 0);
		mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 calc(100% - 2.5px));
	}

	.topbar {
		display: none;
	}

	.tabbar {
		position: fixed;
		inset: auto 0 0 0;
		z-index: 20;
		padding-bottom: env(safe-area-inset-bottom);
		background: var(--noite-funda);
		border-top: 1px solid var(--linha);
	}

	.tabbar li {
		flex: 1;
	}

	.tabbar a {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2px;
		min-height: 4rem;
		padding: var(--s-2) var(--s-1) var(--s-2);
		font-size: var(--t--1);
		font-weight: 600;
		color: var(--papel-suave);
	}

	.tab-icon {
		position: relative;
		display: grid;
		place-items: center;
	}

	.tabbar a[aria-current='page'] {
		color: var(--farol);
		--icon-accent: var(--papel);
	}

	@media (min-width: 45em) {
		.tabbar {
			display: none;
		}

		.topbar {
			position: sticky;
			top: 0;
			z-index: 20;
			display: flex;
			align-items: center;
			gap: var(--s-6);
			max-width: var(--page-max);
			margin: 0 auto;
			padding: var(--s-4) var(--page-x);
			background: var(--noite);
		}

		.brand {
			display: block;
			padding-block: var(--s-1);
		}

		.topbar ul {
			gap: var(--s-2);
		}

		.topbar nav a {
			position: relative;
			display: block;
			padding: var(--s-3) var(--s-3);
			font-weight: 700;
			color: var(--papel-suave);
		}

		.topbar nav a:hover {
			color: var(--papel);
		}

		.topbar nav a[aria-current='page'] {
			color: var(--papel);
		}

		/* The current page's link is underlined in the sung colour. */
		.topbar nav a[aria-current='page']::after {
			content: '';
			position: absolute;
			inset: auto var(--s-3) 0.35rem;
			height: 3px;
			border-radius: 2px;
			background: var(--farol);
		}

		.create {
			position: relative;
			display: inline-flex;
			align-items: center;
			gap: var(--s-2);
			min-height: var(--target);
			margin-left: auto;
			padding: 0 var(--s-5);
			border-radius: var(--radius-control);
			background: var(--farol);
			color: var(--noite);
			font-weight: 800;
		}

		.create:hover {
			background: color-mix(in oklch, var(--farol), white 22%);
		}

		.create .ring {
			inset: auto var(--s-3) -8px;
			height: 4px;
			border-radius: 2px;
			background: linear-gradient(
				to right,
				var(--farol) calc(var(--p) * 100%),
				var(--linha) calc(var(--p) * 100%)
			);
			mask: none;
		}
	}
</style>
