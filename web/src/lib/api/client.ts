import type { KaraokeDoc } from '#lib/contracts';
import { normalizeDoc } from '#lib/lyrics/layout.js';
import type {
	CreateJobInput,
	Device,
	ExportInput,
	Job,
	Me,
	Pairing,
	ServerInfo,
	SongSummary
} from './types';

/**
 * An answer from the server that is not a success; `status` 0 means it could not be reached.
 * `code` says why in a stable word (`not_owner`, `too_long`…) the app can explain in its language.
 */
export class ApiError extends Error {
	readonly status: number;
	readonly code: string | null;

	constructor(status: number, message: string, code: string | null = null) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
		this.code = code;
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
		let code: string | null = null;
		try {
			const body = await response.json();
			if (typeof body?.detail === 'string') detail = body.detail;
			if (typeof body?.code === 'string') code = body.code;
		} catch {
			// Not JSON: the status text says enough.
		}
		throw new ApiError(response.status, detail, code);
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
			else {
				const body = xhr.response as { detail?: string; code?: string } | null;
				fail(new ApiError(xhr.status, body?.detail ?? xhr.statusText, body?.code ?? null));
			}
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

/** Runs a failed or cancelled job again with what the server kept of it (no new upload). */
export function retryJob(id: string, fetchImpl?: Fetch): Promise<Job> {
	return request(`/api/jobs/${encodeURIComponent(id)}/retry`, { method: 'POST' }, fetchImpl);
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

// Pairing: a device becomes the owner's with a short code shown on one that already is.

export function getMe(fetchImpl?: Fetch): Promise<Me> {
	return request('/api/me', {}, fetchImpl);
}

export function startPairing(fetchImpl?: Fetch): Promise<Pairing> {
	return request('/api/devices/pairing', { method: 'POST' }, fetchImpl);
}

/** The server answers with a cookie that makes this browser the owner's. */
export function pairDevice(code: string, fetchImpl?: Fetch): Promise<Device> {
	return request('/api/devices/pair', json('POST', { code }), fetchImpl);
}

export function listDevices(fetchImpl?: Fetch): Promise<Device[]> {
	return request('/api/devices', {}, fetchImpl);
}

export function revokeDevice(id: string, fetchImpl?: Fetch): Promise<void> {
	return request(`/api/devices/${encodeURIComponent(id)}`, { method: 'DELETE' }, fetchImpl);
}

export { request as apiRequest, json as jsonBody };
