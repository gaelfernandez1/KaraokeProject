import type { KaraokeDoc } from '#lib/contracts';
import { normalizeDoc } from '#lib/lyrics/layout.js';
import type { CreateJobInput, ExportInput, Job, ServerInfo, SongSummary } from './types';

/** An answer from the server that is not a success; `status` 0 means it could not be reached. */
export class ApiError extends Error {
	readonly status: number;

	constructor(status: number, message: string) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
	}
}

type Fetch = typeof fetch;

async function request<T>(
	url: string,
	init: RequestInit = {},
	fetchImpl: Fetch = fetch
): Promise<T> {
	let response: Response;
	try {
		response = await fetchImpl(url, init);
	} catch (error) {
		throw new ApiError(0, error instanceof Error ? error.message : String(error));
	}
	if (!response.ok) {
		let detail = response.statusText;
		try {
			const body = await response.json();
			if (typeof body?.detail === 'string') detail = body.detail;
		} catch {
			// Not JSON: the status text says enough.
		}
		throw new ApiError(response.status, detail);
	}
	if (response.status === 204) return undefined as T;
	return (await response.json()) as T;
}

const json = (method: string, body: unknown): RequestInit => ({
	method,
	headers: { 'Content-Type': 'application/json' },
	body: JSON.stringify(body)
});

/** Where a file of a song's package is served. */
export function mediaUrl(id: string, file: string): string {
	return `/media/${encodeURIComponent(id)}/${file}`;
}

export function listSongs(fetchImpl?: Fetch): Promise<SongSummary[]> {
	return request('/api/songs', {}, fetchImpl);
}

/** The song's lyrics document, upgraded to the current contract (1.0.0 lines become lead). */
export async function getDoc(id: string, fetchImpl?: Fetch): Promise<KaraokeDoc> {
	return normalizeDoc(await request<KaraokeDoc>(mediaUrl(id, 'karaoke.json'), {}, fetchImpl));
}

/** Saves corrected lyrics; the server validates them and answers with what it stored. */
export async function saveDoc(id: string, doc: KaraokeDoc, fetchImpl?: Fetch): Promise<KaraokeDoc> {
	const saved = await request<KaraokeDoc>(
		`/api/songs/${encodeURIComponent(id)}/doc`,
		json('PUT', doc),
		fetchImpl
	);
	return normalizeDoc(saved);
}

export function deleteSong(id: string, fetchImpl?: Fetch): Promise<void> {
	return request(`/api/songs/${encodeURIComponent(id)}`, { method: 'DELETE' }, fetchImpl);
}

function jobForm(input: CreateJobInput): FormData {
	const form = new FormData();
	if (input.file) form.set('file', input.file);
	if (input.url) form.set('url', input.url);
	form.set('language', input.language);
	if (input.lyrics) form.set('lyrics', input.lyrics);
	if (input.lrclib) form.set('lrclib', 'true');
	if (input.title) form.set('title', input.title);
	if (input.artist) form.set('artist', input.artist);
	return form;
}

export function createJob(input: CreateJobInput, fetchImpl?: Fetch): Promise<Job> {
	return request('/api/jobs', { method: 'POST', body: jobForm(input) }, fetchImpl);
}

/**
 * Like `createJob`, reporting how much of the upload has gone (0–1): a long video can take a
 * while over Wi-Fi, and fetch cannot tell upload progress.
 */
export function uploadJob(
	input: CreateJobInput,
	onProgress: (fraction: number) => void
): Promise<Job> {
	return new Promise((done, fail) => {
		const xhr = new XMLHttpRequest();
		xhr.open('POST', '/api/jobs');
		xhr.responseType = 'json';
		xhr.upload.onprogress = (event) => {
			if (event.lengthComputable) onProgress(event.loaded / event.total);
		};
		xhr.onload = () => {
			if (xhr.status >= 200 && xhr.status < 300) done(xhr.response as Job);
			else
				fail(
					new ApiError(
						xhr.status,
						(xhr.response as { detail?: string } | null)?.detail ?? xhr.statusText
					)
				);
		};
		xhr.onerror = () => fail(new ApiError(0, 'network'));
		xhr.send(jobForm(input));
	});
}

export function listJobs(fetchImpl?: Fetch): Promise<Job[]> {
	return request('/api/jobs', {}, fetchImpl);
}

export function cancelJob(id: string, fetchImpl?: Fetch): Promise<void> {
	return request(`/api/jobs/${encodeURIComponent(id)}`, { method: 'DELETE' }, fetchImpl);
}

export function jobEventsUrl(id: string): string {
	return `/api/jobs/${encodeURIComponent(id)}/events`;
}

export function createExport(id: string, input: ExportInput, fetchImpl?: Fetch): Promise<Job> {
	return request(`/api/songs/${encodeURIComponent(id)}/exports`, json('POST', input), fetchImpl);
}

export function serverInfo(fetchImpl?: Fetch): Promise<ServerInfo> {
	return request('/api/server', {}, fetchImpl);
}

export { request as apiRequest, json as jsonBody };
