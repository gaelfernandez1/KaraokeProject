import { getDoc, mediaUrl } from '#lib/api';
import type { KaraokeDoc } from '#lib/contracts';
import { PlayerSession } from '#lib/player/session.svelte.js';
import { advance, endParty, publishPlayback, updateSettings } from './client';
import { PartyConnection } from './connection.svelte';
import { nowPlaying, upcoming } from './rotation';
import type { PartyCommand, PartyCreated, QueueItem } from './types';

/** Seconds the "now singing" card shows before a song starts. */
export const COUNTDOWN = 10;
/** How often the TV tells the phones where the song is, besides every change. */
const PUBLISH_EVERY = 5000;
/** A song whose sound stops (the output sleeps, the browser refuses it) is skipped after this. */
export const ERROR_GRACE_MS = 8000;

export type HostPhase = 'lobby' | 'countdown' | 'singing';

export interface HostOptions {
	device: { vocals: number; latencyMs: number };
	session?: PlayerSession;
}

/**
 * The TV's side of a party: it plays the queue in turn order, shows who sings next, applies the
 * phones' commands and tells them what is playing. The page calls `frame()` once per frame.
 */
export class HostParty {
	phase = $state<HostPhase>('lobby');
	/** Seconds left on the "now singing" card. */
	countdown = $state(COUNTDOWN);
	/** The song being announced or sung. */
	current = $state.raw<QueueItem | null>(null);
	doc = $state.raw<KaraokeDoc | null>(null);

	readonly code: string;
	readonly connection: PartyConnection;
	readonly session: PlayerSession;
	readonly #token: string;
	readonly #device: { vocals: number; latencyMs: number };
	#timer: ReturnType<typeof setInterval> | null = null;
	#lastPublish = 0;
	#busy = false;
	/** Bumped by every announcement and every ending: work started for an older one gives way. */
	#generation = 0;
	/** Songs this TV has ended, until the server's state catches up (it travels separately). */
	// Plain Set on purpose: only frame() reads it, nothing renders from it.
	// eslint-disable-next-line svelte/prefer-svelte-reactivity
	readonly #ended = new Set<string>();
	#starting = false;
	/** Whether the announced song is loaded (or failed to): only then can it start. */
	#loaded = false;
	/** When the sound of the song being sung failed, to skip it after ERROR_GRACE_MS. */
	#errorSince: number | null = null;

	constructor(created: PartyCreated, options: HostOptions) {
		this.code = created.code;
		this.#token = created.host_token;
		this.#device = options.device;
		this.session = options.session ?? new PlayerSession();
		this.connection = new PartyConnection(created.code, created.host_token, {
			onCommand: (command) => this.#apply(command)
		});
	}

	get state() {
		return this.connection.state;
	}

	start(): void {
		this.connection.start();
	}

