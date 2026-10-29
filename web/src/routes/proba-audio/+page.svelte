<script lang="ts">
	// Test bench for the audio engine on real devices: playback, guide vocals, key, latency and
	// its calibration. The lyrics here are plain text to judge sync; the real renderer is C5's.
	import type { KaraokeDoc } from '#lib/contracts';
	import { AudioEngine } from '#lib/audio/engine.js';
	import { clickTimes, estimateLatency, manualOffset } from '#lib/audio/calibration.js';

	const OFFSET_KEY = 'karaoke.latency-offset-ms';

	let context: AudioContext | null = null;
	let engine: AudioEngine | null = null;
	let doc = $state<KaraokeDoc | null>(null);
	let packages = $state<string[]>([]);
	let chosen = $state('');
	let message = $state('');
	let now = $state(0);
	let playing = $state(false);
	let vocals = $state(1);
	let pitch = $state(0);
	let offsetMs = $state(readOffset());
	let calibrating = $state(false);
	let clicks: number[] = [];
	let taps: number[] = [];

	const lineIndex = $derived(doc ? doc.lines.findLastIndex((l) => l.start - 0.4 <= now) : -1);
	const line = $derived(doc && lineIndex >= 0 ? doc.lines[lineIndex] : null);
	const next = $derived(doc ? doc.lines[lineIndex + 1] : null);

	$effect(() => {
		fetch('/paquetes/index.json')
			.then((response) => response.json())
			.then((ids: string[]) => {
				packages = ids;
				chosen = ids[0] ?? '';
			})
			.catch(() => (message = 'Non hai paquetes: esta páxina só funciona con `pnpm dev`.'));
	});

	$effect(() => {
		let frame = requestAnimationFrame(function tick() {
			if (engine) {
				now = engine.now();
				playing = engine.playing;
			}
			frame = requestAnimationFrame(tick);
		});
		return () => cancelAnimationFrame(frame);
	});

	function readOffset(): number {
		try {
			return Number(localStorage.getItem(OFFSET_KEY)) || 0;
		} catch {
			return 0;
		}
	}

	function setOffset(ms: number) {
		offsetMs = Math.round(ms);
		engine?.setManualOffset(offsetMs / 1000);
		try {
			localStorage.setItem(OFFSET_KEY, String(offsetMs));
		} catch {
			// Private windows can refuse storage; the offset still applies to this visit.
		}
	}

	function audio(): AudioEngine {
		context ??= new AudioContext();
		engine ??= new AudioEngine(context);
		return engine;
	}

	async function load() {
		const player = audio();
		player.pause();
		const base = `/paquetes/${chosen}/`;
		message = 'Cargando…';
		try {
			const response = await fetch(base + 'karaoke.json');
			if (!response.ok) throw new Error(`karaoke.json: HTTP ${response.status}`);
			const loaded = (await response.json()) as KaraokeDoc;
			await player.load({
				instrumental: base + loaded.audio.instrumental,
				vocals: loaded.audio.vocals ? base + loaded.audio.vocals : null
			});
			player.setManualOffset(offsetMs / 1000);
			player.setVocalVolume(vocals);
			await player.setPitch(pitch);
			doc = loaded;
			message = '';
		} catch (error) {
			message = `Non se puido cargar: ${error}`;
		}
	}

	async function toggle() {
		if (!engine || !doc) return;
		if (engine.playing) engine.pause();
		else await engine.play();
	}

	async function changePitch(step: number) {
		pitch = Math.max(-12, Math.min(12, pitch + step));
		try {
			await engine?.setPitch(pitch);
		} catch (error) {
			message = `O cambio de ton non funciona neste navegador: ${error}`;
		}
	}

	function beep(ctx: AudioContext, at: number) {
		const osc = ctx.createOscillator();
		const gain = ctx.createGain();
		osc.frequency.value = 1000;
		gain.gain.setValueAtTime(0.5, at);
		gain.gain.exponentialRampToValueAtTime(0.001, at + 0.05);
		osc.connect(gain).connect(ctx.destination);
		osc.start(at);
		osc.stop(at + 0.06);
	}

	async function calibrate() {
		const player = audio();
		player.pause();
		const ctx = context!;
		await ctx.resume();
		clicks = clickTimes(ctx.currentTime, 10, 0.6, 1);
		for (const at of clicks) beep(ctx, at);
		taps = [];
		calibrating = true;
		message = 'Toca o botón (ou a barra de espazo) xusto cando oias cada clic.';
		setTimeout(finishCalibration, (clicks[clicks.length - 1] - ctx.currentTime + 0.8) * 1000);
	}

	function tap() {
		if (calibrating && context) taps.push(context.currentTime);
	}

	function finishCalibration() {
		calibrating = false;
		const ctx = context!;
		const measured = estimateLatency(clicks, taps);
		if (measured === null) {
			message = 'Non quedou claro. Proba outra vez seguindo o ritmo dos clics.';
			return;
		}
		const reported = (ctx.outputLatency || 0) + (ctx.baseLatency || 0);
		setOffset(manualOffset(measured, reported) * 1000);
		message =
			`Retardo medido: ${Math.round(measured * 1000)} ms ` +
			`(o navegador informa de ${Math.round(reported * 1000)} ms).`;
	}

	function onKey(event: KeyboardEvent) {
		if (event.key !== ' ') return;
		event.preventDefault();
		if (calibrating) tap();
		else toggle();
	}

	const fmt = (t: number) => `${Math.floor(t / 60)}:${(t % 60).toFixed(1).padStart(4, '0')}`;
