import {
	cancelJob,
	createExport,
	retryJob,
	uploadJob,
	jobEventsUrl,
	listJobs,
	subscribe,
	type CreateJobInput,
	type ExportInput,
	type Job,
	type Subscription
} from '#lib/api';
import { isRunning, overallProgress } from './stages';

/**
 * The karaoke (and video) jobs on the server, kept up to date live. One store for the whole
 * app, so a job keeps being followed while the singer browses elsewhere.
 */
class Jobs {
	list = $state<Job[]>([]);
	/** What each job was asked with, so a failed one can be tried again. */
	readonly #inputs = new Map<string, CreateJobInput>();
	readonly #following = new Map<string, Subscription>();
	#dismissed = $state<string[]>([]);
	#refreshed = false;

	/** Jobs to show: newest first, without the ones the singer cleared. */
	get shown(): Job[] {
		return this.list.filter((job) => !this.#dismissed.includes(job.id));
	}

	/** Progress of the first karaoke still being made, for the navigation; null if none. */
	get working(): number | null {
		const job = this.list.find((j) => j.kind === 'make' && isRunning(j));
		return job ? (overallProgress(job) ?? 0) : null;
	}

	/** Loads the server's jobs once per visit and follows the running ones. */
	async refresh(): Promise<void> {
		if (this.#refreshed) return;
		this.#refreshed = true;
		try {
			this.list = await listJobs();
		} catch {
			this.#refreshed = false;
			return;
		}
		for (const job of this.list) if (isRunning(job)) this.#follow(job.id);
	}

	/** Upload progress of the job being sent, 0–1; null when nothing is being sent. */
	uploading = $state<number | null>(null);

	async start(input: CreateJobInput): Promise<Job> {
		this.uploading = 0;
		let job: Job;
		try {
			job = await uploadJob(input, (fraction) => (this.uploading = fraction));
		} finally {
			this.uploading = null;
		}
		this.#inputs.set(job.id, input);
		this.#add(job);
		return job;
	}

	async startExport(songId: string, input: ExportInput): Promise<Job> {
		const job = await createExport(songId, input);
		this.#add(job);
		return job;
	}

	/**
	 * Starts a failed or cancelled job again: on the server, which kept the song (no new upload),
	 * or else by sending again what it was first asked; null if neither is possible.
	 */
	async retry(job: Job): Promise<Job | null> {
		if (job.can_retry) {
			const again = await retryJob(job.id);
			this.#add(again);
			return again;
		}
		const input = this.#inputs.get(job.id);
		if (!input) return null;
		this.dismiss(job.id);
		return this.start(input);
	}

	canRetry(job: Job): boolean {
		return job.can_retry || this.#inputs.has(job.id);
	}

	async cancel(id: string): Promise<void> {
		await cancelJob(id);
	}

	dismiss(id: string): void {
		this.#dismissed = [...this.#dismissed, id];
	}

	#add(job: Job): void {
		this.list = [job, ...this.list.filter((j) => j.id !== job.id)];
		this.#follow(job.id);
	}

	#follow(id: string): void {
		if (this.#following.has(id)) return;
		const subscription = subscribe(jobEventsUrl(id), {
			job: (data) => {
				const job = data as Job;
				this.list = this.list.map((j) => (j.id === job.id ? job : j));
				if (!isRunning(job)) {
					subscription.close();
					this.#following.delete(id);
				}
			}
		});
		this.#following.set(id, subscription);
	}
}

export const jobs = new Jobs();
