import { ApiError, type Job } from '#lib/api';
import type { Messages } from '#lib/i18n';

/** Why the server said no, in the singer's language; `fallback` when it gave no known reason. */
export function explain(error: unknown, fallback: string, t: Messages): string {
	if (!(error instanceof ApiError)) return fallback;
	if (error.status === 0) return t.errors.network;
	const known = error.code ? (t.errors.server as Record<string, string>)[error.code] : undefined;
	return known ?? fallback;
}

/** Whether pairing this device with the laptop would let it do what it was refused. */
export function needsPairing(error: unknown): boolean {
	return error instanceof ApiError && (error.code === 'not_owner' || error.code === 'not_paired');
}

/** Why a job failed: its code in the singer's language, else the server's own words. */
export function jobError(
	job: Pick<Job, 'error_code' | 'error'>,
	fallback: string,
	t: Messages
): string {
	if (job.error_code) return t.errors.server[job.error_code];
	return job.error ?? fallback;
}