</script>

<svelte:window onkeydown={onKey} />

<main>
	<h1>Proba do son</h1>

	<section class="row">
		<select bind:value={chosen}>
			{#each packages as id (id)}<option value={id}>{id}</option>{/each}
		</select>
		<button onclick={load}>Cargar</button>
	</section>

	{#if doc}
		<section class="lyrics">
			<p class="current">
				{#if line}
					{#each line.words as word, i (i)}<span class:sung={word.start <= now}
							>{word.text}
						</span>{/each}
				{:else}…{/if}
			</p>
			<p class="next">{next ? next.words.map((w) => w.text).join(' ') : ''}</p>
		</section>

		<section class="row">
			<button onclick={toggle}>{playing ? '⏸ Parar' : '▶ Tocar'}</button>
			<input
				type="range"
				min="0"
				max={doc.duration}
				step="0.1"
				value={now}
				onchange={(e) => engine?.seek(Number(e.currentTarget.value))}
			/>
			<span>{fmt(now)} / {fmt(doc.duration)}</span>
		</section>

		<section class="row">
			<label
				>Voz guía
				<input
					type="range"
					min="0"
					max="1"
					step="0.05"
					bind:value={vocals}
					oninput={() => engine?.setVocalVolume(vocals)}
				/>
			</label>
			<span>Ton</span>
			<button onclick={() => changePitch(-1)}>−</button>
			<span>{pitch > 0 ? '+' : ''}{pitch}</span>
			<button onclick={() => changePitch(1)}>+</button>
		</section>
	{/if}

	<section class="row">
		<span>Retardo do son: {offsetMs} ms</span>
		<button onclick={() => setOffset(offsetMs - 10)}>−10</button>
		<button onclick={() => setOffset(offsetMs + 10)}>+10</button>
		<button onclick={calibrate} disabled={calibrating}>Calibrar</button>
		{#if calibrating}<button class="tap" onpointerdown={tap}>Toca aquí</button>{/if}
	</section>

	{#if message}<p class="message">{message}</p>{/if}
</main>

<style>
	main {
		max-width: 46rem;
		margin: 0 auto;
		padding: 1rem;
		font-family: system-ui, sans-serif;
	}
	.row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.6rem;
		align-items: center;
		margin: 1rem 0;
	}
	.lyrics {
		min-height: 6rem;
		text-align: center;
	}
	.current {
		font-size: 1.8rem;
		margin: 0.4rem 0;
	}
	.current span {
		opacity: 0.45;
	}
	.current span.sung {
		opacity: 1;
		color: #d9480f;
	}
	.next {
		opacity: 0.6;
	}
	input[type='range'] {
		flex: 1;
		min-width: 8rem;
	}
	button {
		font-size: 1rem;
		padding: 0.4rem 0.8rem;
	}
	.tap {
		padding: 1.2rem 2rem;
		font-size: 1.2rem;
	}
	.message {
		font-style: italic;
	}
</style>
