import type { Job, JobStage } from '#lib/api';

/** Share of a job's time each stage takes on the laptop's GPU (separation is the long one). */
const MAKE: [JobStage, number][] = [
	['queued', 0.03],
	['download', 0.1],
	['separate', 0.45],
	['transcribe', 0.15],
	['align', 0.15],
	['audio', 0.1],
	['video', 0.05]
];

/** A video export only waits for the GPU and renders. */
const EXPORT: [JobStage, number][] = [
	['queued', 0.1],
	['video', 0.9]
];

/**
 * How far the whole job has gone, 0–1; null once it has stopped without finishing. The server
 * knows what each stage takes on its machine and sends `overall`; the weights below are for
 * when it does not.
 */
export function overallProgress(job: Job): number | null {
	if (job.stage === 'done') return 1;
	if (job.stage === 'error' || job.stage === 'cancelled') return null;
	if (job.overall !== null && job.overall !== undefined) return job.overall;
	const weights = job.kind === 'export' ? EXPORT : MAKE;
	const stages = weights.filter(([stage]) => !(stage === 'transcribe' && job.with_lyrics));
	const total = stages.reduce((sum, [, w]) => sum + w, 0);
	let done = 0;
	for (const [stage, weight] of stages) {
		if (stage === job.stage)
			return (done + weight * Math.min(1, Math.max(0, job.progress))) / total;
		done += weight;
	}
	return done / total;
}

export const isRunning = (job: Job): boolean => !['done', 'error', 'cancelled'].includes(job.stage);
