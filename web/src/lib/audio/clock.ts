import type { PlaybackClock } from '#lib/contracts';

/** What the clock reads from the browser; `audioTimeSource` wraps a real AudioContext. */
export interface TimeSource {
	/** AudioContext.currentTime, in seconds. */
	contextTime(): number;
	/** performance.now(), in milliseconds. */
	perfNow(): number;
	/** Output latency the browser reports (outputLatency + baseLatency), 0 if it reports none. */
	reportedLatency(): number;
}

export function audioTimeSource(context: AudioContext): TimeSource {
	return {
		contextTime: () => context.currentTime,
		perfNow: () => performance.now(),
		// Safari has no outputLatency: there the manual calibration carries the whole delay.
		reportedLatency: () => (context.outputLatency || 0) + (context.baseLatency || 0)
	};
}

/**
 * The audio clock only moves once per rendered block (a few ms, more in some browsers), so
 * between blocks the position is extrapolated with performance.now(), at most this far.
 */
const MAX_INTERPOLATION = 0.05;

/**
 * Song position for the audio engine and the lyrics.
 *
 * `position()` is the transport: where the audio graph is playing, which is where playback
 * resumes after a pause. `now()` is what the listener hears at this instant: the transport minus
 * the output latency (speakers, HDMI, Bluetooth), the latency of effects such as the pitch
 * shifter and the user's own calibration. The lyrics follow `now()`.
 */
export class SongClock implements PlaybackClock {
	#playing = false;
	#startPosition = 0;
	#startContext = 0;
	#pausedAt = 0;
	#manualOffset = 0;
	#extraLatency = 0;
	#lastContext = Number.NEGATIVE_INFINITY;
	#lastPerf = 0;
	#lastHeard = Number.NEGATIVE_INFINITY;
	readonly #time: TimeSource;
	readonly duration: number;

	constructor(time: TimeSource, duration: number) {
		this.#time = time;
		this.duration = duration;
	}

	get playing(): boolean {
		return this.#playing;
	}

	/** The engine calls this in the same instant it starts its audio sources. */
	play(position: number): void {
		this.#startPosition = this.#clamp(position);
		this.#startContext = this.#time.contextTime();
		this.#playing = true;
		this.#lastContext = Number.NEGATIVE_INFINITY;
		this.#lastHeard = Number.NEGATIVE_INFINITY;
	}

	pause(): void {
		if (!this.#playing) return;
		this.#pausedAt = this.position();
		this.#playing = false;
	}

	seek(position: number): void {
		if (this.#playing) this.play(position);
		else this.#pausedAt = this.#clamp(position);
	}

	position(): number {
		if (!this.#playing) return this.#pausedAt;
		return this.#clamp(this.#startPosition + this.#time.contextTime() - this.#startContext);
	}

	now(): number {
		if (!this.#playing) return this.#pausedAt;
		const elapsed = this.#smoothedContext() - this.#startContext;
		// Until the first sound reaches the speaker, the listener is still at the start position.
		const heard = Math.max(
			this.#startPosition + Math.max(0, elapsed - this.latency()),
			this.#lastHeard
		);
		this.#lastHeard = heard;
		return this.#clamp(heard);
	}

	ended(): boolean {
		return this.position() >= this.duration;
	}

	/** Total delay between the transport and the listener's ears, in seconds. */
	latency(): number {
		return this.#time.reportedLatency() + this.#extraLatency + this.#manualOffset;
	}

	/** The user's calibration for this device: positive when the sound arrives later. */
	setManualOffset(seconds: number): void {
		this.#manualOffset = seconds;
	}

	/** Latency added by effects in the audio graph (the pitch shifter). */
	setExtraLatency(seconds: number): void {
		this.#extraLatency = seconds;
	}

	#smoothedContext(): number {
		const context = this.#time.contextTime();
		const perf = this.#time.perfNow();
		if (context !== this.#lastContext) {
			this.#lastContext = context;
			this.#lastPerf = perf;
			return context;
		}
		return context + Math.min(MAX_INTERPOLATION, (perf - this.#lastPerf) / 1000);
	}

	#clamp(position: number): number {
		return Math.min(Math.max(position, 0), this.duration);
	}
}
