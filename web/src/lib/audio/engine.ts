import type { PlaybackClock } from '#lib/contracts';
import { SongClock, audioTimeSource } from './clock';

/** Seconds between asking to play and the scheduled start, so both stems start together. */
export const START_DELAY = 0.05;
/** Time constant of volume changes: quick, but without clicks. */
const VOLUME_SMOOTHING = 0.02;

export interface StemUrls {
	instrumental: string;
	vocals?: string | null;
}

export interface EngineOptions {
	/** How audio files are fetched; tests replace it. */
	fetchBytes?: (url: string) => Promise<ArrayBuffer>;
}

const fetchArrayBuffer = async (url: string): Promise<ArrayBuffer> => {
	const response = await fetch(url);
	if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
	return response.arrayBuffer();
};

/**
 * Plays a karaoke package: the instrumental and the guide vocals, decoded in memory and started
 * on the same audio frame, so they never drift apart and seeking is instant. The guide vocals
 * have their own volume. It is also the PlaybackClock the lyrics follow.
 *
 * Memory: a 4 minute song takes about 125 MB (stereo instrumental, mono vocals).
 */
export class AudioEngine implements PlaybackClock {
	readonly #context: AudioContext;
	readonly #fetchBytes: (url: string) => Promise<ArrayBuffer>;
	readonly #master: GainNode;
	readonly #vocalGain: GainNode;
	#instrumental: AudioBuffer | null = null;
	#vocals: AudioBuffer | null = null;
	#sources: AudioBufferSourceNode[] = [];
	#clock: SongClock;
	#endedListeners: (() => void)[] = [];
	#manualOffset = 0;

	constructor(context: AudioContext, options: EngineOptions = {}) {
		this.#context = context;
		this.#fetchBytes = options.fetchBytes ?? fetchArrayBuffer;
		this.#master = context.createGain();
		this.#master.connect(context.destination);
		this.#vocalGain = context.createGain();
		this.#vocalGain.connect(this.#master);
		this.#clock = new SongClock(audioTimeSource(context), 0);
	}

	get duration(): number {
		return this.#clock.duration;
	}

	get playing(): boolean {
		return this.#clock.playing;
	}

	get vocalsBuffer(): AudioBuffer | null {
		return this.#vocals;
	}

	/** Where the listener is now, with latency compensated: what the lyrics follow. */
	now(): number {
		return this.#clock.now();
	}

	/** Where playback resumes after a pause. */
	position(): number {
		return this.#clock.position();
	}

	async load(urls: StemUrls): Promise<void> {
		this.#stopSources();
		const [instrumental, vocals] = await Promise.all([
			this.#decode(urls.instrumental),
			urls.vocals ? this.#decode(urls.vocals).then((b) => this.#toMono(b)) : null
		]);
		this.#instrumental = instrumental;
		this.#vocals = vocals;
		this.#clock = new SongClock(audioTimeSource(this.#context), instrumental.duration);
		this.#clock.setManualOffset(this.#manualOffset);
	}

	async play(): Promise<void> {
		if (!this.#instrumental || this.playing) return;
		// Browsers start the context suspended until the user interacts with the page.
		if (this.#context.state !== 'running') await this.#context.resume();
		const from = this.#clock.ended() ? 0 : this.#clock.position();
		this.#start(from);
	}

	pause(): void {
		if (!this.playing) return;
		this.#clock.pause();
		this.#stopSources();
	}

	seek(seconds: number): void {
		if (this.playing) {
			this.#stopSources();
			this.#clock.pause();
			this.#clock.seek(seconds);
			this.#start(this.#clock.position());
		} else {
			this.#clock.seek(seconds);
		}
	}

	/** Guide vocals volume, from 0 (karaoke) to 1 (the original mix). */
	setVocalVolume(volume: number): void {
		const value = Math.min(Math.max(volume, 0), 1);
		this.#vocalGain.gain.setTargetAtTime(value, this.#context.currentTime, VOLUME_SMOOTHING);
	}

	/** The user's latency calibration for this device, in seconds. */
	setManualOffset(seconds: number): void {
		this.#manualOffset = seconds;
		this.#clock.setManualOffset(seconds);
	}

	onEnded(listener: () => void): void {
		this.#endedListeners.push(listener);
	}

	#start(from: number): void {
		const at = this.#context.currentTime + START_DELAY;
		const stems: [AudioBuffer | null, AudioNode][] = [
			[this.#instrumental, this.#master],
			[this.#vocals, this.#vocalGain]
		];
		this.#sources = stems.flatMap(([buffer, target]) => {
			if (!buffer) return [];
			const source = this.#context.createBufferSource();
			source.buffer = buffer;
			source.connect(target);
			source.start(at, from);
			return [source];
		});
		// The instrumental is always there and as long as the song: its end is the song's end.
		this.#sources[0].onended = () => this.#finish();
		this.#clock.play(from, at);
	}

	#finish(): void {
		this.#clock.pause();
		this.#clock.seek(this.duration);
		this.#stopSources();
		for (const listener of this.#endedListeners) listener();
	}

	#stopSources(): void {
		for (const source of this.#sources) {
			source.onended = null;
			source.stop();
			source.disconnect();
		}
		this.#sources = [];
	}

	async #decode(url: string): Promise<AudioBuffer> {
		return this.#context.decodeAudioData(await this.#fetchBytes(url));
	}

	/** The guide vocals in mono: half the memory, and nobody misses their stereo image. */
	#toMono(buffer: AudioBuffer): AudioBuffer {
		if (buffer.numberOfChannels === 1) return buffer;
		const mono = this.#context.createBuffer(1, buffer.length, buffer.sampleRate);
		const out = mono.getChannelData(0);
		for (let channel = 0; channel < buffer.numberOfChannels; channel++) {
			const data = buffer.getChannelData(channel);
			for (let i = 0; i < data.length; i++) out[i] += data[i] / buffer.numberOfChannels;
		}
		return mono;
	}
}
