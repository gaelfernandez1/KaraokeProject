<script lang="ts">
	// Test page for the animated lyrics on real devices: any package, any theme, and frames the
	// size of a phone, a laptop or a TV. `?t=12.3` freezes the lyrics at that moment without audio
	// (for screenshots); `?paquete=`, `?tema=` and `?marco=` choose the rest, and `?fondo=liso`
	// swaps the stand-in video background for a plain one.
	import type { KaraokeDoc, PlaybackClock } from '#lib/contracts';
	import { AudioEngine } from '#lib/audio/engine.js';
	import { DEFAULT_THEME, Lyrics, THEMES, normalizeDoc } from '#lib/lyrics';

	const FRAMES: Record<string, { label: string; size: [number, number] | null }> = {
		completa: { label: 'Pantalla completa', size: null },
		mobil: { label: 'Móbil (390 × 844)', size: [390, 844] },
		portatil: { label: 'Portátil (1440 × 900)', size: [1440, 900] },
		tele: { label: 'Tele (1920 × 1080)', size: [1920, 1080] },
		vertical: { label: 'Vídeo vertical (1080 × 1920)', size: [1080, 1920] }
	};

	const params = new URLSearchParams(location.search);
	// Frozen time for screenshots and tests, which can move it with window.__lyricsTime(t).
	const frozenAt = params.has('t') ? Number(params.get('t')) : null;
	let frozen = $state(frozenAt);
	const plain = params.get('fondo') === 'liso';
	if (frozenAt !== null) {
		(window as unknown as { __lyricsTime: (t: number) => void }).__lyricsTime = (t) => (frozen = t);
	}

	let packages = $state<string[]>([]);
	let chosen = $state(params.get('paquete') ?? '');
	let themeId = $state(params.get('tema') ?? DEFAULT_THEME);
	let frameId = $state(params.get('marco') ?? 'completa');
	let doc = $state.raw<KaraokeDoc | null>(null);
	let message = $state('');
	let now = $state(frozenAt ?? 0);
	let playing = $state(false);
	let vocals = $state(1);
	let stage = $state<HTMLElement | null>(null);
	let stageWidth = $state(0);
	let stageHeight = $state(0);

	let context: AudioContext | null = null;
	let engine: AudioEngine | null = null;
	const clock: PlaybackClock = { now: () => frozen ?? engine?.now() ?? 0 };

	const theme = $derived(THEMES[themeId] ?? THEMES[DEFAULT_THEME]);
	const frame = $derived(FRAMES[frameId] ?? FRAMES.completa);
	const scale = $derived.by(() => {
		if (!frame.size || stageWidth === 0) return 1;
		return Math.min(1, stageWidth / frame.size[0], stageHeight / frame.size[1]);
	});

	$effect(() => {
		fetch('/paquetes/index.json')
			.then((response) => response.json())
			.then((ids: string[]) => {
				packages = ids;
				if (!ids.includes(chosen)) chosen = ids[0] ?? '';
			})
			.catch(() => (message = 'Non hai paquetes: esta páxina só funciona con `pnpm dev`.'));
	});

	// Load the lyrics as soon as a package is chosen; the audio waits for a tap (browsers ask).
	$effect(() => {
		const id = chosen;
		if (!id) return;
		engine?.pause();
		doc = null;
		fetch(`/paquetes/${id}/karaoke.json`)
			.then((response) => {
				if (!response.ok) throw new Error(`HTTP ${response.status}`);
				return response.json();
			})
			.then((loaded: KaraokeDoc) => {
				if (id === chosen) doc = normalizeDoc(loaded);
			})
			.catch((error) => (message = `Non se puido cargar ${id}: ${error}`));
	});

	$effect(() => {
		let raf = requestAnimationFrame(function tick() {
			now = clock.now();
			playing = engine?.playing ?? false;
			raf = requestAnimationFrame(tick);
		});
		return () => cancelAnimationFrame(raf);
	});

	async function toggle() {
		if (!doc) return;
		if (engine?.playing) {
			engine.pause();
			return;
		}
		if (!engine) {
			context = new AudioContext();
			engine = new AudioEngine(context);
		}
		const base = `/paquetes/${chosen}/`;
		if (engine.duration === 0 || loadedFor !== chosen) {
			message = 'Cargando o audio…';
			try {
				await engine.load({
					instrumental: base + doc.audio.instrumental,
					vocals: doc.audio.vocals ? base + doc.audio.vocals : null
				});
				engine.setVocalVolume(vocals);
				loadedFor = chosen;
				message = '';
			} catch (error) {
				message = `Non se puido cargar o audio: ${error}`;
				return;
			}
		}
		await engine.play();
	}
	let loadedFor = '';

	function seek(event: Event) {
		engine?.seek(Number((event.target as HTMLInputElement).value));
	}

	function setVocals(event: Event) {
		vocals = Number((event.target as HTMLInputElement).value);
		engine?.setVocalVolume(vocals);
	}

	const clockText = (seconds: number) =>
		`${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}.${Math.floor((seconds % 1) * 10)}`;
