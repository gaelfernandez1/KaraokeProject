import type { Job, JobStage } from '../../src/lib/api/types.ts';
import type { Library } from './library.ts';

export interface JobRequest {
	url?: string;
	fileName?: string;
	language: string;
	lyrics?: string;
	lrclib?: boolean;
	title?: string;
	artist?: string;
}

interface Running {
	job: Job;
	started: number;
	weights: [JobStage, number][];
	stages: { stage: JobStage; until: number }[];
	finish: (job: Job) => void;
}

/** The song every mock job "makes": its media are reused under the new song's id. */
const SOURCE = 'demo-sintetico';

/**
 * Pretend processing: each job walks through the engine's stages in about `seconds`, with the
 * share of time each one takes on the real machine, then adds its song to the library.
 */
export class Jobs {
	readonly #library: Library;
	readonly #seconds: number;
	readonly #now: () => number;
	readonly #jobs = new Map<string, Running>();
	readonly #listeners = new Map<string, Set<(job: Job) => void>>();
	#count = 0;

	constructor(library: Library, options: { seconds?: number; now?: () => number } = {}) {
		this.#library = library;
		this.#seconds = options.seconds ?? 12;
		this.#now = options.now ?? Date.now;
	}

	create(request: JobRequest): Job {
		const withLyrics = Boolean(request.lyrics?.trim());
		const weights: [JobStage, number][] = [
			['queued', 0.03],
			...(request.url ? ([['download', 0.1]] as [JobStage, number][]) : []),
			['separate', 0.45],
			...(withLyrics ? [] : ([['transcribe', 0.15]] as [JobStage, number][])),
			['align', 0.15],
			['audio', 0.1],
			...(request.url ? ([['video', 0.05]] as [JobStage, number][]) : [])
		];
		const job = this.#add('make', request.title?.trim() || 'Canción nova', withLyrics, weights);
		const running = this.#jobs.get(job.id) as Running;
		running.finish = (done) => {
			done.song_id = this.#library.addVirtual(SOURCE, {
				title: done.title,
				artist: request.artist?.trim() || null,
				language: request.language,
				lyricsSource: withLyrics ? 'user' : request.lrclib ? 'lrclib' : 'asr'
			});
		};
		return job;
	}

	createExport(songId: string): Job | undefined {
		const summary = this.#library.summary(songId);
		if (!summary) return undefined;
		const job = this.#add('export', summary.title, true, [
			['queued', 0.1],
			['video', 0.9]
		]);
		const running = this.#jobs.get(job.id) as Running;
		running.finish = (done) => {
			done.song_id = songId;
			// The mock cannot render: it offers the package's background video, if any.
			done.file = this.#library.filePath(songId, 'background.mp4') ? 'background.mp4' : null;
		};
		return job;
	}

	#schedule(weights: [JobStage, number][], started: number) {
		const total = weights.reduce((sum, [, w]) => sum + w, 0);
		let until = started;
		return weights.map(([stage, weight]) => {
			until += (weight / total) * this.#seconds * 1000;
			return { stage, until };
		});
	}

	#add(kind: Job['kind'], title: string, withLyrics: boolean, weights: [JobStage, number][]): Job {
		const started = this.#now();
		const stages = this.#schedule(weights, started);
		const job: Job = {
			id: `job-${++this.#count}`,
			kind,
			title,
			stage: stages[0].stage,
			progress: 0,
			song_id: null,
			file: null,
			error: null,
			error_code: null,
			with_lyrics: withLyrics,
			created_at: new Date(started).toISOString(),
			overall: null,
			eta: null,
			can_retry: false,
			attempt: 1
		};
		this.#jobs.set(job.id, { job, started, weights, stages, finish: () => {} });
		return job;
	}

	get(id: string): Job | undefined {
		return this.#jobs.get(id)?.job;
	}

	list(): Job[] {
		return [...this.#jobs.values()].map((r) => r.job).reverse();
	}

	cancel(id: string): boolean {
		const running = this.#jobs.get(id);
		if (!running || ['done', 'error', 'cancelled'].includes(running.job.stage)) return false;
		running.job.stage = 'cancelled';
		running.job.can_retry = true;
		this.#emit(running.job);
		return true;
	}

	/** Runs a cancelled (or failed) job again, from the start, as the real server does. */
	retry(id: string): Job | undefined {
		const running = this.#jobs.get(id);
		if (!running || !running.job.can_retry) return undefined;
		running.started = this.#now();
		running.stages = this.#schedule(running.weights, running.started);
		Object.assign(running.job, {
			stage: running.stages[0].stage,
			progress: 0,
			error: null,
			error_code: null,
			can_retry: false,
			attempt: running.job.attempt + 1
		});
		this.#emit(running.job);
		return running.job;
	}

	/** Moves every job on to where it should be now. */
	tick(): void {
		const now = this.#now();
		for (const running of this.#jobs.values()) {
			const { job, stages } = running;
			if (['done', 'error', 'cancelled'].includes(job.stage)) continue;
			const index = stages.findIndex((s) => now < s.until);
			if (index === -1) {
				job.stage = 'done';
				job.progress = 1;
				running.finish(job);
				this.#emit(job);
				continue;
			}
			const from = index === 0 ? running.started : stages[index - 1].until;
			const progress = Math.min(1, (now - from) / (stages[index].until - from));
			if (stages[index].stage !== job.stage || progress - job.progress >= 0.02) {
				job.stage = stages[index].stage;
				job.progress = Math.round(progress * 100) / 100;
				this.#emit(job);
			}
		}
	}

	subscribe(id: string, listener: (job: Job) => void): () => void {
		const set = this.#listeners.get(id) ?? new Set();
		set.add(listener);
		this.#listeners.set(id, set);
		return () => set.delete(listener);
	}

	#emit(job: Job): void {
		for (const listener of this.#listeners.get(job.id) ?? []) listener({ ...job });
	}
}
