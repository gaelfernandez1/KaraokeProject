<script lang="ts">
	// Living style guide (dev only): tokens, type and components in every state.
	import Button from '#lib/ui/Button.svelte';
	import Icon from '#lib/ui/Icon.svelte';
	import Slider from '#lib/ui/Slider.svelte';
	import SungText from '#lib/ui/SungText.svelte';
	import Wordmark from '#lib/ui/Wordmark.svelte';

	const COLORS = [
		['noite', '#16122E'],
		['noite-alta', '#221C45'],
		['noite-funda', '#0F0C22'],
		['linha', '#3A3266'],
		['papel', '#F3EFFA'],
		['papel-suave', '#B9B2D3'],
		['farol', '#FFC531'],
		['fucsia', '#FF5FAE'],
		['erro', '#FF7A6B'],
		['cantante-2', '#4FD1FF'],
		['cantante-3', '#FF6FB5'],
		['cantante-4', '#7CE38B']
	];
	const STEPS = ['t--1', 't-0', 't-1', 't-2', 't-3', 't-4', 't-5', 't-6'];
	const ICONS = [
		'songs',
		'create',
		'party',
		'settings',
		'play',
		'pause',
		'back5',
		'forward5',
		'search',
		'back',
		'close',
		'check',
		'edit',
		'download',
		'fullscreen',
		'tv',
		'sound',
		'minus',
		'plus',
		'upload',
		'link',
		'queue',
		'remote',
		'offline',
		'skip',
		'loop',
		'undo',
		'redo',
		'tap',
		'trash'
	] as const;

	let vocals = $state(0.15);
	let progress = $state(0.4);
</script>

<svelte:head><title>Estilo · Proxecto Karaoke en Galego</title></svelte:head>

<main>
	<h1><Wordmark size="var(--t-6)" /></h1>

	<section>
		<h2>Cor</h2>
		<ul class="swatches">
			{#each COLORS as [name, hex] (name)}
				<li><span style:background={hex}></span><b>{name}</b><small>{hex}</small></li>
			{/each}
		</ul>
	</section>

	<section>
		<h2>Tipos</h2>
		{#each STEPS as step (step)}
			<p style:font-size="var(--{step})" class:display={step >= 't-4'}>
				<small>{step}</small> Deixeiche janarme na pista de baile
			</p>
		{/each}
		<p class="poster-type">Ó PÉ DA PONTE VELLA · ÁÉÍÓÚ ÑÇ</p>
	</section>

	<section>
		<h2>Botóns</h2>
		<div class="row">
			<Button variant="primary" icon="create">Crear karaoke</Button>
			<Button variant="primary" size="l" icon="play">Cantar</Button>
			<Button>Cancelar</Button>
			<Button variant="ghost" icon="edit">Corrixir a letra</Button>
			<Button variant="danger" icon="trash">Borrar</Button>
			<Button variant="primary" disabled>Desactivado</Button>
			<Button iconOnly icon="pause">Pausa</Button>
			<Button iconOnly size="l" icon="fullscreen">Pantalla completa</Button>
		</div>
	</section>

	<section>
		<h2>Controis</h2>
		<div class="controls">
			<Slider label="Voz guía" value={vocals} oninput={(v) => (vocals = v)} />
			<Slider label="Progreso" value={progress} oninput={(v) => (progress = v)} />
			<Slider label="Desactivado" value={0.6} disabled />
		</div>
		<div class="sung">
			<SungText text="La Favorita" progress={0} as="h3" />
			<SungText text="La Favorita" {progress} as="h3" />
			<SungText text="La Favorita" progress={1} as="h3" />
		</div>
	</section>

	<section>
		<h2>Iconas</h2>
		<ul class="icons">
			{#each ICONS as name (name)}
				<li><Icon {name} size={2} /><small>{name}</small></li>
			{/each}
		</ul>
	</section>
</main>

<style>
	main {
		max-width: var(--page-max);
		margin: 0 auto;
		padding: var(--s-6) var(--page-x) var(--s-9);
		display: grid;
		gap: var(--s-8);
	}

	h2 {
		font-size: var(--t-1);
		margin-bottom: var(--s-4);
		color: var(--papel-suave);
	}

	.swatches,
	.icons {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr));
		gap: var(--s-4);
		padding: 0;
		list-style: none;
	}

	.swatches li {
		display: grid;
		gap: var(--s-1);
	}

	.swatches span {
		height: 4rem;
		border-radius: var(--radius-control);
		border: 1px solid var(--linha);
	}

	small {
		color: var(--papel-suave);
		font-size: var(--t--1);
	}

	section > p {
		margin-bottom: var(--s-2);
		line-height: 1.2;
	}

	.display {
		font-family: var(--font-display);
		font-weight: 900;
		line-height: 0.95;
	}

	.poster-type {
		font-family: var(--font-display);
		font-weight: 900;
		font-size: var(--t-5);
		line-height: 0.88;
		color: var(--farol);
	}

	.row {
		display: flex;
		flex-wrap: wrap;
		gap: var(--s-3);
		align-items: center;
	}

	.controls {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
		gap: var(--s-5);
	}

	.sung {
		margin-top: var(--s-5);
		display: grid;
		gap: var(--s-2);
		font-family: var(--font-display);
		font-size: var(--t-4);
	}

	.icons li {
		display: grid;
		justify-items: center;
		gap: var(--s-2);
		padding: var(--s-4);
		border: 1px solid var(--linha);
		border-radius: var(--radius-control);
	}
</style>