</script>

<svelte:head><title>Proba da letra</title></svelte:head>

<main class:frozen={frozen !== null}>
	{#if frozen === null}
		<header>
			<label>
				Canción
				<select bind:value={chosen}>
					{#each packages as id (id)}<option value={id}>{id}</option>{/each}
				</select>
			</label>
			<label>
				Tema
				<select bind:value={themeId}>
					{#each Object.keys(THEMES) as id (id)}<option value={id}>{THEMES[id].name}</option>{/each}
				</select>
			</label>
			<label>
				Pantalla
				<select bind:value={frameId}>
					{#each Object.entries(FRAMES) as [id, f] (id)}<option value={id}>{f.label}</option>{/each}
				</select>
			</label>
			<button onclick={toggle} disabled={!doc}>{playing ? 'Pausa' : 'Reproducir'}</button>
			<input
				class="seek"
				type="range"
				min="0"
				max={doc?.duration ?? 0}
				step="0.1"
				value={now}
				oninput={seek}
				aria-label="Posición"
			/>
			<span class="time">{clockText(now)}</span>
			<label>
				Voz guía
				<input type="range" min="0" max="1" step="0.05" value={vocals} oninput={setVocals} />
			</label>
			{#if message}<p class="message">{message}</p>{/if}
		</header>
	{/if}

	<section
		class="stage"
		bind:this={stage}
		bind:clientWidth={stageWidth}
		bind:clientHeight={stageHeight}
	>
		<div
			class="screen"
			class:plain
			class:framed={frame.size !== null}
			style:width={frame.size ? `${frame.size[0]}px` : '100%'}
			style:height={frame.size ? `${frame.size[1]}px` : '100%'}
			style:transform={frame.size ? `scale(${scale})` : 'none'}
		>
			{#if doc}
				<Lyrics {doc} {theme} {clock} />
			{/if}
		</div>
	</section>
</main>

<style>
	:global(html, body) {
		margin: 0;
		height: 100%;
		background: #0b0b12;
		color: #eee;
		font-family: system-ui, sans-serif;
	}

	main {
		display: flex;
		flex-direction: column;
		height: 100dvh;
	}

	header {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem 1rem;
		align-items: center;
		padding: 0.5rem 1rem;
		background: #15151f;
	}

	label {
		display: flex;
		gap: 0.4rem;
		align-items: center;
	}

	.seek {
		flex: 1 1 12rem;
	}

	.time {
		font-variant-numeric: tabular-nums;
	}

	.message {
		flex-basis: 100%;
		margin: 0;
		color: #ffb4a8;
	}

	.stage {
		position: relative;
		flex: 1;
		overflow: hidden;
		display: grid;
		place-items: center;
	}

	.screen {
		position: relative;
		flex: none;
		/* Stand-in for a video background. */
		background:
			radial-gradient(circle at 30% 20%, #3b2a6b, transparent 60%),
			radial-gradient(circle at 80% 90%, #1d4b6b, transparent 55%), #141428;
	}

	.screen.plain {
		background: #141428;
	}

	.screen.framed {
		transform-origin: center;
		box-shadow: 0 0 0 1px #333;
	}

	.frozen .stage {
		display: block;
	}

	.frozen .screen {
		transform: none !important;
	}
</style>
