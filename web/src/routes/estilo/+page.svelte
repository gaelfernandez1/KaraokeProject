<script lang="ts">
	/*
	 * Living style guide (dev only): the night's colours with their roles, the three faces and the
	 * type scale, and the components in their states, live, with the real tokens.
	 */
	import { listSongs, type SongSummary } from '#lib/api';
	import GlobeAnchor from '#lib/globe/GlobeAnchor.svelte';
	import SongRow from '#lib/library/SongRow.svelte';
	import Cover from '#lib/poster/Cover.svelte';
	import Button from '#lib/ui/Button.svelte';
	import Slider from '#lib/ui/Slider.svelte';
	import Switch from '#lib/ui/Switch.svelte';
	import Wordmark from '#lib/ui/Wordmark.svelte';

	const PALETTE: { group: string; tokens: [string, string][] }[] = [
		{
			group: 'A noite',
			tokens: [
				['fondo', 'O chan de todo: o mar e o ceo, case negros, cun punto de azul'],
				['fondo-2', 'Un chanzo por riba'],
				['fondo-3', 'O máis fondo'],
				['raia', 'O fío entre dúas cousas'],
				['raia-forte', 'O bordo dos controis'],
				['texto', 'As palabras'],
				['texto-2', 'O texto secundario'],
				['texto-3', 'As notas']
			]
		},
		{
			group: 'A bandeira: branco e ceo',
			tokens: [
				['accion', 'A acción principal de cada pantalla: branco sobre a noite'],
				['ceo', 'O escollido e o foco, e a costa no globo'],
				['ceo-fondo', 'O chan do escollido']
			]
		},
		{
			group: 'A luz',
			tokens: [
				['ouro', 'Aceso: o cantado, o de agora, as luces das vilas'],
				['ouro-forte', 'O ouro máis fondo'],
				['erro', 'Os erros']
			]
		},
		{
			group: 'As persoas da festa',
			tokens: [
				['cantante-1', 'Cantante 1: nin ouro nin ceo'],
				['cantante-2', 'Cantante 2'],
				['cantante-3', 'Cantante 3'],
				['cantante-4', 'Cantante 4']
			]
		}
	];

	const FACES = [
		{
			name: 'Unbounded',
			font: 'var(--font-display)',
			use: 'O menú, os títulos e os nomes: palabras grandes, nunca liñas longas.',
			sample: 'Deixeiche a ventá aberta'
		},
		{
			name: 'Figtree',
			font: 'var(--font-text)',
			use: 'Todo o demais: texto, etiquetas, botóns.',
			sample: 'Sube a canción ou pega unha ligazón; a letra é opcional.'
		},
		{
			name: 'Martian Mono',
			font: 'var(--font-data)',
			use: 'As cifras que se miden ou se len en voz alta: horas, tempos, o código da festa.',
			sample: '2 762 451  08:23  WQPN'
		}
	];

	const SCALE = ['--t--1', '--t-0', '--t-1', '--t-2', '--t-3', '--t-4', '--t-5', '--t-6'];

	let songs = $state.raw<SongSummary[]>([]);
	let on = $state(true);
	let volume = $state(0.4);
	let choice = $state('gl');
	listSongs()
		.then((list) => (songs = list.slice(0, 4)))
		.catch(() => {});
</script>

<svelte:head><title>Guía de estilo · Karaoke en Galego</title></svelte:head>

