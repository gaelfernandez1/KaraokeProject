/** What the sync needs from an HTMLVideoElement (tests use a fake). */
export interface VideoLike {
	currentTime: number;
	playbackRate: number;
	readonly paused: boolean;
	readonly seeking: boolean;
	readonly duration: number;
	play(): Promise<void> | void;
	pause(): void;
}

/** The song position the video must follow: the audio engine (latency already compensated). */
export interface SyncClock {
	now(): number;
	readonly playing: boolean;
}

/** Further than this (s) and the video jumps to the song position. */
const SEEK = 0.3;
/** Between this and SEEK, the video speeds up or slows down a little until it catches up. */
const NUDGE = 0.04;
/** Closer than this and it plays at normal speed again. */
const SETTLE = 0.02;
const MAX_RATE_CHANGE = 0.05;
/** While paused, moves smaller than this are not worth a seek. */
const PAUSED_TOLERANCE = 0.05;

/**
 * Keeps a muted background video in step with the song. A video's own clock drifts from the
 * audio one, and its `currentTime` is too coarse to correct every frame, so small drifts are
 * absorbed by changing the playback rate a few percent and only big ones by seeking. A video
 * shorter than the song loops, as in the exported MP4.
 */
export class BackgroundSync {
	readonly #video: VideoLike;
	readonly #clock: SyncClock;
	/** The browser refused to play (autoplay rules): no more tries until the song stops. */
	#refused = false;

	constructor(video: VideoLike, clock: SyncClock) {
		this.#video = video;
		this.#clock = clock;
	}

	/** Call once per animation frame. */
	tick(): void {
		const video = this.#video;
		const length = video.duration;
		if (!Number.isFinite(length) || length <= 0) return;
		// A seek takes a while on slow devices; asking again would cancel it and freeze the picture.
		if (video.seeking) return;
		const target = this.#clock.now() % length;
		if (!this.#clock.playing) {
			this.#refused = false;
			if (!video.paused) video.pause();
			video.playbackRate = 1;
			if (Math.abs(video.currentTime - target) > PAUSED_TOLERANCE) video.currentTime = target;
			return;
		}
		if (video.paused) {
			if (this.#refused) return;
			video.currentTime = target;
			void Promise.resolve(video.play()).catch(() => {
				// Autoplay can be refused; the lyrics and the audio go on without the picture.
				this.#refused = true;
			});
			return;
		}
		// Ahead is positive; across the loop point the shorter way round counts.
		let drift = video.currentTime - target;
		if (drift > length / 2) drift -= length;
		if (drift < -length / 2) drift += length;
		const size = Math.abs(drift);
		if (size > SEEK) {
			video.currentTime = target;
			video.playbackRate = 1;
		} else if (size > NUDGE) {
			video.playbackRate = 1 - Math.max(-MAX_RATE_CHANGE, Math.min(MAX_RATE_CHANGE, drift * 0.5));
		} else if (size < SETTLE) {
			video.playbackRate = 1;
		}
	}
}
