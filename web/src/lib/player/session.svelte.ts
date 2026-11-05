import type { PlaybackClock } from '#lib/contracts';
import { AudioEngine, MAX_SEMITONES, type StemUrls } from '#lib/audio/engine.js';
import { BackgroundSync } from '#lib/video/background.js';

/** What the session needs from the audio engine (tests use a fake). */
export interface EngineLike {
	readonly duration: number;
	readonly playing: boolean;
	load(urls: StemUrls): Promise<void>;
	play(): Promise<void>;
	pause(): void;
	seek(seconds: number): void;
	now(): number;
	position(): number;
	setVocalVolume(volume: number): void;
	setManualOffset(seconds: number): void;
	setPitch(semitones: number): Promise<void>;
	onEnded(listener: () => void): void;
	/** The decoded guide vocals (mono), for drawing the waveform in the editor. */
	readonly vocalsBuffer?: AudioBuffer | null;
}

export type PlayerState = 'idle' | 'loading' | 'ready' | 'playing' | 'paused' | 'ended' | 'error';

/**
 * How long the audio clock may stay still after pressing play before the session says the
 * browser is not playing sound (instead of a song frozen at 0:00 with no explanation).
 */
export const STALL_MS = 4000;

export interface SessionOptions {
	createEngine?: () => EngineLike;
	/** Whether the page is in a secure context (AudioWorklet, hence the key change, needs it). */
	secure?: boolean;
	/** Wall clock in milliseconds (performance.now); tests move it by hand. */
	wallNow?: () => number;
}

/**
 * One song being sung: the audio engine, its background video and the state the controls
 * show. The page calls `tick()` once per frame; everything the screen shows is read from here.
 */
export class PlayerSession {
	state = $state<PlayerState>('idle');
	/** Message key in `errors` when the state is 'error'. */
	error = $state<'audioLoad' | 'audioStalled' | null>(null);
	/** What the listener hears now, in seconds. */
	time = $state(0);
	duration = $state(0);
	vocals = $state(0.15);
	pitch = $state(0);
	pitchAvailable = $state(true);
	#vocalsBuffer = $state.raw<AudioBuffer | null>(null);

	readonly clock: PlaybackClock;
	readonly #createEngine: () => EngineLike;
	#engine: EngineLike | null = null;
	#sync: BackgroundSync | null = null;
	#urls: StemUrls | null = null;
	#latencyMs = 0;
	#ended = false;
	/** Whether it has played since loading: a stop is then a pause, not the start screen. */
	#started = false;
	#context: AudioContext | null = null;
	readonly #wallNow: () => number;
	/** Right after play: where the song was and when, until the audio clock is seen moving. */
	#stallWatch: { position: number; since: number } | null = null;

	constructor(options: SessionOptions = {}) {
		this.#wallNow = options.wallNow ?? (() => performance.now());
		this.#createEngine =
			options.createEngine ??
			(() => {
				// One audio context for the whole session (browsers allow only a few), closed at the end.
				this.#context = new AudioContext();
				return new AudioEngine(this.#context);
			});
		this.pitchAvailable =
			(options.secure ?? (typeof window !== 'undefined' && window.isSecureContext)) &&
			(typeof AudioWorkletNode !== 'undefined' || options.createEngine !== undefined);
		this.clock = { now: () => this.#engine?.now() ?? this.time };
	}

	get playing(): boolean {
		return this.#engine?.playing ?? false;
	}

	/** The decoded guide vocals, once loaded (for the editor's waveform). */
	get vocalsBuffer(): AudioBuffer | null {
		return this.#vocalsBuffer;
	}

	/** Loads the song's audio; the browser lets it play once the user taps (see `play`). */
	async load(urls: StemUrls, device: { vocals: number; latencyMs: number }): Promise<void> {
		this.#urls = urls;
		this.vocals = device.vocals;
		this.#latencyMs = device.latencyMs;
		if (!this.#engine) {
			this.#engine = this.#createEngine();
			this.#engine.onEnded(() => {
				this.#ended = true;
			});
		}
		const engine = this.#engine;
		this.state = 'loading';
		this.error = null;
		this.#started = false;
		try {
			await engine.load(urls);
		} catch {
			this.state = 'error';
			this.error = 'audioLoad';
			return;
		}
		engine.setVocalVolume(this.vocals);
		engine.setManualOffset(this.#latencyMs / 1000);
		this.duration = engine.duration;
		this.#vocalsBuffer = engine.vocalsBuffer ?? null;
		this.state = 'ready';
	}

	async retry(): Promise<void> {
		if (this.#urls)
			await this.load(this.#urls, { vocals: this.vocals, latencyMs: this.#latencyMs });
	}

	async play(): Promise<void> {
		if (!this.#engine || this.state === 'loading' || this.state === 'error') return;
		this.#ended = false;
		this.#started = true;
		try {
			await this.#engine.play();
		} catch {
			this.#stalled();
			return;
		}
		this.#stallWatch = { position: this.#engine.position(), since: this.#wallNow() };
		this.tick();
	}

	pause(): void {
		this.#stallWatch = null;
		this.#engine?.pause();
		this.tick();
	}

	/** The browser is not playing the sound: stop, and say so. */
	#stalled(): void {
		this.#stallWatch = null;
		this.#engine?.pause();
		this.state = 'error';
		this.error = 'audioStalled';
	}

	async toggle(): Promise<void> {
		if (this.playing) this.pause();
		else await this.play();
	}

	seek(seconds: number): void {
		if (!this.#engine) return;
		this.#engine.seek(Math.min(Math.max(seconds, 0), this.duration));
		this.#ended = false;
		this.tick();
	}

	skip(delta: number): void {
		this.seek((this.#engine?.position() ?? this.time) + delta);
	}

	setVocals(volume: number): void {
		this.vocals = Math.min(1, Math.max(0, volume));
		this.#engine?.setVocalVolume(this.vocals);
	}

	/** Changes key; where the shifter cannot run, the key goes back to 0 and the option goes. */
	async setPitch(semitones: number): Promise<void> {
		const target = Math.round(Math.min(MAX_SEMITONES, Math.max(-MAX_SEMITONES, semitones)));
		if (!this.pitchAvailable || !this.#engine) return;
		this.pitch = target;
		try {
			await this.#engine.setPitch(target);
		} catch {
			this.pitch = 0;
			this.pitchAvailable = false;
		}
	}

	setLatencyMs(ms: number): void {
		this.#latencyMs = ms;
		this.#engine?.setManualOffset(ms / 1000);
	}

	/** The song's video follows the audio; pass null when it goes away. */
	attachVideo(video: HTMLVideoElement | null): void {
		const playing = () => this.playing;
		this.#sync = video
			? new BackgroundSync(video, {
					now: () => this.clock.now(),
					get playing() {
						return playing();
					}
				})
			: null;
	}

	/** Once per frame: reads the clock and the engine's state. */
	tick(): void {
		const engine = this.#engine;
		if (!engine) return;
		this.time = engine.now();
		this.#sync?.tick();
		if (this.state === 'loading' || this.state === 'error' || this.state === 'idle') return;
		const watch = this.#stallWatch;
		if (watch && engine.playing) {
			if (engine.position() !== watch.position) this.#stallWatch = null;
			else if (this.#wallNow() - watch.since > STALL_MS) return this.#stalled();
		}
		if (engine.playing) this.state = 'playing';
		else if (this.#ended) this.state = 'ended';
		else this.state = this.#started ? 'paused' : 'ready';
	}

	destroy(): void {
		this.#engine?.pause();
		this.#sync = null;
		void this.#context?.close();
	}
}