<main class="guide">
	<header class="top">
		<div>
			<h1><Wordmark size="min(var(--t-3), 7.2vw)" /></h1>
			<p class="lead">
				Galicia de noite vista dende o Atlántico: un mar case negro, branco e azul celeste para as
				palabras e o escollido, e o ouro dunha ventá acesa para o que está en marcha.
			</p>
		</div>
		<div class="globe"><GlobeAnchor label="O globo de Galicia de noite" turnable /></div>
	</header>

	<section>
		<h2>Cor</h2>
		<div class="palette">
			{#each PALETTE as { group, tokens } (group)}
				<div class="group">
					<h3>{group}</h3>
					<ul>
						{#each tokens as [token, role] (token)}
							<li>
								<span class="chip" style:background="var(--{token})"></span>
								<span class="token data">--{token}</span>
								<span class="role">{role}</span>
							</li>
						{/each}
					</ul>
				</div>
			{/each}
		</div>
	</section>

	<section>
		<h2>Tipos</h2>
		<div class="stack">
			<ul class="faces">
				{#each FACES as face (face.name)}
					<li>
						<p class="sample" style:font-family={face.font}>{face.sample}</p>
						<p class="role"><strong>{face.name}</strong> {face.use}</p>
					</li>
				{/each}
			</ul>
			<ul class="scale">
				{#each SCALE as step (step)}
					<li>
						<span class="token data">{step}</span>
						<span style:font-size="var({step})">Cantar</span>
					</li>
				{/each}
			</ul>
		</div>
	</section>

	<section>
		<h2>Botóns</h2>
		<div class="stack">
			<div class="row">
				<Button variant="primary" size="l" icon="play">Cantar</Button>
				<Button variant="primary" icon="create">Crear karaoke</Button>
				<Button icon="loop">Tentar de novo</Button>
				<Button variant="ghost" icon="edit">Corrixir a letra</Button>
				<Button variant="danger" icon="trash">Borrar a canción</Button>
				<Button disabled>Gardar</Button>
				<Button iconOnly icon="pause">Parar</Button>
			</div>
			<p class="role">
				Branco para a acción principal de cada pantalla, só unha; o resto, translúcidos. Din un
				verbo e o que fan.
			</p>
		</div>
	</section>

	<section>
		<h2>Controis</h2>
		<div class="stack">
			<div class="row">
				<div class="choices" role="radiogroup" aria-label="Idioma">
					{#each [['gl', 'Galego'], ['es', 'Castellano'], ['en', 'English']] as [code, name] (code)}
						<button
							type="button"
							role="radio"
							aria-checked={choice === code}
							onclick={() => (choice = code ?? 'gl')}>{name}</button
						>
					{/each}
				</div>
				<Switch bind:checked={on} label="Aceso" />
			</div>
			<div class="narrow">
				<Slider label="Voz guía" value={volume} oninput={(v) => (volume = v)} />
			</div>
			<label class="field">
				<span>Título</span>
				<input type="text" placeholder="Ó pé da ponte vella" />
			</label>
		</div>
	</section>

	<section>
		<h2>Cancións</h2>
		<div class="stack">
			<ul class="rows">
				{#each songs as song, i (song.id)}
					<li><SongRow {song} href="#top" selected={i === 0} /></li>
				{/each}
			</ul>
			<div class="covers">
				{#each songs.slice(0, 2) as song (song.id)}
					<div class="plate"><Cover {song} shape="plate" awake /></div>
				{/each}
				{#each songs.slice(0, 3) as song (song.id)}
					<div class="square wake"><Cover {song} /></div>
				{/each}
			</div>
			<p class="role">
				A fila sinalada sae da noite; a escollida, en celeste. Sen imaxe, cada canción ten o seu
				propio ceo, sempre o mesmo.
			</p>
		</div>
	</section>

	<section>
		<h2>Paneis</h2>
		<div class="stack">
			<div class="panel sample-panel">
				<div>
					<p class="role">Cancións</p>
					<p class="figure data">24</p>
				</div>
				<div>
					<p class="role">Música</p>
					<p class="figure data">1 h 34 min</p>
				</div>
				<div>
					<p class="role">Na cola</p>
					<p class="figure data">3</p>
				</div>
			</div>
			<p class="role">
				O que flota sobre o globo deixa ver a noite a través: cantos redondos, un fío claro e a luz
				de dentro, en ouro, só para as cifras que importan.
			</p>
		</div>
	</section>
</main>

<style>
	.guide {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: var(--s-6);
		max-width: var(--page-max);
		margin: 0 auto;
		padding: var(--s-6) var(--page-x) var(--s-9);
	}

	.top {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		align-items: center;
		gap: var(--s-5);
	}

	.globe {
		display: none;
	}

	.lead {
		max-width: 46rem;
		margin-top: var(--s-3);
		font-size: var(--t-1);
		color: var(--texto-2);
	}

	section {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: var(--s-4);
		padding-top: var(--s-5);
		border-top: 1px solid var(--raia);
	}

	h2 {
		font-family: var(--font-display);
		font-size: var(--t-1);
		font-weight: 600;
		letter-spacing: -0.02em;
	}

	h3 {
		font-size: var(--t-0);
		font-weight: 650;
	}

	@media (min-width: 64em) {
		.top {
			grid-template-columns: minmax(0, 1fr) clamp(14rem, 22vw, 20rem);
		}

		.globe {
			display: block;
		}

		section {
			grid-template-columns: minmax(12rem, 16rem) minmax(0, 1fr);
			column-gap: var(--s-7);
			align-items: start;
		}
	}

	.stack {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: var(--s-5);
		min-width: 0;
	}

	.role {
		max-width: 46rem;
		font-size: var(--t--1);
		color: var(--texto-2);
	}

	.role strong {
		margin-right: 0.4em;
		color: var(--texto);
	}

	.token {
		font-size: var(--t--1);
		color: var(--ceo);
	}

	ul {
		margin: 0;
		padding: 0;
		list-style: none;
	}

	/* Colour: one line per token. */
	.palette {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 24rem), 1fr));
		gap: var(--s-5) var(--s-7);
	}

	.group {
		display: grid;
		gap: var(--s-3);
		align-content: start;
	}

	.group ul {
		display: grid;
		gap: var(--s-2);
	}

	.group li {
		display: grid;
		grid-template-columns: 2.5rem minmax(0, 1fr);
		grid-template-areas:
			'chip token'
			'chip role';
		column-gap: var(--s-3);
		align-items: center;
	}

	.chip {
		grid-area: chip;
		width: 2.5rem;
		height: 2.5rem;
		border: 1px solid var(--raia-forte);
		border-radius: var(--radius-control);
	}

	.group .role {
		grid-area: role;
	}

	/* Type. */
	.faces {
		display: grid;
		gap: var(--s-5);
	}

	.faces li {
		display: grid;
		gap: var(--s-1);
	}

	.sample {
		font-size: var(--t-3);
		font-weight: 600;
		line-height: 1.15;
		letter-spacing: -0.02em;
		overflow-wrap: anywhere;
	}

	.scale {
		display: grid;
		gap: var(--s-2);
	}

	.scale li {
		display: grid;
		grid-template-columns: 5rem minmax(0, 1fr);
		align-items: baseline;
		gap: var(--s-4);
		font-family: var(--font-display);
		font-weight: 600;
		line-height: 1.1;
		letter-spacing: -0.03em;
	}

	.row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--s-3);
	}

	/* One choice of three: a single control, the chosen part raised in sky blue. */
	.choices {
		display: flex;
		gap: 2px;
		padding: 4px;
		border: 1px solid var(--raia);
		border-radius: var(--radius-pill);
		background: var(--panel-claro);
	}

	.choices button {
		min-height: 2.5rem;
		padding: 0 var(--s-4);
		border: 0;
		border-radius: var(--radius-pill);
		background: transparent;
		font-weight: 650;
		color: var(--texto-2);
		transition:
			background-color var(--dur-1) ease,
			color var(--dur-1) ease;
	}

	.choices button[aria-checked='true'] {
		background: var(--ceo);
		color: var(--fondo);
	}

	.narrow {
		max-width: 26rem;
	}

	.field {
		display: grid;
		gap: var(--s-2);
		max-width: 26rem;
		font-weight: 650;
	}

	.field input {
		min-height: var(--target);
		padding: 0 var(--s-4);
		border: 1px solid var(--raia-forte);
		border-radius: var(--radius-control);
		background: var(--panel-claro);
		font-weight: 400;
	}

	.field input:focus {
		outline: none;
		border-color: var(--ceo);
		box-shadow: 0 0 0 1px var(--ceo);
	}

	.rows {
		display: grid;
		gap: 2px;
		max-width: 52rem;
		container-type: inline-size;
	}

	.covers {
		display: flex;
		flex-wrap: wrap;
		align-items: end;
		gap: var(--s-4);
	}

	.plate {
		width: 11rem;
	}

	.square {
		width: 5rem;
	}

	.sample-panel {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
		gap: var(--s-4) var(--s-6);
		max-width: 46rem;
		padding: var(--s-5);
	}

	.figure {
		font-size: var(--t-2);
		color: var(--ouro);
	}
</style>
