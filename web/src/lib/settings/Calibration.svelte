<script lang="ts">
	/*
	 * Measures this device's sound delay: ten clicks, one per second, and the singer taps along.
	 * Only the ear counts here, so nothing on screen moves with the clicks; each tap answers
	 * with a ripple where it landed.
	 */
	import {
		CLICK_INTERVAL,
		clickTimes,
		estimateLatency,
		manualOffset
	} from '#lib/audio/calibration.js';
	import { preferPlayback, resumeWithin } from '#lib/audio/engine.js';
	import { i18n } from '#lib/i18n';
	import Button from '#lib/ui/Button.svelte';

	interface Props {
		/** Receives the delay to add to what the browser reports, in ms. */
		onresult: (ms: number) => void;
	}

	let { onresult }: Props = $props();

	const COUNT = 10;
	// 'silent': the browser is not playing sound at all, so there is nothing to tap along to.
	let phase = $state<'idle' | 'running' | 'done' | 'failed' | 'silent'>('idle');
	let tapCount = $state(0);
	let resultMs = $state(0);
	let ripples = $state<{ id: number; x: number; y: number }[]>([]);
	let context: AudioContext | null = null;
	let clicks: number[] = [];
	let startedAt = 0;
	let taps: number[] = [];
	let ripple = 0;

	const t = $derived(i18n.t.settings);

	function click(ctx: AudioContext, at: number) {
		// A short wooden "tock": easy to tap to, unlike a long beep.
		const osc = ctx.createOscillator();
		const gain = ctx.createGain();
		osc.frequency.setValueAtTime(1400, at);
		osc.frequency.exponentialRampToValueAtTime(600, at + 0.03);
		gain.gain.setValueAtTime(0.6, at);
		gain.gain.exponentialRampToValueAtTime(0.001, at + 0.06);
		osc.connect(gain).connect(ctx.destination);
		osc.start(at);
		osc.stop(at + 0.07);
	}

	async function start() {
		if (!context) preferPlayback();
		context ??= new AudioContext();
		try {
			await resumeWithin(context);
		} catch {
			phase = 'silent';
			return;
		}
		startedAt = context.currentTime;
		clicks = clickTimes(context.currentTime, COUNT, CLICK_INTERVAL, 1);
		for (const at of clicks) click(context, at);
		taps = [];
		tapCount = 0;
		phase = 'running';
		const last = clicks[clicks.length - 1];
		timer = setTimeout(finish, (last - context.currentTime + CLICK_INTERVAL) * 1000);
	}

	let timer: ReturnType<typeof setTimeout> | null = null;

	function tap(event?: PointerEvent) {
		if (phase !== 'running' || !context) return;
		taps.push(context.currentTime);
		tapCount = taps.length;
		const box = (event?.currentTarget as HTMLElement | undefined)?.getBoundingClientRect();
		const id = ++ripple;
		ripples = [
			...ripples.slice(-4),
			{
				id,
				x: event && box ? event.clientX - box.left : -1,
				y: event && box ? event.clientY - box.top : -1
			}
		];
	}

	function finish() {
		if (!context) return;
		// Ten seconds went by and the audio clock did not: no click ever sounded.
		if (context.currentTime === startedAt) {
			phase = 'silent';
			return;
		}
		const measured = estimateLatency(clicks, taps);
		if (measured === null) {
			phase = 'failed';
			return;
		}
		const reported = (context.outputLatency || 0) + (context.baseLatency || 0);
		resultMs = Math.round(measured * 1000);
		onresult(Math.round(manualOffset(measured, reported) * 1000));
		phase = 'done';
	}

	function onKey(event: KeyboardEvent) {
		if (phase === 'running' && event.key === ' ') {
			event.preventDefault();
			tap();
		}
	}

	// Leaving mid-way stops it: a calibration nobody finished is not saved.
	$effect(() => () => {
		if (timer) clearTimeout(timer);
		void context?.close();
	});
</script>

<svelte:window onkeydown={onKey} />

<div class="calibration">
	{#if phase === 'running'}
		<button type="button" class="pad" onpointerdown={tap} aria-label={t.calibrateTap}>
			{#each ripples as r (r.id)}
				<span class="ripple" class:center={r.x < 0} style:left="{r.x}px" style:top="{r.y}px"></span>
			{/each}
			<span class="pad-label">{t.calibrateTap}</span>
			<span class="count data" aria-live="polite">{tapCount} / {COUNT}</span>
		</button>
	{:else}
		<p class="intro">{t.calibrateIntro}</p>
		{#if phase === 'done'}<p class="result" role="status">{t.calibrateResult(resultMs)}</p>{/if}
		{#if phase === 'failed'}<p class="failed" role="alert">{t.calibrateFailed}</p>{/if}
		{#if phase === 'silent'}
			<p class="failed" role="alert">{i18n.t.errors.audioStalled}</p>
		{/if}
		<Button variant={phase === 'idle' ? 'primary' : 'quiet'} icon="tap" onclick={start}>
			{phase === 'idle' ? t.calibrateStart : i18n.t.common.retry}
		</Button>
	{/if}
</div>

<style>
	.calibration {
		display: grid;
		justify-items: start;
		gap: var(--s-3);
	}

	.intro {
		color: var(--texto-2);
		max-width: 38rem;
	}

	.result {
		font-weight: 650;
		color: var(--ouro);
	}

	.failed {
		max-width: 38rem;
		font-weight: 650;
		color: var(--erro);
	}

	/* The pad to tap on: a square of the night; each tap lights a ring where it lands. */
	.pad {
		position: relative;
		display: grid;
		place-items: center;
		align-content: center;
		gap: var(--s-3);
		width: 100%;
		min-height: 14rem;
		overflow: hidden;
		border: 1px solid var(--raia-forte);
		background:
			radial-gradient(circle, var(--raia) 0 1.25px, transparent 1.75px) 50% 50% / 12px 12px,
			var(--fondo-3);
		touch-action: manipulation;
		user-select: none;
		-webkit-user-select: none;
	}

	.pad-label {
		font-family: var(--font-text);
		font-size: var(--t-5);
		font-weight: 700;
		line-height: 1;
	}

	.count {
		font-size: var(--t-3);
		line-height: 1;
		color: var(--ouro);
	}

	.ripple {
		position: absolute;
		width: 2rem;
		height: 2rem;
		margin: -1rem 0 0 -1rem;
		border-radius: 50%;
		border: 3px solid var(--ouro);
		animation: ripple 600ms var(--ease) forwards;
		pointer-events: none;
	}

	.ripple.center {
		left: 50% !important;
		top: 50% !important;
	}

	@keyframes ripple {
		to {
			transform: scale(6);
			opacity: 0;
		}
	}
</style>