	/** Once per frame: the audio clock, the end of a song, what to announce next. */
	frame(now = Date.now()): void {
		this.session.tick();
		if (this.phase === 'singing' && this.session.state === 'ended') {
			void this.#finish('done');
			return;
		}
		if (this.phase === 'singing' && this.session.state === 'error') {
			this.#errorSince ??= now;
			if (now - this.#errorSince > ERROR_GRACE_MS) {
				void this.#finish('skipped');
				return;
			}
		} else this.#errorSince = null;
		if (this.phase === 'lobby' && !this.#busy && this.state) {
			// A song left playing (the TV was reloaded) comes back first.
			const playing = nowPlaying(this.state);
			const next =
				(playing && !this.#ended.has(playing.id) ? playing : null) ??
				upcoming(this.state).find((item) => !this.#ended.has(item.id));
			if (next) void this.#announce(next);
		}
		if (this.phase === 'singing' && now - this.#lastPublish > PUBLISH_EVERY) this.#publish(now);
	}

	/** Skips the countdown. */
	startNow(): void {
		if (this.phase === 'countdown') void this.#sing();
	}

	/** Ends the current song (or the announcement) and moves on. */
	skip(): void {
		if (this.phase !== 'lobby') void this.#finish('skipped');
	}

	async setGuestsControl(allowed: boolean): Promise<void> {
		await updateSettings(this.code, this.#token, { guests_control: allowed });
	}

	/**
	 * Ends the party for everyone: the phones are told and stop following it. If the server
	 * cannot be reached, they find out when it forgets the party.
	 */
	async end(): Promise<void> {
		this.stop();
		await endParty(this.code, this.#token).catch(() => {});
	}

	stop(): void {
		this.#clearTimer();
		this.connection.close();
		this.session.destroy();
	}

	async #announce(item: QueueItem): Promise<void> {
		const generation = ++this.#generation;
		this.#busy = true;
		this.current = item;
		this.doc = null;
		this.#loaded = false;
		this.phase = 'countdown';
		this.countdown = COUNTDOWN;
		this.#clearTimer();
		this.#timer = setInterval(() => {
			this.countdown = Math.max(0, this.countdown - 1);
			if (this.countdown === 0) void this.#sing();
		}, 1000);
		// Load during the countdown, so the song starts the moment it ends.
		try {
			const doc = await getDoc(item.song_id);
			if (generation !== this.#generation) return;
			this.doc = doc;
			await this.session.load(
				{
					instrumental: mediaUrl(item.song_id, doc.audio.instrumental),
					vocals: doc.audio.vocals ? mediaUrl(item.song_id, doc.audio.vocals) : null
				},
				this.#device
			);
			if (generation === this.#generation) this.#loaded = true;
		} catch {
			// A song that cannot be loaded is skipped rather than blocking the party.
			if (generation === this.#generation) await this.#finish('skipped');
		}
	}

	async #sing(): Promise<void> {
		this.#clearTimer();
		const item = this.current;
		if (!item || this.phase !== 'countdown' || this.#starting) return;
		const generation = this.#generation;
		this.#starting = true;
		try {
			// Wait for the song (its lyrics, then its audio) if the countdown was cut short.
			while (!this.#loaded && generation === this.#generation) {
				await new Promise((r) => setTimeout(r, 100));
			}
			// Skipped (or another song announced) while it loaded.
			if (generation !== this.#generation) return;
			if (this.session.state === 'error') return this.#finish('skipped');
			this.phase = 'singing';
			await advance(this.code, this.#token, item.id, 'playing').catch(() => {});
			if (generation !== this.#generation) return;
			this.session.seek(0);
			await this.session.play();
			this.#publish();
		} finally {
			this.#starting = false;
		}
	}

	async #finish(state: 'done' | 'skipped'): Promise<void> {
		this.#generation++;
		this.#clearTimer();
		const item = this.current;
		this.session.pause();
		this.phase = 'lobby';
		this.current = null;
		this.doc = null;
		if (item) {
			this.#ended.add(item.id);
			await advance(this.code, this.#token, item.id, state).catch(() => {});
		}
		this.#publish();
		this.#busy = false;
	}

	#apply(command: PartyCommand): void {
		switch (command.type) {
			case 'play':
				if (this.phase === 'countdown') this.startNow();
				else void this.session.play();
				break;
			case 'pause':
				this.session.pause();
				break;
			case 'skip':
				this.skip();
				break;
			case 'vocals':
				this.session.setVocals(command.value);
				break;
			case 'pitch':
				void this.session.setPitch(command.value).then(() => this.#publish());
				break;
		}
		this.#publish();
	}

	#publish(now = Date.now()): void {
		this.#lastPublish = now;
		void publishPlayback(this.code, this.#token, {
			item_id: this.phase === 'singing' ? (this.current?.id ?? null) : null,
			playing: this.session.playing,
			position: this.session.time,
			at: now,
			vocals: this.session.vocals,
			pitch: this.session.pitch
		}).catch(() => {});
	}

	#clearTimer(): void {
		if (this.#timer) clearInterval(this.#timer);
		this.#timer = null;
	}
}
